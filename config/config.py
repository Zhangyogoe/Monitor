import os
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseConfig:
    uri: str = "sqlite:///feishu_bot.db"
    track_modifications: bool = False

@dataclass
class FeishuConfig:
    webhook_url: str = os.getenv("FEISHU_WEBHOOK_URL", "")
    webhook_secret: str = os.getenv("FEISHU_WEBHOOK_SECRET", "")
    
    # 飞书多维表格配置
    app_id: str = os.getenv("FEISHU_APP_ID", "")
    app_secret: str = os.getenv("FEISHU_APP_SECRET", "")
    bitable_token: str = os.getenv("FEISHU_BITABLE_TOKEN", "")
    table_id: str = os.getenv("FEISHU_TABLE_ID", "")

@dataclass
class CrawlerConfig:
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    request_delay: int = 2
    max_retries: int = 3
    timeout: int = 30

@dataclass
class SchedulerConfig:
    timezone: str = "Asia/Shanghai"
    default_schedule: str = "0 9 * * *"  # 每日9点
    max_workers: int = 4

@dataclass
class Config:
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    database: DatabaseConfig = DatabaseConfig()
    feishu: FeishuConfig = FeishuConfig()
    crawler: CrawlerConfig = CrawlerConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    
    # OpenAI API 配置
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Google Gemini API 配置
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    @classmethod
    def load_from_yaml(cls, config_path: str) -> "Config":
        """从YAML文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 这里可以实现更复杂的配置加载逻辑
        return cls()

# 全局配置实例
config = Config() 