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
        self.api_key = "xxxxxxxx自行添加"
        self.model = "gemini-1.5-flash"
        
        # 文档指定的AI提示词
        self.system_prompt = """你是一个理工科资料整理分析专家，具备专业多国语言翻译能力，请按品牌公司进行分类，根据帖子输出各品牌公司的产品动态及用户反馈。用户反馈可整理在一起进行输出，输出格式为：标题、内容总结（翻译为中文）、所有涉及原文链接。目的是让阅读人员清晰、快速的了解相关公司产品动态与用户反馈。"""
    
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
        """AI失败时的备用总结"""
        if not posts:
            return "暂无竞品动态"
        
        summary_parts = []
        summary_parts.append(f"📊 **竞品动态汇总** (共{len(posts)}条)")
        summary_parts.append("")
        
        # 按平台分组
        platforms = {}
        for post in posts:
            platform = post.get('platform', '未知平台')
            if platform not in platforms:
                platforms[platform] = []
            platforms[platform].append(post)
        
        for platform, platform_posts in platforms.items():
            summary_parts.append(f"### {platform} ({len(platform_posts)}条)")
            
            for post in platform_posts[:5]:  # 最多显示5条
                title = post.get('title', '无标题')[:100]
                author = post.get('author', '未知作者')
                url = post.get('post_url', '')
                
                summary_parts.append(f"- **{title}**")
                summary_parts.append(f"  作者: {author}")
                if url:
                    summary_parts.append(f"  链接: {url}")
                summary_parts.append("")
        
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
