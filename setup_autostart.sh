#!/bin/bash

# 竞品监控系统开机自启动设置脚本
# 支持 macOS 系统

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="feishu_bot_autostart"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$LAUNCH_AGENT_DIR/com.feishu.bot.plist"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[错误]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

# 检查是否为 macOS
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        error "此脚本仅支持 macOS 系统"
        exit 1
    fi
}

# 创建启动脚本
create_startup_script() {
    log "创建启动脚本..."
    
    cat > "$APP_DIR/autostart.sh" << 'EOF'
#!/bin/bash

# 竞品监控系统自动启动脚本
# 由 LaunchAgent 调用

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$APP_DIR/logs/autostart.log"
PID_FILE="$APP_DIR/app.pid"

# 创建日志目录
mkdir -p "$APP_DIR/logs"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 等待网络连接
wait_for_network() {
    log "等待网络连接..."
    for i in {1..30}; do
        if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
            log "网络连接正常"
            return 0
        fi
        sleep 2
    done
    log "网络连接超时，继续启动"
    return 1
}

# 停止现有进程
stop_existing() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log "停止现有进程 (PID: $PID)"
            kill "$PID" 2>/dev/null
            sleep 3
            if ps -p "$PID" > /dev/null 2>&1; then
                log "强制停止进程"
                kill -9 "$PID" 2>/dev/null
            fi
        fi
        rm -f "$PID_FILE"
    fi
}

# 启动应用
start_app() {
    log "启动竞品监控系统..."
    
    cd "$APP_DIR"
    
    # 启动应用
    /usr/bin/python3 start_competitor.py >> "$LOG_FILE" 2>&1 &
    APP_PID=$!
    
    # 保存PID
    echo "$APP_PID" > "$PID_FILE"
    
    log "应用已启动 (PID: $APP_PID)"
    
    # 等待应用启动
    sleep 10
    
    # 检查应用是否正常启动
    if curl -s http://localhost:8080/api/stats > /dev/null 2>&1; then
        log "应用启动成功"
        return 0
    else
        log "应用启动失败"
        return 1
    fi
}

# 主函数
main() {
    log "=========================================="
    log "竞品监控系统自动启动"
    log "=========================================="
    
    # 等待网络连接
    wait_for_network
    
    # 停止现有进程
    stop_existing
    
    # 启动应用
    if start_app; then
        log "✅ 应用启动成功"
    else
        log "❌ 应用启动失败"
        exit 1
    fi
}

# 运行主函数
main
EOF

    chmod +x "$APP_DIR/autostart.sh"
    log "✅ 启动脚本创建完成: $APP_DIR/autostart.sh"
}

# 创建 LaunchAgent plist 文件
create_launch_agent() {
    log "创建 LaunchAgent 配置..."
    
    # 确保目录存在
    mkdir -p "$LAUNCH_AGENT_DIR"
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.feishu.bot</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$APP_DIR/autostart.sh</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$APP_DIR/logs/launchagent.log</string>
    
    <key>StandardErrorPath</key>
    <string>$APP_DIR/logs/launchagent_error.log</string>
    
    <key>WorkingDirectory</key>
    <string>$APP_DIR</string>
    
    <key>StartInterval</key>
    <integer>300</integer>
    
    <key>ThrottleInterval</key>
    <integer>60</integer>
</dict>
</plist>
EOF

    log "✅ LaunchAgent 配置创建完成: $PLIST_FILE"
}

# 加载 LaunchAgent
load_launch_agent() {
    log "加载 LaunchAgent..."
    
    # 卸载现有的（如果存在）
    launchctl unload "$PLIST_FILE" 2>/dev/null
    
    # 加载新的
    if launchctl load "$PLIST_FILE"; then
        log "✅ LaunchAgent 加载成功"
        return 0
    else
        error "❌ LaunchAgent 加载失败"
        return 1
    fi
}

# 检查 LaunchAgent 状态
check_launch_agent() {
    log "检查 LaunchAgent 状态..."
    
    if launchctl list | grep -q "com.feishu.bot"; then
        log "✅ LaunchAgent 已加载"
        return 0
    else
        warn "⚠️  LaunchAgent 未加载"
        return 1
    fi
}

# 显示状态信息
show_status() {
    echo ""
    log "=========================================="
    log "开机自启动设置完成"
    log "=========================================="
    log "应用目录: $APP_DIR"
    log "启动脚本: $APP_DIR/autostart.sh"
    log "LaunchAgent: $PLIST_FILE"
    log "日志文件: $APP_DIR/logs/autostart.log"
    echo ""
    log "📋 管理命令:"
    log "  检查状态: launchctl list | grep feishu"
    log "  手动启动: launchctl start com.feishu.bot"
    log "  停止服务: launchctl stop com.feishu.bot"
    log "  卸载服务: launchctl unload $PLIST_FILE"
    echo ""
    log "🌐 访问地址:"
    log "   主页: http://localhost:8080"
    log "   配置: http://localhost:8080/config"
    log "   查看: http://localhost:8080/viewer"
    echo ""
    log "📝 下次开机时将自动启动应用"
    log "=========================================="
}

# 卸载自启动
uninstall_autostart() {
    log "卸载开机自启动..."
    
    # 停止服务
    launchctl stop com.feishu.bot 2>/dev/null
    launchctl unload "$PLIST_FILE" 2>/dev/null
    
    # 删除文件
    rm -f "$PLIST_FILE"
    rm -f "$APP_DIR/autostart.sh"
    
    log "✅ 开机自启动已卸载"
}

# 主函数
main() {
    echo "🚀 竞品监控系统开机自启动设置"
    echo "=========================================="
    
    # 检查系统
    check_macos
    
    # 检查参数
    if [[ "$1" == "uninstall" ]]; then
        uninstall_autostart
        exit 0
    fi
    
    # 创建启动脚本
    create_startup_script
    
    # 创建 LaunchAgent
    create_launch_agent
    
    # 加载 LaunchAgent
    if load_launch_agent; then
        show_status
    else
        error "设置失败，请检查权限"
        exit 1
    fi
}

# 运行主函数
main "$@" 