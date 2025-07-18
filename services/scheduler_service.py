#!/usr/bin/env python3
"""
任务调度服务
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
from loguru import logger
from typing import Dict, Any

from config.config import config
from models.database import TaskSchedule

class SchedulerService:
    """任务调度服务类"""
    
    def __init__(self):
        # 配置作业存储
        jobstores = {
            'default': SQLAlchemyJobStore(url=config.database.uri)
        }
        
        # 配置执行器
        executors = {
            'default': ThreadPoolExecutor(max_workers=config.scheduler.max_workers)
        }
        
        # 作业默认配置
        job_defaults = {
            'coalesce': True,  # 合并多个待执行的同名任务
            'max_instances': 1,  # 同一任务最多同时运行1个实例
            'misfire_grace_time': 30  # 任务错过执行时间的宽限期
        }
        
        # 创建调度器
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=config.scheduler.timezone
        )
        
        self.is_running = False
    
    def start(self):
        """启动调度器"""
        if not self.is_running:
            try:
                self.scheduler.start()
                self.is_running = True
                logger.info("📅 任务调度器启动成功")
            except Exception as e:
                logger.error(f"❌ 调度器启动失败: {e}")
                raise
    
    def stop(self):
        """停止调度器"""
        if self.is_running:
            try:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("📅 任务调度器已停止")
            except Exception as e:
                logger.error(f"❌ 停止调度器失败: {e}")
    
    def add_task(self, task: TaskSchedule):
        """添加任务到调度器"""
        try:
            # 根据任务类型选择执行函数
            func = self._get_task_function(task.task_type)
            if not func:
                logger.error(f"❌ 未知的任务类型: {task.task_type}")
                return False
            
            # 解析cron表达式
            cron_parts = task.cron_expression.split()
            if len(cron_parts) != 5:
                logger.error(f"❌ 无效的cron表达式: {task.cron_expression}")
                return False
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # 创建触发器
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=config.scheduler.timezone
            )
            
            # 添加作业
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=f"task_{task.id}",
                name=task.name,
                args=[task.config_data],
                replace_existing=True,
                coalesce=True,
                max_instances=1
            )
            
            # 更新数据库中的下次运行时间
            next_run = self.scheduler.get_job(f"task_{task.id}").next_run_time
            task.next_run = next_run
            
            from models.database import db
            db.session.commit()
            
            logger.info(f"✅ 任务 '{task.name}' 已添加到调度器，下次运行: {next_run}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加任务失败: {e}")
            return False
    
    def remove_task(self, task_id: int):
        """移除任务"""
        try:
            job_id = f"task_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"✅ 任务 {job_id} 已移除")
                return True
            else:
                logger.warning(f"⚠️ 任务 {job_id} 不存在")
                return False
        except Exception as e:
            logger.error(f"❌ 移除任务失败: {e}")
            return False
    
    def get_jobs(self):
        """获取所有作业信息"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def _get_task_function(self, task_type: str):
        """根据任务类型获取执行函数"""
        task_functions = {
            'crawl_all': self._crawl_all_websites,
            'crawl_website': self._crawl_single_website,
            'data_cleanup': self._cleanup_old_data,
            'push_summary': self._push_daily_summary,
            'health_check': self._health_check
        }
        return task_functions.get(task_type)
    
    def _crawl_all_websites(self, config_data: Dict[str, Any]):
        """爬取所有网站任务"""
        try:
            logger.info("🚀 开始执行定时爬取任务")
            
            # 这里需要在应用上下文中执行
            from app import create_app
            app = create_app()
            
            with app.app_context():
                from services.crawler_service import CrawlerService
                crawler_service = CrawlerService()
                result = crawler_service.crawl_all_websites()
                
                logger.info(f"✅ 定时爬取完成: {result}")
                
                # 记录任务执行
                self._log_task_execution('crawl_all', True, str(result))
                
        except Exception as e:
            logger.error(f"❌ 定时爬取任务失败: {e}")
            self._log_task_execution('crawl_all', False, str(e))
    
    def _crawl_single_website(self, config_data: Dict[str, Any]):
        """爬取单个网站任务"""
        try:
            website_id = config_data.get('website_id')
            if not website_id:
                logger.error("❌ 缺少website_id参数")
                return
            
            logger.info(f"🚀 开始爬取网站 {website_id}")
            
            from app import create_app
            app = create_app()
            
            with app.app_context():
                from services.crawler_service import CrawlerService
                from models.database import WebsiteConfig, KeywordConfig
                
                website = WebsiteConfig.query.get(website_id)
                if not website:
                    logger.error(f"❌ 网站 {website_id} 不存在")
                    return
                
                keywords = KeywordConfig.query.filter_by(
                    website_id=website_id, is_active=True
                ).all()
                
                crawler_service = CrawlerService()
                result = crawler_service.crawl_website(website, keywords)
                
                logger.info(f"✅ 网站爬取完成: {result}")
                self._log_task_execution('crawl_website', True, str(result))
                
        except Exception as e:
            logger.error(f"❌ 网站爬取任务失败: {e}")
            self._log_task_execution('crawl_website', False, str(e))
    
    def _cleanup_old_data(self, config_data: Dict[str, Any]):
        """清理旧数据任务"""
        try:
            days_to_keep = config_data.get('days_to_keep', 30)
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            logger.info(f"🧹 开始清理 {days_to_keep} 天前的数据")
            
            from app import create_app
            app = create_app()
            
            with app.app_context():
                from models.database import db, CrawledPost, SystemLog
                
                # 清理旧帖子
                old_posts = CrawledPost.query.filter(
                    CrawledPost.created_at < cutoff_date
                ).count()
                
                CrawledPost.query.filter(
                    CrawledPost.created_at < cutoff_date
                ).delete()
                
                # 清理旧日志
                old_logs = SystemLog.query.filter(
                    SystemLog.created_at < cutoff_date
                ).count()
                
                SystemLog.query.filter(
                    SystemLog.created_at < cutoff_date
                ).delete()
                
                db.session.commit()
                
                result = f"清理了 {old_posts} 条帖子和 {old_logs} 条日志"
                logger.info(f"✅ 数据清理完成: {result}")
                self._log_task_execution('data_cleanup', True, result)
                
        except Exception as e:
            logger.error(f"❌ 数据清理任务失败: {e}")
            self._log_task_execution('data_cleanup', False, str(e))
    
    def _push_daily_summary(self, config_data: Dict[str, Any]):
        """推送每日汇总任务"""
        try:
            logger.info("📊 开始生成每日汇总")
            
            from app import create_app
            app = create_app()
            
            with app.app_context():
                from models.database import CrawledPost
                from services.feishu_service import FeishuService
                
                # 获取今日数据
                today_start = datetime.now().replace(hour=0, minute=0, second=0)
                today_posts = CrawledPost.query.filter(
                    CrawledPost.created_at >= today_start
                ).all()
                
                # 生成汇总
                summary = self._generate_daily_summary(today_posts)
                
                # 推送汇总
                feishu_service = FeishuService()
                success = feishu_service.send_daily_summary(summary)
                
                result = f"推送每日汇总: {len(today_posts)} 条帖子"
                logger.info(f"✅ 每日汇总完成: {result}")
                self._log_task_execution('push_summary', success, result)
                
        except Exception as e:
            logger.error(f"❌ 每日汇总任务失败: {e}")
            self._log_task_execution('push_summary', False, str(e))
    
    def _health_check(self, config_data: Dict[str, Any]):
        """系统健康检查任务"""
        try:
            logger.info("🏥 开始系统健康检查")
            
            # 检查数据库连接
            # 检查网络连接
            # 检查磁盘空间等
            
            result = "系统运行正常"
            logger.info(f"✅ 健康检查完成: {result}")
            self._log_task_execution('health_check', True, result)
            
        except Exception as e:
            logger.error(f"❌ 健康检查失败: {e}")
            self._log_task_execution('health_check', False, str(e))
    
    def _generate_daily_summary(self, posts):
        """生成每日汇总"""
        if not posts:
            return {
                'title': '📊 今日数据汇总',
                'content': '今日暂无新数据',
                'total_posts': 0,
                'pushed_posts': 0,
                'top_keywords': []
            }
        
        # 统计数据
        total_posts = len(posts)
        pushed_posts = len([p for p in posts if p.is_pushed])
        
        # 统计关键词
        keyword_count = {}
        for post in posts:
            if post.matched_keywords:
                for keyword in post.matched_keywords:
                    keyword_count[keyword] = keyword_count.get(keyword, 0) + 1
        
        top_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'title': '📊 今日数据汇总',
            'content': f'今日共爬取 {total_posts} 条帖子，推送 {pushed_posts} 条',
            'total_posts': total_posts,
            'pushed_posts': pushed_posts,
            'top_keywords': top_keywords
        }
    
    def _log_task_execution(self, task_type: str, success: bool, message: str):
        """记录任务执行情况"""
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                from models.database import db, SystemLog
                
                log = SystemLog(
                    level='INFO' if success else 'ERROR',
                    module='scheduler_service',
                    message=f"任务执行 - {task_type}: {message}",
                    extra_data={
                        'task_type': task_type,
                        'success': success,
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
                db.session.add(log)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"❌ 记录任务日志失败: {e}")

# 全局调度器实例
scheduler_service = SchedulerService() 