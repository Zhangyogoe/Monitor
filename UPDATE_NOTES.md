# 竞品监控系统更新说明

## 版本更新 - 2025年7月

### 🎯 主要新增功能

#### 1. 数据删除功能
- **新增功能**：爬取记录删除功能，支持清除历史数据后重新推送相同内容
- **Web界面**：在"最近监控结果"列表中每条记录都有删除按钮
- **API接口**：
  - `DELETE /api/session/delete/<session_id>` - 删除指定爬取会话
  - `DELETE /api/posts/delete` - 批量删除帖子记录
  - `POST /api/records/clear` - 清理旧记录
- **数据库操作**：支持级联删除会话及相关帖子记录

#### 2. 飞书消息格式优化
- **富文本消息**：使用交互式卡片消息，支持粗体、颜色等格式
- **消息结构**：
  - 大标题：日期 + "竞品动态"
  - 子标题：按平台分类显示
  - AI摘要：简洁的微信公众号风格内容
  - 查看详情链接：`http://localhost:8080/`
- **条件推送**：只在有新内容时推送，手动爬取不触发推送

#### 3. 系统守护进程
- **自动启动**：支持macOS开机自动启动
- **进程管理**：LaunchAgent配置，自动重启异常退出的进程
- **管理脚本**：
  - `daemon_start.sh` - 守护进程启动脚本
  - `manage_autostart.sh` - 自启动管理脚本
  - `com.makeblock.competitor-monitor-daemon.plist` - macOS服务配置

#### 4. 安全性增强
- **API密钥管理**：通过`config.py`管理敏感信息
- **Git忽略**：`config.py`和其他敏感文件不上传到GitHub
- **环境变量**：支持通过环境变量配置API密钥
- **安全文档**：`SECURITY.md`提供安全使用指南

### 🔧 技术改进

#### 1. AI服务优化
- **Gemini API**：更新为最新的API调用方式
- **提示词优化**：AI摘要更加简洁、清晰，符合微信公众号风格
- **错误处理**：增强API调用失败时的错误处理和重试机制

#### 2. 定时任务改进
- **时间调整**：定时爬取时间从上午9点调整为10点
- **推送逻辑**：定时爬取触发飞书推送，手动爬取不推送
- **状态跟踪**：更好的任务执行状态记录

#### 3. 前端界面优化
- **删除按钮**：使用`data-`属性避免JavaScript字符串转义问题
- **样式优化**：删除按钮使用红色主题，hover效果
- **交互体验**：删除确认对话框，操作反馈

#### 4. 数据库扩展
- **会话管理**：完善的爬取会话记录
- **关联删除**：支持会话和帖子的级联删除
- **数据完整性**：增强数据约束和完整性检查

### 📁 新增文件

```
SECURITY.md                           # 安全使用指南
UPDATE_NOTES.md                       # 本更新说明
config.example.py                     # 配置文件模板
daemon_start.sh                       # 守护进程脚本
manage_autostart.sh                   # 自启动管理脚本
manage_records.py                     # 记录管理工具
services/feishu_webhook_service.py    # 飞书Webhook服务
com.makeblock.competitor-monitor-daemon.plist  # macOS服务配置
飞书推送设置指南.md                     # 飞书配置文档
templates/competitor_index_backup.html # 模板备份
```

### 🔄 修改文件

```
.gitignore                           # 增加config.py等敏感文件
competitor_app.py                    # 新增删除API接口
services/competitor_ai_service.py    # API密钥管理优化
services/competitor_monitor_service.py # 删除功能实现
templates/competitor_index.html      # 删除按钮和界面优化
manage_autostart.sh                  # 自启动逻辑改进
```

### 🚀 部署说明

#### 1. 环境配置
```bash
# 1. 创建配置文件
cp config.example.py config.py

# 2. 编辑配置文件，添加API密钥
# GEMINI_API_KEY = "your_api_key_here"
# FEISHU_WEBHOOK_URL = "your_webhook_url"

# 3. 设置自启动（可选）
chmod +x manage_autostart.sh
./manage_autostart.sh install
```

#### 2. 服务启动
```bash
# 手动启动
python3 competitor_app.py

# 或者使用守护进程
chmod +x daemon_start.sh
./daemon_start.sh
```

### ⚠️ 重要提示

1. **API密钥安全**：请勿将`config.py`文件上传到公开仓库
2. **删除操作**：删除爬取记录后，相同内容会重新推送
3. **自启动设置**：macOS用户可以设置开机自动启动
4. **飞书配置**：请参考`飞书推送设置指南.md`配置Webhook

### 🐛 已修复问题

1. **定时爬取问题**：修复定时任务不执行的问题
2. **AI摘要格式**：去除markdown噪音，改为简洁格式
3. **进程管理**：解决应用异常退出问题
4. **删除按钮显示**：修复前端删除按钮不显示的问题
5. **飞书消息格式**：修复富文本消息显示问题

### 📈 性能优化

1. **内存使用**：优化数据处理减少内存占用
2. **数据库查询**：优化删除操作的查询效率
3. **API调用**：减少不必要的API调用
4. **前端加载**：优化页面加载速度

### 🔮 下一步计划

1. **Facebook集成**：考虑集成Facebook Graph API或第三方服务
2. **更多平台**：支持更多社交媒体平台监控
3. **数据分析**：增加趋势分析和统计功能
4. **移动端**：开发移动端管理界面

---

**更新时间**：2025年7月  
**版本标签**：v2.1.0  
**兼容性**：向后兼容，建议更新配置文件 