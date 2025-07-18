import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from config.config import config

class PostData:
    """帖子数据结构"""
    def __init__(self):
        self.title: str = ""
        self.content: str = ""
        self.author: str = ""
        self.post_url: str = ""
        self.post_time: datetime = None
        self.likes_count: int = 0
        self.comments_count: int = 0
        self.source_website: str = ""
        self.matched_keywords: List[str] = []
        self.comments: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "post_url": self.post_url,
            "post_time": self.post_time.isoformat() if self.post_time else None,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "source_website": self.source_website,
            "matched_keywords": self.matched_keywords,
            "comments": self.comments
        }

class BaseCrawler(ABC):
    """基础爬虫类"""
    
    def __init__(self, website_config: Dict[str, Any]):
        self.website_config = website_config
        self.website_name = website_config.get("name", "")
        self.base_url = website_config.get("url", "")
        self.crawler_config = website_config.get("config_data", {})
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.crawler.user_agent
        })
        self.driver = None
    
    def init_webdriver(self) -> webdriver.Chrome:
        """初始化Chrome WebDriver"""
        if self.driver:
            return self.driver
            
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"--user-agent={config.crawler.user_agent}")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(config.crawler.timeout)
            return self.driver
        except Exception as e:
            logger.error(f"初始化WebDriver失败: {e}")
            return None
    
    def close_webdriver(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def make_request(self, url: str, method: str = "GET", **kwargs) -> Optional[requests.Response]:
        """发送HTTP请求"""
        try:
            response = self.session.request(method, url, timeout=config.crawler.timeout, **kwargs)
            response.raise_for_status()
            
            # 请求延迟
            time.sleep(config.crawler.request_delay)
            
            return response
        except Exception as e:
            logger.error(f"请求失败 {url}: {e}")
            return None
    
    def check_keyword_match(self, text: str, keywords: List[str]) -> List[str]:
        """检查文本是否匹配关键词"""
        matched = []
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)
        
        return matched
    
    def parse_datetime(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        # 这里可以根据不同网站的时间格式进行适配
        time_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%m-%d %H:%M",
            "%Y-%m-%d",
        ]
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"无法解析时间格式: {time_str}")
        return None
    
    @abstractmethod
    def crawl_posts(self, keywords: List[str], limit: int = 50) -> List[PostData]:
        """爬取帖子数据"""
        pass
    
    @abstractmethod
    def crawl_comments(self, post_url: str, limit: int = 20) -> List[Dict[str, Any]]:
        """爬取评论数据"""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_webdriver()

class GenericCrawler(BaseCrawler):
    """通用爬虫实现"""
    
    def crawl_posts(self, keywords: List[str], limit: int = 50) -> List[PostData]:
        """爬取帖子数据"""
        posts = []
        
        # 获取配置
        selectors = self.crawler_config.get("selectors", {})
        search_url_template = self.crawler_config.get("search_url_template", "")
        
        if not search_url_template:
            logger.error(f"未配置搜索URL模板: {self.website_name}")
            return posts
        
        # 遍历关键词
        for keyword in keywords:
            try:
                # 构造搜索URL
                search_url = search_url_template.format(keyword=keyword)
                logger.info(f"开始爬取: {search_url}")
                
                # 发送请求
                response = self.make_request(search_url)
                if not response:
                    continue
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取帖子列表
                post_elements = soup.select(selectors.get("post_list", ""))
                
                for element in post_elements[:limit]:
                    try:
                        post = self.parse_post_element(element, keyword, selectors)
                        if post and post.title:
                            posts.append(post)
                    except Exception as e:
                        logger.error(f"解析帖子元素失败: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"爬取关键词'{keyword}'失败: {e}")
                continue
        
        return posts
    
    def parse_post_element(self, element, keyword: str, selectors: Dict[str, str]) -> Optional[PostData]:
        """解析帖子元素"""
        try:
            post = PostData()
            post.source_website = self.website_name
            post.matched_keywords = [keyword]
            
            # 提取标题
            title_element = element.select_one(selectors.get("title", ""))
            if title_element:
                post.title = title_element.get_text(strip=True)
            
            # 提取作者
            author_element = element.select_one(selectors.get("author", ""))
            if author_element:
                post.author = author_element.get_text(strip=True)
            
            # 提取内容
            content_element = element.select_one(selectors.get("content", ""))
            if content_element:
                post.content = content_element.get_text(strip=True)
            
            # 提取URL
            url_element = element.select_one(selectors.get("url", ""))
            if url_element:
                post.post_url = url_element.get("href", "")
                if post.post_url.startswith("/"):
                    post.post_url = self.base_url + post.post_url
            
            # 提取时间
            time_element = element.select_one(selectors.get("time", ""))
            if time_element:
                time_str = time_element.get_text(strip=True)
                post.post_time = self.parse_datetime(time_str)
            
            # 提取点赞数
            likes_element = element.select_one(selectors.get("likes", ""))
            if likes_element:
                likes_text = likes_element.get_text(strip=True)
                try:
                    post.likes_count = int(''.join(filter(str.isdigit, likes_text)))
                except:
                    post.likes_count = 0
            
            # 提取评论数
            comments_element = element.select_one(selectors.get("comments", ""))
            if comments_element:
                comments_text = comments_element.get_text(strip=True)
                try:
                    post.comments_count = int(''.join(filter(str.isdigit, comments_text)))
                except:
                    post.comments_count = 0
            
            return post
            
        except Exception as e:
            logger.error(f"解析帖子元素失败: {e}")
            return None
    
    def crawl_comments(self, post_url: str, limit: int = 20) -> List[Dict[str, Any]]:
        """爬取评论数据"""
        comments = []
        
        try:
            response = self.make_request(post_url)
            if not response:
                return comments
            
            soup = BeautifulSoup(response.text, 'html.parser')
            selectors = self.crawler_config.get("comment_selectors", {})
            
            comment_elements = soup.select(selectors.get("comment_list", ""))
            
            for element in comment_elements[:limit]:
                try:
                    comment = {}
                    
                    # 提取评论内容
                    content_element = element.select_one(selectors.get("content", ""))
                    if content_element:
                        comment["content"] = content_element.get_text(strip=True)
                    
                    # 提取评论作者
                    author_element = element.select_one(selectors.get("author", ""))
                    if author_element:
                        comment["author"] = author_element.get_text(strip=True)
                    
                    # 提取评论时间
                    time_element = element.select_one(selectors.get("time", ""))
                    if time_element:
                        time_str = time_element.get_text(strip=True)
                        comment["comment_time"] = self.parse_datetime(time_str)
                    
                    # 提取点赞数
                    likes_element = element.select_one(selectors.get("likes", ""))
                    if likes_element:
                        likes_text = likes_element.get_text(strip=True)
                        try:
                            comment["likes_count"] = int(''.join(filter(str.isdigit, likes_text)))
                        except:
                            comment["likes_count"] = 0
                    
                    if comment.get("content"):
                        comments.append(comment)
                        
                except Exception as e:
                    logger.error(f"解析评论元素失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"爬取评论失败 {post_url}: {e}")
        
        return comments 