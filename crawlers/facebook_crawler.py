#!/usr/bin/env python3
"""
Facebook爬虫 - 基于GitHub项目优化的实现
使用Cookie和Headers进行身份验证，提高爬取成功率
参考: https://github.com/wz289494/Crawl_Facebook_User
"""

import re
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from loguru import logger

class FacebookPost:
    """Facebook帖子数据结构"""
    def __init__(self):
        self.title: str = ""
        self.content: str = ""
        self.author: str = ""
        self.post_url: str = ""
        self.post_time: datetime = None
        self.likes_count: int = 0
        self.comments_count: int = 0
        self.shares_count: int = 0
        self.platform: str = "facebook"
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "post_url": self.post_url,
            "post_time": self.post_time.isoformat() if self.post_time else None,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "shares_count": self.shares_count,
            "platform": self.platform
        }

class FacebookCrawler:
    """Facebook专用爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # 基于GitHub项目优化的Headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        self.session.headers.update(self.headers)
        
        # 可选的Cookies配置（需要用户提供）
        self.cookies = {}
        
        # 加载配置
        self._load_config()
        
    def _load_config(self):
        """加载Facebook配置"""
        try:
            # 尝试从配置文件加载
            import config
            if hasattr(config, 'FACEBOOK_COOKIES'):
                self.cookies.update(config.FACEBOOK_COOKIES)
                logger.info("✅ 加载Facebook Cookie配置")
        except (ImportError, AttributeError):
            logger.warning("⚠️ 未找到Facebook Cookie配置，将使用公开访问模式")
    
    def crawl_page(self, page_url: str, max_posts: int = 20) -> List[FacebookPost]:
        """爬取Facebook页面的帖子"""
        posts = []
        
        try:
            logger.info(f"🕷️ 开始爬取Facebook页面: {page_url}")
            
            # 方法1: 尝试移动版Facebook (更容易爬取)
            mobile_url = self._convert_to_mobile_url(page_url)
            posts_mobile = self._crawl_mobile_facebook(mobile_url, max_posts)
            
            if posts_mobile:
                logger.info(f"✅ 移动版爬取成功，获得 {len(posts_mobile)} 条帖子")
                return posts_mobile
            
            # 方法2: 如果移动版失败，尝试桌面版
            logger.info("📱 移动版爬取失败，尝试桌面版...")
            posts_desktop = self._crawl_desktop_facebook(page_url, max_posts)
            
            if posts_desktop:
                logger.info(f"✅ 桌面版爬取成功，获得 {len(posts_desktop)} 条帖子")
                return posts_desktop
            
            # 方法3: 使用Selenium作为最后手段
            logger.info("💻 桌面版爬取失败，尝试Selenium...")
            posts_selenium = self._crawl_with_selenium(page_url, max_posts)
            
            if posts_selenium:
                logger.info(f"✅ Selenium爬取成功，获得 {len(posts_selenium)} 条帖子")
                return posts_selenium
            
        except Exception as e:
            logger.error(f"❌ Facebook爬取异常: {e}")
        
        return posts
    
    def _convert_to_mobile_url(self, url: str) -> str:
        """转换为移动版Facebook URL"""
        if 'facebook.com' in url:
            # 修复URL转换逻辑
            url = url.replace('www.facebook.com', 'm.facebook.com')
            if 'm.facebook.com' not in url:
                url = url.replace('facebook.com', 'm.facebook.com')
        return url
    
    def _crawl_mobile_facebook(self, url: str, max_posts: int) -> List[FacebookPost]:
        """爬取移动版Facebook"""
        posts = []
        
        try:
            # 更新Cookie
            if self.cookies:
                self.session.cookies.update(self.cookies)
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ 移动版Facebook访问失败: {response.status_code}")
                return posts
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找帖子容器 (移动版Facebook的结构)
            post_elements = soup.find_all('div', {'data-ft': True}) or soup.find_all('article')
            
            logger.info(f"📱 找到 {len(post_elements)} 个潜在帖子元素")
            
            for i, element in enumerate(post_elements[:max_posts]):
                try:
                    post = self._parse_mobile_post(element)
                    if post and self._is_recent_post(post.post_time):
                        posts.append(post)
                        logger.debug(f"✅ 解析帖子 {i+1}: {post.title[:50]}...")
                except Exception as e:
                    logger.debug(f"⚠️ 解析帖子 {i+1} 失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ 移动版爬取异常: {e}")
        
        return posts
    
    def _crawl_desktop_facebook(self, url: str, max_posts: int) -> List[FacebookPost]:
        """爬取桌面版Facebook"""
        posts = []
        
        try:
            # 更新Cookie
            if self.cookies:
                self.session.cookies.update(self.cookies)
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ 桌面版Facebook访问失败: {response.status_code}")
                return posts
            
            # 检查是否被重定向到登录页
            if 'login.php' in response.url or 'checkpoint' in response.url:
                logger.warning("⚠️ 需要登录才能访问该Facebook页面")
                return posts
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找帖子容器 (桌面版Facebook的结构)
            post_elements = (soup.find_all('div', {'data-pagelet': True}) or 
                           soup.find_all('div', class_=re.compile(r'.*story.*', re.I)) or
                           soup.find_all('div', {'role': 'article'}))
            
            logger.info(f"💻 找到 {len(post_elements)} 个潜在帖子元素")
            
            for i, element in enumerate(post_elements[:max_posts]):
                try:
                    post = self._parse_desktop_post(element)
                    if post and self._is_recent_post(post.post_time):
                        posts.append(post)
                        logger.debug(f"✅ 解析帖子 {i+1}: {post.title[:50]}...")
                except Exception as e:
                    logger.debug(f"⚠️ 解析帖子 {i+1} 失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ 桌面版爬取异常: {e}")
        
        return posts
    
    def _crawl_with_selenium(self, url: str, max_posts: int) -> List[FacebookPost]:
        """使用Selenium爬取Facebook"""
        posts = []
        driver = None
        
        try:
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 设置User-Agent
            chrome_options.add_argument(f'--user-agent={self.headers["User-Agent"]}')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 添加Cookie
            driver.get("https://www.facebook.com")
            for name, value in self.cookies.items():
                driver.add_cookie({'name': name, 'value': value})
            
            # 访问目标页面
            driver.get(url)
            time.sleep(3)
            
            # 滚动加载更多内容
            self._scroll_and_wait(driver, max_scrolls=3)
            
            # 查找帖子元素
            post_elements = driver.find_elements(By.CSS_SELECTOR, 
                "[data-pagelet*='FeedUnit'], [role='article'], div[data-ft]")
            
            logger.info(f"🤖 Selenium找到 {len(post_elements)} 个潜在帖子元素")
            
            for i, element in enumerate(post_elements[:max_posts]):
                try:
                    post = self._parse_selenium_post(element)
                    if post and self._is_recent_post(post.post_time):
                        posts.append(post)
                        logger.debug(f"✅ 解析帖子 {i+1}: {post.title[:50]}...")
                except Exception as e:
                    logger.debug(f"⚠️ 解析帖子 {i+1} 失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ Selenium爬取异常: {e}")
        finally:
            if driver:
                driver.quit()
        
        return posts
    
    def _scroll_and_wait(self, driver, max_scrolls=3):
        """滚动页面加载更多内容"""
        for i in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            logger.debug(f"📜 滚动 {i+1}/{max_scrolls}")
    
    def _parse_mobile_post(self, element) -> Optional[FacebookPost]:
        """解析移动版Facebook帖子"""
        post = FacebookPost()
        
        try:
            # 提取内容文本
            content_elem = element.find('p') or element.find('div', string=True)
            if content_elem:
                post.content = content_elem.get_text(strip=True)
                post.title = post.content[:100] + "..." if len(post.content) > 100 else post.content
            
            # 提取作者
            author_elem = element.find('h3') or element.find('strong')
            if author_elem:
                post.author = author_elem.get_text(strip=True)
            
            # 提取链接
            link_elem = element.find('a', href=True)
            if link_elem:
                post.post_url = urljoin('https://m.facebook.com', link_elem['href'])
            
            # 设置时间（移动版较难提取准确时间，使用当前时间）
            post.post_time = datetime.now()
            
            return post if post.content else None
            
        except Exception as e:
            logger.debug(f"移动版帖子解析失败: {e}")
            return None
    
    def _parse_desktop_post(self, element) -> Optional[FacebookPost]:
        """解析桌面版Facebook帖子"""
        post = FacebookPost()
        
        try:
            # 提取内容文本
            content_selectors = [
                '[data-ad-preview="message"]',
                '[data-testid="post_message"]',
                'div[dir="auto"]',
                'p',
                'span'
            ]
            
            for selector in content_selectors:
                content_elem = element.select_one(selector)
                if content_elem and content_elem.get_text(strip=True):
                    post.content = content_elem.get_text(strip=True)
                    break
            
            if post.content:
                post.title = post.content[:100] + "..." if len(post.content) > 100 else post.content
            
            # 提取作者
            author_selectors = [
                'h3[dir="auto"] a',
                'strong a',
                '[data-testid="story-subtitle"] a'
            ]
            
            for selector in author_selectors:
                author_elem = element.select_one(selector)
                if author_elem:
                    post.author = author_elem.get_text(strip=True)
                    break
            
            # 提取链接
            link_elem = element.find('a', href=True)
            if link_elem and 'href' in link_elem.attrs:
                post.post_url = urljoin('https://www.facebook.com', link_elem['href'])
            
            # 设置时间
            post.post_time = datetime.now()
            
            return post if post.content else None
            
        except Exception as e:
            logger.debug(f"桌面版帖子解析失败: {e}")
            return None
    
    def _parse_selenium_post(self, element) -> Optional[FacebookPost]:
        """解析Selenium获取的Facebook帖子"""
        post = FacebookPost()
        
        try:
            # 提取内容文本
            try:
                post.content = element.find_element(By.CSS_SELECTOR, 
                    '[data-ad-preview="message"], [data-testid="post_message"], div[dir="auto"]').text
            except:
                post.content = element.text[:500] if element.text else ""
            
            if post.content:
                post.title = post.content[:100] + "..." if len(post.content) > 100 else post.content
            
            # 提取作者
            try:
                post.author = element.find_element(By.CSS_SELECTOR, 
                    'h3[dir="auto"] a, strong a').text
            except:
                post.author = "Unknown"
            
            # 提取链接
            try:
                link_elem = element.find_element(By.TAG_NAME, 'a')
                post.post_url = link_elem.get_attribute('href')
            except:
                post.post_url = ""
            
            # 设置时间
            post.post_time = datetime.now()
            
            return post if post.content else None
            
        except Exception as e:
            logger.debug(f"Selenium帖子解析失败: {e}")
            return None
    
    def _is_recent_post(self, post_time: datetime) -> bool:
        """检查是否为72小时内的帖子"""
        if not post_time:
            return True  # 如果无法确定时间，默认包含
        
        now = datetime.now()
        return (now - post_time).total_seconds() <= 72 * 3600
    
    def test_crawl(self, page_url: str) -> Dict[str, Any]:
        """测试Facebook爬取功能"""
        logger.info(f"🧪 开始测试Facebook爬取: {page_url}")
        
        start_time = time.time()
        posts = self.crawl_page(page_url, max_posts=5)
        end_time = time.time()
        
        result = {
            "success": len(posts) > 0,
            "posts_count": len(posts),
            "execution_time": round(end_time - start_time, 2),
            "posts": [post.to_dict() for post in posts],
            "page_url": page_url
        }
        
        if posts:
            logger.info(f"✅ 测试成功！爬取到 {len(posts)} 条帖子，耗时 {result['execution_time']}秒")
        else:
            logger.warning("❌ 测试失败！未能爬取到任何内容")
        
        return result

# 使用示例
if __name__ == "__main__":
    crawler = FacebookCrawler()
    
    # 测试爬取Facebook页面
    test_urls = [
        "https://www.facebook.com/LightBurnSoftware",
        "https://www.facebook.com/LaserMasterCorp",
        "https://www.facebook.com/xTool.tech"
    ]
    
    for url in test_urls:
        result = crawler.test_crawl(url)
        print(f"\n📊 测试结果 - {url}")
        print(f"成功: {result['success']}")
        print(f"帖子数: {result['posts_count']}")
        print(f"耗时: {result['execution_time']}秒")
        
        if result['posts']:
            print("📝 示例帖子:")
            for i, post in enumerate(result['posts'][:2]):
                print(f"  {i+1}. {post['title']}")
                print(f"     作者: {post['author']}")
                print(f"     内容: {post['content'][:100]}...")
        print("-" * 50) 