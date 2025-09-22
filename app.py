from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import speech_recognition as sr
import json
import os
from werkzeug.utils import secure_filename
import tempfile
import whisper
import socket
from dotenv import load_dotenv
import opencc
import openai
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# 配置上传文件
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'webm'}
# Configure OpenAI API key
openai.api_key = os.environ.get('OPENAI_API_KEY')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 全局Whisper模型
whisper_model = None

# Ollama配置
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')




# 在文件顶部添加转换器
cc = opencc.OpenCC('t2s')  # 繁体转简体

def load_whisper_model():
    global whisper_model
    if whisper_model is None:
        print("正在加载Whisper模型...")
        whisper_model = whisper.load_model("base")
        print("Whisper模型加载完成")
    return whisper_model

# 加载知识库
def load_qa_data():
    try:
        with open('qa_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"unknown": "知识库文件未找到。"}
    except json.JSONDecodeError:
        return {"unknown": "知识库文件格式错误。"}

# 检查文件扩展名
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 查找可用端口
def find_free_port(start_port=5000):
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def speech_to_text(audio_file_path):
    try:
        # 使用Whisper进行语音识别，设置为简体中文
        model = load_whisper_model()
        result = model.transcribe(audio_file_path, language='zh')
        text = result["text"].strip()
        # 强制转换为简体中文
        simplified_text = cc.convert(text)
        return simplified_text
    except Exception as e:
        print(f"Whisper识别失败: {e}")
        
        # 回退到Google语音识别（不需要PyAudio）
        try:
            recognizer = sr.Recognizer()
            
            # 直接使用音频文件（SpeechRecognition支持多种格式）
            with sr.AudioFile(audio_file_path) as source:
                audio = recognizer.record(source)
                # 设置为简体中文
                text = recognizer.recognize_google(audio, language='zh-CN')
                # 确保是简体中文
                simplified_text = cc.convert(text)
                return simplified_text
        except sr.UnknownValueError:
            return "无法识别语音内容"
        except sr.RequestError as e:
            return f"语音识别服务错误: {e}"
        except Exception as e:
            return f"处理音频文件时出错: {e}"

# LLM-based intent detection using Ollama
def detect_intent_LLM(text):
    try:
        # Define the available intent categories
        intent_categories = [
            'weather', 'time', 'greeting', 'music', 'news', 'food', 'travel', 'unknown'
        ]

        # Create the prompt for Ollama
        prompt = f"""你是一个意图识别专家。请分析用户的输入文本，并从以下类别中选择最符合用户当前主要目的的一个意图类别：

意图类别：
- weather: 天气相关询问（天气、温度、下雨、晴天等）
- time: 时间相关询问（几点、现在时间等）
- greeting: 问候语（你好、早上好等）
- music: 音乐相关（播放音乐、歌曲等）
- news: 新闻资讯相关
- food: 美食、餐厅、吃饭相关
- travel: 旅游、景点相关
- unknown: 以上都不匹配或意图不明确

注意：
- 如果句子包含多个主题，请判断用户最有可能希望得到回答的部分。
- 忽略天气/音乐等背景叙述，专注于可能触发动作的问题（例如「不知道吃什么」→ food）。

请只返回最相关的一个意图类别名称，例如："food"

用户输入："{text}"

回答："""

        # Call Ollama API
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "max_tokens": 10
            }
        }

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            predicted_intent = result.get('response', '').strip().lower()

            # Clean up the response - sometimes Ollama returns extra text
            for category in intent_categories:
                if category in predicted_intent:
                    return category

            # If no direct match, fallback to keyword-based detection
            print(f"Ollama返回了无效意图: {predicted_intent}，回退到关键词匹配")
            return detect_intent(text)
        else:
            print(f"Ollama API错误: {response.status_code}")
            return detect_intent(text)

    except requests.exceptions.ConnectionError:
        print("无法连接到Ollama服务，使用关键词匹配")
        return detect_intent(text)
    except Exception as e:
        print(f"Ollama意图识别失败: {e}")
        # Fallback to the original keyword-based method
        return detect_intent(text)

# 意图识别（基于关键词匹配）
def detect_intent(text):
    text = text.lower()
    
    # 定义关键词映射
    intent_keywords = {
        'weather': ['天气', '温度', '下雨', '晴天', '阴天', '雪'],
        'time': ['时间', '几点', '现在', '钟点'],
        'greeting': ['你好', '您好', 'hi', 'hello', '早上好', '下午好', '晚上好'],
        'music': ['音乐', '歌曲', '播放', '听歌'],
        'news': ['新闻', '消息', '资讯', '头条'],
        'food': ['吃', '美食', '菜', '饭', '餐厅', '推荐'],
        'travel': ['旅游', '景点', '旅行', '去哪', '玩']
    }
    
    # 匹配关键词
    for intent, keywords in intent_keywords.items():
        for keyword in keywords:
            if keyword in text:
                return intent
    
    return 'unknown'

# 使用Ollama生成智能回答
def generate_ollama_response(text, intent):
    try:
        # 根据意图构建提示词
        if intent == 'weather':
            prompt = f"请用中文回答。用户询问天气相关问题：{text}。请提供一个友好、有帮助的回答。"
        elif intent == 'time':
            prompt = f"请用中文回答。用户询问时间相关问题：{text}。请提供当前时间信息或相关帮助。"
        elif intent == 'greeting':
            prompt = f"请用中文回答。用户打招呼：{text}。请给出一个友好的回应。"
        elif intent == 'food':
            prompt = f"请用中文回答。用户询问美食相关问题：{text}。请提供有用的美食建议或推荐。"
        elif intent == 'travel':
            prompt = f"请用中文回答。用户询问旅游相关问题：{text}。请提供旅游建议或信息。"
        elif intent == 'music':
            prompt = f"请用中文回答。用户询问音乐相关问题：{text}。请提供音乐相关的回答。"
        elif intent == 'news':
            prompt = f"请用中文回答。用户询问新闻相关问题：{text}。请提供新闻或资讯相关的回答。"
        else:
            prompt = f"请用中文回答。用户说：{text}。请提供一个有帮助、友好的回答。"

        # 调用Ollama API
        system_prompt = "你是一个中文助手，必须用中文回答用户的问题。"
        full_prompt = f"{system_prompt}\n\n{prompt}\n\n请用中文回答："

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 100
            }
        }

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            return result.get('response', '抱歉，我无法生成回答。').strip()
        else:
            print(f"Ollama API错误: {response.status_code}")
            return get_fallback_answer(intent)

    except requests.exceptions.ConnectionError:
        print("无法连接到Ollama服务，请确保Ollama正在运行")
        return get_fallback_answer(intent)
    except Exception as e:
        print(f"Ollama调用失败: {e}")
        return get_fallback_answer(intent)

# 获取回答（保留原有逻辑作为后备）
def get_fallback_answer(intent):
    fallback_answers = {
        'weather': '今天天气不错！不过我无法获取实时天气信息，建议你查看天气应用。',
        'time': '我无法获取当前时间，请查看你的设备时间。',
        'greeting': '你好！很高兴和你聊天！',
        'music': '我很喜欢音乐！你喜欢什么类型的音乐呢？',
        'news': '我无法获取最新新闻，建议你查看新闻应用或网站。',
        'food': '美食真是太棒了！你想了解什么类型的美食呢？',
        'travel': '旅游是很棒的体验！你想去哪里旅游呢？',
        'unknown': '抱歉，我不太明白你的意思。你可以尝试询问天气、时间、音乐、美食或旅游相关的问题。'
    }
    return fallback_answers.get(intent, fallback_answers['unknown'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # 语音转文字
            recognized_text = speech_to_text(filepath)
            
            # 使用关键字进行意图识别
            # intent = detect_intent(recognized_text)
            # 使用LLM进行意图识别
            intent = detect_intent_LLM(recognized_text)
            
            # 使用Ollama生成智能回答
            answer = generate_ollama_response(recognized_text, intent)
            
            # 清理上传的文件
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'recognized_text': recognized_text,
                'intent': intent,
                'answer': answer
            })
            
        except Exception as e:
            # 清理上传的文件
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'处理文件时出错: {str(e)}'}), 500
    
    return jsonify({'error': '不支持的文件格式'}), 400

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()

        if not text:
            return jsonify({'error': '文本内容不能为空'}), 400

        # 使用LLM进行意图识别
        intent = detect_intent_LLM(text)

        # 使用Ollama生成智能回答
        answer = generate_ollama_response(text, intent)

        return jsonify({
            'success': True,
            'recognized_text': text,
            'intent': intent,
            'answer': answer
        })

    except Exception as e:
        return jsonify({'error': f'处理请求时出错: {str(e)}'}), 500

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': '服务器运行正常'})

if __name__ == '__main__':
    # Debug configuration with environment variables
    debug_mode = os.environ.get('FLASK_DEBUG', '1').lower() in ['1', 'true', 'yes']
    preferred_port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Find available port
    port = find_free_port(preferred_port)
    if port is None:
        print("❌ 无法找到可用端口")
        exit(1)
    
    if port != preferred_port:
        print(f"⚠️  端口{preferred_port}被占用，使用端口{port}")
    
    print("启动AI语音聊天机器人服务...")
    print(f"Debug模式: {'开启' if debug_mode else '关闭'}")
    print(f"访问地址: http://localhost:{port}")
    
    app.run(
        debug=debug_mode,
        host=host,
        port=port,
        use_reloader=debug_mode,
        use_debugger=debug_mode
    )
