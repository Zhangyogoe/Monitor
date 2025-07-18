#!/usr/bin/env python3
"""
AI内容总结服务
提供智能内容摘要功能
"""

import re
import requests
from typing import Optional
from loguru import logger
from config.config import config

class AISummaryService:
    """AI内容总结服务"""
    
    def __init__(self):
        # 可以配置多个AI服务提供商
        self.openai_api_key = getattr(config, 'openai_api_key', '')
        self.openai_base_url = getattr(config, 'openai_base_url', 'https://api.openai.com/v1')
        self.openai_model = getattr(config, 'openai_model', 'gpt-3.5-turbo')
        
        # Gemini API 配置
        self.gemini_api_key = getattr(config, 'gemini_api_key', '')
        self.gemini_model = getattr(config, 'gemini_model', 'gemini-1.5-flash')
    
    def summarize_content(self, title: str, content: str, max_length: int = 150) -> str:
        """
        对内容进行AI总结
        
        Args:
            title: 文章标题
            content: 文章内容
            max_length: 最大总结长度
            
        Returns:
            总结后的内容
        """
        try:
            # 优先使用 Gemini API
            if self.gemini_api_key:
                return self._gemini_summarize(title, content, max_length)
            # 如果配置了OpenAI，使用OpenAI进行总结
            elif self.openai_api_key:
                return self._openai_summarize(title, content, max_length)
            else:
                # 回退到简单的提取式总结
                return self._simple_summarize(content, max_length)
                
        except Exception as e:
            logger.error(f"❌ AI总结失败: {e}")
            # 出错时回退到简单总结
            return self._simple_summarize(content, max_length)
    
    def _openai_summarize(self, title: str, content: str, max_length: int) -> str:
        """使用OpenAI进行内容总结"""
        # 清理和截取内容
        clean_content = self._clean_text(content)
        if len(clean_content) > 3000:  # 限制输入长度
            clean_content = clean_content[:3000] + "..."
        
        prompt = f"""请对以下文章内容进行简洁的总结，要求：
1. 总结长度不超过{max_length}字
2. 突出关键信息和要点
3. 语言简洁明了
4. 保持客观中性

标题：{title}

内容：{clean_content}

请提供总结："""

        try:
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.openai_model,
                'messages': [
                    {
                        'role': 'user', 
                        'content': prompt
                    }
                ],
                'max_tokens': max_length * 2,  # 给一些缓冲
                'temperature': 0.3
            }
            
            response = requests.post(
                f'{self.openai_base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result['choices'][0]['message']['content'].strip()
                logger.info("✅ OpenAI总结成功")
                return summary
            else:
                logger.error(f"❌ OpenAI API错误: {response.status_code} - {response.text}")
                return self._simple_summarize(content, max_length)
                
        except Exception as e:
            logger.error(f"❌ OpenAI总结异常: {e}")
            return self._simple_summarize(content, max_length)
    
    def _gemini_summarize(self, title: str, content: str, max_length: int) -> str:
        """使用Google Gemini进行内容总结"""
        # 清理和截取内容
        clean_content = self._clean_text(content)
        if len(clean_content) > 3000:  # 限制输入长度
            clean_content = clean_content[:3000] + "..."
        
        prompt = f"""请对以下文章内容进行简洁的总结，要求：
1. 总结长度不超过{max_length}字
2. 突出关键信息和要点
3. 语言简洁明了
4. 保持客观中性

标题：{title}

内容：{clean_content}

请提供总结："""

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
                    "maxOutputTokens": max_length * 2,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    summary = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    logger.info("✅ Gemini总结成功")
                    return summary
                else:
                    logger.error(f"❌ Gemini API返回格式异常: {result}")
                    return self._simple_summarize(content, max_length)
            else:
                logger.error(f"❌ Gemini API错误: {response.status_code} - {response.text}")
                return self._simple_summarize(content, max_length)
                
        except Exception as e:
            logger.error(f"❌ Gemini总结异常: {e}")
            return self._simple_summarize(content, max_length)
    
    def _simple_summarize(self, content: str, max_length: int) -> str:
        """简单的提取式总结"""
        clean_content = self._clean_text(content)
        
        # 如果内容已经很短，直接返回
        if len(clean_content) <= max_length:
            return clean_content
        
        # 按句子分割
        sentences = re.split(r'[。！？.!?]', clean_content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 提取前几句作为总结
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) <= max_length - 3:  # 留出省略号空间
                summary += sentence + "。"
            else:
                break
        
        if not summary:
            # 如果没有提取到句子，直接截取
            summary = clean_content[:max_length-3] + "..."
        elif len(summary) < len(clean_content):
            summary = summary.rstrip("。") + "..."
        
        return summary
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除多余的空白字符和特殊符号"""
        if not text:
            return ""
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符（保留中文、英文、数字、常用标点）
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？；：""''（）【】《》\.,!?;:()\[\]<>"\']+', '', text)
        
        return text.strip()
    
    def is_ai_available(self) -> bool:
        """检查AI服务是否可用"""
        return bool(self.gemini_api_key or self.openai_api_key)
    
    def get_summary_status(self) -> str:
        """获取总结服务状态描述"""
        if self.gemini_api_key:
            return f"🤖 Gemini总结 (模型: {self.gemini_model})"
        elif self.openai_api_key:
            return f"🤖 OpenAI总结 (模型: {self.openai_model})"
        else:
            return "📄 简单总结 (基于规则)" 