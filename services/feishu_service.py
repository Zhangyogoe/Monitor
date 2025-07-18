#!/usr/bin/env python3
"""
飞书服务 - 包含Webhook机器人、工作流推送和多维表格集成
"""

import json
import time
import hashlib
import hmac
import base64
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger
from config.config import config
from .ai_summary_service import AISummaryService

class FeishuService:
    """飞书服务类 - 包含Webhook和多维表格功能"""
    
    def __init__(self):
        self.webhook_url = config.feishu.webhook_url
        self.webhook_secret = getattr(config.feishu, 'webhook_secret', None)
        
        # 飞书开放平台配置（用于多维表格）
        self.app_id = getattr(config.feishu, 'app_id', '')
        self.app_secret = getattr(config.feishu, 'app_secret', '')
        self.bitable_token = getattr(config.feishu, 'bitable_token', '')
        self.table_id = getattr(config.feishu, 'table_id', '')
        
        self.session = requests.Session()
        self.access_token = None
        self.token_expires_at = 0
        
        # AI总结服务
        self.ai_summary = AISummaryService()
        
        # 消息模板配置
        self.message_templates = {
            'default': self._get_default_template(),
            'simple': self._get_simple_template(),
            'detailed': self._get_detailed_template(),
            'workflow': self._get_workflow_template()
        }
    
    def _generate_signature(self, timestamp: str) -> str:
        """生成Webhook签名"""
        if not self.webhook_secret:
            return ""
        string_to_sign = f"{timestamp}\n{self.webhook_secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode('utf-8')
    
    def _get_access_token(self) -> Optional[str]:
        """获取飞书访问令牌（用于多维表格API）"""
        if not self.app_id or not self.app_secret:
            return None
            
        # 检查token是否过期
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                self.access_token = data["tenant_access_token"]
                self.token_expires_at = time.time() + data.get("expire", 7200) - 60  # 提前1分钟刷新
                logger.info("✅ 飞书访问令牌获取成功")
                return self.access_token
            else:
                logger.error(f"❌ 获取飞书访问令牌失败: {data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取飞书访问令牌异常: {e}")
            return None
    
    def send_webhook_message(self, message: str, msg_type: str = "text") -> bool:
        """发送Webhook消息"""
        if not self.webhook_url:
            logger.warning("⚠️ 未配置飞书Webhook URL")
            return False
            
        timestamp = str(int(time.time()))
        
        data = {
            "timestamp": timestamp,
            "msg_type": msg_type
        }
        
        # 添加签名
        if self.webhook_secret:
            data["sign"] = self._generate_signature(timestamp)
        
        # 构造消息体
        if msg_type == "text":
            data["content"] = {"text": message}
        elif msg_type == "rich_text":
            data["content"] = message
        elif msg_type == "interactive":
            data["card"] = message
        else:
            data["content"] = {"text": message}
        
        try:
            response = self.session.post(self.webhook_url, json=data)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0:
                logger.info("✅ Webhook消息发送成功")
                return True
            else:
                logger.error(f"❌ Webhook消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 发送Webhook消息异常: {e}")
            return False
    
    def send_card_message(self, card_data: Dict[str, Any]) -> bool:
        """发送卡片消息"""
        return self.send_webhook_message(card_data, "interactive")
    
    def send_workflow_data(self, post_data: Dict[str, Any]) -> bool:
        """发送数据到飞书工作流"""
        if not self.webhook_url:
            logger.warning("⚠️ 未配置飞书Webhook URL")
            return False
        
        try:
            # 生成AI总结
            title = post_data.get('title', '无标题')
            content = post_data.get('content', '无内容')
            url = post_data.get('post_url', '')
            
            # 对内容进行AI总结
            summary = self.ai_summary.summarize_content(title, content, max_length=150)
            
            # 构造工作流数据
            workflow_data = {
                "标题": title,
                "内容总结": summary,
                "原文链接": url
            }
            
            # 发送到工作流
            response = self.session.post(self.webhook_url, json=workflow_data)
            response.raise_for_status()
            
            logger.info(f"✅ 工作流数据推送成功 - 标题: {title[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ 工作流数据推送失败: {e}")
            return False
    
    def create_post_card(self, post_data: Dict[str, Any], template: str = 'default') -> Dict[str, Any]:
        """创建文章卡片"""
        template_func = self.message_templates.get(template, self.message_templates['default'])
        return template_func(post_data)
    
    def _get_default_template(self):
        """默认消息模板"""
        def template(post_data: Dict[str, Any]) -> Dict[str, Any]:
            title = post_data.get('title', '无标题')
            content = post_data.get('content', '无内容')
            url = post_data.get('post_url', '')
            source = post_data.get('source_website', '未知来源')
            keywords = post_data.get('matched_keywords', [])
            pub_time = post_data.get('post_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            likes_count = post_data.get('likes_count', 0)
            comments_count = post_data.get('comments_count', 0)
            
            # 截取内容
            if len(content) > 200:
                content = content[:200] + "..."
            
            # 构造卡片
            elements = [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**📰 {title}**",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "content": content,
                        "tag": "plain_text"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "content": f"**来源:** {source}",
                                "tag": "lark_md"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "content": f"**时间:** {pub_time}",
                                "tag": "lark_md"
                            }
                        }
                    ]
                }
            ]
            
            # 添加互动数据
            if likes_count > 0 or comments_count > 0:
                elements.append({
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "content": f"**👍 点赞:** {likes_count}",
                                "tag": "lark_md"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "content": f"**💬 评论:** {comments_count}",
                                "tag": "lark_md"
                            }
                        }
                    ]
                })
            
            # 添加关键词
            if keywords:
                keyword_text = " ".join([f"`{kw}`" for kw in keywords[:5]])
                elements.append({
                    "tag": "div",
                    "text": {
                        "content": f"**🏷️ 关键词:** {keyword_text}",
                        "tag": "lark_md"
                    }
                })
            
            # 添加操作按钮
            actions = []
            if url:
                actions.append({
                    "tag": "button",
                    "text": {
                        "content": "🔗 查看原文",
                        "tag": "plain_text"
                    },
                    "url": url,
                    "type": "default"
                })
            
            if actions:
                elements.append({
                    "tag": "action",
                    "actions": actions
                })
            
            return {
                "config": {
                    "wide_screen_mode": True,
                    "enable_forward": True
                },
                "header": {
                    "title": {
                        "content": "🔥 热点内容推送",
                        "tag": "plain_text"
                    },
                    "template": "blue"
                },
                "elements": elements
            }
        
        return template
    
    def _get_simple_template(self):
        """简单消息模板"""
        def template(post_data: Dict[str, Any]) -> Dict[str, Any]:
            title = post_data.get('title', '无标题')
            url = post_data.get('post_url', '')
            source = post_data.get('source_website', '未知来源')
            
            text = f"📰 **{title}**\n📍 来源: {source}"
            if url:
                text += f"\n🔗 [查看详情]({url})"
            
            return {
                "config": {"wide_screen_mode": True},
                "elements": [{
                    "tag": "div",
                    "text": {
                        "content": text,
                        "tag": "lark_md"
                    }
                }]
            }
        
        return template
    
    def _get_detailed_template(self):
        """详细消息模板"""
        def template(post_data: Dict[str, Any]) -> Dict[str, Any]:
            # 这里可以实现更详细的模板
            return self._get_default_template()(post_data)
        
        return template
    
    def _get_workflow_template(self):
        """工作流推送模板"""
        def template(post_data: Dict[str, Any]) -> Dict[str, Any]:
            title = post_data.get('title', '无标题')
            content = post_data.get('content', '无内容')
            url = post_data.get('post_url', '')
            
            # 生成AI总结
            summary = self.ai_summary.summarize_content(title, content, max_length=150)
            
            # 返回工作流格式数据
            return {
                "标题": title,
                "内容总结": summary,
                "原文链接": url
            }
        
        return template
    
    def push_post_data(self, post_data: Dict[str, Any], template: str = 'workflow') -> bool:
        """推送文章数据"""
        try:
            webhook_success = False
            
            # 根据模板类型选择推送方式
            if template == 'workflow':
                # 推送到飞书工作流
                webhook_success = self.send_workflow_data(post_data)
            else:
                # 发送传统卡片消息到飞书群
                card = self.create_post_card(post_data, template)
                webhook_success = self.send_card_message(card)
            
            # 写入多维表格
            bitable_success = self.write_to_bitable(post_data)
            
            # 记录推送结果
            self._record_push(post_data, webhook_success, bitable_success)
            
            return webhook_success or bitable_success
            
        except Exception as e:
            logger.error(f"❌ 推送文章数据异常: {e}")
            return False
    
    def write_to_bitable(self, post_data: Dict[str, Any]) -> bool:
        """写入飞书多维表格"""
        if not self.bitable_token or not self.table_id:
            logger.warning("⚠️ 未配置飞书多维表格参数，跳过写入")
            return False
        
        access_token = self._get_access_token()
        if not access_token:
            logger.error("❌ 无法获取访问令牌，跳过多维表格写入")
            return False
        
        try:
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.bitable_token}/tables/{self.table_id}/records"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # 构造记录数据
            record_data = {
                "fields": {
                    "标题": post_data.get('title', ''),
                    "内容": post_data.get('content', ''),
                    "作者": post_data.get('author', ''),
                    "来源网站": post_data.get('source_website', ''),
                    "原文链接": post_data.get('post_url', ''),
                    "发布时间": post_data.get('post_time', ''),
                    "点赞数": post_data.get('likes_count', 0),
                    "评论数": post_data.get('comments_count', 0),
                    "关键词": json.dumps(post_data.get('matched_keywords', []), ensure_ascii=False),
                    "抓取时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "推送状态": "已推送"
                }
            }
            
            payload = {"records": [record_data]}
            
            response = self.session.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0:
                logger.info(f"✅ 成功写入多维表格: {post_data.get('title', '无标题')}")
                return True
            else:
                logger.error(f"❌ 写入多维表格失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 写入多维表格异常: {e}")
            return False
    
    def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """发送每日汇总"""
        try:
            title = summary_data.get('title', '📊 每日汇总')
            total_posts = summary_data.get('total_posts', 0)
            pushed_posts = summary_data.get('pushed_posts', 0)
            top_keywords = summary_data.get('top_keywords', [])
            
            # 构造汇总卡片
            elements = [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**{title}**",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "content": f"**📊 总帖子数:** {total_posts}",
                                "tag": "lark_md"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "content": f"**📤 已推送:** {pushed_posts}",
                                "tag": "lark_md"
                            }
                        }
                    ]
                }
            ]
            
            # 添加热门关键词
            if top_keywords:
                keyword_text = "\n".join([f"• {kw[0]} ({kw[1]}次)" for kw in top_keywords])
                elements.extend([
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**🔥 热门关键词:**\n{keyword_text}",
                            "tag": "lark_md"
                        }
                    }
                ])
            
            card = {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "content": "📈 数据汇总报告",
                        "tag": "plain_text"
                    },
                    "template": "green"
                },
                "elements": elements
            }
            
            return self.send_card_message(card)
            
        except Exception as e:
            logger.error(f"❌ 发送每日汇总异常: {e}")
            return False
    
    def send_notification(self, message: str, msg_type: str = "info") -> bool:
        """发送通知消息"""
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        
        emoji = emoji_map.get(msg_type, "ℹ️")
        formatted_message = f"{emoji} {message}"
        
        return self.send_webhook_message(formatted_message)
    
    def _record_push(self, post_data: Dict[str, Any], webhook_success: bool, bitable_success: bool):
        """记录推送结果"""
        try:
            from models.database import db, PushRecord
            
            # 记录Webhook推送
            if webhook_success:
                webhook_record = PushRecord(
                    post_id=post_data.get('id'),
                    push_type='webhook',
                    target=self.webhook_url,
                    status='success',
                    message='Webhook推送成功'
                )
                db.session.add(webhook_record)
            
            # 记录多维表格写入
            if bitable_success:
                bitable_record = PushRecord(
                    post_id=post_data.get('id'),
                    push_type='bitable',
                    target=f"{self.bitable_token}/{self.table_id}",
                    status='success',
                    message='多维表格写入成功'
                )
                db.session.add(bitable_record)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"❌ 记录推送结果失败: {e}")

# 创建全局实例
feishu_service = FeishuService() 