#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加AI总结和存档功能
"""

import sqlite3
from loguru import logger
from pathlib import Path

def migrate_database():
    """执行数据库迁移"""
    db_path = Path("feishu_bot.db")
    
    if not db_path.exists():
        logger.info("数据库文件不存在，跳过迁移")
        return True
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查是否已经存在新字段
        cursor.execute("PRAGMA table_info(crawled_posts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        logger.info(f"当前字段: {columns}")
        
        # 添加 ai_summary 字段
        if 'ai_summary' not in columns:
            logger.info("添加 ai_summary 字段...")
            cursor.execute("ALTER TABLE crawled_posts ADD COLUMN ai_summary TEXT")
            
        # 添加 is_archived 字段
        if 'is_archived' not in columns:
            logger.info("添加 is_archived 字段...")
            cursor.execute("ALTER TABLE crawled_posts ADD COLUMN is_archived BOOLEAN DEFAULT 0")
            
        # 添加 archive_date 字段
        if 'archive_date' not in columns:
            logger.info("添加 archive_date 字段...")
            cursor.execute("ALTER TABLE crawled_posts ADD COLUMN archive_date DATE")
            
        # 删除旧的推送相关字段 (SQLite不支持DROP COLUMN，我们保留但不使用)
        logger.info("保留旧的推送字段但不再使用")
        
        conn.commit()
        logger.info("✅ 数据库迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_database() 