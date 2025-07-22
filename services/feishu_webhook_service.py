#!/usr/bin/env python3
"""
飞书Webhook推送服务
用于向飞书发送竞品监控汇总消息
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
from services.competitor_ai_service import CompetitorAIService

class FeishuWebhookService:
    """飞书Webhook推送服务"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or self._get_webhook_url()
        self.ai_service = CompetitorAIService()
    
    def _get_webhook_url(self) -> str:
        """获取飞书Webhook地址"""
        # 1. 优先从配置文件获取
        try:
            import config
            if hasattr(config, 'FEISHU_WEBHOOK_URL') and config.FEISHU_WEBHOOK_URL != "your_feishu_webhook_url_here":
                return config.FEISHU_WEBHOOK_URL
        except ImportError:
            pass
        
        # 2. 使用默认地址
        return "https://open.feishu.cn/open-apis/bot/v2/hook/b4051018-a48b-46e0-983a-7978456b3a00"
    
    def generate_daily_summary(self, posts: List[Dict[str, Any]]) -> str:
        """生成每日推送的简洁汇总"""
        if not posts:
            return None
        
        # 使用按品牌分类的简洁汇总提示词
        summary_prompt = """
请基于以下竞品动态数据，生成一份简洁的每日汇总推送，要求：

1. 风格类似微信公众号推送，简洁明了
2. 总字数控制在300字以内
3. 按品牌公司分类整理，每个品牌单独一段
4. 使用简洁的分点式描述，不要冗长段落
5. 语言专业但易懂，适合商业决策者阅读
6. 去除markdown格式符号，使用纯文本
7. 不需要总标题，直接从品牌开始

格式示例：
🔥 LightBurn 软件
• 发布2.0版本更新，修复显示问题
• 用户反映字体雕刻效果需要优化

💡 xTool 激光雕刻
• 推出新款M1激光雕刻机
• 社区用户分享创作技巧

⭐ Ortur 激光设备
• 更新固件支持新材料
• 用户咨询安装高度问题

请按品牌分类整理以下实际数据：
"""
        
        try:
            # 调用AI生成按品牌分类的汇总
            full_summary = self.ai_service.analyze_posts(posts, custom_prompt=summary_prompt)
            
            # 进一步精简处理
            summary = self._clean_and_simplify(full_summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"生成简洁汇总失败: {e}")
            # 生成备用简单汇总
            return self._generate_fallback_summary(posts)
    
    def _clean_and_simplify(self, text: str) -> str:
        """清理和简化文本"""
        if not text:
            return text
        
        # 去除markdown格式
        text = text.replace('**', '').replace('*', '').replace('#', '')
        text = text.replace('##', '').replace('###', '')
        
        # 去除多余空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # 限制字数
        if len(text) > 250:
            text = text[:247] + "..."
        
        return text
    
    def _generate_fallback_summary(self, posts: List[Dict[str, Any]]) -> str:
        """生成备用简单汇总"""
        if not posts:
            return None
        
        brands = set()
        total_posts = len(posts)
        
        for post in posts:
            if post.get('brand'):
                brands.add(post['brand'])
        
        summary = f"📈 监控到 {total_posts} 条动态"
        
        if brands:
            brands_text = "、".join(list(brands)[:3])
            if len(brands) > 3:
                brands_text += "等"
            summary += f"，涉及 {brands_text}"
        
        summary += "\n\n💡 详细内容请查看监控平台"
        
        return summary
    
    def send_daily_summary(self, posts: List[Dict[str, Any]], session_name: str = None, session_id: int = None) -> bool:
        """发送每日汇总到飞书"""
        try:
            # 生成简洁汇总
            summary = self.generate_daily_summary(posts)
            
            if not summary:
                logger.info("📱 没有内容需要推送到飞书")
                return False
            
            # 构建飞书消息
            message = self._build_feishu_message(summary, session_name, session_id)
            
            # 发送webhook
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ 飞书消息推送成功")
                return True
            else:
                logger.error(f"❌ 飞书推送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 飞书推送异常: {e}")
            return False
    
    def _build_feishu_message(self, summary: str, session_name: str = None, session_id: int = None) -> Dict[str, Any]:
        """构建飞书消息格式"""
        
        # 添加时间戳
        current_time = datetime.now().strftime("%m月%d日")
        
        if not session_name:
            session_name = "竞品动态监控"
        
        # 生成详情页链接
        if session_id:
            detail_url = f"http://10.10.61.191:8080/session/{session_id}"
        else:
            detail_url = "http://10.10.61.191:8080/"
        
        # 使用简单可靠的富文本消息格式
        message = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"📊 {current_time} 竞品动态",
                        "content": [
                            [
                                {
                                    "tag": "text",
                                    "text": summary + "\n\n"
                                },
                                {
                                    "tag": "a",
                                    "text": "🔍 查看详情",
                                    "href": detail_url
                                }
                            ]
                        ]
                    }
                }
            }
        }
        
        return message
    
    def _format_summary_for_card(self, summary: str) -> str:
        """为卡片消息格式化汇总内容"""
        if not summary:
            return "暂无竞品动态"
        
        # 为飞书卡片格式化内容，使用lark_md语法
        lines = summary.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.strip():
                # 检查是否是分类标题行
                if any(emoji in line for emoji in ['🔥', '💡', '📈', '⭐', '🚀']):
                    # 分类标题使用加粗和颜色
                    formatted_lines.append(f"**{line}**")
                elif line.startswith('• '):
                    # 内容行使用缩进
                    brand_content = line[2:]  # 去掉 '• '
                    formatted_lines.append(f"• {brand_content}")
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append("")
        
        return '\n'.join(formatted_lines)
    
    def _format_summary_with_markdown(self, summary: str) -> str:
        """格式化汇总内容，添加markdown样式（备用方法）"""
        if not summary:
            return summary
        
        # 为内容添加markdown格式
        lines = summary.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.strip():
                # 检查是否是分类标题行
                if any(emoji in line for emoji in ['🔥', '💡', '📈', '⭐', '🚀']):
                    # 分类标题使用加粗
                    formatted_lines.append(f"**{line}**")
                elif line.startswith('• '):
                    # 内容行添加缩进和样式
                    brand_content = line[2:]  # 去掉 '• '
                    formatted_lines.append(f"  • {brand_content}")
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def test_webhook(self) -> bool:
        """测试webhook连接"""
        try:
            test_message = {
                "msg_type": "text",
                "content": {
                    "text": "🔧 竞品监控系统测试消息\n\n系统运行正常，webhook连接成功！"
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=test_message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ 飞书webhook测试成功")
                return True
            else:
                logger.error(f"❌ 飞书webhook测试失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 飞书webhook测试异常: {e}")
            return False
    
    def update_webhook_url(self, new_url: str):
        """更新webhook地址"""
        self.webhook_url = new_url
        logger.info(f"✅ 飞书webhook地址已更新: {new_url}") 