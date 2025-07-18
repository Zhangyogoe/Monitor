from datetime import datetime
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

class WebsiteConfig(BaseModel):
    """网站配置表"""
    __tablename__ = 'website_configs'
    
    name = Column(String(100), nullable=False)  # 网站名称
    url = Column(String(500), nullable=False)   # 网站URL
    crawler_type = Column(String(50), nullable=False)  # 爬虫类型（product/weibo/youtube等）
    website_type = Column(String(20), default='官网')  # 网站类型：官网/论坛/视频
    crawl_mode = Column(String(20), default='keyword')  # 爬取模式：keyword/time
    crawl_keywords = Column(Text)  # 关键词（用/分隔，用于官网/论坛）
    time_range_start = Column(Date)  # 时间范围开始（用于视频）
    is_active = Column(Boolean, default=True)   # 是否启用
    config_data = Column(JSON)  # 爬虫配置数据
    
    # 关联的关键词
    keywords = relationship("KeywordConfig", back_populates="website")
    
    def __repr__(self):
        return f'<WebsiteConfig {self.name}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'crawler_type': self.crawler_type,
            'website_type': self.website_type,
            'crawl_mode': self.crawl_mode,
            'crawl_keywords': self.crawl_keywords,
            'time_range_start': self.time_range_start.isoformat() if self.time_range_start else None,
            'is_active': self.is_active,
            'config_data': self.config_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class KeywordConfig(BaseModel):
    """关键词配置表"""
    __tablename__ = 'keyword_configs'
    
    keyword = Column(String(100), nullable=False)  # 关键词
    category = Column(String(100))  # 关键词分类
    website_id = Column(Integer, ForeignKey('website_configs.id'))
    is_active = Column(Boolean, default=True)
    
    # 关联的网站配置
    website = relationship("WebsiteConfig", back_populates="keywords")
    
    def __repr__(self):
        return f'<KeywordConfig {self.keyword}>'

class CrawledPost(BaseModel):
    """爬取的帖子数据"""
    __tablename__ = 'crawled_posts'
    
    title = Column(String(500), nullable=False)  # 标题
    content = Column(Text)  # 内容
    author = Column(String(100))  # 作者
    post_url = Column(String(500))  # 帖子URL
    post_time = Column(DateTime)  # 发帖时间
    likes_count = Column(Integer, default=0)  # 点赞数
    comments_count = Column(Integer, default=0)  # 评论数
    source_website = Column(String(100))  # 来源网站
    matched_keywords = Column(JSON)  # 匹配的关键词
    ai_summary = Column(Text)  # AI生成的内容总结
    
    # 状态标记
    is_read = Column(Boolean, default=False)  # 是否已读
    is_archived = Column(Boolean, default=False)  # 是否已存档
    archive_date = Column(Date)  # 存档日期
    
    # 关联的评论
    comments = relationship("CrawledComment", back_populates="post")
    
    def __repr__(self):
        return f'<CrawledPost {self.title[:50]}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'ai_summary': self.ai_summary,
            'author': self.author,
            'post_url': self.post_url,
            'post_time': self.post_time.isoformat() if self.post_time else None,
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'source_website': self.source_website,
            'matched_keywords': self.matched_keywords,
            'is_read': self.is_read,
            'is_archived': self.is_archived,
            'archive_date': self.archive_date.isoformat() if self.archive_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CrawledComment(BaseModel):
    """爬取的评论数据"""
    __tablename__ = 'crawled_comments'
    
    post_id = Column(Integer, ForeignKey('crawled_posts.id'))
    content = Column(Text)  # 评论内容
    author = Column(String(100))  # 评论作者
    comment_time = Column(DateTime)  # 评论时间
    likes_count = Column(Integer, default=0)  # 点赞数
    
    # 关联的帖子
    post = relationship("CrawledPost", back_populates="comments")
    
    def __repr__(self):
        return f'<CrawledComment {self.content[:50]}>'

class PushRecord(BaseModel):
    """推送记录表"""
    __tablename__ = 'push_records'
    
    post_id = Column(Integer, ForeignKey('crawled_posts.id'))
    push_type = Column(String(50))  # 推送类型（飞书机器人、多维表格等）
    target = Column(String(200))  # 推送目标（群组ID、个人ID等）
    status = Column(String(20))  # 推送状态（成功、失败、待推送）
    message = Column(Text)  # 推送消息/错误信息
    
    def __repr__(self):
        return f'<PushRecord {self.push_type}>'

class TaskSchedule(BaseModel):
    """任务调度表"""
    __tablename__ = 'task_schedules'
    
    name = Column(String(100), nullable=False)  # 任务名称
    task_type = Column(String(50), nullable=False)  # 任务类型
    cron_expression = Column(String(100))  # cron表达式
    is_active = Column(Boolean, default=True)  # 是否启用
    last_run = Column(DateTime)  # 上次运行时间
    next_run = Column(DateTime)  # 下次运行时间
    config_data = Column(JSON)  # 任务配置数据
    
    def __repr__(self):
        return f'<TaskSchedule {self.name}>'

class SystemLog(BaseModel):
    """系统日志表"""
    __tablename__ = 'system_logs'
    
    level = Column(String(20))  # 日志级别
    module = Column(String(100))  # 模块名称
    message = Column(Text)  # 日志消息
    extra_data = Column(JSON)  # 额外数据
    
    def __repr__(self):
        return f'<SystemLog {self.level}>' 