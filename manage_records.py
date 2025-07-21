#!/usr/bin/env python3
"""
监控记录管理工具
用于管理和删除监控爬取记录
"""

import sys
import os
import requests
import json
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.competitor_monitor_service import CompetitorMonitorService
from models.competitor_models import db, CrawlSession, CompetitorPost

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)

def show_sessions():
    """显示所有爬取会话"""
    print_header("📊 监控会话列表")
    
    try:
        # 初始化服务
        monitor_service = CompetitorMonitorService()
        
        # 获取所有会话
        sessions = monitor_service.get_recent_sessions(limit=20)
        
        if not sessions:
            print("📭 暂无监控会话记录")
            return
        
        print(f"{'ID':<5} {'会话名称':<30} {'爬取时间':<20} {'帖子数':<8} {'状态':<10}")
        print("-" * 80)
        
        for session in sessions:
            session_id = session['id']
            name = session['session_name'][:28] + "..." if len(session['session_name']) > 30 else session['session_name']
            crawl_time = session['crawl_time'][:16] if session['crawl_time'] else 'N/A'
            posts_count = session['processed_posts']
            status = session['status']
            
            print(f"{session_id:<5} {name:<30} {crawl_time:<20} {posts_count:<8} {status:<10}")
            
    except Exception as e:
        print(f"❌ 获取会话列表失败: {e}")

def show_session_details(session_id):
    """显示会话详情"""
    print_header(f"📋 会话 {session_id} 详情")
    
    try:
        monitor_service = CompetitorMonitorService()
        
        # 获取会话详情
        session_data = monitor_service.get_session_details(session_id)
        
        if not session_data:
            print(f"❌ 会话 {session_id} 不存在")
            return
        
        print(f"📝 会话名称: {session_data['session_name']}")
        print(f"⏰ 爬取时间: {session_data['crawl_time']}")
        print(f"📊 总帖子数: {session_data['total_posts']}")
        print(f"✅ 处理帖子数: {session_data['processed_posts']}")
        print(f"🏷️ 状态: {session_data['status']}")
        
        if session_data.get('ai_summary'):
            print(f"\n🤖 AI汇总:")
            print("-" * 40)
            print(session_data['ai_summary'][:200] + "..." if len(session_data['ai_summary']) > 200 else session_data['ai_summary'])
        
        # 显示帖子列表
        posts = session_data.get('posts', [])
        if posts:
            print(f"\n📄 帖子列表 ({len(posts)} 条):")
            print("-" * 40)
            for i, post in enumerate(posts[:5], 1):  # 只显示前5条
                print(f"{i}. {post['title'][:50]}...")
                print(f"   🔗 {post['post_url']}")
                print(f"   👤 {post['author']} | 🕒 {post['post_time'][:16] if post['post_time'] else 'N/A'}")
                print()
            
            if len(posts) > 5:
                print(f"... 还有 {len(posts) - 5} 条帖子")
                
    except Exception as e:
        print(f"❌ 获取会话详情失败: {e}")

def delete_session_interactive():
    """交互式删除会话"""
    print_header("🗑️ 删除监控会话")
    
    try:
        # 先显示会话列表
        show_sessions()
        
        print("\n🚨 警告: 删除会话将同时删除该会话的所有帖子记录！")
        print("删除后，如果再次遇到相同内容，系统将重新推送。")
        
        session_id = input("\n请输入要删除的会话ID (或按Enter取消): ").strip()
        
        if not session_id:
            print("❌ 取消删除操作")
            return
        
        try:
            session_id = int(session_id)
        except ValueError:
            print("❌ 请输入有效的数字ID")
            return
        
        # 确认删除
        confirm = input(f"确认删除会话 {session_id} 吗？(y/N): ").strip().lower()
        
        if confirm != 'y':
            print("❌ 取消删除操作")
            return
        
        # 执行删除
        monitor_service = CompetitorMonitorService()
        result = monitor_service.delete_crawl_session(session_id)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ 删除失败: {result['message']}")
            
    except Exception as e:
        print(f"❌ 删除操作失败: {e}")

def clear_old_records_interactive():
    """交互式清理老记录"""
    print_header("🧹 清理老记录")
    
    try:
        print("清理指定天数前的所有监控记录")
        days = input("请输入天数 (默认30天): ").strip()
        
        if not days:
            days = 30
        else:
            try:
                days = int(days)
            except ValueError:
                print("❌ 请输入有效的天数")
                return
        
        print(f"\n🚨 警告: 将删除 {days} 天前的所有记录！")
        confirm = input("确认清理吗？(y/N): ").strip().lower()
        
        if confirm != 'y':
            print("❌ 取消清理操作")
            return
        
        # 执行清理
        monitor_service = CompetitorMonitorService()
        result = monitor_service.clear_old_records(days)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ 清理失败: {result['message']}")
            
    except Exception as e:
        print(f"❌ 清理操作失败: {e}")

def test_delete_api():
    """测试删除API接口"""
    print_header("🧪 测试删除API")
    
    base_url = "http://localhost:8080"
    
    try:
        # 测试获取会话列表
        print("1️⃣ 测试获取统计信息...")
        response = requests.get(f"{base_url}/api/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ 当前统计: {stats['total_sessions']} 个会话, {stats['total_posts']} 条帖子")
        else:
            print("❌ 无法获取统计信息")
            return
        
        # 询问是否测试删除
        if stats['total_sessions'] > 0:
            print(f"\n2️⃣ 可以测试删除功能")
            print("请通过网页界面或其他方式测试删除API:")
            print(f"- 删除会话: DELETE {base_url}/api/session/delete/<session_id>")
            print(f"- 清理老记录: DELETE {base_url}/api/records/clear")
        else:
            print("\n📭 没有记录可供删除测试")
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")

def main():
    """主菜单"""
    while True:
        print_header("🛠️ 监控记录管理工具")
        print("1. 查看监控会话列表")
        print("2. 查看会话详情")
        print("3. 删除监控会话")
        print("4. 清理老记录")
        print("5. 测试删除API")
        print("0. 退出")
        
        choice = input("\n请选择操作 (0-5): ").strip()
        
        if choice == '0':
            print("👋 再见！")
            break
        elif choice == '1':
            show_sessions()
        elif choice == '2':
            session_id = input("请输入会话ID: ").strip()
            try:
                session_id = int(session_id)
                show_session_details(session_id)
            except ValueError:
                print("❌ 请输入有效的数字ID")
        elif choice == '3':
            delete_session_interactive()
        elif choice == '4':
            clear_old_records_interactive()
        elif choice == '5':
            test_delete_api()
        else:
            print("❌ 无效选择，请重试")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 操作已取消，再见！")
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
        import traceback
        traceback.print_exc() 