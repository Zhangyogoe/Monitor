#!/usr/bin/env python3
"""
飞书自动推送机器人 - Web应用
"""

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import json

from config.config import config
from models.database import (
    db, WebsiteConfig, KeywordConfig, CrawledPost, 
    CrawledComment, PushRecord, TaskSchedule, SystemLog
)
from sqlalchemy import or_
from services.crawler_service import CrawlerService
from services.feishu_service import FeishuService
from services.data_filter_service import DataFilterService
from services.scheduler_service import scheduler_service
from services.resumable_service import resumable_service

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 应用配置
    app.config['SECRET_KEY'] = config.secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database.uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.database.track_modifications
    
    # 初始化扩展
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # 创建服务实例
    crawler_service = CrawlerService()
    feishu_service = FeishuService()
    data_filter = DataFilterService()
    
    @app.route('/')
    def index():
        """首页 - 内容聚合展示"""
        # 获取筛选参数
        source = request.args.get('source', '')
        date_filter = request.args.get('date', 'today')
        keyword = request.args.get('keyword', '')
        
        # 构建查询
        query = CrawledPost.query.filter_by(is_archived=False)
        
        # 按来源筛选
        if source:
            query = query.filter(CrawledPost.source_website == source)
        
        # 按日期筛选
        today = datetime.now().date()
        if date_filter == 'today':
            query = query.filter(CrawledPost.created_at >= datetime.combine(today, datetime.min.time()))
        elif date_filter == 'week':
            week_ago = today - timedelta(days=7)
            query = query.filter(CrawledPost.created_at >= datetime.combine(week_ago, datetime.min.time()))
        elif date_filter == 'month':
            month_ago = today - timedelta(days=30)
            query = query.filter(CrawledPost.created_at >= datetime.combine(month_ago, datetime.min.time()))
        
        # 按关键词搜索
        if keyword:
            query = query.filter(
                or_(
                    CrawledPost.title.contains(keyword),
                    CrawledPost.content.contains(keyword),
                    CrawledPost.ai_summary.contains(keyword)
                )
            )
        
        # 获取内容列表
        posts = query.order_by(CrawledPost.created_at.desc()).limit(20).all()
        
        # 获取统计数据
        today_start = datetime.combine(today, datetime.min.time())
        stats = {
            'today_posts': CrawledPost.query.filter(
                CrawledPost.created_at >= today_start,
                CrawledPost.is_archived == False
            ).count(),
            'total_posts': CrawledPost.query.filter_by(is_archived=False).count(),
            'active_sources': db.session.query(CrawledPost.source_website).distinct().count()
        }
        
        # 获取所有来源列表
        sources = db.session.query(CrawledPost.source_website).distinct().all()
        sources = [s[0] for s in sources if s[0]]
        
        return render_template('dashboard.html', 
                             posts=posts,
                             stats=stats, 
                             sources=sources)
    
    @app.route('/websites')
    def websites():
        """网站管理页面"""
        websites = WebsiteConfig.query.all()
        return render_template('websites.html', websites=websites)
    
    @app.route('/websites/add', methods=['GET', 'POST'])
    def add_website():
        """添加网站"""
        if request.method == 'POST':
            data = request.get_json()
            
            # 根据网站类型确定爬取模式
            website_type = data.get('website_type', '官网')
            crawl_mode = 'time' if website_type == '视频' else 'keyword'
            
            # 处理时间范围
            time_range_start = None
            if data.get('time_range_start'):
                from datetime import datetime
                try:
                    time_range_start = datetime.strptime(data['time_range_start'], '%Y-%m-%d').date()
                except:
                    pass
            
            website = WebsiteConfig(
                name=data['name'],
                url=data['url'],
                website_type=website_type,
                crawler_type=data['crawler_type'],
                crawl_mode=crawl_mode,
                crawl_keywords=data.get('crawl_keywords', ''),
                time_range_start=time_range_start,
                config_data=data.get('config_data', {}),
                is_active=data.get('is_active', True)
            )
            
            try:
                db.session.add(website)
                db.session.commit()
                return jsonify({'success': True, 'message': '网站添加成功'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})
        
        return render_template('add_website.html')
    
    @app.route('/keywords')
    def keywords():
        """关键词管理页面"""
        keywords = KeywordConfig.query.all()
        websites = WebsiteConfig.query.all()
        return render_template('keywords.html', keywords=keywords, websites=websites)
    
    @app.route('/keywords/add', methods=['POST'])
    def add_keyword():
        """添加关键词"""
        data = request.get_json()
        
        keyword = KeywordConfig(
            keyword=data['keyword'],
            category=data.get('category', ''),
            website_id=data['website_id'],
            is_active=data.get('is_active', True)
        )
        
        try:
            db.session.add(keyword)
            db.session.commit()
            return jsonify({'success': True, 'message': '关键词添加成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})
    
    @app.route('/posts')
    def posts():
        """帖子管理页面"""
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        posts = CrawledPost.query.order_by(
            CrawledPost.created_at.desc()
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('posts.html', posts=posts)
    
    @app.route('/tasks')
    def tasks():
        """任务管理页面"""
        tasks = TaskSchedule.query.all()
        return render_template('tasks.html', tasks=tasks)
    
    @app.route('/tasks/add', methods=['POST'])
    def add_task():
        """添加定时任务"""
        data = request.get_json()
        
        task = TaskSchedule(
            name=data['name'],
            task_type=data['task_type'],
            cron_expression=data['cron_expression'],
            config_data=data.get('config_data', {}),
            is_active=data.get('is_active', True)
        )
        
        try:
            db.session.add(task)
            db.session.commit()
            
            # 添加到调度器
            scheduler_service.add_task(task)
            
            return jsonify({'success': True, 'message': '任务添加成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})
    
    @app.route('/crawl/manual', methods=['POST'])
    def manual_crawl():
        """手动触发爬取"""
        try:
            result = crawler_service.crawl_all_websites(manual_trigger=True)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'message': f'爬取失败: {str(e)}'})
    
    @app.route('/push/manual', methods=['POST'])
    def manual_push():
        """手动推送指定帖子"""
        data = request.get_json()
        post_id = data.get('post_id')
        
        try:
            post = CrawledPost.query.get(post_id)
            if not post:
                return jsonify({'success': False, 'message': '帖子不存在'})
            
            # 推送到飞书工作流
            success = feishu_service.push_post_data(post.to_dict(), template='workflow')
            
            if success:
                post.is_pushed = True
                post.push_time = datetime.now()
                db.session.commit()
                
            return jsonify({'success': success, 'message': '推送成功' if success else '推送失败'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'推送失败: {str(e)}'})
    
    @app.route('/logs')
    def logs():
        """日志查看页面"""
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        logs = SystemLog.query.order_by(
            SystemLog.created_at.desc()
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('logs.html', logs=logs)
    
    @app.route('/config')
    def config_page():
        """配置页面"""
        return render_template('config.html', config=config)
    
    @app.route('/config/update', methods=['POST'])
    def update_config():
        """更新配置"""
        data = request.get_json()
        
        try:
            # 这里可以实现配置更新逻辑
            # 例如更新环境变量文件等
            return jsonify({'success': True, 'message': '配置更新成功'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})
    
    @app.route('/api/health')
    def health_check():
        """健康检查接口"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0'
        })
    
    @app.route('/api/stats')
    def api_stats():
        """统计数据API"""
        stats = {
            'posts': {
                'total': CrawledPost.query.count(),
                'today': CrawledPost.query.filter(
                    CrawledPost.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
                ).count(),
                'pushed': CrawledPost.query.filter_by(is_pushed=True).count()
            },
            'websites': {
                'total': WebsiteConfig.query.count(),
                'active': WebsiteConfig.query.filter_by(is_active=True).count()
            },
            'keywords': {
                'total': KeywordConfig.query.count(),
                'active': KeywordConfig.query.filter_by(is_active=True).count()
            },
            'tasks': {
                'total': TaskSchedule.query.count(),
                'active': TaskSchedule.query.filter_by(is_active=True).count()
            }
        }
        return jsonify(stats)
    
    @app.route('/history')
    def crawl_history():
        """爬取历史页面"""
        website_id = request.args.get('website_id', type=int)
        days = request.args.get('days', 30, type=int)
        
        history = resumable_service.get_crawl_history(website_id, days)
        websites = WebsiteConfig.query.all()
        
        return render_template('history.html', 
                             history=history, 
                             websites=websites,
                             selected_website=website_id,
                             days=days)
    
    @app.route('/api/history')
    def api_crawl_history():
        """爬取历史API"""
        website_id = request.args.get('website_id', type=int)
        days = request.args.get('days', 30, type=int)
        
        history = resumable_service.get_crawl_history(website_id, days)
        return jsonify(history)
    
    @app.route('/api/checkpoint/reset', methods=['POST'])
    def reset_checkpoint():
        """重置网站检查点"""
        data = request.get_json()
        website_id = data.get('website_id')
        
        if not website_id:
            return jsonify({'success': False, 'message': '缺少website_id参数'})
        
        try:
            resumable_service.reset_website_checkpoint(website_id)
            return jsonify({'success': True, 'message': '检查点重置成功'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'重置失败: {str(e)}'})
    
    @app.route('/api/checkpoint/status/<int:website_id>')
    def get_checkpoint_status(website_id):
        """获取网站检查点状态"""
        try:
            checkpoint = resumable_service.load_crawl_checkpoint(website_id)
            return jsonify({
                'success': True,
                'checkpoint': checkpoint
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取状态失败: {str(e)}'
            })
    
    @app.route('/api/resumable/stats')
    def resumable_stats():
        """获取断点续传统计信息"""
        try:
            stats = resumable_service.get_statistics()
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)})
    
    @app.route('/data-management')
    def data_management():
        """数据管理页面"""
        stats = resumable_service.get_statistics()
        return render_template('data_management.html', stats=stats)
    
    # 新增：存档相关API
    @app.route('/posts/<int:post_id>/archive', methods=['POST'])
    def archive_post(post_id):
        """存档单个帖子"""
        try:
            post = CrawledPost.query.get(post_id)
            if not post:
                return jsonify({'success': False, 'message': '帖子不存在'})
            
            post.is_archived = True
            post.archive_date = datetime.now().date()
            db.session.commit()
            
            return jsonify({'success': True, 'message': '存档成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'存档失败: {str(e)}'})
    
    @app.route('/posts/<int:post_id>/mark-read', methods=['POST'])
    def mark_post_read(post_id):
        """标记帖子为已读"""
        try:
            post = CrawledPost.query.get(post_id)
            if not post:
                return jsonify({'success': False, 'message': '帖子不存在'})
            
            post.is_read = True
            db.session.commit()
            
            return jsonify({'success': True, 'message': '已标记为已读'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
    
    @app.route('/api/archive-old-posts', methods=['POST'])
    def archive_old_posts():
        """存档7天前的内容"""
        try:
            seven_days_ago = datetime.now() - timedelta(days=7)
            old_posts = CrawledPost.query.filter(
                CrawledPost.created_at < seven_days_ago,
                CrawledPost.is_archived == False
            ).all()
            
            count = 0
            for post in old_posts:
                post.is_archived = True
                post.archive_date = datetime.now().date()
                count += 1
            
            db.session.commit()
            return jsonify({'success': True, 'count': count, 'message': f'成功存档{count}条内容'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'存档失败: {str(e)}'})
    
    @app.route('/archive')
    def archive_page():
        """存档页面"""
        # 获取筛选参数
        date_str = request.args.get('date', '')
        source = request.args.get('source', '')
        
        # 构建查询 - 只显示已存档的内容
        query = CrawledPost.query.filter_by(is_archived=True)
        
        if date_str:
            try:
                archive_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                query = query.filter(CrawledPost.archive_date == archive_date)
            except ValueError:
                pass
        
        if source:
            query = query.filter(CrawledPost.source_website == source)
        
        # 获取已存档的内容
        archived_posts = query.order_by(CrawledPost.archive_date.desc()).limit(50).all()
        
        # 获取存档日期列表
        archive_dates = db.session.query(CrawledPost.archive_date).filter(
            CrawledPost.is_archived == True
        ).distinct().order_by(CrawledPost.archive_date.desc()).all()
        archive_dates = [d[0] for d in archive_dates if d[0]]
        
        # 获取来源列表
        sources = db.session.query(CrawledPost.source_website).filter(
            CrawledPost.is_archived == True
        ).distinct().all()
        sources = [s[0] for s in sources if s[0]]
        
        return render_template('archive.html', 
                             posts=archived_posts,
                             archive_dates=archive_dates,
                             sources=sources,
                             selected_date=date_str,
                             selected_source=source)
    
    @app.route('/posts/<int:post_id>/restore', methods=['POST'])
    def restore_post(post_id):
        """从存档恢复帖子"""
        try:
            post = CrawledPost.query.get(post_id)
            if not post:
                return jsonify({'success': False, 'message': '帖子不存在'})
            
            post.is_archived = False
            post.archive_date = None
            db.session.commit()
            
            return jsonify({'success': True, 'message': '恢复成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'恢复失败: {str(e)}'})
    
    @app.route('/posts/<int:post_id>/delete', methods=['DELETE'])
    def delete_post(post_id):
        """永久删除帖子"""
        try:
            post = CrawledPost.query.get(post_id)
            if not post:
                return jsonify({'success': False, 'message': '帖子不存在'})
            
            db.session.delete(post)
            db.session.commit()
            
            return jsonify({'success': True, 'message': '删除成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})
    
    return app

def init_database():
    """初始化数据库"""
    db.create_all()

def start_scheduler():
    """启动任务调度器"""
    scheduler_service.start()
    
    # 加载数据库中的任务
    tasks = TaskSchedule.query.filter_by(is_active=True).all()
    for task in tasks:
        scheduler_service.add_task(task)

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        init_database()
        start_scheduler()
    app.run(debug=True) 