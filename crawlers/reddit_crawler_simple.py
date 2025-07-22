#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化的Reddit爬虫 - 基于分析结果的有效实现
根据测试结果，JSON API是最佳方法
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta
from typing import List
from loguru import logger

def crawl_reddit_simple(subreddit_url: str, keywords: List[str] = None) -> List[dict]:
    """
    简化的Reddit爬取方法
    基于分析结果，使用最有效的JSON API方法
    """
    posts = []
    
    try:
        # 从URL提取subreddit名称
        if '/r/' in subreddit_url:
            subreddit = subreddit_url.split('/r/')[-1].split('/')[0]
        else:
            logger.error(f"无效的Reddit URL: {subreddit_url}")
            return []
        
        # 构造JSON API URL
        json_url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=25"
        
        logger.info(f"🚀 使用JSON API爬取: {json_url}")
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
        
        # 添加随机延迟
        time.sleep(random.uniform(2, 4))
        
        # 发送请求
        response = requests.get(json_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.warning(f"Reddit API请求失败，状态码: {response.status_code}")
            return []
        
        # 解析JSON响应
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []
        
        # 检查数据结构
        if 'data' not in data or 'children' not in data['data']:
            logger.warning("Reddit API返回数据结构异常")
            return []
        
        # 72小时前的时间戳
        seventy_two_hours_ago = datetime.now() - timedelta(hours=72)
        seventy_two_hours_timestamp = seventy_two_hours_ago.timestamp()
        
        # 处理帖子数据
        for item in data['data']['children']:
            try:
                post_data = item['data']
                
                # 检查时间（UTC时间戳）
                created_utc = post_data.get('created_utc', 0)
                if created_utc < seventy_two_hours_timestamp:
                    continue  # 跳过72小时前的帖子
                
                # 提取帖子信息
                title = post_data.get('title', '').strip()
                if not title:
                    continue
                
                # 关键词过滤
                if keywords:
                    if not any(keyword.lower() in title.lower() for keyword in keywords):
                        continue
                
                # 构造帖子对象
                post = {
                    'title': title,
                    'content': post_data.get('selftext', ''),
                    'author': post_data.get('author', 'unknown'),
                    'post_time': datetime.fromtimestamp(created_utc),
                    'post_url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                    'likes_count': post_data.get('score', 0),
                    'comments_count': post_data.get('num_comments', 0),
                    'platform': 'Reddit'
                }
                
                posts.append(post)
                
            except Exception as e:
                logger.warning(f"处理帖子数据时出错: {e}")
                continue
        
        logger.success(f"✅ Reddit爬取成功: 总计 {len(data['data']['children'])} 条，24小时内 {len(posts)} 条")
        return posts
        
    except Exception as e:
        logger.error(f"❌ Reddit爬取异常: {e}")
        return []

def test_reddit_crawler():
    """测试Reddit爬虫"""
    print("🧪 测试简化Reddit爬虫")
    
    test_urls = [
        "https://www.reddit.com/r/xToolOfficial/",
        "https://www.reddit.com/r/WeCreat/"
    ]
    
    for url in test_urls:
        print(f"\n📍 测试URL: {url}")
        posts = crawl_reddit_simple(url)
        print(f"📊 结果: {len(posts)} 条帖子")
        
        if posts:
            print("📝 帖子预览:")
            for i, post in enumerate(posts[:3], 1):
                print(f"  {i}. {post['title'][:50]}...")

if __name__ == "__main__":
    test_reddit_crawler() 