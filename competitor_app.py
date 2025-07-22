#!/usr/bin/env python3
"""
竞品动态推送 - 简化版Flask应用
专注于竞品监控需求
"""

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_apscheduler import APScheduler
from models.competitor_models import db, MonitorConfig, CrawlSession, CompetitorPost, SystemSettings
from services.competitor_monitor_service import CompetitorMonitorService
from loguru import logger
from datetime import datetime

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 配置
app.config['SECRET_KEY'] = 'competitor-monitor-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///competitor_monitor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 调度器配置
app.config['SCHEDULER_API_ENABLED'] = True

# 初始化扩展
db.init_app(app)
scheduler = APScheduler()

# 创建监控服务实例
monitor_service = CompetitorMonitorService()

@app.route('/')
def index():
    """主页 - 显示最新的监控结果"""
    try:
        # 获取最近的爬取会话
        recent_sessions = monitor_service.get_recent_sessions(limit=5)
        
        # 获取统计信息
        stats = monitor_service.get_statistics()
        
        return render_template('competitor_index.html', 
                             sessions=recent_sessions,
                             stats=stats)
    except Exception as e:
        logger.error(f"首页加载失败: {e}")
        return render_template('competitor_index.html', 
                             sessions=[],
                             stats={},
                             error=str(e))

@app.route('/config')
def config_page():
    """监控配置页面"""
    try:
        configs = monitor_service.get_monitor_configs()
        return render_template('competitor_config.html', configs=configs)
    except Exception as e:
        logger.error(f"配置页面加载失败: {e}")
        return render_template('competitor_config.html', configs=[], error=str(e))

@app.route('/session/<int:session_id>')
def session_detail(session_id):
    """会话详情页面"""
    try:
        session_data = monitor_service.get_session_details(session_id)
        if not session_data:
            return "会话不存在", 404
        
        return render_template('competitor_session.html', session=session_data)
    except Exception as e:
        logger.error(f"会话详情加载失败: {e}")
        return f"加载失败: {e}", 500

@app.route('/api/crawl', methods=['POST'])
def manual_crawl():
    """手动触发爬取"""
    try:
        session_name = request.json.get('session_name', f"手动爬取 {datetime.now().strftime('%H:%M')}")
        
        result = monitor_service.execute_crawl_session(session_name)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"手动爬取失败: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/config', methods=['POST'])
def add_config():
    """添加监控配置"""
    try:
        config_data = request.json
        
        # 验证必要字段
        if not config_data.get('name'):
            return jsonify({"success": False, "message": "请提供配置名称"})
        
        if not config_data.get('config_type'):
            return jsonify({"success": False, "message": "请选择配置类型"})
        
        if config_data['config_type'] == 'account' and not config_data.get('account_url'):
            return jsonify({"success": False, "message": "账号模式需要提供账号链接"})
        
        if config_data['config_type'] == 'keyword' and not config_data.get('website_url'):
            return jsonify({"success": False, "message": "关键词模式需要提供网站链接"})
        
        if config_data['config_type'] == 'webpage_update' and not config_data.get('webpage_url'):
            return jsonify({"success": False, "message": "网页更新模式需要提供网页链接"})
        
        result = monitor_service.add_monitor_config(config_data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"添加配置失败: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/config/<int:config_id>', methods=['PUT'])
def update_config(config_id):
    """更新监控配置"""
    try:
        config_data = request.json
        result = monitor_service.update_monitor_config(config_id, config_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/config/<int:config_id>', methods=['DELETE'])
def delete_config(config_id):
    """删除监控配置"""
    try:
        result = monitor_service.delete_monitor_config(config_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"删除配置失败: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/scheduler/status')
def scheduler_status():
    """获取定时任务状态"""
    try:
        jobs = scheduler.get_jobs()
        job_info = []
        
        for job in jobs:
            job_info.append({
                'id': job.id,
                'name': job.name or job.func.__name__,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'func_name': job.func.__name__
            })
        
        return jsonify({
            'success': True,
            'scheduler_running': scheduler.running,
            'jobs_count': len(jobs),
            'jobs': job_info
        })
        
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'scheduler_running': False,
            'jobs_count': 0,
            'jobs': []
        })

@app.route('/api/scheduler/trigger', methods=['POST'])
def trigger_scheduled_crawl():
    """手动触发定时爬取任务"""
    try:
        logger.info("🔧 手动触发定时爬取任务")
        scheduled_crawl()
        return jsonify({
            'success': True,
            'message': '定时爬取任务已手动触发'
        })
    except Exception as e:
        logger.error(f"手动触发定时任务失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/stats')
def get_stats():
    """获取统计信息"""
    try:
        stats = monitor_service.get_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return jsonify({"error": str(e)})

@app.route('/viewer')
def viewer_page():
    """只读查看页面（多设备访问）"""
    try:
        recent_sessions = monitor_service.get_recent_sessions(limit=10)
        return render_template('competitor_viewer.html', sessions=recent_sessions)
    except Exception as e:
        logger.error(f"查看页面加载失败: {e}")
        return render_template('competitor_viewer.html', sessions=[], error=str(e))

@app.route('/api/feishu/test', methods=['POST'])
def test_feishu_webhook():
    """测试飞书webhook连接"""
    try:
        success = monitor_service.test_feishu_webhook()
        return jsonify({
            'success': success,
            'message': '飞书webhook测试成功' if success else '飞书webhook测试失败'
        })
    except Exception as e:
        logger.error(f"测试飞书webhook失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/feishu/webhook', methods=['POST'])
def update_feishu_webhook():
    """更新飞书webhook地址"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url')
        
        if not webhook_url:
            return jsonify({
                'success': False,
                'message': 'webhook地址不能为空'
            })
        
        monitor_service.update_feishu_webhook(webhook_url)
        return jsonify({
            'success': True,
            'message': '飞书webhook地址已更新'
        })
    except Exception as e:
        logger.error(f"更新飞书webhook失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/feishu/send-test', methods=['POST'])
def send_test_feishu_message():
    """发送测试飞书消息"""
    try:
        # 获取最近的一些帖子作为测试数据
        recent_posts = CompetitorPost.query.order_by(
            CompetitorPost.created_at.desc()
        ).limit(5).all()
        
        if recent_posts:
            post_dicts = [post.to_dict() for post in recent_posts]
            success = monitor_service.feishu_service.send_daily_summary(
                post_dicts, 
                "测试推送"
            )
        else:
            # 没有数据时发送测试消息
            success = monitor_service.test_feishu_webhook()
        
        return jsonify({
            'success': success,
            'message': '测试消息发送成功' if success else '测试消息发送失败'
        })
    except Exception as e:
        logger.error(f"发送测试消息失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/session/delete/<int:session_id>', methods=['DELETE'])
def delete_crawl_session(session_id):
    """删除爬取会话和相关记录"""
    try:
        result = monitor_service.delete_crawl_session(session_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/posts/delete', methods=['DELETE'])
def delete_posts_by_urls():
    """根据URL删除帖子记录"""
    try:
        data = request.get_json()
        post_urls = data.get('post_urls', [])
        
        if not post_urls:
            return jsonify({
                'success': False,
                'message': '请提供要删除的帖子URL列表'
            })
        
        result = monitor_service.delete_posts_by_url(post_urls)
        return jsonify(result)
    except Exception as e:
        logger.error(f"删除帖子失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/records/clear', methods=['DELETE'])
def clear_old_records():
    """清理老的监控记录"""
    try:
        data = request.get_json() or {}
        days_before = data.get('days_before', 30)  # 默认清理30天前的记录
        
        result = monitor_service.clear_old_records(days_before)
        return jsonify(result)
    except Exception as e:
        logger.error(f"清理老记录失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/session/<int:session_id>/posts')
def get_session_posts(session_id):
    """获取指定会话的所有帖子"""
    try:
        posts = monitor_service.get_session_posts(session_id)
        return jsonify({
            'success': True,
            'posts': posts
        })
    except Exception as e:
        logger.error(f"获取会话帖子失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/feishu/push/<int:session_id>', methods=['POST'])
def push_to_feishu(session_id):
    """手动推送指定会话内容到飞书"""
    try:
        # 检查访问权限 - 只允许localhost访问
        if request.remote_addr != '127.0.0.1':
            return jsonify({
                'success': False,
                'message': '权限不足：仅允许本地访问此功能'
            }), 403
        
        with app.app_context():
            result = monitor_service.push_session_to_feishu(session_id)
            return jsonify(result)
    except Exception as e:
        logger.error(f"推送到飞书失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

# 定时任务
def scheduled_crawl():
    """定时爬取任务（每日11点）- 有内容时推送飞书"""
    logger.info("🕘 执行定时竞品监控...")
    try:
        with app.app_context():  # 添加Flask应用上下文
            result = monitor_service.execute_scheduled_crawl()
            logger.info(f"定时监控完成: {result}")
            
            # 记录飞书推送状态
            if result.get("feishu_sent"):
                logger.info("📱 飞书消息已推送")
            elif result.get("processed_posts", 0) > 0:
                logger.warning("⚠️ 有新内容但飞书推送失败")
            else:
                logger.info("📱 无新内容，未推送飞书消息")
                
    except Exception as e:
        logger.error(f"定时监控失败: {e}")

def init_database():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        
        # 初始化系统设置
        settings = [
            ("crawl_schedule", "0 10 * * *", "每日10点定时爬取"),
            ("ai_api_key", "AIzaSyBvGjWPijmwETZoPgrcPIuggo1xU0Qzyjg", "Gemini API密钥"),
            ("ai_model", "gemini-1.5-flash", "AI模型")
        ]
        
        for key, value, desc in settings:
            existing = SystemSettings.query.filter_by(key=key).first()
            if not existing:
                setting = SystemSettings(key=key, value=value, description=desc)
                db.session.add(setting)
        
        db.session.commit()
        logger.info("✅ 数据库初始化完成")

def init_sample_configs():
    """初始化示例配置"""
    with app.app_context():
        # 检查是否已有配置
        if MonitorConfig.query.count() > 0:
            return
        
        # 文档中的示例配置
        sample_configs = [
            {
                "name": "kickstarter_cubiio",
                "config_type": "account",
                "account_url": "https://www.kickstarter.com/profile/cubiio/created"
            },
            {
                "name": "reddit_wecreat",
                "config_type": "keyword",
                "website_url": "https://www.reddit.com/r/WeCreat/",
                "keywords": ""  # 空关键词表示爬取所有24小时内帖子
            }
        ]
        
        for config_data in sample_configs:
            result = monitor_service.add_monitor_config(config_data)
            logger.info(f"添加示例配置: {result}")

def init_scheduler():
    """初始化调度器（不添加定时任务）"""
    try:
        # 配置调度器
        scheduler.init_app(app)
        scheduler.start()
        logger.info("✅ 调度器已启动（无定时任务）")
        
        # 不再添加定时任务 - 改为手动推送模式
        logger.info("📱 已切换为手动推送模式")
                
    except Exception as e:
        logger.error(f"❌ 初始化调度器失败: {e}")
        raise

if __name__ == '__main__':
    try:
        # 初始化
        init_database()
        init_sample_configs()
        init_scheduler()
        
        # 获取端口
        port = int(os.environ.get('PORT', 8080))
        
        logger.info(f"🚀 竞品监控系统启动在端口 {port}")
        logger.info(f"📱 访问地址: http://localhost:{port}")
        logger.info(f"👀 只读查看: http://localhost:{port}/viewer")
        
        # 生产模式运行，提高稳定性
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        logger.info("🛑 收到停止信号，正在关闭应用...")
        if scheduler.running:
            scheduler.shutdown()
        logger.info("✅ 应用已安全关闭")
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        if scheduler.running:
            scheduler.shutdown()
        raise 