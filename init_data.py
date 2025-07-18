#!/usr/bin/env python3
"""
飞书自动推送机器人 - 初始化数据脚本
"""

from app import create_app
from models.database import db, WebsiteConfig, KeywordConfig, TaskSchedule
from crawlers.crawler_factory import EXAMPLE_CONFIGS
from loguru import logger

def init_sample_data():
    """初始化示例数据"""
    
    # 创建示例网站配置
    websites = [
        {
            "name": "微博",
            "url": "https://wecreat.com/pages/wecreat-lumos?gad_source=1&gad_campaignid=22698328025&gbraid=0AAAAA_5qn7jFtPgF3xoAqigxULk3xVqhW&gclid=Cj0KCQjwss3DBhC3ARIsALdgYxNNByUn9VN1UTH5kPriPtY3xTDMzPICqMPeFrHJaahrANogbC9cItoaAt9pEALw_wcB",
            "crawler_type": "weibo",
            "is_active": True,
            "config_data": {}
        },
        {
            "name": "知乎",
            "url": "https://www.zhihu.com",
            "crawler_type": "generic",
            "is_active": True,
            "config_data": EXAMPLE_CONFIGS["zhihu"]["config_data"]
        }
    ]
    
    for site_data in websites:
        existing_site = WebsiteConfig.query.filter_by(name=site_data["name"]).first()
        if not existing_site:
            website = WebsiteConfig(
                name=site_data["name"],
                url=site_data["url"],
                crawler_type=site_data["crawler_type"],
                is_active=site_data["is_active"],
                config_data=site_data["config_data"]
            )
            db.session.add(website)
            db.session.flush()
            
            # 添加示例关键词
            if site_data["name"] == "微博":
                keywords = [
                    {"keyword": "人工智能", "category": "技术"},
                    {"keyword": "机器学习", "category": "技术"},
                    {"keyword": "区块链", "category": "技术"},
                    {"keyword": "创业", "category": "商业"},
                    {"keyword": "投资", "category": "商业"}
                ]
            elif site_data["name"] == "知乎":
                keywords = [
                    {"keyword": "Python", "category": "编程"},
                    {"keyword": "Flask", "category": "编程"},
                    {"keyword": "爬虫", "category": "技术"},
                    {"keyword": "数据分析", "category": "技术"},
                    {"keyword": "深度学习", "category": "技术"}
                ]
            else:
                keywords = []
            
            for kw_data in keywords:
                keyword = KeywordConfig(
                    keyword=kw_data["keyword"],
                    category=kw_data["category"],
                    website_id=website.id,
                    is_active=True
                )
                db.session.add(keyword)
            
            logger.info(f"创建网站配置: {site_data['name']}")
    
    # 创建默认任务调度
    default_tasks = [
        {
            "name": "每日爬取任务",
            "task_type": "crawler",
            "cron_expression": "0 9 * * *",
            "is_active": True,
            "config_data": {}
        },
        {
            "name": "每日汇总报告",
            "task_type": "summary",
            "cron_expression": "0 18 * * *",
            "is_active": True,
            "config_data": {}
        },
        {
            "name": "数据清理任务",
            "task_type": "cleanup",
            "cron_expression": "0 2 * * *",
            "is_active": True,
            "config_data": {}
        }
    ]
    
    for task_data in default_tasks:
        existing_task = TaskSchedule.query.filter_by(name=task_data["name"]).first()
        if not existing_task:
            task = TaskSchedule(
                name=task_data["name"],
                task_type=task_data["task_type"],
                cron_expression=task_data["cron_expression"],
                is_active=task_data["is_active"],
                config_data=task_data["config_data"]
            )
            db.session.add(task)
            logger.info(f"创建默认任务: {task_data['name']}")
    
    db.session.commit()
    logger.info("示例数据初始化完成")

def main():
    """主函数"""
    app = create_app()
    
    with app.app_context():
        # 创建数据库表
        db.create_all()
        logger.info("数据库表创建完成")
        
        # 初始化示例数据
        init_sample_data()
        
        logger.info("🎉 飞书自动推送机器人初始化完成!")
        logger.info("📝 请按照README.md配置飞书相关参数")
        logger.info("🚀 运行 'python start.py' 启动系统")

if __name__ == '__main__':
    main() 