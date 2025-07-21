#!/usr/bin/env python3
"""
竞品动态监控系统 - 简化启动脚本
专注于竞品监控需求，删除冗余功能
"""

import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from competitor_app import app, init_database, init_sample_configs, init_scheduler
    from loguru import logger
    
    def main():
        """主启动函数"""
        print("🚀 竞品动态监控系统启动中...")
        print("=" * 50)
        
        try:
            # 初始化数据库
            print("📦 初始化数据库...")
            init_database()
            
            # 初始化示例配置
            print("🔧 检查示例配置...")
            init_sample_configs()
            
            # 初始化调度器
            print("⏰ 初始化定时任务...")
            init_scheduler()
            
            # 获取端口
            port = int(os.environ.get('PORT', 8080))
            
            print(f"✅ 初始化完成！")
            print("=" * 50)
            print(f"🌐 访问地址:")
            print(f"   主页（管理）: http://localhost:{port}")
            print(f"   监控配置   : http://localhost:{port}/config")
            print(f"   只读查看   : http://localhost:{port}/viewer")
            print("=" * 50)
            print(f"⏰ 定时爬取: 每日 10:00")
            print(f"🤖 AI 引擎: Gemini 1.5 Flash")
            print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            print("💡 系统功能:")
            print("   - 两种爬取模式：账号链接 / 网站关键词")
            print("   - 24小时爬取范围，自动去重")
            print("   - AI品牌分类和内容总结")
            print("   - 定时和手动爬取")
            print("   - 多设备只读访问")
            print("=" * 50)
            
            # 启动应用
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False,  # 生产环境关闭调试
                threaded=True
            )
            
        except Exception as e:
            logger.error(f"❌ 启动失败: {e}")
            print(f"❌ 启动失败: {e}")
            sys.exit(1)
    
    if __name__ == '__main__':
        main()
        
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保已安装所有依赖包:")
    print("pip install flask flask-cors flask-apscheduler flask-sqlalchemy")
    print("pip install requests beautifulsoup4 selenium loguru")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ 未知错误: {e}")
    sys.exit(1) 