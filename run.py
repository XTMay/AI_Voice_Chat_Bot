#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import socket
import argparse

def check_dependencies():
    """检查并安装依赖"""
    print("检查依赖包...")
    try:
        import flask
        import flask_cors
        import speech_recognition
        print("✅ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("正在安装依赖...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ 依赖安装完成")
            return True
        except subprocess.CalledProcessError:
            print("❌ 依赖安装失败，请手动运行: pip install -r requirements.txt")
            return False

def create_directories():
    """创建必要的目录"""
    directories = ['uploads', 'templates', '.vscode']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ 创建目录: {directory}")

def find_free_port(start_port=5000):
    """查找可用端口"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def main():
    parser = argparse.ArgumentParser(description='AI语音聊天机器人')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--port', type=int, default=5000, help='指定端口号')
    parser.add_argument('--host', default='0.0.0.0', help='指定主机地址')
    args = parser.parse_args()
    
    print("🚀 启动AI语音聊天机器人系统")
    print("=" * 50)
    
    # 设置环境变量
    os.environ['FLASK_DEBUG'] = '1' if args.debug else '0'
    os.environ['PORT'] = str(args.port)
    os.environ['HOST'] = args.host
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 创建目录
    create_directories()
    
    # 检查必要文件
    required_files = ['qa_data.json', 'app.py', 'templates/index.html']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ 缺少文件: {', '.join(missing_files)}")
        print("请确保所有文件都已创建")
        return
    
    print("✅ 所有文件检查完成")
    
    # 查找可用端口
    port = find_free_port(args.port)
    if port is None:
        print("❌ 无法找到可用端口")
        return
    
    if port != args.port:
        print(f"⚠️  端口{args.port}被占用，使用端口{port}")
        os.environ['PORT'] = str(port)
    
    print("\n🌐 启动Web服务器...")
    print(f"调试模式: {'开启' if args.debug else '关闭'}")
    print(f"访问地址: http://localhost:{port}")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 启动应用
    try:
        from app import app
        app.run(
            debug=args.debug,
            host=args.host,
            port=port,
            use_reloader=args.debug,
            use_debugger=args.debug
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == '__main__':
    main()