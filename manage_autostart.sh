#!/bin/bash

# 管理开机自启动脚本（守护进程版本）
# 功能：安装、卸载、查看状态

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_FILE="$SCRIPT_DIR/com.makeblock.competitor-monitor-daemon.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$LAUNCH_AGENTS_DIR/com.makeblock.competitor-monitor-daemon.plist"
DAEMON_SCRIPT="$SCRIPT_DIR/daemon_start.sh"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查守护进程状态
check_daemon_status() {
    if [ -f "$SCRIPT_DIR/daemon.pid" ]; then
        local pid=$(cat "$SCRIPT_DIR/daemon.pid")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_message $GREEN "✅ 守护进程运行中 (PID: $pid)"
            return 0
        else
            print_message $RED "❌ 守护进程PID文件存在但进程未运行"
            rm -f "$SCRIPT_DIR/daemon.pid"
            return 1
        fi
    else
        print_message $RED "❌ 守护进程未运行"
        return 1
    fi
}

# 检查应用状态
check_app_status() {
    # 检查端口是否被占用（更准确的检测方式）
    if lsof -ti:8080 > /dev/null 2>&1; then
        print_message $GREEN "✅ 竞品监控应用运行中"
        return 0
    else
        print_message $RED "❌ 竞品监控应用未运行"
        return 1
    fi
}

# 检查LaunchAgent状态
check_launchagent_status() {
    if [ -f "$TARGET_PLIST" ]; then
        if launchctl list | grep -q "com.makeblock.competitor-monitor-daemon"; then
            print_message $GREEN "✅ 自启动服务已安装且正在运行"
            return 0
        else
            print_message $YELLOW "⚠️  自启动服务已安装但未运行"
            return 1
        fi
    else
        print_message $RED "❌ 自启动服务未安装"
        return 2
    fi
}

# 检查状态
check_status() {
    print_message $BLUE "🔍 检查系统状态..."
    echo ""
    
    print_message $BLUE "1. 守护进程状态:"
    check_daemon_status
    echo ""
    
    print_message $BLUE "2. 应用状态:"
    check_app_status
    echo ""
    
    print_message $BLUE "3. 自启动服务状态:"
    check_launchagent_status
    echo ""
}

# 安装自启动
install_autostart() {
    print_message $BLUE "🚀 正在安装开机自启动服务..."
    
    # 确保脚本可执行
    chmod +x "$DAEMON_SCRIPT"
    
    # 确保LaunchAgents目录存在
    mkdir -p "$LAUNCH_AGENTS_DIR"
    
    # 复制plist文件
    if cp "$PLIST_FILE" "$TARGET_PLIST"; then
        print_message $GREEN "✅ plist文件已复制到 $TARGET_PLIST"
    else
        print_message $RED "❌ 复制plist文件失败"
        return 1
    fi
    
    # 加载服务
    if launchctl load "$TARGET_PLIST"; then
        print_message $GREEN "✅ 自启动服务已加载"
    else
        print_message $RED "❌ 加载自启动服务失败"
        return 1
    fi
    
    # 启动服务
    sleep 2
    if launchctl start com.makeblock.competitor-monitor-daemon; then
        print_message $GREEN "✅ 自启动服务已启动"
    else
        print_message $YELLOW "⚠️  启动服务时出现警告，但服务可能已正常启动"
    fi
    
    print_message $GREEN "🎉 开机自启动安装完成！"
    print_message $BLUE "ℹ️  应用将在每次开机时自动启动，并具备自动重启功能"
    
    return 0
}

# 卸载自启动
uninstall_autostart() {
    print_message $BLUE "🛑 正在卸载开机自启动服务..."
    
    # 停止守护进程
    if [ -x "$DAEMON_SCRIPT" ]; then
        "$DAEMON_SCRIPT" stop
    fi
    
    # 停止LaunchAgent
    launchctl stop com.makeblock.competitor-monitor-daemon 2>/dev/null
    print_message $YELLOW "⏹  已尝试停止LaunchAgent服务"
    
    # 卸载服务
    if launchctl unload "$TARGET_PLIST" 2>/dev/null; then
        print_message $GREEN "✅ 自启动服务已卸载"
    else
        print_message $YELLOW "⚠️  卸载服务时出现警告（可能服务未运行）"
    fi
    
    # 删除plist文件
    if rm -f "$TARGET_PLIST"; then
        print_message $GREEN "✅ plist文件已删除"
    else
        print_message $RED "❌ 删除plist文件失败"
        return 1
    fi
    
    print_message $GREEN "🎉 开机自启动卸载完成！"
    
    return 0
}

# 重启服务
restart_service() {
    print_message $BLUE "🔄 正在重启服务..."
    
    # 重启守护进程
    if [ -x "$DAEMON_SCRIPT" ]; then
        "$DAEMON_SCRIPT" restart
    fi
    
    # 重启LaunchAgent
    launchctl stop com.makeblock.competitor-monitor-daemon 2>/dev/null
    sleep 2
    launchctl start com.makeblock.competitor-monitor-daemon 2>/dev/null
    
    print_message $GREEN "✅ 服务重启完成"
    
    return 0
}

# 手动启动守护进程
start_daemon() {
    print_message $BLUE "🚀 正在启动守护进程..."
    
    if [ -x "$DAEMON_SCRIPT" ]; then
        nohup "$DAEMON_SCRIPT" start > /dev/null 2>&1 &
        sleep 3
        check_daemon_status
    else
        print_message $RED "❌ 守护进程脚本不存在或不可执行"
        return 1
    fi
}

# 手动停止守护进程
stop_daemon() {
    print_message $BLUE "🛑 正在停止守护进程..."
    
    if [ -x "$DAEMON_SCRIPT" ]; then
        "$DAEMON_SCRIPT" stop
    else
        print_message $RED "❌ 守护进程脚本不存在或不可执行"
        return 1
    fi
}

# 查看日志
view_logs() {
    local app_log="$SCRIPT_DIR/logs/app.log"
    local daemon_log="$SCRIPT_DIR/logs/daemon.log"
    
    print_message $BLUE "📋 应用日志 (最后15行):"
    if [ -f "$app_log" ]; then
        tail -15 "$app_log"
    else
        print_message $RED "❌ 应用日志文件不存在"
    fi
    
    echo ""
    print_message $BLUE "📋 守护进程日志 (最后15行):"
    if [ -f "$daemon_log" ]; then
        tail -15 "$daemon_log"
    else
        print_message $RED "❌ 守护进程日志文件不存在"
    fi
}

# 主程序
case "$1" in
    install)
        install_autostart
        ;;
    
    uninstall)
        uninstall_autostart
        ;;
    
    status)
        check_status
        ;;
    
    restart)
        restart_service
        ;;
    
    start)
        start_daemon
        ;;
    
    stop)
        stop_daemon
        ;;
    
    logs)
        view_logs
        ;;
    
    *)
        echo "竞品监控 - 开机自启动管理工具（守护进程版本）"
        echo ""
        echo "使用方法: $0 {install|uninstall|status|restart|start|stop|logs}"
        echo ""
        echo "  install   - 安装开机自启动"
        echo "  uninstall - 卸载开机自启动"
        echo "  status    - 查看服务状态"
        echo "  restart   - 重启服务"
        echo "  start     - 手动启动守护进程"
        echo "  stop      - 手动停止守护进程"
        echo "  logs      - 查看应用日志"
        echo ""
        echo "特性："
        echo "  ✅ 自动重启崩溃的应用"
        echo "  ✅ 开机自动启动"
        echo "  ✅ 实时监控应用状态"
        echo "  ✅ 详细日志记录"
        echo ""
        exit 1
        ;;
esac 