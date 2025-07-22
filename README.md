# 🚀 竞品动态监控系统 v2.2.0

> 🎯 **专业的竞品分析工具，自动监控Reddit、Facebook、Kickstarter等平台动态**

一个智能的竞品监控系统，能够自动爬取和分析竞品在各大平台的动态，通过AI智能分析提供有价值的竞品洞察，帮助企业及时了解竞争对手的最新动向。

## ✨ 核心功能

### 🔍 智能监控
- **多平台支持** - Reddit子版块、Facebook官方页面、Kickstarter账号、网页更新等主流平台
- **72小时数据范围** - 精确获取最新72小时内的竞品动态，覆盖更全面
- **自动去重** - 智能过滤重复内容，确保数据质量
- **手动推送模式** - 每次爬取后可选择是否推送到飞书，更灵活的控制
- **网页更新监控** - 智能检测网页内容变化，只报告更新部分
- **开机自启动** - 电脑开机后自动运行，持续监控
- **飞书选择推送** - 支持手动选择推送至飞书群聊，权限控制更安全

### 🤖 AI智能分析
- **品牌自动分类** - 基于Gemini AI的智能品牌识别，按品牌公司分类展示
- **内容智能总结** - 提取关键信息，生成简洁摘要（公众号推送风格）
- **趋势分析** - 识别热点话题和发展趋势
- **竞品洞察** - 深度分析竞品策略和用户反馈
- **智能格式优化** - 去除无意义字符，清晰易读的呈现格式

### 🌐 现代化界面
- **Web管理界面** - 直观的可视化操作界面
- **移动端适配** - 支持手机、平板等多设备访问
- **只读模式** - 专门的只读查看页面，方便团队协作
- **实时更新** - 数据实时展示，支持手动刷新
- **局域网访问** - 支持多设备同时访问，团队协作更便捷
- **数据管理** - 支持删除历史记录，清除后相同内容可重新推送
- **权限控制** - 推送功能仅localhost用户可见，安全性更高

### 📘 Facebook监控（新增）
- **官方页面爬取** - 支持Facebook品牌官方页面监控
- **三重策略** - 移动版→桌面版→Selenium，确保高成功率
- **智能反爬** - 高度仿真Headers、Cookie支持、滚动加载
- **完整集成** - 无缝集成到主监控系统，统一管理

## 🚀 快速开始

### 方法一：直接访问（推荐）

如果系统已经部署(已与部署者处于同一局域网)，您可以直接通过浏览器访问：

```
主控制台: http://your-server-ip:8080
只读查看: http://your-server-ip:8080/viewer
配置管理: http://your-server-ip:8080/config
```
### 方法二：本地部署

#### 环境要求
- Python 3.9+
- Chrome/Chromium 浏览器（用于Facebook爬取）
- 2GB+ 可用内存
- 稳定的网络连接（访问Facebook需要）

#### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/Zhangyogoe/Monitor.git
cd Monitor
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境（可选）**
```bash
# 复制环境配置文件
cp env.example .env

# 编辑配置文件，设置API密钥等
vim .env
```

4. **启动系统**
```bash
python start_competitor.py
```

5. **访问界面**
访问 http://localhost:8080 开始使用

### 开机自启动设置（macOS）

系统支持开机自启动，确保电脑开机后自动运行：

```bash
# 安装开机自启动
./manage_autostart.sh install

# 查看状态
./manage_autostart.sh status

# 查看日志
./manage_autostart.sh logs

# 卸载自启动
./manage_autostart.sh uninstall
```

详细说明请查看：[开机自启动使用说明](开机自启动使用说明.md)

## 📋 监控配置

### 支持的平台

#### Reddit监控
- **子版块监控** - 监控特定Reddit子版块的新帖子
- **关键词过滤** - 支持按关键词筛选相关内容
- **用户数据** - 获取点赞数、评论数、作者信息等
- **反爬虫绕过** - 智能绕过Reddit反爬虫机制

#### Kickstarter监控
- **账号监控** - 跟踪特定用户的项目更新
- **项目分析** - 分析众筹项目的进展情况
- **动态追踪** - 及时获取项目最新动态

#### 网页更新监控
- **智能差异检测** - 只报告网页内容的变化部分
- **链接内容抓取** - 自动抓取更新中的相关链接内容
- **内容哈希对比** - 基于内容哈希的精确变化检测
- **增量更新** - 避免重复报告相同内容

### 配置示例

1. **Reddit子版块监控**
   - 配置名称: `reddit_xtool`
   - 目标URL: `https://www.reddit.com/r/xToolOfficial/`
   - 关键词: 可选，用于过滤特定内容

2. **Kickstarter账号监控**
   - 配置名称: `kickstarter_cubiio`
   - 目标URL: `https://www.kickstarter.com/profile/cubiio/created`
   - 关键词: 留空，获取所有更新

3. **网页更新监控**
   - 配置名称: `software_lightburn`
   - 目标URL: `https://lightburnsoftware.com/blogs/news`
   - 监控类型: 网页更新
   - 功能: 智能检测网页内容变化，只报告更新部分

## 🛠️ 高级配置

### AI功能配置

系统支持Gemini AI进行智能分析，需要API密钥：

```bash
# 在.env文件中设置
GEMINI_API_KEY=your_api_key_here
```

### 定时任务配置

默认每日10:00执行爬取，可在代码中修改：

```python
# 在competitor_app.py中修改
scheduler.add_job(
    func=scheduled_crawl,
    trigger="cron",
    hour=10,  # 修改小时
    minute=0,
    id='daily_crawl'
)
```

### 开机自启动配置

系统支持macOS开机自启动，确保应用持续运行：

```bash
# 安装自启动服务
./setup_autostart.sh

# 管理自启动服务
./manage_autostart.sh [install|uninstall|status|logs|start|stop|restart]
```

### 数据库配置

默认使用SQLite，如需使用其他数据库：

```bash
# PostgreSQL示例
DATABASE_URL=postgresql://user:pass@localhost/competitor_db

# MySQL示例  
DATABASE_URL=mysql://user:pass@localhost/competitor_db
```

## 📊 数据说明

### 数据字段
- **标题** - 帖子/更新的标题
- **内容** - 详细内容
- **作者** - 发布者信息
- **发布时间** - 准确的时间戳
- **互动数据** - 点赞数、评论数等
- **平台来源** - Reddit、Kickstarter等

### AI分析结果
- **品牌分类** - 自动识别相关品牌
- **内容摘要** - 关键信息提取
- **情感分析** - 正面/负面情感识别
- **热度评估** - 基于互动数据的热度分析

## 🔧 故障排除

### 常见问题

**Q: 爬取结果为0条数据？**
- 检查网络连接
- 确认目标URL有效性
- 查看24小时内是否有新内容

**Q: AI分析功能不工作？**
- 确认已设置GEMINI_API_KEY
- 检查API密钥是否有效
- 查看日志获取详细错误信息

**Q: 无法访问Web界面？**
- 确认服务正常启动
- 检查端口8080是否被占用
- 尝试清除浏览器缓存

**Q: 开机自启动不工作？**
- 检查LaunchAgent状态: `launchctl list | grep feishu`
- 查看自启动日志: `./manage_autostart.sh logs`
- 重新安装自启动: `./manage_autostart.sh install`

**Q: 网页更新监控没有检测到变化？**
- 确认网页确实有内容更新
- 检查网络连接和网页可访问性
- 查看应用日志获取详细信息

### 🚀 新功能配置

#### 飞书推送设置
```bash
# 1. 复制配置模板
cp config.example.py config.py

# 2. 编辑配置文件
vim config.py
# 添加以下内容：
# GEMINI_API_KEY = "your_gemini_api_key_here"
# FEISHU_WEBHOOK_URL = "your_feishu_webhook_url_here"

# 3. 详细配置请参考
cat 飞书推送设置指南.md
```

#### 开机自启动设置（macOS）
```bash
# 安装自启动服务
chmod +x manage_autostart.sh
./manage_autostart.sh install

# 查看服务状态
./manage_autostart.sh status

# 卸载服务
./manage_autostart.sh uninstall
```

#### 守护进程启动
```bash
# 使用守护进程方式启动（推荐）
chmod +x daemon_start.sh
./daemon_start.sh

# 检查进程状态
ps aux | grep competitor_app
```

#### 数据管理
- **删除记录**：在Web界面的"最近监控结果"中点击🗑️删除按钮
- **重新推送**：删除记录后，相同内容下次爬取时会重新推送
- **清理数据**：可通过API接口批量清理历史数据

### 📊 API接口

#### 删除功能相关接口
```bash
# 删除指定爬取会话
curl -X DELETE http://localhost:8080/api/session/delete/{session_id}

# 批量删除帖子记录
curl -X DELETE http://localhost:8080/api/posts/delete \
  -H "Content-Type: application/json" \
  -d '{"config_id": 1, "days": 7}'

# 清理旧记录
curl -X POST http://localhost:8080/api/records/clear \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'
```

#### 飞书推送相关接口
```bash
# 测试飞书推送
curl -X POST http://localhost:8080/api/feishu/test

# 发送测试消息
curl -X POST http://localhost:8080/api/feishu/send-test \
  -H "Content-Type: application/json" \
  -d '{"message": "测试消息"}'
```

### 日志查看

```bash
# 查看应用日志
tail -f competitor_app.log

# 查看错误日志
grep -i error competitor_app.log

# 查看守护进程日志
tail -f ~/Library/Logs/competitor-monitor-daemon.log
```

## 🤝 参与贡献

欢迎提交Issue和Pull Request来改进项目！

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/Zhangyogoe/Monitor.git

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt

# 运行测试（如果有测试文件）
python -m pytest tests/
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Web框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - 数据库ORM
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML解析
- [Selenium](https://selenium.dev/) - 浏览器自动化
- [Google Gemini](https://ai.google.dev/) - AI分析服务

## 📞 支持

如果您在使用过程中遇到问题：

1. 查看 [用户使用指南](用户使用指南.md)
2. 搜索已有的 [Issues](https://github.com/Zhangyogoe/Monitor/issues)
3. 创建新的 Issue 描述问题
4. 联系维护者获取技术支持

---

**⭐ 如果这个项目对您有帮助，请给我们一个Star！** 
