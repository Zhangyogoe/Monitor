import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from models.database import CrawledPost

class DataFilterService:
    """数据过滤服务"""
    
    def __init__(self):
        # 过滤规则配置
        self.filter_rules = {
            "min_content_length": 10,  # 最小内容长度
            "max_content_length": 5000,  # 最大内容长度
            "min_likes_count": 0,  # 最小点赞数
            "blocked_keywords": [  # 屏蔽关键词
                "广告", "推广", "刷单", "兼职", "代购", "微商",
                "加微信", "联系QQ", "点击链接", "立即下载"
            ],
            "spam_patterns": [  # 垃圾内容模式
                r"[QqＱ][QqＱ]?\s*[:：]\s*\d+",  # QQ号
                r"微信[：:]\s*\w+",  # 微信号
                r"电话[：:]\s*\d+",  # 电话号码
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",  # 链接
                r"[点击|扫码|下载|安装].{0,20}[链接|二维码|APP|应用]",  # 推广用词
            ],
            "duplicate_check_hours": 24,  # 去重时间范围（小时）
            "quality_score_threshold": 0.6,  # 质量分数阈值
        }
    
    def should_push(self, post: CrawledPost) -> bool:
        """判断是否应该推送帖子"""
        try:
            # 1. 基础过滤
            if not self.pass_basic_filter(post):
                return False
            
            # 2. 内容质量过滤
            if not self.pass_quality_filter(post):
                return False
            
            # 3. 垃圾内容过滤
            if not self.pass_spam_filter(post):
                return False
            
            # 4. 重复内容过滤
            if not self.pass_duplicate_filter(post):
                return False
            
            # 5. 质量分数评估
            quality_score = self.calculate_quality_score(post)
            if quality_score < self.filter_rules["quality_score_threshold"]:
                logger.info(f"质量分数过低: {post.title[:50]}, 分数: {quality_score:.2f}")
                return False
            
            logger.info(f"帖子通过过滤: {post.title[:50]}, 质量分数: {quality_score:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"过滤判断异常: {str(e)}")
            return False
    
    def pass_basic_filter(self, post: CrawledPost) -> bool:
        """基础过滤"""
        # 检查内容长度
        content_length = len(post.content or "")
        if content_length < self.filter_rules["min_content_length"]:
            logger.debug(f"内容过短: {post.title[:50]}, 长度: {content_length}")
            return False
        
        if content_length > self.filter_rules["max_content_length"]:
            logger.debug(f"内容过长: {post.title[:50]}, 长度: {content_length}")
            return False
        
        # 检查点赞数
        if post.likes_count < self.filter_rules["min_likes_count"]:
            logger.debug(f"点赞数过低: {post.title[:50]}, 点赞数: {post.likes_count}")
            return False
        
        # 检查必要字段
        if not post.title or not post.content:
            logger.debug(f"缺少必要字段: {post.title[:50]}")
            return False
        
        return True
    
    def pass_quality_filter(self, post: CrawledPost) -> bool:
        """内容质量过滤"""
        content = (post.title + " " + post.content).lower()
        
        # 检查屏蔽关键词
        for keyword in self.filter_rules["blocked_keywords"]:
            if keyword in content:
                logger.debug(f"包含屏蔽关键词: {post.title[:50]}, 关键词: {keyword}")
                return False
        
        # 检查重复字符比例
        if self.has_excessive_repeating_chars(content):
            logger.debug(f"重复字符过多: {post.title[:50]}")
            return False
        
        # 检查纯数字或符号内容
        if self.is_nonsense_content(content):
            logger.debug(f"无意义内容: {post.title[:50]}")
            return False
        
        return True
    
    def pass_spam_filter(self, post: CrawledPost) -> bool:
        """垃圾内容过滤"""
        content = post.title + " " + post.content
        
        # 检查垃圾内容模式
        for pattern in self.filter_rules["spam_patterns"]:
            if re.search(pattern, content, re.IGNORECASE):
                logger.debug(f"匹配垃圾模式: {post.title[:50]}, 模式: {pattern}")
                return False
        
        # 检查是否为营销内容
        if self.is_marketing_content(content):
            logger.debug(f"营销内容: {post.title[:50]}")
            return False
        
        return True
    
    def pass_duplicate_filter(self, post: CrawledPost) -> bool:
        """重复内容过滤"""
        # 检查时间范围内的重复内容
        check_time = datetime.now() - timedelta(hours=self.filter_rules["duplicate_check_hours"])
        
        # 检查标题相似度
        similar_posts = CrawledPost.query.filter(
            CrawledPost.created_at >= check_time,
            CrawledPost.source_website == post.source_website,
            CrawledPost.id != post.id
        ).all()
        
        for similar_post in similar_posts:
            if self.calculate_similarity(post.title, similar_post.title) > 0.8:
                logger.debug(f"重复标题: {post.title[:50]}")
                return False
            
            if self.calculate_similarity(post.content, similar_post.content) > 0.9:
                logger.debug(f"重复内容: {post.title[:50]}")
                return False
        
        return True
    
    def calculate_quality_score(self, post: CrawledPost) -> float:
        """计算内容质量分数"""
        score = 0.0
        
        # 基础分数
        score += 0.3
        
        # 内容长度分数 (0-0.2)
        content_length = len(post.content or "")
        if content_length >= 100:
            score += 0.2
        elif content_length >= 50:
            score += 0.1
        
        # 互动数据分数 (0-0.3)
        if post.likes_count > 0:
            score += min(0.2, post.likes_count * 0.01)
        
        if post.comments_count > 0:
            score += min(0.1, post.comments_count * 0.01)
        
        # 时效性分数 (0-0.2)
        if post.post_time:
            hours_ago = (datetime.now() - post.post_time).total_seconds() / 3600
            if hours_ago <= 24:
                score += 0.2
            elif hours_ago <= 72:
                score += 0.1
        
        # 关键词匹配分数 (0-0.2)
        if post.matched_keywords:
            score += min(0.2, len(post.matched_keywords) * 0.1)
        
        return min(1.0, score)
    
    def has_excessive_repeating_chars(self, text: str) -> bool:
        """检查是否有过多重复字符"""
        if len(text) == 0:
            return False
        
        # 检查单字符重复
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        max_count = max(char_counts.values())
        repeat_ratio = max_count / len(text)
        
        return repeat_ratio > 0.3  # 如果某个字符占比超过30%
    
    def is_nonsense_content(self, text: str) -> bool:
        """检查是否为无意义内容"""
        # 去除空格和标点
        clean_text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        
        if len(clean_text) == 0:
            return True
        
        # 检查是否主要是数字
        digit_count = sum(1 for char in clean_text if char.isdigit())
        digit_ratio = digit_count / len(clean_text)
        
        if digit_ratio > 0.7:
            return True
        
        # 检查是否主要是英文字母（对于中文内容）
        alpha_count = sum(1 for char in clean_text if char.isalpha() and ord(char) < 128)
        alpha_ratio = alpha_count / len(clean_text)
        
        if alpha_ratio > 0.8:
            return True
        
        return False
    
    def is_marketing_content(self, text: str) -> bool:
        """检查是否为营销内容"""
        marketing_keywords = [
            "限时", "优惠", "特价", "折扣", "免费", "赠送", 
            "立即", "马上", "快速", "专业", "权威", "独家",
            "保证", "承诺", "效果", "成功", "赚钱", "收益"
        ]
        
        marketing_count = 0
        for keyword in marketing_keywords:
            if keyword in text:
                marketing_count += 1
        
        return marketing_count >= 3  # 包含3个或以上营销关键词
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 简单的字符级相似度计算
        set1 = set(text1)
        set2 = set(text2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def update_filter_rules(self, new_rules: Dict[str, Any]):
        """更新过滤规则"""
        self.filter_rules.update(new_rules)
        logger.info(f"更新过滤规则: {new_rules}")
    
    def get_filter_rules(self) -> Dict[str, Any]:
        """获取当前过滤规则"""
        return self.filter_rules.copy()
    
    def mark_as_read(self, post_id: int):
        """标记帖子为已读"""
        try:
            post = CrawledPost.query.get(post_id)
            if post:
                post.is_read = True
                from models.database import db
                db.session.commit()
                logger.info(f"标记帖子为已读: {post.title[:50]}")
        except Exception as e:
            logger.error(f"标记已读失败: {str(e)}")
    
    def get_filtered_posts(self, source_website: str = None, 
                          limit: int = 20, is_pushed: bool = None) -> List[CrawledPost]:
        """获取过滤后的帖子列表"""
        try:
            query = CrawledPost.query
            
            if source_website:
                query = query.filter_by(source_website=source_website)
            
            if is_pushed is not None:
                query = query.filter_by(is_pushed=is_pushed)
            
            posts = query.order_by(CrawledPost.created_at.desc()).limit(limit).all()
            
            # 应用过滤规则
            filtered_posts = []
            for post in posts:
                if self.should_push(post):
                    filtered_posts.append(post)
            
            return filtered_posts
            
        except Exception as e:
            logger.error(f"获取过滤帖子失败: {str(e)}")
            return [] 