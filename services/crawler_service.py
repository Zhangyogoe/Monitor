from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger
from sqlalchemy import and_, or_
from models.database import (
    db, WebsiteConfig, KeywordConfig, CrawledPost, 
    CrawledComment, PushRecord, SystemLog
)
from crawlers.crawler_factory import CrawlerFactory
from services.feishu_service import feishu_service
from services.data_filter_service import DataFilterService
from services.resumable_service import resumable_service

class CrawlerService:
    """爬虫服务类"""
    
    def __init__(self):
        self.data_filter = DataFilterService()
    
    def crawl_all_websites(self, manual_trigger: bool = False) -> Dict[str, Any]:
        """爬取所有活跃网站的数据"""
        results = {
            "success": True,
            "total_posts": 0,
            "new_posts": 0,
            "pushed_posts": 0,
            "errors": []
        }
        
        try:
            # 获取所有活跃的网站配置
            websites = WebsiteConfig.query.filter_by(is_active=True).all()
            
            for website in websites:
                try:
                    # 获取该网站的关键词
                    keywords = KeywordConfig.query.filter_by(
                        website_id=website.id,
                        is_active=True
                    ).all()
                    
                    if not keywords:
                        logger.warning(f"网站 {website.name} 没有活跃的关键词配置")
                        continue
                    
                    # 爬取网站数据
                    website_result = self.crawl_website(website, keywords, manual_trigger)
                    
                    # 累计结果
                    results["total_posts"] += website_result["total_posts"]
                    results["new_posts"] += website_result["new_posts"]
                    results["pushed_posts"] += website_result["pushed_posts"]
                    
                    if website_result["errors"]:
                        results["errors"].extend(website_result["errors"])
                    
                except Exception as e:
                    error_msg = f"爬取网站 {website.name} 失败: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["success"] = False
            
            # 记录系统日志
            log_message = f"爬虫任务完成 - 总帖子数: {results['total_posts']}, 新帖子数: {results['new_posts']}, 推送数: {results['pushed_posts']}"
            if results["errors"]:
                log_message += f", 错误数: {len(results['errors'])}"
            
            self.log_system_event("crawler_service", "info", log_message, results)
            
            return results
            
        except Exception as e:
            error_msg = f"爬虫服务异常: {str(e)}"
            logger.error(error_msg)
            results["success"] = False
            results["errors"].append(error_msg)
            return results
    
    def crawl_website(self, website: WebsiteConfig, keywords: List[KeywordConfig] = None, 
                     manual_trigger: bool = False) -> Dict[str, Any]:
        """爬取单个网站的数据"""
        result = {
            "total_posts": 0,
            "new_posts": 0,
            "pushed_posts": 0,
            "errors": [],
            "resumed": False
        }
        
        try:
            # 创建爬虫实例，传递完整配置
            website_config = website.to_dict()
            # 确保传递时间范围配置
            if website.time_range_start:
                website_config['time_range_start'] = website.time_range_start.isoformat() if hasattr(website.time_range_start, 'isoformat') else str(website.time_range_start)
            
            crawler = CrawlerFactory.create_crawler(website_config)
            if not crawler:
                error_msg = f"无法创建爬虫: {website.name}"
                result["errors"].append(error_msg)
                return result
            
            # 准备关键词列表 - 支持新的配置方式
            keyword_list = []
            keyword_dict = {}
            
            if website.crawl_mode == 'keyword':
                # 关键词模式：使用网站配置的关键词或传入的关键词
                if website.crawl_keywords:
                    keyword_list = [kw.strip() for kw in website.crawl_keywords.split('/') if kw.strip()]
                elif keywords:
                    keyword_list = [kw.keyword for kw in keywords]
                    keyword_dict = {kw.keyword: kw for kw in keywords}
            else:
                # 时间模式：不使用关键词，传递空列表
                keyword_list = []
            
            # 检查是否需要断点续传
            session_id = f"crawl_{website.id}_{int(datetime.now().timestamp())}"
            should_resume = resumable_service.should_resume_crawl(website.id)
            
            if should_resume:
                resume_position = resumable_service.get_resume_position(website.id)
                result["resumed"] = True
                logger.info(f"断点续传爬取网站: {website.name}, 从位置: {resume_position}")
            else:
                resume_position = {"start_from_beginning": True}
                logger.info(f"开始爬取网站: {website.name}, 关键词: {keyword_list}")
            
            # 初始化检查点数据
            checkpoint_data = {
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "total_posts": 0,
                "pages_processed": resume_position.get("pages_processed", 0),
                "keywords_found": [],
                "last_url": resume_position.get("last_url"),
                "last_post_id": resume_position.get("last_post_id")
            }
            
            # 爬取帖子数据
            with crawler:
                posts = crawler.crawl_posts(keyword_list, limit=50)
                result["total_posts"] = len(posts)
                
                for i, post in enumerate(posts):
                    try:
                        # 更新检查点数据
                        checkpoint_data["pages_processed"] += 1
                        checkpoint_data["last_url"] = getattr(post, 'post_url', website.url)
                        
                        # 检查是否是新帖子
                        if self.is_new_post(post):
                            # 保存帖子数据
                            saved_post = self.save_post_data(post, website, keyword_dict)
                            if saved_post:
                                result["new_posts"] += 1
                                checkpoint_data["total_posts"] += 1
                                checkpoint_data["last_post_id"] = saved_post.id
                                
                                # 收集关键词
                                if saved_post.matched_keywords:
                                    checkpoint_data["keywords_found"].extend(saved_post.matched_keywords)
                                
                                # 生成AI总结（替代飞书推送）
                                if self.generate_ai_summary(saved_post):
                                    result["processed_posts"] = result.get("processed_posts", 0) + 1
                        
                        # 每处理10个帖子保存一次检查点
                        if (i + 1) % 10 == 0:
                            resumable_service.save_crawl_checkpoint(website.id, checkpoint_data)
                        
                    except Exception as e:
                        error_msg = f"处理帖子失败: {getattr(post, 'title', 'Unknown')[:50]}, 错误: {str(e)}"
                        logger.error(error_msg)
                        result["errors"].append(error_msg)
                        checkpoint_data["error"] = error_msg
                        continue
            
            # 保存最终检查点
            checkpoint_data["end_time"] = datetime.now().isoformat()
            checkpoint_data["completed"] = True
            resumable_service.save_crawl_checkpoint(website.id, checkpoint_data)
            
            logger.info(f"完成爬取网站: {website.name}, 结果: {result}")
            return result
            
        except Exception as e:
            error_msg = f"爬取网站 {website.name} 异常: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            
            # 保存错误检查点
            if 'checkpoint_data' in locals():
                checkpoint_data["error"] = error_msg
                checkpoint_data["end_time"] = datetime.now().isoformat()
                checkpoint_data["completed"] = False
                resumable_service.save_crawl_checkpoint(website.id, checkpoint_data)
            
            return result
    
    def is_new_post(self, post_data) -> bool:
        """检查是否是新帖子"""
        # 根据URL和标题检查是否已存在
        existing_post = CrawledPost.query.filter(
            or_(
                CrawledPost.post_url == post_data.post_url,
                and_(
                    CrawledPost.title == post_data.title,
                    CrawledPost.author == post_data.author,
                    CrawledPost.source_website == post_data.source_website
                )
            )
        ).first()
        
        return existing_post is None
    
    def save_post_data(self, post_data, website: WebsiteConfig, 
                      keyword_dict: Dict[str, KeywordConfig]) -> Optional[CrawledPost]:
        """保存帖子数据到数据库"""
        try:
            # 创建帖子记录
            post = CrawledPost(
                title=post_data.title,
                content=post_data.content,
                author=post_data.author,
                post_url=post_data.post_url,
                post_time=post_data.post_time,
                likes_count=post_data.likes_count,
                comments_count=post_data.comments_count,
                source_website=post_data.source_website,
                matched_keywords=post_data.matched_keywords,
                is_read=False,
                is_pushed=False
            )
            
            db.session.add(post)
            db.session.flush()  # 获取ID
            
            # 保存评论数据
            if post_data.comments:
                for comment_data in post_data.comments:
                    comment = CrawledComment(
                        post_id=post.id,
                        content=comment_data.get("content", ""),
                        author=comment_data.get("author", ""),
                        comment_time=comment_data.get("comment_time"),
                        likes_count=comment_data.get("likes_count", 0)
                    )
                    db.session.add(comment)
            
            db.session.commit()
            logger.info(f"保存帖子成功: {post.title[:50]}")
            return post
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"保存帖子失败: {str(e)}")
            return None
    
    def should_push_post(self, post: CrawledPost) -> bool:
        """判断是否应该推送帖子"""
        # 使用数据过滤服务进行过滤
        return self.data_filter.should_push(post)
    
    def generate_ai_summary(self, post: CrawledPost) -> bool:
        """为帖子生成AI总结"""
        try:
            # 检查是否已有总结
            if post.ai_summary:
                logger.info(f"帖子已有AI总结: {post.title[:50]}")
                return True
            
            # 导入AI总结服务
            from .ai_summary_service import AISummaryService
            ai_service = AISummaryService()
            
            # 生成总结
            summary = ai_service.summarize_content(
                title=post.title or "",
                content=post.content or "",
                max_length=150
            )
            
            # 保存总结
            post.ai_summary = summary
            db.session.commit()
            
            logger.info(f"✅ AI总结生成成功: {post.title[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI总结生成失败: {e}")
            return False
    
    def push_post_data(self, post: CrawledPost) -> bool:
        """推送帖子数据"""
        try:
            # 转换为字典格式
            post_dict = {
                "title": post.title,
                "content": post.content,
                "author": post.author,
                "post_url": post.post_url,
                "post_time": post.post_time.strftime("%Y-%m-%d %H:%M:%S") if post.post_time else "",
                "likes_count": post.likes_count,
                "comments_count": post.comments_count,
                "source_website": post.source_website,
                "matched_keywords": post.matched_keywords
            }
            
            # 推送到飞书工作流
            success = feishu_service.push_post_data(post_dict, template='workflow')
            
            # 记录推送结果
            push_record = PushRecord(
                post_id=post.id,
                push_type="feishu",
                target="default",
                status="success" if success else "failed",
                message="推送成功" if success else "推送失败"
            )
            db.session.add(push_record)
            
            # 更新帖子状态
            if success:
                post.is_pushed = True
                post.push_time = datetime.now()
            
            db.session.commit()
            
            return success
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"推送帖子失败: {str(e)}")
            return False
    
    def manual_crawl_keyword(self, website_id: int, keyword: str, limit: int = 20) -> Dict[str, Any]:
        """手动爬取指定关键词"""
        result = {
            "success": False,
            "posts": [],
            "message": ""
        }
        
        try:
            # 获取网站配置
            website = WebsiteConfig.query.get(website_id)
            if not website:
                result["message"] = "网站配置不存在"
                return result
            
            # 创建爬虫实例
            crawler = CrawlerFactory.create_crawler(website.to_dict())
            if not crawler:
                result["message"] = "无法创建爬虫实例"
                return result
            
            # 爬取数据
            with crawler:
                posts = crawler.crawl_posts([keyword], limit=limit)
                result["posts"] = [post.to_dict() for post in posts]
                result["success"] = True
                result["message"] = f"成功爬取 {len(posts)} 个帖子"
            
            return result
            
        except Exception as e:
            result["message"] = f"爬取失败: {str(e)}"
            logger.error(result["message"])
            return result
    
    def get_crawl_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取爬虫统计信息"""
        from datetime import timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            # 总帖子数
            total_posts = CrawledPost.query.filter(
                CrawledPost.created_at >= start_date
            ).count()
            
            # 按网站统计
            website_stats = db.session.query(
                CrawledPost.source_website,
                db.func.count(CrawledPost.id).label('count')
            ).filter(
                CrawledPost.created_at >= start_date
            ).group_by(CrawledPost.source_website).all()
            
            # 推送统计
            pushed_posts = CrawledPost.query.filter(
                CrawledPost.created_at >= start_date,
                CrawledPost.is_pushed == True
            ).count()
            
            # 热门关键词统计
            # 这里需要复杂的JSON查询，简化处理
            keyword_stats = []
            
            return {
                "total_posts": total_posts,
                "pushed_posts": pushed_posts,
                "push_rate": f"{(pushed_posts/total_posts*100):.1f}%" if total_posts > 0 else "0%",
                "website_stats": [{"website": ws[0], "count": ws[1]} for ws in website_stats],
                "keyword_stats": keyword_stats,
                "period": f"{days}天"
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}
    
    def log_system_event(self, module: str, level: str, message: str, extra_data: Dict[str, Any] = None):
        """记录系统事件"""
        try:
            log_entry = SystemLog(
                level=level,
                module=module,
                message=message,
                extra_data=extra_data
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.error(f"记录系统日志失败: {str(e)}")

# 全局服务实例
crawler_service = CrawlerService() 