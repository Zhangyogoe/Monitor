# 飞书机器人Webhook配置详细说明

## 概述

本文档详细说明如何配置飞书自定义机器人的Webhook功能，无需复杂的飞书应用认证，只需要一个简单的Webhook URL即可实现消息推送。

## 配置步骤

### 1. 创建飞书自定义机器人

#### 步骤1：进入群聊设置
1. 打开飞书应用
2. 进入要添加机器人的群聊
3. 点击群聊右上角的"⚙️"设置按钮
4. 在下拉菜单中选择"群机器人"

#### 步骤2：添加自定义机器人
1. 点击"添加机器人"按钮
2. 选择"自定义机器人"
3. 填写机器人信息：
   - **机器人名称**：例如"热点推送机器人"
   - **描述**：例如"自动推送热点内容"
   - **头像**：可选择或上传自定义头像

#### 步骤3：配置安全设置（可选）
1. **IP白名单**：如果需要限制IP访问，可以配置IP白名单
2. **签名校验**：开启后会生成签名密钥，提高安全性

#### 步骤4：获取Webhook URL
1. 点击"添加"按钮创建机器人
2. 复制生成的Webhook URL，格式如下：
   ```
   https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxx
   ```

### 2. 配置环境变量

#### 基础配置
创建或编辑`.env`文件，配置以下必要参数：

```bash
# 应用基本配置
SECRET_KEY=your_secret_key_here_generate_random_string
DEBUG=False

# 数据库配置
DATABASE_URL=sqlite:///feishu_bot.db

# 飞书机器人Webhook配置
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxx
```

#### 高级配置（可选）
如果启用了签名校验，需要添加以下配置：

```bash
# 签名校验密钥（如果启用了签名校验）
FEISHU_WEBHOOK_SECRET=your_webhook_secret_here
```

#### 多群组推送配置
如果需要推送到多个群组，可以配置多个Webhook：

```bash
# 主群组
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/token1
FEISHU_WEBHOOK_SECRET=secret1

# 备用群组
FEISHU_WEBHOOK_URL_2=https://open.feishu.cn/open-apis/bot/v2/hook/token2
FEISHU_WEBHOOK_SECRET_2=secret2

# 第三个群组
FEISHU_WEBHOOK_URL_3=https://open.feishu.cn/open-apis/bot/v2/hook/token3
FEISHU_WEBHOOK_SECRET_3=secret3
```

### 3. 测试配置

#### 测试Webhook连接
系统提供了测试接口，可以验证配置是否正确：

```bash
# 启动系统
python start.py

# 访问测试接口
curl -X POST http://localhost:5000/api/test-webhook \
  -H "Content-Type: application/json" \
  -d '{"message": "测试消息"}'
```

#### 通过Web界面测试
1. 访问 `http://localhost:5000`
2. 进入"系统设置"页面
3. 点击"测试Webhook"按钮
4. 查看群聊中是否收到测试消息

## 消息格式详解

### 支持的消息类型

#### 1. 文本消息
最简单的消息格式，发送纯文本内容：

```python
feishu_service.send_webhook_message("这是一条文本消息")
```

#### 2. 富文本消息
支持markdown格式和链接：

```python
feishu_service.send_rich_text_message(
    title="消息标题",
    content="这是消息内容，支持**粗体**和*斜体*",
    url="https://example.com"
)
```

#### 3. 卡片消息
丰富的卡片格式，包含标题、内容、按钮等：

```python
feishu_service.push_post_data({
    "title": "热点文章标题",
    "content": "文章内容摘要...",
    "url": "https://example.com/article",
    "source": "来源网站",
    "keyword": "关键词",
    "pub_time": "2023-12-01 10:00:00"
})
```

### 消息卡片自定义

可以在`services/feishu_service.py`中的`create_post_card`方法中自定义卡片格式：

```python
def create_post_card(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
    # 自定义卡片内容
    card = {
        "config": {
            "wide_screen_mode": True,
            "enable_forward": True
        },
        "elements": [
            # 添加自定义元素
        ],
        "header": {
            "title": {
                "content": "🔥 自定义标题",
                "tag": "plain_text"
            },
            "template": "blue"  # 可选：blue, green, red, grey
        }
    }
    return card
```

## 签名验证详解

### 为什么需要签名验证
- **安全性**：防止恶意请求
- **身份验证**：确保消息来源的可信性
- **防重放攻击**：基于时间戳的签名机制

### 签名算法
系统使用HMAC-SHA256算法进行签名：

```python
import hmac
import hashlib
import base64

def generate_signature(timestamp: str, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode('utf-8')
```

### 如何启用签名验证
1. 在创建机器人时启用"签名校验"
2. 复制生成的签名密钥
3. 在`.env`文件中配置`FEISHU_WEBHOOK_SECRET`

## 错误处理

### 常见错误及解决方案

#### 1. Webhook URL无效
**错误信息**：`400 Bad Request`
**解决方案**：
- 检查URL格式是否正确
- 确认机器人是否已正确创建
- 重新生成Webhook URL

#### 2. 签名验证失败
**错误信息**：`401 Unauthorized`
**解决方案**：
- 检查签名密钥是否正确
- 确认时间戳是否在有效范围内
- 验证签名算法是否正确

#### 3. 消息格式错误
**错误信息**：`400 Bad Request`
**解决方案**：
- 检查消息JSON格式是否正确
- 确认消息类型是否支持
- 验证卡片模板是否符合规范

#### 4. 频率限制
**错误信息**：`429 Too Many Requests`
**解决方案**：
- 降低消息发送频率
- 实现重试机制
- 优化消息合并策略

### 日志调试
系统提供详细的日志记录，可以通过以下方式查看：

```bash
# 查看实时日志
tail -f logs/feishu_bot.log

# 查看错误日志
grep "ERROR" logs/feishu_bot.log
```

## 最佳实践

### 1. 消息频率控制
```python
# 设置合理的发送间隔
CRAWLER_REQUEST_DELAY=3  # 3秒间隔

# 批量发送优化
def send_batch_messages(messages):
    for i, message in enumerate(messages):
        if i > 0:
            time.sleep(2)  # 每条消息间隔2秒
        send_message(message)
```

### 2. 消息内容优化
```python
# 内容长度限制
def optimize_content(content):
    if len(content) > 500:
        return content[:500] + "..."
    return content

# 关键信息提取
def extract_key_info(post_data):
    return {
        "title": post_data.get("title", "")[:100],
        "summary": post_data.get("content", "")[:200],
        "url": post_data.get("url", "")
    }
```

### 3. 错误重试机制
```python
import time
from functools import wraps

def retry(max_attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry(max_attempts=3, delay=2)
def send_message_with_retry(message):
    return feishu_service.send_webhook_message(message)
```

## 高级配置

### 1. 多群组推送策略
```python
# 配置不同群组的推送策略
WEBHOOK_CONFIGS = {
    "main_group": {
        "url": "https://open.feishu.cn/open-apis/bot/v2/hook/token1",
        "secret": "secret1",
        "priority": ["urgent", "high", "normal"]
    },
    "backup_group": {
        "url": "https://open.feishu.cn/open-apis/bot/v2/hook/token2", 
        "secret": "secret2",
        "priority": ["urgent", "high"]
    }
}
```

### 2. 消息模板管理
```python
# 自定义消息模板
MESSAGE_TEMPLATES = {
    "news": {
        "header_color": "blue",
        "title_prefix": "📰 新闻",
        "emoji": "🔥"
    },
    "alert": {
        "header_color": "red", 
        "title_prefix": "⚠️ 警告",
        "emoji": "🚨"
    }
}
```

## 监控与维护

### 1. 推送成功率监控
```python
# 统计推送成功率
def monitor_push_success():
    success_count = PushRecord.query.filter_by(status="success").count()
    total_count = PushRecord.query.count()
    success_rate = success_count / total_count * 100
    return success_rate
```

### 2. 定期健康检查
```python
# 定期检查Webhook连接
def health_check():
    test_message = "系统健康检查"
    return feishu_service.send_webhook_message(test_message)
```

### 3. 日志轮转配置
```python
# 配置日志轮转
LOG_CONFIG = {
    "handlers": [{
        "sink": "logs/feishu_bot.log",
        "rotation": "10 MB",
        "retention": "30 days",
        "compression": "zip"
    }]
}
```

## 故障排除

### 1. 连接问题
- 检查网络连接
- 验证防火墙设置
- 确认DNS解析正常

### 2. 权限问题
- 确认机器人权限
- 检查群聊设置
- 验证用户权限

### 3. 性能优化
- 优化数据库查询
- 实现连接池
- 使用缓存机制

通过以上配置和优化，您可以构建一个稳定、高效的飞书机器人推送系统。 