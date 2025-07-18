#!/usr/bin/env python3
"""
飞书自动推送机器人 - 启动脚本
"""

import os
import sys
import signal
import time
from app import create_app, init_database, start_scheduler
from services.scheduler_service import scheduler_service
from loguru import logger

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"接收到信号 {signum}，正在关闭系统...")
    
    # 停止任务调度器
    try:
        scheduler_service.stop()
        logger.info("任务调度器已停止")
    except Exception as e:
        logger.error(f"停止任务调度器失败: {e}")
    
    # 退出程序
    sys.exit(0)

def main():
    """主函数"""
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建日志目录
    os.makedirs('logs', exist_ok=True)
    
    # 创建应用
    app = create_app()
    
    # 初始化数据库
    with app.app_context():
        init_database()
    
    # 启动任务调度器
    with app.app_context():
        start_scheduler()
    
    # 启动Web服务器
    try:
        port = int(os.environ.get('PORT', 8888))
        logger.info("🚀 飞书自动推送机器人系统启动成功")
        logger.info(f"📱 访问地址: http://localhost:{port}")
        logger.info(f"📚 管理界面: http://localhost:{port}")
        logger.info(f"🔗 API文档: http://localhost:{port}/api/health")
        
        # 在应用上下文中启动服务器
        with app.app_context():
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                threaded=True,
                use_reloader=False  # 禁用重载器避免重复启动调度器
            )
            
    except Exception as e:
        logger.error(f"❌ 系统启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 