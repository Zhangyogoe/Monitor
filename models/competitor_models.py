#!/usr/bin/env python3
"""
竞品动态监控 - 数据库模型
简化版，专注于竞品监控需求
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class BaseModel(db.Model):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MonitorConfig(BaseModel):
    """监控配置表 - 支持两种配置模式"""
    __tablename__ = 'monitor_configs'
    
    name = Column(String(100), nullable=False)  # 配置名称
    config_type = Column(String(20), nullable=False)  # 配置类型：account/keyword
    
    # 配置1：账号链接模式
    account_url = Column(String(500))  # 指定账号链接
    
    # 配置2：关键词模式  
    website_url = Column(String(500))  # 网站链接
    keywords = Column(Text)  # 关键词（用/分隔）
    
    is_active = Column(Boolean, default=True)  # 是否启用
    last_crawl_time = Column(DateTime)  # 上次爬取时间
    
    def __repr__(self):
        return f'<MonitorConfig {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'config_type': self.config_type,
            'account_url': self.account_url,
            'website_url': self.website_url,
            'keywords': self.keywords,
            'is_active': self.is_active,
            'last_crawl_time': self.last_crawl_time.isoformat() if self.last_crawl_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CrawlSession(BaseModel):
    """爬取会话表 - 每次爬取的汇总结果"""
    __tablename__ = 'crawl_sessions'
    
    session_name = Column(String(100), nullable=False)  # 会话名称（如：2025-07-17 每日爬取）
    crawl_time = Column(DateTime, nullable=False)  # 爬取时间
    ai_summary = Column(Text)  # AI汇总内容
    total_posts = Column(Integer, default=0)  # 总帖子数
    processed_posts = Column(Integer, default=0)  # 处理的帖子数
    status = Column(String(20), default='processing')  # 状态：processing/completed/failed
    
    def __repr__(self):
        return f'<CrawlSession {self.session_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_name': self.session_name,
            'crawl_time': self.crawl_time.isoformat() if self.crawl_time else None,
            'ai_summary': self.ai_summary,
            'total_posts': self.total_posts,
            'processed_posts': self.processed_posts,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CompetitorPost(BaseModel):
    """竞品帖子表 - 原始爬取数据"""
    __tablename__ = 'competitor_posts'
    
    session_id = Column(Integer, ForeignKey('crawl_sessions.id'))  # 关联爬取会话
    monitor_config_id = Column(Integer, ForeignKey('monitor_configs.id'))  # 关联监控配置
    
    title = Column(String(500), nullable=False)  # 标题
    content = Column(Text)  # 内容
    author = Column(String(100))  # 作者
    post_url = Column(String(500))  # 帖子URL
    post_time = Column(DateTime)  # 发帖时间
    likes_count = Column(Integer, default=0)  # 点赞数
    comments_count = Column(Integer, default=0)  # 评论数
    platform = Column(String(50))  # 平台（Kickstarter/Reddit等）
    
    # 状态标记
    is_processed = Column(Boolean, default=False)  # 是否已处理
    is_duplicate = Column(Boolean, default=False)  # 是否重复
    brand_category = Column(String(100))  # 品牌分类（AI识别）
    
    # 关联关系
    session = relationship("CrawlSession", backref="posts")
    monitor_config = relationship("MonitorConfig", backref="posts")
    
    def __repr__(self):
        return f'<CompetitorPost {self.title[:50]}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'post_url': self.post_url,
            'post_time': self.post_time.isoformat() if self.post_time else None,
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'platform': self.platform,
            'is_processed': self.is_processed,
            'brand_category': self.brand_category,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SystemSettings(BaseModel):
    """系统设置表"""
    __tablename__ = 'system_settings'
    
    key = Column(String(50), nullable=False, unique=True)  # 设置键
    value = Column(Text)  # 设置值
    description = Column(String(200))  # 描述
    
    def __repr__(self):
        return f'<SystemSettings {self.key}>' 