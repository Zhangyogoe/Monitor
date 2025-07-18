from typing import Dict, Any, Optional
from loguru import logger
from .base_crawler import BaseCrawler, GenericCrawler
from .weibo_crawler import WeiboCrawler
from .product_crawler import ProductCrawler
from .youtube_crawler import YouTubeCrawler

class CrawlerFactory:
    """爬虫工厂类"""
    
    # 爬虫类型映射
    CRAWLER_MAP = {
        "generic": GenericCrawler,
        "weibo": WeiboCrawler,
        "product": ProductCrawler,  # 产品网站专用爬虫
        "youtube": YouTubeCrawler,  # YouTube视频爬虫
        # 可以继续添加其他网站的爬虫
        # "zhihu": ZhihuCrawler,
        # "xiaohongshu": XiaohongshuCrawler,
        # "douban": DoubanCrawler,
    }
    
    @classmethod
    def create_crawler(cls, website_config: Dict[str, Any]) -> Optional[BaseCrawler]:
        """创建爬虫实例"""
        crawler_type = website_config.get("crawler_type", "generic")
        
        if crawler_type not in cls.CRAWLER_MAP:
            logger.error(f"不支持的爬虫类型: {crawler_type}")
            return None
        
        try:
            crawler_class = cls.CRAWLER_MAP[crawler_type]
            return crawler_class(website_config)
        except Exception as e:
            logger.error(f"创建爬虫失败: {e}")
            return None
    
    @classmethod
    def get_supported_crawlers(cls) -> list:
        """获取支持的爬虫类型列表"""
        return list(cls.CRAWLER_MAP.keys())
    
    @classmethod
    def register_crawler(cls, crawler_type: str, crawler_class: type):
        """注册新的爬虫类型"""
        if not issubclass(crawler_class, BaseCrawler):
            raise ValueError("爬虫类必须继承自BaseCrawler")
        
        cls.CRAWLER_MAP[crawler_type] = crawler_class
        logger.info(f"注册爬虫类型: {crawler_type}")

# 示例网站配置
EXAMPLE_CONFIGS = {
    "weibo": {
        "name": "微博",
        "url": "https://weibo.com",
        "crawler_type": "weibo",
        "config_data": {}
    },
    "zhihu": {
        "name": "知乎",
        "url": "https://www.zhihu.com",
        "crawler_type": "generic",
        "config_data": {
            "search_url_template": "https://www.zhihu.com/search?type=content&q={keyword}",
            "selectors": {
                "post_list": ".ContentItem",
                "title": ".ContentItem-title a",
                "author": ".AuthorInfo-name",
                "content": ".RichContent-inner",
                "url": ".ContentItem-title a",
                "time": ".ContentItem-time",
                "likes": ".VoteButton--up",
                "comments": ".ContentItem-action button:contains('评论')"
            },
            "comment_selectors": {
                "comment_list": ".CommentItem",
                "content": ".CommentItem-content",
                "author": ".CommentItem-author",
                "time": ".CommentItem-time",
                "likes": ".CommentItem-vote"
            }
        }
    },
    "xiaohongshu": {
        "name": "小红书",
        "url": "https://www.xiaohongshu.com",
        "crawler_type": "generic",
        "config_data": {
            "search_url_template": "https://www.xiaohongshu.com/search_result?keyword={keyword}",
            "selectors": {
                "post_list": ".note-item",
                "title": ".title",
                "author": ".author",
                "content": ".desc",
                "url": "a",
                "time": ".time",
                "likes": ".like-count",
                "comments": ".comment-count"
            },
            "comment_selectors": {
                "comment_list": ".comment-item",
                "content": ".comment-content",
                "author": ".comment-author",
                "time": ".comment-time",
                "likes": ".comment-like"
            }
        }
    },
    "douban": {
        "name": "豆瓣",
        "url": "https://www.douban.com",
        "crawler_type": "generic",
        "config_data": {
            "search_url_template": "https://www.douban.com/search?q={keyword}",
            "selectors": {
                "post_list": ".result",
                "title": ".result h3 a",
                "author": ".result .subject-cast",
                "content": ".result .content",
                "url": ".result h3 a",
                "time": ".result .time",
                "likes": ".result .rating_nums",
                "comments": ".result .pl"
            },
            "comment_selectors": {
                "comment_list": ".comment-item",
                "content": ".comment-content",
                "author": ".comment-author",
                "time": ".comment-time",
                "likes": ".comment-vote"
            }
        }
    },
    "wecreat": {
        "name": "WeCreate",
        "url": "https://www.wecreat.com",
        "crawler_type": "product",
        "config_data": {
            "priority_pages": [
                "/changelog", "/updates", "/releases", "/news",
                "/blog", "/announcements", "/feedback"
            ],
            "focus_content": [
                "产品动态", "版本更新", "用户反馈", "问题修复"
            ]
        }
    },
    "product_website": {
        "name": "通用产品网站",
        "url": "https://example-product.com",
        "crawler_type": "product",
        "config_data": {
            "priority_pages": [
                "/changelog", "/updates", "/releases", "/whatsnew"
            ],
            "focus_content": [
                "产品动态", "版本更新", "用户反馈"
            ]
        }
    },
    "youtube_wecreat": {
        "name": "WeCreate YouTube频道",
        "url": "https://www.youtube.com/@WeCreatOfficial/videos",
        "crawler_type": "youtube",
        "website_type": "视频",
        "crawl_mode": "time",
        "time_range_start": "2025-06-01",
        "config_data": {
            "focus_content": [
                "产品展示", "教程视频", "用户案例", "新品发布"
            ]
        }
    }
} 