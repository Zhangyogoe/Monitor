#!/usr/bin/env python3
"""
YouTube爬虫 - 专门用于爬取YouTube频道视频
支持按时间范围爬取视频内容
"""

import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from .base_crawler import BaseCrawler, PostData

class YouTubeCrawler(BaseCrawler):
    """YouTube爬虫"""
    
    def __init__(self, website_config: Dict[str, Any]):
        super().__init__(website_config)
        self.base_url = website_config.get("url", "")
        self.time_range_start = website_config.get("time_range_start")
        
        # YouTube特定选择器
        self.selectors = {
            'video_list': '#contents ytd-rich-item-renderer',
            'video_title': 'h3 a#video-title-link',
            'video_link': 'a#video-title-link',
            'upload_time': '#metadata-line span:nth-child(2)',
            'view_count': '#metadata-line span:nth-child(1)'
        }
    
    def crawl_posts(self, keywords: List[str] = None, limit: int = 50) -> List[PostData]:
        """爬取YouTube视频"""
        posts = []
        
        if not self.base_url:
            logger.error("❌ YouTube URL不能为空")
            return posts
        
        driver = self.init_webdriver()
        if not driver:
            logger.error("❌ 无法初始化WebDriver")
            return posts
        
        try:
            logger.info(f"🎬 开始爬取YouTube频道: {self.base_url}")
            
            driver.get(self.base_url)
            time.sleep(5)
            
            # 滚动加载更多视频
            self._scroll_to_load_videos(driver, limit)
            
            # 获取视频元素
            video_elements = driver.find_elements(By.CSS_SELECTOR, self.selectors['video_list'])
            logger.info(f"找到 {len(video_elements)} 个视频元素")
            
            for element in video_elements[:limit]:
                try:
                    post = self._parse_video_element(element)
                    if post and self._is_within_time_range(post.post_time):
                        posts.append(post)
                except Exception as e:
                    logger.error(f"解析视频元素失败: {e}")
                    continue
            
            logger.info(f"✅ YouTube爬取完成，获取 {len(posts)} 个视频")
            
        except Exception as e:
            logger.error(f"❌ YouTube爬取失败: {e}")
        finally:
            self.close_webdriver()
        
        return posts
    
    def _parse_video_element(self, element) -> Optional[PostData]:
        """解析单个视频元素"""
        try:
            post = PostData()
            post.source_website = "YouTube"
            
            # 获取视频标题和链接
            title_element = element.find_element(By.CSS_SELECTOR, self.selectors['video_title'])
            if title_element:
                post.title = title_element.get_attribute('title') or title_element.text
                post.post_url = title_element.get_attribute('href')
            
            # 获取频道名称
            if '@' in self.base_url:
                post.author = self.base_url.split('@')[1].split('/')[0]
            else:
                post.author = "YouTube频道"
            
            # 获取上传时间
            try:
                time_element = element.find_element(By.CSS_SELECTOR, self.selectors['upload_time'])
                time_text = time_element.text if time_element else ""
                post.post_time = self._parse_youtube_time(time_text)
            except:
                post.post_time = datetime.now()
            
            # 获取观看次数
            try:
                view_element = element.find_element(By.CSS_SELECTOR, self.selectors['view_count'])
                view_text = view_element.text if view_element else "0"
                post.likes_count = self._parse_view_count(view_text)
            except:
                post.likes_count = 0
            
            post.content = f"YouTube视频: {post.title}"
            post.comments_count = 0
            post.matched_keywords = ["视频内容"]
            
            return post if post.title else None
            
        except Exception as e:
            logger.error(f"解析视频元素失败: {e}")
            return None
    
    def _parse_youtube_time(self, time_str: str) -> Optional[datetime]:
        """解析YouTube时间字符串"""
        now = datetime.now()
        
        try:
            time_str = time_str.lower().strip()
            
            if "分钟前" in time_str or "minutes ago" in time_str:
                minutes = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(minutes=minutes)
            elif "小时前" in time_str or "hours ago" in time_str:
                hours = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(hours=hours)
            elif "天前" in time_str or "days ago" in time_str:
                days = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(days=days)
            elif "周前" in time_str or "weeks ago" in time_str:
                weeks = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(weeks=weeks)
            elif "个月前" in time_str or "months ago" in time_str:
                months = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(days=months * 30)
            elif "年前" in time_str or "years ago" in time_str:
                years = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(days=years * 365)
        except Exception as e:
            logger.debug(f"解析YouTube时间失败: {time_str}, {e}")
        
        return now
    
    def _parse_view_count(self, view_str: str) -> int:
        """解析观看次数"""
        try:
            numbers = re.findall(r'[\d,.]+', view_str)
            if numbers:
                num_str = numbers[0].replace(',', '').replace('.', '')
                
                if 'k' in view_str.lower() or '千' in view_str:
                    return int(float(num_str) * 1000)
                elif 'm' in view_str.lower() or '万' in view_str:
                    return int(float(num_str) * 10000)
                else:
                    return int(num_str)
        except:
            pass
        
        return 0
    
    def _scroll_to_load_videos(self, driver, target_count: int):
        """滚动页面加载更多视频"""
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        scroll_count = 0
        max_scrolls = 5
        
        while scroll_count < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(3)
            
            current_videos = len(driver.find_elements(By.CSS_SELECTOR, self.selectors['video_list']))
            if current_videos >= target_count:
                break
            
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            
            last_height = new_height
            scroll_count += 1
    
    def _is_within_time_range(self, post_time: datetime) -> bool:
        """检查时间是否在指定范围内"""
        if not self.time_range_start:
            return True
        
        try:
            if isinstance(self.time_range_start, str):
                start_date = datetime.strptime(self.time_range_start, '%Y-%m-%d')
            else:
                start_date = self.time_range_start
            
            today = datetime.now()
            return start_date <= post_time <= today
            
        except Exception as e:
            logger.error(f"时间范围检查失败: {e}")
            return True
