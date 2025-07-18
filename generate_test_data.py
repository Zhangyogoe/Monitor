#!/usr/bin/env python3
"""
生成测试数据脚本
"""

from datetime import datetime, timedelta
import random
from app import create_app
from models.database import db, CrawledPost, WebsiteConfig, KeywordConfig

# 测试数据
test_posts = [
    {
        "title": "人工智能在医疗领域的最新突破",
        "content": "最新研究显示，人工智能技术在医疗诊断方面取得了重大突破。深度学习算法现在能够更准确地检测癌症细胞，准确率达到95%以上。这项技术的应用将大大提高早期诊断的效率，为患者提供更好的治疗机会。研究团队使用了超过10万张医学影像进行训练，算法已经在多家医院进行了临床试验。",
        "author": "科技日报",
        "source_website": "科技资讯",
        "matched_keywords": ["人工智能", "医疗", "突破"]
    },
    {
        "title": "新能源汽车销量创历史新高",
        "content": "据最新统计数据显示，今年新能源汽车销量同比增长120%，创下历史新高。电动汽车技术的不断进步和政府政策的支持是推动这一增长的主要因素。充电基础设施的完善也为消费者选择电动汽车提供了便利。预计未来五年，新能源汽车将占据汽车市场的重要份额。",
        "author": "汽车之家",
        "source_website": "汽车资讯",
        "matched_keywords": ["新能源", "汽车", "销量"]
    },
    {
        "title": "5G技术推动智慧城市建设加速",
        "content": "5G网络的普及正在推动智慧城市建设进入新阶段。高速、低延迟的网络连接使得物联网设备能够更好地协同工作，城市管理效率显著提升。智能交通系统、环境监测网络、公共安全系统等都因5G技术而得到优化。多个城市已经开始部署基于5G的智慧城市解决方案。",
        "author": "通信世界",
        "source_website": "科技资讯",
        "matched_keywords": ["5G", "智慧城市", "技术"]
    },
    {
        "title": "区块链技术在供应链管理中的应用",
        "content": "区块链技术正在改变传统的供应链管理模式。通过分布式账本技术，企业可以实现供应链的全程可追溯，提高透明度和信任度。这项技术特别适用于食品安全、药品追踪等对可追溯性要求较高的行业。多家跨国公司已经开始采用区块链技术来优化其供应链管理。",
        "author": "区块链周刊",
        "source_website": "科技资讯",
        "matched_keywords": ["区块链", "供应链", "管理"]
    },
    {
        "title": "量子计算研究取得重要进展",
        "content": "国际研究团队在量子计算领域取得重要突破，成功实现了100量子比特的稳定运行。这一成果标志着量子计算向实用化迈出了重要一步。量子计算机在密码学、药物发现、金融建模等领域具有巨大潜力。研究人员表示，这项技术预计在未来10年内将有更广泛的应用。",
        "author": "科学前沿",
        "source_website": "科技资讯",
        "matched_keywords": ["量子计算", "研究", "突破"]
    }
]

def generate_test_data():
    """生成测试数据"""
    app = create_app()
    
    with app.app_context():
        # 删除现有数据
        CrawledPost.query.delete()
        
        # 生成测试帖子
        for i, post_data in enumerate(test_posts):
            # 随机生成发布时间（最近7天内）
            days_ago = random.randint(0, 6)
            hours_ago = random.randint(0, 23)
            post_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
            
            # 为每个帖子生成简单的AI总结
            ai_summary = post_data["content"][:100] + "..." if len(post_data["content"]) > 100 else post_data["content"]
            
            post = CrawledPost(
                title=post_data["title"],
                content=post_data["content"],
                ai_summary=ai_summary,
                author=post_data["author"],
                post_url=f"https://example.com/post/{i+1}",
                post_time=post_time,
                likes_count=random.randint(10, 1000),
                comments_count=random.randint(5, 100),
                source_website=post_data["source_website"],
                matched_keywords=post_data["matched_keywords"],
                is_read=random.choice([True, False]),
                is_archived=False,
                created_at=post_time
            )
            
            db.session.add(post)
        
        # 生成一些已存档的数据
        for i in range(3):
            days_ago = random.randint(7, 14)  # 7-14天前的数据
            archive_time = datetime.now() - timedelta(days=days_ago)
            
            post = CrawledPost(
                title=f"已存档的内容 - {i+1}",
                content=f"这是一个已存档的测试内容，创建于{days_ago}天前。内容包含了相关的技术信息和分析。",
                author="测试作者",
                post_url=f"https://example.com/archived/{i+1}",
                post_time=archive_time,
                likes_count=random.randint(5, 50),
                comments_count=random.randint(1, 20),
                source_website="历史资讯",
                matched_keywords=["存档", "测试"],
                is_read=True,
                is_archived=True,
                archive_date=archive_time.date(),
                created_at=archive_time
            )
            
            db.session.add(post)
        
        db.session.commit()
        print(f"✅ 成功生成 {len(test_posts) + 3} 条测试数据")

if __name__ == "__main__":
    generate_test_data() 