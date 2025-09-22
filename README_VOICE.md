# AI 语音聊天机器人

一个支持语音对话的智能聊天机器人，集成了语音识别、文字转语音和本地 Ollama 模型。

## 功能特点

### 🎤 语音交互
- **实时语音录制**：点击录音按钮开始语音对话
- **语音识别**：支持 Web Speech API 和 Whisper 模型双重识别
- **语音回复**：AI 回答可以转换为语音播放

### 💬 文字对话
- **文字输入**：支持直接输入文字与 AI 对话
- **智能回复**：使用本地 Ollama 模型生成回答
- **意图识别**：自动识别用户意图（天气、时间、问候等）

### 📁 文件上传
- **音频文件支持**：支持 .wav, .mp3, .flac, .m4a 格式
- **拖拽上传**：可以直接拖拽音频文件到页面

## 安装和运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 安装和启动 Ollama
```bash
# 安装 Ollama（如果未安装）
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型（默认使用 llama3.2）
ollama pull llama3.2

# 启动 Ollama 服务
ollama serve
```

### 3. 配置环境变量
编辑 `.env` 文件：
```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Flask Configuration
FLASK_DEBUG=1
PORT=5000
HOST=0.0.0.0
```

### 4. 启动应用
```bash
python app.py
```

应用将在 http://localhost:5000 启动

## 使用方法

### 语音对话
1. 点击 "🎤 开始录音" 按钮
2. 对着麦克风说话（浏览器会请求麦克风权限）
3. 点击 "⏹️ 停止录音" 结束录音
4. 系统自动进行语音识别并获取 AI 回答
5. 点击 "🔊 播放语音回答" 听取语音回复

### 文字对话
1. 在文本框中输入问题
2. 点击 "💬 发送文字消息" 或按 Enter 键
3. 查看 AI 回答
4. 可以播放语音回答

### 文件上传
1. 点击上传区域或拖拽音频文件
2. 选择支持的音频格式文件
3. 点击 "🚀 处理文件" 按钮
4. 查看识别结果和 AI 回答

## 技术架构

### 前端
- **HTML5**：现代化响应式界面
- **JavaScript**：
  - MediaRecorder API：录音功能
  - Web Speech API：实时语音识别
  - Speech Synthesis API：文字转语音

### 后端
- **Flask**：Web 框架
- **Whisper**：离线语音识别（备用）
- **Ollama**：本地大语言模型
- **SpeechRecognition**：Google 语音识别（备用）

### 语音处理流程
1. 前端录音 → MediaRecorder 生成音频文件
2. Web Speech API 实时识别（主要方式）
3. 或上传到后端用 Whisper 识别（备用方式）
4. 后端 Ollama 生成智能回答
5. 前端 Speech Synthesis API 播放语音回答

## 支持的意图类型
- **weather**：天气查询
- **time**：时间查询
- **greeting**：问候语
- **music**：音乐相关
- **news**：新闻资讯
- **food**：美食推荐
- **travel**：旅游咨询
- **unknown**：其他类型

## 注意事项

1. **浏览器支持**：需要现代浏览器支持 Web Speech API
2. **麦克风权限**：首次使用需要授权麦克风访问
3. **Ollama 服务**：确保 Ollama 服务正在运行
4. **网络连接**：某些功能需要网络连接（如 Google 语音识别）

## 故障排除

### Ollama 连接失败
- 检查 Ollama 服务是否启动：`ollama serve`
- 确认模型是否下载：`ollama list`
- 检查端口配置：默认 11434

### 麦克风无法访问
- 检查浏览器麦克风权限
- 确保使用 HTTPS 或 localhost
- 尝试刷新页面重新授权

### 语音识别失败
- Web Speech API 需要网络连接
- 如果网络问题，系统会自动回退到 Whisper 模型