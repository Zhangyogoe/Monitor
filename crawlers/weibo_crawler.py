import re
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from .base_crawler import BaseCrawler, PostData

class WeiboCrawler(BaseCrawler):
    """微博爬虫"""
    
    def __init__(self, website_config: Dict[str, Any]):
        super().__init__(website_config)
        self.search_url = "https://s.weibo.com/weibo"
        self.mobile_search_url = "https://m.weibo.cn/search"
        
    def crawl_posts(self, keywords: List[str], limit: int = 50) -> List[PostData]:
        """爬取微博帖子"""
        posts = []
        
        # 初始化WebDriver
        driver = self.init_webdriver()
        if not driver:
            return posts
        
        try:
            for keyword in keywords:
                logger.info(f"开始爬取微博关键词: {keyword}")
                
                # 构造搜索URL
                search_url = f"{self.search_url}?q={keyword}&typeall=1&suball=1&timescope=custom:2023-01-01:2024-12-31&Refer=g"
                
                try:
                    driver.get(search_url)
                    time.sleep(3)  # 等待页面加载
                    
                    # 等待微博列表加载
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".card-wrap"))
                    )
                    
                    # 滚动加载更多内容
                    self.scroll_to_load_more(driver, limit)
                    
                    # 获取微博元素
                    post_elements = driver.find_elements(By.CSS_SELECTOR, ".card-wrap")
                    
                    for element in post_elements[:limit]:
                        try:
                            post = self.parse_weibo_element(element, keyword)
                            if post and post.title:
                                posts.append(post)
                        except Exception as e:
                            logger.error(f"解析微博元素失败: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"爬取关键词'{keyword}'失败: {e}")
                    continue
            
        finally:
            self.close_webdriver()
        
        return posts
    
    def parse_weibo_element(self, element, keyword: str) -> Optional[PostData]:
        """解析微博元素"""
        try:
            post = PostData()
            post.source_website = "微博"
            post.matched_keywords = [keyword]
            
            # 提取微博内容
            content_element = element.find_element(By.CSS_SELECTOR, ".txt")
            if content_element:
                post.content = content_element.text.strip()
                # 微博的标题就是内容的前50个字符
                post.title = post.content[:50] + "..." if len(post.content) > 50 else post.content
            
            # 提取作者信息
            try:
                author_element = element.find_element(By.CSS_SELECTOR, ".name")
                if author_element:
                    post.author = author_element.text.strip()
            except:
                pass
            
            # 提取链接
            try:
                link_element = element.find_element(By.CSS_SELECTOR, "a[href*='/u/']")
                if link_element:
                    post.post_url = link_element.get_attribute("href")
            except:
                pass
            
            # 提取时间
            try:
                time_element = element.find_element(By.CSS_SELECTOR, ".from")
                if time_element:
                    time_text = time_element.text.strip()
                    post.post_time = self.parse_weibo_time(time_text)
            except:
                pass
            
            # 提取点赞数
            try:
                like_element = element.find_element(By.CSS_SELECTOR, ".card-act li:nth-child(3)")
                if like_element:
                    like_text = like_element.text.strip()
                    post.likes_count = self.parse_number(like_text)
            except:
                pass
            
            # 提取转发数
            try:
                repost_element = element.find_element(By.CSS_SELECTOR, ".card-act li:nth-child(1)")
                if repost_element:
                    repost_text = repost_element.text.strip()
                    # 将转发数作为评论数的一部分
                    post.comments_count = self.parse_number(repost_text)
            except:
                pass
            
            # 提取评论数
            try:
                comment_element = element.find_element(By.CSS_SELECTOR, ".card-act li:nth-child(2)")
                if comment_element:
                    comment_text = comment_element.text.strip()
                    post.comments_count += self.parse_number(comment_text)
            except:
                pass
            
            return post
            
        except Exception as e:
            logger.error(f"解析微博元素失败: {e}")
            return None
    
    def parse_weibo_time(self, time_str: str) -> Optional[datetime]:
        """解析微博时间"""
        now = datetime.now()
        
        try:
            # 处理相对时间
            if "分钟前" in time_str:
                minutes = int(re.findall(r'(\d+)分钟前', time_str)[0])
                return now - timedelta(minutes=minutes)
            elif "小时前" in time_str:
                hours = int(re.findall(r'(\d+)小时前', time_str)[0])
                return now - timedelta(hours=hours)
            elif "今天" in time_str:
                time_part = re.findall(r'今天\s*(\d{2}:\d{2})', time_str)
                if time_part:
                    today = now.date()
                    time_obj = datetime.strptime(time_part[0], "%H:%M").time()
                    return datetime.combine(today, time_obj)
            elif "昨天" in time_str:
                time_part = re.findall(r'昨天\s*(\d{2}:\d{2})', time_str)
                if time_part:
                    yesterday = now.date() - timedelta(days=1)
                    time_obj = datetime.strptime(time_part[0], "%H:%M").time()
                    return datetime.combine(yesterday, time_obj)
            else:
                # 处理绝对时间
                date_patterns = [
                    r'(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})',
                    r'(\d{2}-\d{2})\s*(\d{2}:\d{2})',
                    r'(\d{4}年\d{2}月\d{2}日)\s*(\d{2}:\d{2})',
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, time_str)
                    if match:
                        date_part, time_part = match.groups()
                        if "年" in date_part:
                            date_obj = datetime.strptime(date_part, "%Y年%m月%d日").date()
                        elif len(date_part) == 5:  # MM-DD格式
                            date_obj = datetime.strptime(f"{now.year}-{date_part}", "%Y-%m-%d").date()
                        else:
                            date_obj = datetime.strptime(date_part, "%Y-%m-%d").date()
                        
                        time_obj = datetime.strptime(time_part, "%H:%M").time()
                        return datetime.combine(date_obj, time_obj)
            
        except Exception as e:
            logger.error(f"解析微博时间失败: {time_str}, {e}")
        
        return None
    
    def parse_number(self, text: str) -> int:
        """解析数字（支持万、千等单位）"""
        try:
            text = text.strip()
            if "万" in text:
                num = float(re.findall(r'([\d.]+)万', text)[0])
                return int(num * 10000)
            elif "千" in text:
                num = float(re.findall(r'([\d.]+)千', text)[0])
                return int(num * 1000)
            else:
                numbers = re.findall(r'\d+', text)
                return int(numbers[0]) if numbers else 0
        except:
            return 0
    
    def scroll_to_load_more(self, driver, target_count: int):
        """滚动加载更多内容"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        max_scrolls = 10  # 最多滚动10次
        
        while scroll_count < max_scrolls:
            # 滚动到页面底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 等待新内容加载
            time.sleep(2)
            
            # 计算新的滚动高度
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # 检查是否加载了足够的内容
            current_posts = len(driver.find_elements(By.CSS_SELECTOR, ".card-wrap"))
            if current_posts >= target_count:
                break
            
            # 如果页面高度没有变化，说明没有更多内容了
            if new_height == last_height:
                break
            
            last_height = new_height
            scroll_count += 1
    
    def crawl_comments(self, post_url: str, limit: int = 20) -> List[Dict[str, Any]]:
        """爬取微博评论"""
        comments = []
        
        # 初始化WebDriver
        driver = self.init_webdriver()
        if not driver:
            return comments
        
        try:
            driver.get(post_url)
            time.sleep(3)
            
            # 等待评论加载
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".comment_txt"))
                )
            except:
                logger.warning(f"未找到评论元素: {post_url}")
                return comments
            
            # 获取评论元素
            comment_elements = driver.find_elements(By.CSS_SELECTOR, ".comment_txt")
            
            for element in comment_elements[:limit]:
                try:
                    comment = {}
                    
                    # 提取评论内容
                    content_elem = element.find_element(By.CSS_SELECTOR, ".txt")
                    if content_elem:
                        comment["content"] = content_elem.text.strip()
                    
                    # 提取评论作者
                    try:
                        author_elem = element.find_element(By.CSS_SELECTOR, ".name")
                        if author_elem:
                            comment["author"] = author_elem.text.strip()
                    except:
                        pass
                    
                    # 提取评论时间
                    try:
                        time_elem = element.find_element(By.CSS_SELECTOR, ".time")
                        if time_elem:
                            time_text = time_elem.text.strip()
                            comment["comment_time"] = self.parse_weibo_time(time_text)
                    except:
                        pass
                    
                    # 提取点赞数
                    try:
                        like_elem = element.find_element(By.CSS_SELECTOR, ".like_num")
                        if like_elem:
                            like_text = like_elem.text.strip()
                            comment["likes_count"] = self.parse_number(like_text)
                    except:
                        comment["likes_count"] = 0
                    
                    if comment.get("content"):
                        comments.append(comment)
                        
                except Exception as e:
                    logger.error(f"解析评论元素失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"爬取评论失败 {post_url}: {e}")
        finally:
            self.close_webdriver()
        
        return comments 