#!/usr/bin/env python3
"""
Facebook爬虫适配器 - 适配BaseCrawler接口
"""

from typing import Dict, List, Any
from .base_crawler import BaseCrawler, PostData
from .facebook_crawler import FacebookCrawler as FacebookEngine
from loguru import logger

class FacebookCrawler(BaseCrawler):
    """Facebook爬虫适配器"""
    
    def __init__(self, website_config: Dict[str, Any]):
        super().__init__(website_config)
        self.facebook_engine = FacebookEngine()
        logger.info(f"✅ 初始化Facebook爬虫: {self.website_name}")
    
    def crawl_posts(self, keywords: List[str], limit: int = 50) -> List[PostData]:
        """爬取帖子数据"""
        posts = []
        
        try:
            logger.info(f"🕷️ 开始爬取Facebook页面: {self.base_url}")
            
            # 使用Facebook引擎爬取
            facebook_posts = self.facebook_engine.crawl_page(self.base_url, max_posts=limit)
            
            # 转换为BaseCrawler格式
            for fb_post in facebook_posts:
                post = PostData()
                post.title = fb_post.title
                post.content = fb_post.content
                post.author = fb_post.author
                post.post_url = fb_post.post_url
                post.post_time = fb_post.post_time
                post.likes_count = fb_post.likes_count
                post.comments_count = fb_post.comments_count
                post.source_website = self.website_name
                
                # 检查关键词匹配
                matched_keywords = self._check_keywords(post, keywords)
                if matched_keywords:
                    post.matched_keywords = matched_keywords
                    posts.append(post)
                    logger.debug(f"✅ 匹配关键词: {matched_keywords} - {post.title[:50]}...")
            
            logger.info(f"✅ Facebook爬取完成: {len(posts)}/{len(facebook_posts)} 条匹配")
            
        except Exception as e:
            logger.error(f"❌ Facebook爬取失败: {e}")
        
        return posts
    
    def crawl_comments(self, post_url: str, limit: int = 20) -> List[Dict[str, Any]]:
        """爬取评论数据 - Facebook评论爬取较复杂，暂时返回空列表"""
        logger.info(f"📝 Facebook评论爬取暂未实现: {post_url}")
        return []
    
    def _check_keywords(self, post: PostData, keywords: List[str]) -> List[str]:
        """检查帖子是否包含关键词"""
        matched = []
        
        # 检查内容
        content = f"{post.title} {post.content}".lower()
        
        for keyword in keywords:
            if keyword.lower() in content:
                matched.append(keyword)
        
        return matched
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            result = self.facebook_engine.test_crawl(self.base_url)
            return result.get('success', False)
        except Exception as e:
            logger.error(f"❌ Facebook连接测试失败: {e}")
            return False 