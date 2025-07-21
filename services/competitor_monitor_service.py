#!/usr/bin/env python3
"""
竞品监控核心服务
整合爬虫、AI分析、数据存储等功能
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from models.competitor_models import db, MonitorConfig, CrawlSession, CompetitorPost
from crawlers.competitor_crawler import CompetitorCrawler
from services.competitor_ai_service import CompetitorAIService
from loguru import logger
import hashlib

class CompetitorMonitorService:
    """竞品监控核心服务"""
    
    def __init__(self):
        self.crawler = CompetitorCrawler()
        self.ai_service = CompetitorAIService()
    
    def execute_crawl_session(self, session_name: str = None) -> Dict[str, Any]:
        """执行一次完整的爬取会话"""
        if not session_name:
            session_name = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} 竞品监控"
        
        logger.info(f"🚀 开始竞品监控会话: {session_name}")
        
        # 创建爬取会话
        session = CrawlSession(
            session_name=session_name,
            crawl_time=datetime.now(),
            status='processing'
        )
        db.session.add(session)
        db.session.commit()
        
        try:
            # 获取所有活跃的监控配置
            configs = MonitorConfig.query.filter_by(is_active=True).all()
            
            if not configs:
                logger.warning("⚠️ 没有找到活跃的监控配置")
                session.status = 'completed'
                session.ai_summary = "没有配置监控源"
                db.session.commit()
                return {"success": False, "message": "没有配置监控源"}
            
            all_posts = []
            total_posts = 0
            
            # 遍历每个监控配置
            for config in configs:
                logger.info(f"📡 爬取配置: {config.name}")
                
                try:
                    # 爬取数据
                    posts = self.crawler.crawl_by_config(config.to_dict())
                    
                    # 去重和保存
                    unique_posts = self._deduplicate_posts(posts, config.id, session.id)
                    
                    all_posts.extend(unique_posts)
                    total_posts += len(posts)
                    
                    # 更新配置的最后爬取时间
                    config.last_crawl_time = datetime.now()
                    
                    logger.info(f"✅ {config.name}: 爬取 {len(posts)} 条，去重后 {len(unique_posts)} 条")
                    
                except Exception as e:
                    logger.error(f"❌ 爬取配置失败 {config.name}: {e}")
                    continue
            
            # 更新会话统计
            session.total_posts = total_posts
            session.processed_posts = len(all_posts)
            
            # AI分析
            if all_posts:
                logger.info("🤖 开始AI分析...")
                post_dicts = [post.to_dict() for post in all_posts]
                ai_summary = self.ai_service.analyze_posts(post_dicts)
                session.ai_summary = ai_summary
            else:
                session.ai_summary = "24小时内暂无新的竞品动态"
            
            session.status = 'completed'
            db.session.commit()
            
            logger.info(f"🎉 竞品监控完成: 处理 {len(all_posts)} 条有效数据")
            
            return {
                "success": True,
                "session_id": session.id,
                "total_posts": total_posts,
                "processed_posts": len(all_posts),
                "summary": session.ai_summary
            }
            
        except Exception as e:
            logger.error(f"❌ 竞品监控会话失败: {e}")
            session.status = 'failed'
            session.ai_summary = f"监控失败: {str(e)}"
            db.session.commit()
            
            return {
                "success": False,
                "message": str(e),
                "session_id": session.id
            }
        
        finally:
            # 清理资源
            self.crawler.close()
    
    def _deduplicate_posts(self, posts: List, config_id: int, session_id: int) -> List[CompetitorPost]:
        """去重并保存帖子"""
        unique_posts = []
        
        for post_data in posts:
            # 生成内容hash用于去重
            content_hash = self._generate_post_hash(
                post_data.title,
                post_data.post_url,
                post_data.author
            )
            
            # 检查是否已存在
            existing = CompetitorPost.query.filter_by(
                title=post_data.title,
                post_url=post_data.post_url
            ).first()
            
            if existing:
                existing.is_duplicate = True
                logger.debug(f"发现重复帖子: {post_data.title[:50]}")
                continue
            
            # 创建新记录
            new_post = CompetitorPost(
                session_id=session_id,
                monitor_config_id=config_id,
                title=post_data.title,
                content=post_data.content,
                author=post_data.author,
                post_url=post_data.post_url,
                post_time=post_data.post_time,
                likes_count=post_data.likes_count,
                comments_count=post_data.comments_count,
                platform=post_data.platform,
                is_processed=True
            )
            
            db.session.add(new_post)
            unique_posts.append(new_post)
        
        db.session.commit()
        return unique_posts
    
    def _generate_post_hash(self, title: str, url: str, author: str) -> str:
        """生成帖子内容的hash值"""
        content = f"{title}|{url}|{author}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的爬取会话"""
        sessions = CrawlSession.query.order_by(
            CrawlSession.crawl_time.desc()
        ).limit(limit).all()
        
        return [session.to_dict() for session in sessions]
    
    def get_session_details(self, session_id: int) -> Optional[Dict[str, Any]]:
        """获取会话详情"""
        session = CrawlSession.query.get(session_id)
        if not session:
            return None
        
        session_data = session.to_dict()
        
        # 获取关联的帖子
        posts = CompetitorPost.query.filter_by(session_id=session_id).all()
        session_data['posts'] = [post.to_dict() for post in posts]
        
        return session_data
    
    def add_monitor_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加监控配置"""
        try:
            config = MonitorConfig(
                name=config_data['name'],
                config_type=config_data['config_type'],
                account_url=config_data.get('account_url'),
                website_url=config_data.get('website_url'),
                keywords=config_data.get('keywords'),
                webpage_url=config_data.get('webpage_url'),
                content_hash=None,  # 网页更新模式初始化为None，首次爬取时设置
                last_content=None,  # 上次内容初始化为None
                is_active=True
            )
            
            db.session.add(config)
            db.session.commit()
            
            logger.info(f"✅ 添加监控配置: {config.name}")
            
            return {
                "success": True,
                "config_id": config.id,
                "message": "监控配置添加成功"
            }
            
        except Exception as e:
            logger.error(f"❌ 添加监控配置失败: {e}")
            db.session.rollback()
            
            return {
                "success": False,
                "message": str(e)
            }
    
    def update_monitor_config(self, config_id: int, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新监控配置"""
        try:
            config = MonitorConfig.query.get(config_id)
            if not config:
                return {"success": False, "message": "配置不存在"}
            
            config.name = config_data.get('name', config.name)
            config.config_type = config_data.get('config_type', config.config_type)
            config.account_url = config_data.get('account_url', config.account_url)
            config.website_url = config_data.get('website_url', config.website_url)
            config.keywords = config_data.get('keywords', config.keywords)
            config.is_active = config_data.get('is_active', config.is_active)
            
            db.session.commit()
            
            logger.info(f"✅ 更新监控配置: {config.name}")
            
            return {
                "success": True,
                "message": "监控配置更新成功"
            }
            
        except Exception as e:
            logger.error(f"❌ 更新监控配置失败: {e}")
            db.session.rollback()
            
            return {
                "success": False,
                "message": str(e)
            }
    
    def delete_monitor_config(self, config_id: int) -> Dict[str, Any]:
        """删除监控配置"""
        try:
            config = MonitorConfig.query.get(config_id)
            if not config:
                return {"success": False, "message": "配置不存在"}
            
            db.session.delete(config)
            db.session.commit()
            
            logger.info(f"✅ 删除监控配置: {config.name}")
            
            return {
                "success": True,
                "message": "监控配置删除成功"
            }
            
        except Exception as e:
            logger.error(f"❌ 删除监控配置失败: {e}")
            db.session.rollback()
            
            return {
                "success": False,
                "message": str(e)
            }
    
    def get_monitor_configs(self) -> List[Dict[str, Any]]:
        """获取所有监控配置"""
        configs = MonitorConfig.query.order_by(MonitorConfig.created_at.desc()).all()
        return [config.to_dict() for config in configs]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_configs = MonitorConfig.query.count()
        active_configs = MonitorConfig.query.filter_by(is_active=True).count()
        total_sessions = CrawlSession.query.count()
        total_posts = CompetitorPost.query.count()
        
        # 最近24小时的数据
        yesterday = datetime.now() - timedelta(days=1)
        recent_sessions = CrawlSession.query.filter(
            CrawlSession.crawl_time >= yesterday
        ).count()
        recent_posts = CompetitorPost.query.filter(
            CompetitorPost.created_at >= yesterday
        ).count()
        
        return {
            "total_configs": total_configs,
            "active_configs": active_configs,
            "total_sessions": total_sessions,
            "total_posts": total_posts,
            "recent_sessions": recent_sessions,
            "recent_posts": recent_posts,
            "ai_status": self.ai_service.get_summary_status()
        } 