#!/usr/bin/env python3
"""
断点续传服务 - 支持数据持久化和历史数据回查
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger

from models.database import db, WebsiteConfig, CrawledPost, SystemLog

class ResumableService:
    """断点续传服务类"""
    
    def __init__(self):
        self.checkpoint_dir = Path("data/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # 每个网站的爬取状态文件
        self.status_file = self.checkpoint_dir / "crawl_status.json"
        
        # 初始化状态文件
        self._init_status_file()
    
    def _init_status_file(self):
        """初始化状态文件"""
        if not self.status_file.exists():
            initial_status = {
                "websites": {},
                "last_global_crawl": None,
                "version": "1.0"
            }
            self._save_status(initial_status)
    
    def _load_status(self) -> Dict[str, Any]:
        """加载爬取状态"""
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载状态文件失败: {e}")
            return {"websites": {}, "last_global_crawl": None, "version": "1.0"}
    
    def _save_status(self, status: Dict[str, Any]):
        """保存爬取状态"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")
    
    def save_crawl_checkpoint(self, website_id: int, checkpoint_data: Dict[str, Any]):
        """保存爬取检查点"""
        try:
            status = self._load_status()
            
            website_key = str(website_id)
            
            # 更新网站爬取状态
            status["websites"][website_key] = {
                "last_crawl_time": datetime.now().isoformat(),
                "last_successful_url": checkpoint_data.get("last_url"),
                "last_post_id": checkpoint_data.get("last_post_id"),
                "total_posts_crawled": checkpoint_data.get("total_posts", 0),
                "last_error": checkpoint_data.get("error"),
                "crawl_session_id": checkpoint_data.get("session_id"),
                "pages_processed": checkpoint_data.get("pages_processed", 0),
                "keywords_found": checkpoint_data.get("keywords_found", [])
            }
            
            # 更新全局状态
            status["last_global_crawl"] = datetime.now().isoformat()
            
            self._save_status(status)
            
            # 保存详细的检查点数据
            self._save_detailed_checkpoint(website_id, checkpoint_data)
            
            logger.info(f"已保存网站 {website_id} 的爬取检查点")
            
        except Exception as e:
            logger.error(f"保存爬取检查点失败: {e}")
    
    def _save_detailed_checkpoint(self, website_id: int, data: Dict[str, Any]):
        """保存详细的检查点数据"""
        checkpoint_file = self.checkpoint_dir / f"website_{website_id}_checkpoint.pkl"
        
        try:
            checkpoint_data = {
                "timestamp": datetime.now().isoformat(),
                "website_id": website_id,
                "data": data,
                "version": "1.0"
            }
            
            with open(checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
                
        except Exception as e:
            logger.error(f"保存详细检查点失败: {e}")
    
    def load_crawl_checkpoint(self, website_id: int) -> Optional[Dict[str, Any]]:
        """加载爬取检查点"""
        try:
            status = self._load_status()
            website_key = str(website_id)
            
            if website_key not in status["websites"]:
                return None
            
            # 获取基本状态
            basic_status = status["websites"][website_key]
            
            # 尝试加载详细检查点
            detailed_checkpoint = self._load_detailed_checkpoint(website_id)
            
            # 合并数据
            checkpoint = {
                **basic_status,
                "detailed_data": detailed_checkpoint
            }
            
            logger.info(f"已加载网站 {website_id} 的爬取检查点")
            return checkpoint
            
        except Exception as e:
            logger.error(f"加载爬取检查点失败: {e}")
            return None
    
    def _load_detailed_checkpoint(self, website_id: int) -> Optional[Dict[str, Any]]:
        """加载详细的检查点数据"""
        checkpoint_file = self.checkpoint_dir / f"website_{website_id}_checkpoint.pkl"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"加载详细检查点失败: {e}")
            return None
    
    def should_resume_crawl(self, website_id: int, max_interval_hours: int = 24) -> bool:
        """判断是否应该断点续传"""
        checkpoint = self.load_crawl_checkpoint(website_id)
        
        if not checkpoint:
            return False
        
        try:
            last_crawl_time = datetime.fromisoformat(checkpoint["last_crawl_time"])
            time_since_last = datetime.now() - last_crawl_time
            
            # 如果距离上次爬取时间不超过设定间隔，且有错误或未完成，则继续爬取
            if time_since_last <= timedelta(hours=max_interval_hours):
                return bool(checkpoint.get("last_error") or 
                          checkpoint.get("pages_processed", 0) > 0)
            
            return False
            
        except Exception as e:
            logger.error(f"判断断点续传失败: {e}")
            return False
    
    def get_resume_position(self, website_id: int) -> Dict[str, Any]:
        """获取续传位置信息"""
        checkpoint = self.load_crawl_checkpoint(website_id)
        
        if not checkpoint:
            return {"start_from_beginning": True}
        
        return {
            "start_from_beginning": False,
            "last_url": checkpoint.get("last_successful_url"),
            "last_post_id": checkpoint.get("last_post_id"),
            "session_id": checkpoint.get("crawl_session_id"),
            "pages_processed": checkpoint.get("pages_processed", 0)
        }
    
    def cleanup_old_checkpoints(self, days_to_keep: int = 7):
        """清理旧的检查点文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            cleaned_count = 0
            for checkpoint_file in self.checkpoint_dir.glob("*.pkl"):
                try:
                    file_mtime = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        checkpoint_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.debug(f"清理检查点文件失败 {checkpoint_file}: {e}")
            
            logger.info(f"清理了 {cleaned_count} 个旧检查点文件")
            
        except Exception as e:
            logger.error(f"清理检查点文件失败: {e}")
    
    def get_crawl_history(self, website_id: Optional[int] = None, 
                         days: int = 30) -> List[Dict[str, Any]]:
        """获取爬取历史记录"""
        try:
            # 从数据库查询历史记录
            query = CrawledPost.query.filter(
                CrawledPost.created_at >= datetime.now() - timedelta(days=days)
            )
            
            if website_id:
                # 通过source_website字段关联
                website = WebsiteConfig.query.get(website_id)
                if website:
                    query = query.filter(CrawledPost.source_website.contains(website.name))
            
            posts = query.order_by(CrawledPost.created_at.desc()).all()
            
            history = []
            for post in posts:
                history.append({
                    "id": post.id,
                    "title": post.title,
                    "source_website": post.source_website,
                    "crawl_time": post.created_at.isoformat(),
                    "is_pushed": post.is_pushed,
                    "keywords": post.matched_keywords,
                    "url": post.post_url
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取爬取历史失败: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取爬取统计信息"""
        try:
            status = self._load_status()
            
            stats = {
                "total_websites": len(status["websites"]),
                "last_global_crawl": status.get("last_global_crawl"),
                "websites_status": []
            }
            
            for website_id, website_status in status["websites"].items():
                stats["websites_status"].append({
                    "website_id": int(website_id),
                    "last_crawl": website_status.get("last_crawl_time"),
                    "total_posts": website_status.get("total_posts_crawled", 0),
                    "has_error": bool(website_status.get("last_error")),
                    "pages_processed": website_status.get("pages_processed", 0)
                })
            
            # 从数据库获取更多统计信息
            total_posts = CrawledPost.query.count()
            pushed_posts = CrawledPost.query.filter_by(is_pushed=True).count()
            
            stats.update({
                "total_posts_in_db": total_posts,
                "total_pushed_posts": pushed_posts,
                "push_rate": (pushed_posts / total_posts * 100) if total_posts > 0 else 0
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def reset_website_checkpoint(self, website_id: int):
        """重置网站的检查点"""
        try:
            status = self._load_status()
            website_key = str(website_id)
            
            # 移除状态记录
            if website_key in status["websites"]:
                del status["websites"][website_key]
                self._save_status(status)
            
            # 删除详细检查点文件
            checkpoint_file = self.checkpoint_dir / f"website_{website_id}_checkpoint.pkl"
            if checkpoint_file.exists():
                checkpoint_file.unlink()
            
            logger.info(f"已重置网站 {website_id} 的检查点")
            
        except Exception as e:
            logger.error(f"重置检查点失败: {e}")
    
    def backup_checkpoints(self, backup_dir: str):
        """备份检查点数据"""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 备份状态文件
            if self.status_file.exists():
                backup_status_file = backup_path / f"crawl_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                self.status_file.copy_to(backup_status_file)
            
            # 备份检查点文件
            for checkpoint_file in self.checkpoint_dir.glob("*.pkl"):
                backup_checkpoint_file = backup_path / f"{checkpoint_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
                checkpoint_file.copy_to(backup_checkpoint_file)
            
            logger.info(f"检查点数据已备份到: {backup_path}")
            
        except Exception as e:
            logger.error(f"备份检查点数据失败: {e}")
    
    def restore_checkpoints(self, backup_file: str):
        """从备份恢复检查点数据"""
        try:
            backup_path = Path(backup_file)
            
            if backup_path.is_file() and backup_path.suffix == '.json':
                # 恢复状态文件
                self.status_file.write_text(backup_path.read_text(encoding='utf-8'))
                logger.info(f"已从 {backup_file} 恢复状态文件")
            
        except Exception as e:
            logger.error(f"恢复检查点数据失败: {e}")

# 全局实例
resumable_service = ResumableService() 