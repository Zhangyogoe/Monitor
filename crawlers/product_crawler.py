#!/usr/bin/env python3
"""
产品网站爬虫 - 专门针对产品动态、版本更新、用户反馈的爬虫
适用于 wecreat 等产品网站
"""

import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger

from crawlers.base_crawler import BaseCrawler

class ProductCrawler(BaseCrawler):
    """产品网站专用爬虫"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 产品网站特定配置
        self.product_selectors = {
            # 产品动态相关选择器
            'product_news': [
                '.news-item', '.product-update', '.announcement',
                '.release-note', '.product-news', '.update-item'
            ],
            # 版本更新选择器
            'version_updates': [
                '.version-item', '.release-item', '.changelog-item',
                '.update-log', '.version-note'
            ],
            # 用户反馈选择器
            'user_feedback': [
                '.feedback-item', '.review-item', '.comment-item',
                '.user-review', '.testimonial'
            ],
            # 标题选择器
            'title': [
                'h1', 'h2', 'h3', '.title', '.subject', 
                '.headline', '.news-title'
            ],
            # 内容选择器
            'content': [
                '.content', '.description', '.summary', 
                '.detail', '.text', 'p'
            ],
            # 时间选择器
            'time': [
                '.time', '.date', '.published', '.created',
                'time', '.timestamp', '.update-time'
            ],
            # 版本号选择器
            'version': [
                '.version', '.ver', '.release-version',
                '.version-number', '.build'
            ]
        }
        
        # 关键词映射
        self.keyword_patterns = {
            '产品动态': [
                '新功能', '产品更新', '功能发布', '产品发布',
                '新特性', '产品改进', '功能优化'
            ],
            '版本更新': [
                '版本', 'version', 'v\d+', '更新日志', 'changelog',
                '发布说明', 'release', '升级', 'update'
            ],
            '用户反馈': [
                '用户反馈', '客户评价', '用户评论', '反馈建议',
                '用户体验', '问题反馈', '建议'
            ],
            '问题修复': [
                '修复', 'fix', 'bug', '问题解决', '错误修正',
                '修正', '补丁', 'patch'
            ]
        }
    
    def parse_page(self, html: str, url: str) -> List[Dict[str, Any]]:
        """解析产品网站页面"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # 根据网站类型选择解析策略
            if 'wecreat' in url.lower():
                results.extend(self._parse_wecreat(soup, url))
            else:
                # 通用产品网站解析
                results.extend(self._parse_generic_product_site(soup, url))
            
            # 对结果进行分类和清理
            results = self._classify_and_clean_results(results, url)
            
            logger.info(f"产品网站 {url} 解析完成，获取 {len(results)} 条内容")
            
        except Exception as e:
            logger.error(f"解析产品网站页面失败 {url}: {e}")
        
        return results
    
    def _parse_wecreat(self, soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
        """解析 WeCreate 网站"""
        results = []
        
        # WeCreate 特定的选择器
        selectors_mapping = {
            # 更新日志页面
            'update': {
                'container': '.changelog-item, .update-item, .release-item',
                'title': '.title, h3, h2',
                'content': '.content, .description, .summary',
                'version': '.version, .ver',
                'date': '.date, .time, time'
            },
            # 产品新闻页面
            'news': {
                'container': '.news-item, .post-item, .article',
                'title': '.title, h1, h2, h3',
                'content': '.content, .excerpt, .summary',
                'date': '.date, .published, time'
            },
            # 用户反馈页面
            'feedback': {
                'container': '.feedback-item, .review, .comment',
                'title': '.title, h4',
                'content': '.content, .text, .message',
                'author': '.author, .user, .name',
                'date': '.date, .time, time'
            }
        }
        
        # 尝试每种类型的解析
        for page_type, selectors in selectors_mapping.items():
            items = soup.select(selectors['container'])
            
            for item in items:
                try:
                    result = self._extract_item_data(item, selectors, url)
                    if result:
                        result['page_type'] = page_type
                        results.append(result)
                except Exception as e:
                    logger.debug(f"解析项目失败: {e}")
        
        return results
    
    def _parse_generic_product_site(self, soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
        """通用产品网站解析"""
        results = []
        
        # 尝试多种常见的内容选择器
        content_selectors = [
            'article', '.article', '.post', '.news-item',
            '.update-item', '.changelog-item', '.release-item',
            '.content-item', '.list-item'
        ]
        
        for selector in content_selectors:
            items = soup.select(selector)
            if items:
                logger.debug(f"使用选择器 {selector} 找到 {len(items)} 个项目")
                
                for item in items:
                    result = self._extract_generic_item(item, url)
                    if result:
                        results.append(result)
                
                # 如果找到内容就停止尝试其他选择器
                if results:
                    break
        
        return results
    
    def _extract_item_data(self, item, selectors: Dict[str, str], url: str) -> Optional[Dict[str, Any]]:
        """从HTML元素中提取数据"""
        try:
            # 提取标题
            title_elem = item.select_one(selectors.get('title', ''))
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # 提取内容
            content_elem = item.select_one(selectors.get('content', ''))
            content = content_elem.get_text(strip=True) if content_elem else ''
            
            # 提取时间
            date_elem = item.select_one(selectors.get('date', ''))
            date_text = ''
            if date_elem:
                # 尝试多种时间属性
                date_text = (date_elem.get('datetime') or 
                           date_elem.get('data-time') or 
                           date_elem.get_text(strip=True))
            
            # 提取版本号（如果有）
            version_elem = item.select_one(selectors.get('version', ''))
            version = version_elem.get_text(strip=True) if version_elem else ''
            
            # 提取作者（如果有）
            author_elem = item.select_one(selectors.get('author', ''))
            author = author_elem.get_text(strip=True) if author_elem else ''
            
            # 基本验证
            if not title or len(title) < 5:
                return None
            
            return {
                'title': title,
                'content': content,
                'author': author,
                'post_time': self._parse_datetime(date_text),
                'post_url': self._extract_url(item, url),
                'version': version,
                'source_website': urlparse(url).netloc,
                'raw_data': {
                    'date_text': date_text,
                    'html_snippet': str(item)[:200] + '...'
                }
            }
            
        except Exception as e:
            logger.debug(f"提取项目数据失败: {e}")
            return None
    
    def _extract_generic_item(self, item, url: str) -> Optional[Dict[str, Any]]:
        """通用项目数据提取"""
        try:
            # 使用多种选择器尝试提取标题
            title = ''
            for selector in self.product_selectors['title']:
                title_elem = item.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # 提取内容
            content = ''
            for selector in self.product_selectors['content']:
                content_elem = item.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    break
            
            # 如果没有找到内容，使用整个item的文本
            if not content:
                content = item.get_text(strip=True)
            
            # 提取时间
            date_text = ''
            for selector in self.product_selectors['time']:
                date_elem = item.select_one(selector)
                if date_elem:
                    date_text = (date_elem.get('datetime') or 
                               date_elem.get_text(strip=True))
                    break
            
            # 基本验证
            if not title or len(title) < 5:
                return None
            
            return {
                'title': title,
                'content': content[:500],  # 限制内容长度
                'author': '',
                'post_time': self._parse_datetime(date_text),
                'post_url': self._extract_url(item, url),
                'source_website': urlparse(url).netloc,
                'raw_data': {
                    'date_text': date_text
                }
            }
            
        except Exception as e:
            logger.debug(f"通用项目提取失败: {e}")
            return None
    
    def _classify_and_clean_results(self, results: List[Dict[str, Any]], url: str) -> List[Dict[str, Any]]:
        """对结果进行分类和清理"""
        classified_results = []
        
        for result in results:
            # 内容分类
            category = self._classify_content(result['title'], result['content'])
            result['content_category'] = category
            
            # 清理和标准化数据
            result['title'] = self._clean_text(result['title'])
            result['content'] = self._clean_text(result['content'])
            
            # 提取版本信息
            if 'version' not in result or not result['version']:
                result['version'] = self._extract_version_from_text(
                    result['title'] + ' ' + result['content']
                )
            
            # 设置默认值
            result.setdefault('likes_count', 0)
            result.setdefault('comments_count', 0)
            result.setdefault('matched_keywords', [category] if category else [])
            
            classified_results.append(result)
        
        return classified_results
    
    def _classify_content(self, title: str, content: str) -> str:
        """根据内容对结果进行分类"""
        text = (title + ' ' + content).lower()
        
        for category, patterns in self.keyword_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        
        return '其他'
    
    def _extract_version_from_text(self, text: str) -> str:
        """从文本中提取版本号"""
        version_patterns = [
            r'v?(\d+\.\d+\.\d+)',
            r'version\s*(\d+\.\d+)',
            r'v(\d+\.\d+)',
            r'(\d+\.\d+\.\d+)',
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return ''
    
    def _parse_datetime(self, date_text: str) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not date_text:
            return None
        
        # 常见的日期格式
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{4}/\d{2}/\d{2})',
            r'(\d{2}-\d{2}-\d{4})',
            r'(\d{2}/\d{2}/\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    date_str = match.group(1)
                    # 尝试多种解析格式
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass
        
        # 如果解析失败，返回当前时间
        return datetime.now()
    
    def _extract_url(self, item, base_url: str) -> str:
        """提取链接地址"""
        # 尝试找到链接
        link_elem = item.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href')
            if href:
                return urljoin(base_url, href)
        
        return base_url
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ''
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()【】()，。！？；：]', '', text)
        
        return text
    
    def should_crawl_url(self, url: str) -> bool:
        """判断是否应该爬取该URL"""
        # 产品网站常见的页面类型
        product_indicators = [
            'update', 'changelog', 'release', 'news', 'blog',
            'announcement', 'feedback', 'review', 'version'
        ]
        
        url_lower = url.lower()
        return any(indicator in url_lower for indicator in product_indicators)
    
    def get_priority_urls(self, base_url: str) -> List[str]:
        """获取优先爬取的URL列表"""
        domain = urlparse(base_url).netloc
        
        priority_paths = [
            '/changelog', '/updates', '/releases', '/news',
            '/blog', '/announcements', '/feedback', '/reviews',
            '/version', '/whatsnew', '/release-notes'
        ]
        
        urls = []
        for path in priority_paths:
            urls.append(f"https://{domain}{path}")
            urls.append(f"http://{domain}{path}")
        
        return urls 