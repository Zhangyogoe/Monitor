#!/usr/bin/env python3
"""
竞品爬虫 - 支持Kickstarter、Reddit等平台
专注于24小时内的内容爬取
"""

import re
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from loguru import logger

class CompetitorPost:
    """竞品帖子数据结构"""
    def __init__(self):
        self.title: str = ""
        self.content: str = ""
        self.author: str = ""
        self.post_url: str = ""
        self.post_time: datetime = None
        self.likes_count: int = 0
        self.comments_count: int = 0
        self.platform: str = ""
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "post_url": self.post_url,
            "post_time": self.post_time.isoformat() if self.post_time else None,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "platform": self.platform
        }

class CompetitorCrawler:
    """竞品爬虫主类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.driver = None
        
        # 24小时时间范围
        self.time_cutoff = datetime.now() - timedelta(hours=24)
    
    def crawl_by_config(self, config: Dict[str, Any]) -> List[CompetitorPost]:
        """根据配置爬取内容"""
        posts = []
        
        if config['config_type'] == 'account':
            # 账号链接模式
            posts = self.crawl_account_posts(config['account_url'])
        elif config['config_type'] == 'keyword':
            # 关键词模式
            keywords = config['keywords'].split('/') if config['keywords'] else []
            posts = self.crawl_website_posts(config['website_url'], keywords)
        elif config['config_type'] == 'webpage_update':
            # 网页更新模式
            posts = self.crawl_webpage_updates(config)
        
        # 过滤24小时内的内容
        recent_posts = []
        for post in posts:
            if post.post_time and post.post_time >= self.time_cutoff:
                recent_posts.append(post)
        
        logger.info(f"爬取完成：总计 {len(posts)} 条，24小时内 {len(recent_posts)} 条")
        return recent_posts
    
    def crawl_account_posts(self, account_url: str) -> List[CompetitorPost]:
        """爬取指定账号的帖子"""
        domain = urlparse(account_url).netloc.lower()
        
        if 'kickstarter.com' in domain:
            return self._crawl_kickstarter_account(account_url)
        elif 'reddit.com' in domain:
            return self._crawl_reddit_user(account_url)
        else:
            logger.warning(f"不支持的账号平台: {domain}")
            return []
    
    def crawl_website_posts(self, website_url: str, keywords: List[str]) -> List[CompetitorPost]:
        """爬取网站的关键词相关帖子"""
        domain = urlparse(website_url).netloc.lower()
        
        if 'reddit.com' in domain:
            return self._crawl_reddit_subreddit(website_url, keywords)
        elif 'kickstarter.com' in domain:
            return self._crawl_kickstarter_search(website_url, keywords)
        else:
            logger.warning(f"不支持的网站平台: {domain}")
            return []
    
    def _crawl_kickstarter_account(self, account_url: str) -> List[CompetitorPost]:
        """爬取Kickstarter账号页面"""
        posts = []
        
        try:
            logger.info(f"爬取Kickstarter账号: {account_url}")
            
            # 使用Selenium处理动态内容
            driver = self._init_webdriver()
            if not driver:
                return posts
            
            driver.get(account_url)
            time.sleep(3)
            
            # 查找项目列表
            project_elements = driver.find_elements(By.CSS_SELECTOR, '.project-card, .js-react-on-rails-component')
            
            for element in project_elements:
                try:
                    post = CompetitorPost()
                    post.platform = "Kickstarter"
                    
                    # 提取项目标题
                    title_element = element.find_element(By.CSS_SELECTOR, 'h3 a, .project-title a')
                    if title_element:
                        post.title = title_element.text.strip()
                        post.post_url = title_element.get_attribute('href')
                    
                    # 提取作者
                    author_element = element.find_element(By.CSS_SELECTOR, '.by-author a, .creator-name')
                    if author_element:
                        post.author = author_element.text.strip()
                    
                    # 提取描述
                    desc_element = element.find_element(By.CSS_SELECTOR, '.project-description, .description')
                    if desc_element:
                        post.content = desc_element.text.strip()
                    
                    # 提取时间（Kickstarter比较复杂，设置为当前时间）
                    post.post_time = datetime.now()
                    
                    if post.title:
                        posts.append(post)
                        
                except Exception as e:
                    logger.debug(f"解析Kickstarter项目失败: {e}")
                    continue
            
            driver.quit()
            
        except Exception as e:
            logger.error(f"爬取Kickstarter账号失败: {e}")
            if self.driver:
                self.driver.quit()
        
        return posts
    
    def _crawl_reddit_subreddit(self, subreddit_url: str, keywords: List[str]) -> List[CompetitorPost]:
        """爬取Reddit子版块 - 使用验证有效的JSON API方法"""
        posts = []
        
        try:
            logger.info(f"🚀 爬取Reddit子版块: {subreddit_url}")
            
            # 从URL提取subreddit名称
            if '/r/' in subreddit_url:
                subreddit = subreddit_url.split('/r/')[-1].split('/')[0]
            else:
                logger.error(f"无效的Reddit URL: {subreddit_url}")
                return []
            
            # 构造JSON API URL（已验证有效）
            json_url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=25"
            logger.info(f"📡 使用验证有效的JSON API: {json_url}")
            
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
            import random
            time.sleep(random.uniform(2, 4))
            
            # 发送请求
            response = self.session.get(json_url, headers=headers, timeout=30)
            
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
            
            # 24小时前的时间戳
            from datetime import datetime, timedelta
            twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
            twenty_four_hours_timestamp = twenty_four_hours_ago.timestamp()
            
            # 处理帖子数据
            for item in data['data']['children']:
                try:
                    post_data = item['data']
                    
                    # 检查时间（UTC时间戳）
                    created_utc = post_data.get('created_utc', 0)
                    if created_utc < twenty_four_hours_timestamp:
                        continue  # 跳过24小时前的帖子
                    
                    # 提取帖子信息
                    title = post_data.get('title', '').strip()
                    if not title:
                        continue
                    
                    # 关键词过滤
                    if keywords:
                        if not any(keyword.lower() in title.lower() for keyword in keywords):
                            continue
                    
                    # 构造帖子对象
                    post = CompetitorPost()
                    post.title = title
                    post.content = post_data.get('selftext', '')
                    post.author = post_data.get('author', 'unknown')
                    post.post_time = datetime.fromtimestamp(created_utc)
                    post.post_url = f"https://www.reddit.com{post_data.get('permalink', '')}"
                    post.likes_count = post_data.get('score', 0)
                    post.comments_count = post_data.get('num_comments', 0)
                    post.platform = 'Reddit'
                    
                    posts.append(post)
                    
                except Exception as e:
                    logger.warning(f"处理帖子数据时出错: {e}")
                    continue
            
            logger.success(f"✅ Reddit爬取成功: 总计 {len(data['data']['children'])} 条，24小时内 {len(posts)} 条")
            return posts
            
        except Exception as e:
            logger.error(f"爬取Reddit子版块失败: {e}")
            return []
    
    def _crawl_reddit_json_api(self, subreddit_url: str, keywords: List[str]) -> List[CompetitorPost]:
        """使用Reddit JSON API爬取"""
        posts = []
        
        try:
            # 构造JSON API URL
            # 例如: https://www.reddit.com/r/xToolOfficial/ -> https://www.reddit.com/r/xToolOfficial/new.json
            base_url = subreddit_url.rstrip('/')
            json_url = base_url + '/new.json?limit=25'
            
            # 设置请求头模拟真实浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # 发送请求
            response = self.session.get(json_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # 检查是否返回有效JSON
            try:
                data = response.json()
            except:
                logger.warning("响应不是有效JSON，可能被重定向或阻止")
                return posts
            
            # 检查数据结构
            if not isinstance(data, dict) or 'data' not in data:
                logger.warning("JSON响应格式不符合预期")
                return posts
            
            children = data.get('data', {}).get('children', [])
            logger.info(f"从JSON API获取到 {len(children)} 个原始帖子")
            
            # 处理每个帖子
            for item in children:
                try:
                    post_data = item.get('data', {})
                    if not post_data:
                        continue
                    
                    # 检查时间限制（24小时内）
                    created_utc = post_data.get('created_utc', 0)
                    if not self._is_within_24_hours(created_utc):
                        continue
                    
                    # 提取帖子信息
                    title = post_data.get('title', '').strip()
                    if not title:  # 跳过没有标题的帖子
                        continue
                    
                    content = post_data.get('selftext', '').strip()
                    author = post_data.get('author', '')
                    score = post_data.get('score', 0)
                    num_comments = post_data.get('num_comments', 0)
                    permalink = post_data.get('permalink', '')
                    
                    # 构建完整URL
                    post_url = f"https://www.reddit.com{permalink}" if permalink else subreddit_url
                    
                    # 关键词过滤
                    if keywords:
                        content_text = (title + ' ' + content).lower()
                        if not any(keyword.lower() in content_text for keyword in keywords):
                            continue
                    
                    # 创建帖子对象
                    post = CompetitorPost()
                    post.title = title
                    post.content = content[:500] if content else ""
                    post.author = author
                    post.post_time = datetime.fromtimestamp(created_utc) if created_utc > 0 else datetime.now()
                    post.post_url = post_url
                    post.likes_count = score if score > 0 else 0
                    post.comments_count = num_comments if num_comments > 0 else 0
                    post.platform = "Reddit"
                    
                    posts.append(post)
                    logger.debug(f"成功解析帖子: {title[:50]}")
                    
                except Exception as e:
                    logger.debug(f"解析单个帖子失败: {e}")
                    continue
            
            logger.info(f"JSON API最终获取 {len(posts)} 条有效帖子")
            return posts
            
        except Exception as e:
            logger.warning(f"Reddit JSON API爬取失败: {e}")
            return []
    
    def _crawl_reddit_selenium(self, subreddit_url: str, keywords: List[str]) -> List[CompetitorPost]:
        """使用Selenium爬取Reddit（备用方案）"""
        posts = []
        
        try:
            # 构造新帖子URL  
            if not subreddit_url.endswith('/'):
                subreddit_url += '/'
            new_posts_url = subreddit_url + 'new/'
            
            # 先尝试无头浏览器方式
            driver = self._init_webdriver()
            if not driver:
                logger.warning("WebDriver初始化失败")
                return posts
            
            try:
                driver.get(new_posts_url)
                time.sleep(5)  # 等待页面加载
                
                # 检查是否被阻止
                page_source = driver.page_source
                if "blocked by network security" in page_source.lower() or "you've been blocked" in page_source.lower():
                    logger.warning("Reddit访问被网络安全阻止")
                    with open('reddit_debug.html', 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    logger.info("调试信息已保存到 reddit_debug.html")
                    return posts
                
                # 尝试多种可能的帖子选择器
                post_selectors = [
                    'shreddit-post',  # 新版Reddit
                    '[data-testid="post-container"]',  # 中版Reddit 
                    'div[data-click-id="body"]',  # 旧版Reddit
                    '.Post',  # 备用选择器
                    'article'  # 通用文章标签
                ]
                
                post_elements = []
                for selector in post_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"使用选择器 {selector} 找到 {len(elements)} 个帖子")
                        post_elements = elements
                        break
                
                if not post_elements:
                    logger.warning("未找到任何帖子元素")
                    with open('reddit_debug.html', 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    logger.info("页面源码已保存到 reddit_debug.html")
                    return posts
                
                for element in post_elements[:20]:  # 限制最多处理20个帖子
                    try:
                        post = CompetitorPost()
                        post.platform = "Reddit"
                        
                        # 提取标题 - 尝试多种选择器
                        title_selectors = [
                            'h3 a[slot="title"]',
                            'h3 a',
                            '[data-testid="post-content"] h3',
                            '.title a',
                            'a[data-click-id="title"]',
                            'shreddit-post h3'
                        ]
                        
                        title_found = False
                        for title_selector in title_selectors:
                            try:
                                title_element = element.find_element(By.CSS_SELECTOR, title_selector)
                                if title_element:
                                    post.title = title_element.text.strip()
                                    post.post_url = title_element.get_attribute('href') or ''
                                    title_found = True
                                    break
                            except:
                                continue
                        
                        if not title_found:
                            # 如果没找到标题链接，尝试直接找标题文本
                            try:
                                title_element = element.find_element(By.TAG_NAME, 'h3')
                                post.title = title_element.text.strip()
                            except:
                                continue
                        
                        # 提取作者
                        author_selectors = [
                            'shreddit-post-author-line a',
                            '[data-testid="post_author_link"]',
                            '.author',
                            'a[href*="/user/"]'
                        ]
                        
                        for author_selector in author_selectors:
                            try:
                                author_element = element.find_element(By.CSS_SELECTOR, author_selector)
                                post.author = author_element.text.strip().replace('u/', '')
                                break
                            except:
                                continue
                        
                        # 提取时间
                        time_selectors = [
                            'shreddit-post-author-line time',
                            'time',
                            '[data-testid="post_timestamp"]',
                            '.live-timestamp'
                        ]
                        
                        post_time_found = False
                        for time_selector in time_selectors:
                            try:
                                time_element = element.find_element(By.CSS_SELECTOR, time_selector)
                                time_str = time_element.get_attribute('datetime') or time_element.get_attribute('title') or time_element.text
                                post.post_time = self._parse_reddit_time(time_str)
                                post_time_found = True
                                break
                            except:
                                continue
                        
                        if not post_time_found:
                            post.post_time = datetime.now()
                        
                        # 提取内容预览
                        try:
                            content_element = element.find_element(By.CSS_SELECTOR, '[data-testid="post-content"] div, .usertext-body, p')
                            post.content = content_element.text.strip()[:500]
                        except:
                            post.content = ""
                        
                        # 关键词过滤
                        if keywords:
                            content_text = (post.title + ' ' + post.content).lower()
                            if not any(keyword.lower() in content_text for keyword in keywords):
                                continue
                        
                        if post.title:
                            posts.append(post)
                            logger.debug(f"成功提取帖子: {post.title[:50]}")
                            
                    except Exception as e:
                        logger.debug(f"解析Reddit帖子失败: {e}")
                        continue
                
                driver.quit()
                
            except Exception as e:
                logger.error(f"Selenium爬取Reddit失败: {e}")
                if driver:
                    driver.quit()
                # 降级到静态请求
                return self._crawl_reddit_static(new_posts_url, keywords)
            
        except Exception as e:
            logger.error(f"爬取Reddit子版块失败: {e}")
        
        logger.info(f"Reddit爬取完成: {len(posts)} 条帖子")
        return posts
    
    def _crawl_reddit_static(self, url: str, keywords: List[str]) -> List[CompetitorPost]:
        """静态方式爬取Reddit（备用方案）"""
        posts = []
        
        try:
            # 尝试不同的User-Agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            # 如果返回的是登录页面，说明被重定向了
            if 'login' in response.url or 'sign_in' in response.url:
                logger.warning("被重定向到登录页面，无法访问内容")
                return posts
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试查找旧版Reddit的帖子
            post_elements = soup.select('.thing, .Post, div[data-domain]')
            
            for element in post_elements[:20]:
                try:
                    post = CompetitorPost()
                    post.platform = "Reddit"
                    
                    # 提取标题
                    title_element = element.select_one('.title a, h3 a, a.title')
                    if title_element:
                        post.title = title_element.get_text(strip=True)
                        href = title_element.get('href', '')
                        if href.startswith('/'):
                            post.post_url = 'https://www.reddit.com' + href
                        else:
                            post.post_url = href
                    
                    # 提取作者
                    author_element = element.select_one('.author, [data-author]')
                    if author_element:
                        post.author = author_element.get_text(strip=True)
                    
                    # 设置时间为当前时间（静态方式难以准确获取）
                    post.post_time = datetime.now()
                    
                    if post.title:
                        posts.append(post)
                        
                except Exception as e:
                    logger.debug(f"解析静态Reddit帖子失败: {e}")
                    continue
            
            logger.info(f"静态方式爬取Reddit: {len(posts)} 条")
            
        except Exception as e:
            logger.error(f"静态爬取Reddit失败: {e}")
        
        return posts
    
    def _crawl_reddit_user(self, user_url: str) -> List[CompetitorPost]:
        """爬取Reddit用户页面"""
        posts = []
        
        try:
            logger.info(f"爬取Reddit用户: {user_url}")
            
            response = self.session.get(user_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找用户发布的帖子
            post_elements = soup.select('[data-testid="post-container"], .thing')
            
            for element in post_elements:
                try:
                    post = CompetitorPost()
                    post.platform = "Reddit"
                    
                    # 提取标题
                    title_element = element.select_one('h3 a, .title a')
                    if title_element:
                        post.title = title_element.get_text(strip=True)
                        post.post_url = title_element.get('href', '')
                    
                    # 提取作者（从用户页面爬取，作者就是该用户）
                    post.author = user_url.split('/')[-1] if user_url.endswith('/') else user_url.split('/')[-1]
                    
                    # 提取时间
                    post.post_time = datetime.now()  # 简化处理
                    
                    if post.title:
                        posts.append(post)
                        
                except Exception as e:
                    logger.debug(f"解析Reddit用户帖子失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"爬取Reddit用户失败: {e}")
        
        return posts
    
    def _crawl_kickstarter_search(self, website_url: str, keywords: List[str]) -> List[CompetitorPost]:
        """爬取Kickstarter搜索结果"""
        posts = []
        
        for keyword in keywords:
            try:
                search_url = f"https://www.kickstarter.com/discover/advanced?term={keyword}&sort=newest"
                logger.info(f"搜索Kickstarter关键词: {keyword}")
                
                response = self.session.get(search_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找项目列表
                project_elements = soup.select('.project-card, .js-react-on-rails-component')
                
                for element in project_elements:
                    try:
                        post = CompetitorPost()
                        post.platform = "Kickstarter"
                        
                        # 提取项目信息
                        title_element = element.select_one('h3 a, .project-title a')
                        if title_element:
                            post.title = title_element.get_text(strip=True)
                            post.post_url = title_element.get('href', '')
                        
                        post.post_time = datetime.now()
                        
                        if post.title:
                            posts.append(post)
                            
                    except Exception as e:
                        logger.debug(f"解析Kickstarter搜索结果失败: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"搜索Kickstarter关键词失败 {keyword}: {e}")
        
        return posts
    
    def _parse_reddit_time(self, time_str: str) -> datetime:
        """解析Reddit时间"""
        try:
            # 尝试ISO格式
            if 'T' in time_str:
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            
            # 相对时间解析
            now = datetime.now()
            time_str = time_str.lower()
            
            if 'minute' in time_str:
                minutes = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(minutes=minutes)
            elif 'hour' in time_str:
                hours = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(hours=hours)
            elif 'day' in time_str:
                days = int(re.findall(r'(\d+)', time_str)[0])
                return now - timedelta(days=days)
            
        except Exception as e:
            logger.debug(f"解析时间失败: {time_str}, {e}")
        
        return datetime.now()
    
    def _init_webdriver(self) -> webdriver.Chrome:
        """初始化WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            return self.driver
        except Exception as e:
            logger.error(f"初始化WebDriver失败: {e}")
            return None
    
    def close(self):
        """关闭资源"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _is_within_24_hours(self, timestamp):
        """检查时间戳是否在24小时内"""
        try:
            if isinstance(timestamp, (int, float)):
                post_time = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                # 尝试解析时间字符串
                post_time = self._parse_reddit_time(timestamp)
            else:
                return True  # 如果无法解析，默认包含
            
            now = datetime.now()
            time_diff = now - post_time
            return time_diff.days == 0 and time_diff.seconds < 86400  # 24小时 = 86400秒
        except:
            return True
    
    def _crawl_reddit_html_direct(self, subreddit_url: str, keywords: List[str]) -> List[CompetitorPost]:
        """直接HTML解析Reddit页面（绕过API限制）"""
        posts = []
        
        try:
            # 确保URL格式正确
            if not subreddit_url.endswith('/'):
                subreddit_url += '/'
            new_url = subreddit_url + 'new/'
            
            logger.info(f"使用HTML方式爬取Reddit: {new_url}")
            
            # 设置逼真的浏览器头部
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,zh;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # 添加随机延迟
            import random
            time.sleep(random.uniform(3, 6))
            
            # 发送请求
            response = self.session.get(new_url, headers=headers, timeout=30)
            
            # 检查响应
            if response.status_code != 200:
                logger.warning(f"Reddit HTML访问失败，状态码: {response.status_code}")
                return posts
            
            html_content = response.text
            
            # 检查是否被阻止
            if 'blocked by network security' in html_content.lower():
                logger.error("Reddit HTML访问也被阻止")
                return posts
            
            # 保存调试信息
            try:
                with open('reddit_html_debug.html', 'w', encoding='utf-8') as f:
                    f.write(html_content[:5000])  # 只保存前5000字符
                logger.info("HTML调试信息已保存到 reddit_html_debug.html")
            except:
                pass
            
            # 使用BeautifulSoup解析
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尝试多种可能的帖子选择器（Reddit经常改变结构）
            post_selectors = [
                'shreddit-post',  # 新版Reddit
                '[data-testid="post-container"]',  # 中版Reddit
                '.Post',  # 旧版Reddit
                'article',  # 通用
                '[data-click-id="body"]',  # 另一种可能
                '.thing',  # 更旧的版本
            ]
            
            post_elements = []
            for selector in post_selectors:
                post_elements = soup.select(selector)
                if post_elements:
                    logger.info(f"使用选择器找到帖子: {selector}, 数量: {len(post_elements)}")
                    break
            
            if not post_elements:
                logger.warning("未找到任何帖子元素，尝试寻找链接")
                # 尝试寻找Reddit风格的链接
                link_elements = soup.find_all('a', href=True)
                post_links = []
                for link in link_elements:
                    href = link.get('href', '')
                    if '/comments/' in href and href.startswith(('/r/', 'https://www.reddit.com/r/')):
                        post_links.append({
                            'title': link.get_text(strip=True),
                            'url': href if href.startswith('http') else f"https://www.reddit.com{href}"
                        })
                
                logger.info(f"找到 {len(post_links)} 个帖子链接")
                
                # 为每个链接创建基本帖子对象
                for link_data in post_links[:10]:  # 限制处理数量
                    if link_data['title'] and len(link_data['title']) > 5:
                        post = CompetitorPost()
                        post.title = link_data['title']
                        post.content = ""
                        post.author = "unknown"
                        post.post_time = datetime.now()
                        post.post_url = link_data['url']
                        post.likes_count = 0
                        post.comments_count = 0
                        post.platform = "Reddit"
                        
                        # 关键词检查
                        if keywords:
                            if any(keyword.lower() in post.title.lower() for keyword in keywords):
                                posts.append(post)
                        else:
                            posts.append(post)
                
                logger.info(f"HTML链接方式获取 {len(posts)} 条帖子")
                return posts
            
            # 解析找到的帖子元素
            for element in post_elements[:15]:  # 限制处理数量
                try:
                    # 提取标题
                    title = ""
                    title_selectors = [
                        '[slot="title"]',
                        'h3',
                        '.title',
                        '[data-testid="post-content"] h3'
                    ]
                    
                    for title_sel in title_selectors:
                        title_elem = element.select_one(title_sel)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            break
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # 提取链接
                    url = ""
                    link_elem = element.find('a', href=True)
                    if link_elem:
                        href = link_elem.get('href', '')
                        if href.startswith('/'):
                            url = f"https://www.reddit.com{href}"
                        elif href.startswith('http'):
                            url = href
                    
                    # 提取作者（如果可能）
                    author = "unknown"
                    author_selectors = ['[slot="authorName"]', '.author', '[data-testid="comment_author_link"]']
                    for auth_sel in author_selectors:
                        auth_elem = element.select_one(auth_sel)
                        if auth_elem:
                            author = auth_elem.get_text(strip=True)
                            break
                    
                    # 创建帖子对象
                    post = CompetitorPost()
                    post.title = title
                    post.content = ""
                    post.author = author
                    post.post_time = datetime.now()  # HTML解析难以获取精确时间
                    post.post_url = url if url else subreddit_url
                    post.likes_count = 0
                    post.comments_count = 0
                    post.platform = "Reddit"
                    
                    # 关键词过滤
                    if keywords:
                        if any(keyword.lower() in title.lower() for keyword in keywords):
                            posts.append(post)
                    else:
                        posts.append(post)
                    
                    logger.debug(f"HTML解析获取帖子: {title[:50]}")
                    
                except Exception as e:
                    logger.debug(f"解析HTML帖子元素失败: {e}")
                    continue
            
            logger.info(f"HTML解析最终获取 {len(posts)} 条帖子")
            return posts
            
        except Exception as e:
            logger.error(f"Reddit HTML解析失败: {e}")
            return []
    
    def crawl_webpage_updates(self, config: dict) -> List[CompetitorPost]:
        """网页更新监控模式 - 智能差异检测，只报告更新部分"""
        posts = []
        webpage_url = config.get('webpage_url')
        stored_hash = config.get('content_hash')
        last_content = config.get('last_content', '')
        
        if not webpage_url:
            logger.warning("网页更新模式缺少webpage_url配置")
            return posts
        
        try:
            logger.info(f"🔍 智能检测网页更新: {webpage_url}")
            
            # 获取网页内容
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = self.session.get(webpage_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"网页访问失败，状态码: {response.status_code}")
                return posts
            
            # 提取并清理网页内容
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除不相关的标签
            for tag in soup(["script", "style", "nav", "footer", "header", "sidebar", "advertisement"]):
                tag.decompose()
            
            # 获取清理后的文本内容
            current_content = soup.get_text(separator='\n', strip=True)
            
            # 计算内容哈希
            import hashlib
            current_hash = hashlib.md5(current_content.encode('utf-8')).hexdigest()
            
            # 检查是否有更新
            if stored_hash and current_hash == stored_hash:
                logger.info("📋 网页内容无更新")
                return posts
            
            # 提取页面标题
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else "网页更新"
            
            if not last_content:
                # 首次爬取，记录全部内容
                logger.success(f"🆕 首次爬取网页: {title_text}")
                
                post = CompetitorPost()
                post.title = f"📋 {title_text} (首次建立监控)"
                post.content = current_content[:2000] + "..." if len(current_content) > 2000 else current_content
                post.author = "网页监控"
                post.post_time = datetime.now()
                post.post_url = webpage_url
                post.platform = "网页更新"
                post.likes_count = 0
                post.comments_count = 0
                
                posts.append(post)
                
            else:
                # 检测具体更新内容
                logger.success(f"🆕 检测到网页更新，分析差异: {title_text}")
                
                # 获取更新的具体内容
                updated_parts = self._extract_content_differences(last_content, current_content, soup)
                
                if updated_parts:
                    # 检查更新部分是否包含链接，并爬取链接内容
                    enriched_content = self._enrich_updates_with_links(updated_parts, webpage_url)
                    
                    post = CompetitorPost()
                    post.title = f"🔄 {title_text} (内容更新)"
                    post.content = enriched_content[:2000] + "..." if len(enriched_content) > 2000 else enriched_content
                    post.author = "网页监控"
                    post.post_time = datetime.now()
                    post.post_url = webpage_url
                    post.platform = "网页更新"
                    post.likes_count = 0
                    post.comments_count = 0
                    
                    posts.append(post)
                    logger.success(f"📄 发现更新内容，长度: {len(enriched_content)} 字符")
                else:
                    logger.info("📋 虽然哈希值变化，但未发现明显的内容更新")
            
            # 更新数据库中的哈希值和内容
            self._update_webpage_data(config['id'], current_hash, current_content)
            
            logger.success(f"✅ 智能网页更新监控完成，获取 {len(posts)} 条更新")
            
        except Exception as e:
            logger.error(f"❌ 网页更新监控失败: {e}")
        
        return posts
    
    def _extract_content_differences(self, old_content: str, new_content: str, soup: BeautifulSoup) -> str:
        """提取网页内容的具体差异部分"""
        try:
            import difflib
            
            # 按行分割内容进行对比
            old_lines = old_content.split('\n')
            new_lines = new_content.split('\n')
            
            # 使用difflib找出新增的行
            differ = difflib.unified_diff(old_lines, new_lines, lineterm='', n=0)
            diff_lines = list(differ)
            
            # 提取新增的内容行
            added_lines = []
            for line in diff_lines:
                if line.startswith('+ ') or line.startswith('+'):
                    clean_line = line[1:].strip() if line.startswith('+ ') else line[1:].strip()
                    if clean_line and len(clean_line) > 3:  # 过滤掉太短的行
                        added_lines.append(clean_line)
            
            if not added_lines:
                # 如果没有明显的新增行，尝试找到变化的段落
                added_lines = self._find_content_blocks_differences(old_content, new_content, soup)
            
            # 组合新增内容
            if added_lines:
                updated_content = '\n'.join(added_lines)
                logger.info(f"📄 检测到 {len(added_lines)} 行新增内容")
                return updated_content
            else:
                logger.info("📋 未检测到明显的内容差异")
                return ""
                
        except Exception as e:
            logger.error(f"内容差异分析失败: {e}")
            return ""
    
    def _find_content_blocks_differences(self, old_content: str, new_content: str, soup: BeautifulSoup) -> List[str]:
        """寻找内容块级别的差异"""
        try:
            # 尝试从HTML结构中提取新的内容块
            # 查找常见的内容块标签
            content_blocks = []
            
            for tag in soup.find_all(['article', 'section', 'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                block_text = tag.get_text(strip=True)
                if block_text and len(block_text) > 20:  # 只考虑有足够内容的块
                    # 检查这个块是否在旧内容中存在
                    if block_text not in old_content:
                        content_blocks.append(block_text)
            
            return content_blocks
            
        except Exception as e:
            logger.debug(f"内容块差异分析失败: {e}")
            return []
    
    def _enrich_updates_with_links(self, updated_content: str, base_url: str) -> str:
        """检查更新内容中的链接并爬取链接内容"""
        try:
            import re
            from urllib.parse import urljoin, urlparse
            
            enriched_content = f"🔄 **更新内容**:\n{updated_content}\n\n"
            
            # 提取链接（支持多种格式）
            link_patterns = [
                r'https?://[^\s<>"]+',  # 普通HTTP链接
                r'www\.[^\s<>"]+',      # www开头的链接
            ]
            
            found_links = set()
            for pattern in link_patterns:
                links = re.findall(pattern, updated_content, re.IGNORECASE)
                for link in links:
                    # 标准化链接
                    if not link.startswith('http'):
                        link = 'https://' + link
                    
                    # 验证链接是否有效
                    try:
                        parsed = urlparse(link)
                        if parsed.netloc:
                            found_links.add(link)
                    except:
                        continue
            
            if found_links:
                logger.info(f"🔗 在更新内容中发现 {len(found_links)} 个链接，开始爬取")
                
                enriched_content += "🔗 **相关链接内容**:\n"
                
                for i, link in enumerate(list(found_links)[:3], 1):  # 最多处理3个链接
                    try:
                        logger.info(f"📎 爬取链接 {i}: {link}")
                        
                        # 爬取链接内容
                        link_content = self._crawl_link_content(link)
                        
                        if link_content:
                            enriched_content += f"\n**链接 {i}**: {link}\n"
                            enriched_content += f"**内容摘要**: {link_content[:500]}{'...' if len(link_content) > 500 else ''}\n"
                        else:
                            enriched_content += f"\n**链接 {i}**: {link} (无法获取内容)\n"
                            
                    except Exception as e:
                        logger.warning(f"爬取链接失败 {link}: {e}")
                        enriched_content += f"\n**链接 {i}**: {link} (爬取失败)\n"
                        continue
            
            return enriched_content
            
        except Exception as e:
            logger.error(f"链接内容丰富化失败: {e}")
            return updated_content
    
    def _crawl_link_content(self, url: str) -> str:
        """爬取单个链接的内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return ""
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除不相关的标签
            for tag in soup(["script", "style", "nav", "footer", "header", "sidebar", "advertisement"]):
                tag.decompose()
            
            # 提取主要内容
            content = soup.get_text(separator=' ', strip=True)
            
            # 清理和缩短内容
            lines = content.split('\n')
            meaningful_lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
            
            return '\n'.join(meaningful_lines[:20])  # 最多20行
            
        except Exception as e:
            logger.debug(f"链接内容爬取失败 {url}: {e}")
            return ""
    
    def _update_webpage_data(self, config_id: int, new_hash: str, new_content: str):
        """更新配置中的网页数据（哈希值和内容）"""
        try:
            from models.competitor_models import db, MonitorConfig
            
            config = MonitorConfig.query.get(config_id)
            if config:
                config.content_hash = new_hash
                config.last_content = new_content
                db.session.commit()
                logger.debug(f"已更新配置 {config_id} 的网页数据")
            
        except Exception as e:
            logger.error(f"更新网页数据失败: {e}") 