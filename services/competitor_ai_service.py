#!/usr/bin/env python3
"""
竞品AI分析服务
使用Gemini API进行品牌分类和内容总结
"""

import requests
from typing import List, Dict, Any
from loguru import logger

class CompetitorAIService:
    """竞品AI分析服务"""
    
    def __init__(self):
        # 使用文档指定的API key
        self.api_key = "AIzaSyBvGjWPijmwETZoPgrcPIuggo1xU0Qzyjg"
        self.model = "gemini-1.5-flash"
        
        # 优化的AI提示词 - 公众号推送风格
        self.system_prompt = """你是一个科技媒体编辑，专门整理竞品动态信息。请用公众号推送的简洁风格，按品牌分类整理产品动态和用户反馈。

输出要求：
1. 完全避免使用markdown符号（如 # * ** [] 等）
2. 用简洁的文字和表情符号分隔内容
3. 每个品牌用一个简单标题，后跟产品动态和用户反馈
4. 用"📢 产品动态"和"💬 用户反馈"来区分内容类型
5. 每条信息用简短语言概括，避免冗长描述
6. 在每段最后提供相关链接

示例格式：
🔥 LightBurn 软件

📢 产品动态：
发布2.0版本更新，修复显示问题

💬 用户反馈：
字体雕刻效果需要优化
摄像头安装高度咨询较多

🔗 相关链接：www.example.com

请用这种简洁清晰的格式整理以下内容："""
    
    def analyze_posts(self, posts: List[Dict[str, Any]]) -> str:
        """分析竞品帖子，生成按品牌分类的总结"""
        if not posts:
            return "暂无新的竞品动态"
        
        try:
            # 构造分析请求
            posts_text = self._format_posts_for_analysis(posts)
            
            prompt = f"{self.system_prompt}\n\n以下是需要分析的帖子数据：\n\n{posts_text}\n\n请按品牌公司进行分类整理并输出分析结果："
            
            # 调用Gemini API
            summary = self._call_gemini_api(prompt)
            
            if summary:
                logger.info("✅ AI分析完成")
                return summary
            else:
                logger.error("❌ AI分析失败，返回原始数据")
                return self._fallback_summary(posts)
                
        except Exception as e:
            logger.error(f"❌ AI分析异常: {e}")
            return self._fallback_summary(posts)
    
    def _format_posts_for_analysis(self, posts: List[Dict[str, Any]]) -> str:
        """格式化帖子数据供AI分析"""
        formatted_posts = []
        
        for i, post in enumerate(posts, 1):
            post_text = f"""
帖子 {i}:
平台: {post.get('platform', '未知')}
标题: {post.get('title', '无标题')}
作者: {post.get('author', '未知作者')}
内容: {post.get('content', '无内容')[:300]}
链接: {post.get('post_url', '无链接')}
时间: {post.get('post_time', '未知时间')}
---"""
            formatted_posts.append(post_text)
        
        return "\n".join(formatted_posts)
    
    def _call_gemini_api(self, prompt: str) -> str:
        """调用Gemini API"""
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 2048,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            url = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}'
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return content.strip()
                else:
                    logger.error(f"❌ Gemini API返回格式异常: {result}")
                    return ""
            else:
                logger.error(f"❌ Gemini API错误: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ 调用Gemini API失败: {e}")
            return ""
    
    def _fallback_summary(self, posts: List[Dict[str, Any]]) -> str:
        """AI失败时的备用总结 - 公众号推送风格"""
        if not posts:
            return "📭 暂无竞品动态"
        
        summary_parts = []
        summary_parts.append(f"📊 竞品动态汇总")
        summary_parts.append(f"本次共收集 {len(posts)} 条信息")
        summary_parts.append("")
        
        # 按平台分组
        platforms = {}
        for post in posts:
            platform = post.get('platform', '未知平台')
            if platform not in platforms:
                platforms[platform] = []
            platforms[platform].append(post)
        
        for platform, platform_posts in platforms.items():
            platform_emoji = "🌐" if platform == "网页更新" else "💬" if "Reddit" in platform else "🚀"
            summary_parts.append(f"{platform_emoji} {platform}")
            summary_parts.append(f"收集到 {len(platform_posts)} 条动态")
            summary_parts.append("")
            
            for i, post in enumerate(platform_posts[:3], 1):  # 最多显示3条
                title = post.get('title', '无标题')[:80]
                author = post.get('author', '未知作者')
                url = post.get('post_url', '')
                
                summary_parts.append(f"{i}. {title}")
                if author != '未知作者' and author != '网页监控':
                    summary_parts.append(f"   来源：{author}")
                if url:
                    summary_parts.append(f"   🔗 {url}")
                summary_parts.append("")
        
        summary_parts.append("📝 注：AI分析服务暂时不可用，以上为原始数据整理")
        
        return "\n".join(summary_parts)
    
    def extract_brand_categories(self, posts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """提取品牌分类（简化版）"""
        categories = {
            'WeCreate': [],
            'Cubiio': [],
            'Glowforge': [],
            'xTool': [],
            'Other': []
        }
        
        for post in posts:
            title_content = (post.get('title', '') + ' ' + post.get('content', '')).lower()
            
            # 简单的品牌识别
            if any(keyword in title_content for keyword in ['wecreat', 'we creat']):
                categories['WeCreate'].append(post)
            elif any(keyword in title_content for keyword in ['cubiio']):
                categories['Cubiio'].append(post)
            elif any(keyword in title_content for keyword in ['glowforge']):
                categories['Glowforge'].append(post)
            elif any(keyword in title_content for keyword in ['xtool', 'x-tool']):
                categories['xTool'].append(post)
            else:
                categories['Other'].append(post)
        
        # 移除空分类
        return {k: v for k, v in categories.items() if v}
    
    def get_summary_status(self) -> str:
        """获取AI服务状态"""
        return f"🤖 Gemini竞品分析 (模型: {self.model})" 