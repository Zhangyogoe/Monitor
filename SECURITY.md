# 🔐 安全配置指南

## API密钥管理

本项目使用Gemini AI API进行竞品分析，为保护API密钥安全，请遵循以下配置方式：

### 📋 配置方法

1. **使用配置文件（推荐）**
   ```bash
   # 复制配置模板
   cp config.example.py config.py
   
   # 编辑配置文件，填入真实的API密钥
   nano config.py
   ```

2. **使用环境变量**
   ```bash
   export GEMINI_API_KEY="your_actual_api_key"
   export GEMINI_MODEL="gemini-1.5-flash"
   ```

### 🚫 安全注意事项

- ✅ `config.py` 已添加到 `.gitignore`，不会上传到GitHub
- ✅ 使用 `config.example.py` 作为模板分享
- ❌ 绝对不要在代码中硬编码API密钥
- ❌ 不要将包含真实密钥的文件上传到公共仓库

### 📦 GitHub上传清单

上传前请确保：

- [ ] `config.py` 不在Git跟踪中
- [ ] `.gitignore` 包含敏感文件
- [ ] `config.example.py` 只包含占位符
- [ ] 代码中没有硬编码的API密钥

### 🔧 部署配置

部署时：

1. 将 `config.example.py` 复制为 `config.py`
2. 填入真实的API密钥和Webhook地址
3. 确保配置文件权限设置正确

### 🔄 API密钥获取优先级

系统按以下顺序获取API密钥：

1. `config.py` 配置文件
2. 环境变量 `GEMINI_API_KEY`
3. 数据库中的 `ai_api_key` 设置
4. 默认密钥（仅开发环境）

推荐使用配置文件方式，既安全又便于管理。 