#!/usr/bin/env python3
"""
竞品监控系统配置文件模板
使用时请复制为 config.py 并填入真实的API密钥
"""

# Gemini AI API配置
GEMINI_API_KEY = "your_gemini_api_key_here"  # 请替换为你的Gemini API密钥
GEMINI_MODEL = "gemini-1.5-flash"

# 飞书Webhook配置
FEISHU_WEBHOOK_URL = "your_feishu_webhook_url_here"  # 请替换为你的飞书Webhook地址

# 应用配置
FLASK_ENV = "production"
DEBUG = False
HOST = "0.0.0.0"
PORT = 8080

# 数据库配置
DATABASE_URL = "sqlite:///competitor_monitor.db" 