#!/bin/bash

# 竞品监控系统开机自启动管理脚本

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.feishu.bot.plist"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 显示帮助信息
show_help() {
    echo "🚀 竞品监控系统开机自启动管理"
    echo "=========================================="
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  install    安装开机自启动"
    echo "  uninstall  卸载开机自启动"
    echo "  status     查看当前状态"
    echo "  start      手动启动服务"
    echo "  stop       停止服务"
    echo "  restart    重启服务"
    echo "  logs       查看日志"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 install    # 安装开机自启动"
    echo "  $0 status     # 查看状态"
    echo "  $0 logs       # 查看日志"
}

# 检查服务状态
check_status() {
    echo "📊 服务状态检查"
    echo "=========================================="
    
    # 检查 LaunchAgent
    if [ -f "$PLIST_FILE" ]; then
        echo "✅ LaunchAgent 配置文件存在"
    else
        echo "❌ LaunchAgent 配置文件不存在"
    fi
    
    # 检查服务是否加载
    if launchctl list | grep -q "com.feishu.bot"; then
        echo "✅ LaunchAgent 已加载"
    else
        echo "❌ LaunchAgent 未加载"
    fi
    
    # 检查应用进程
    if [ -f "$APP_DIR/app.pid" ]; then
        PID=$(cat "$APP_DIR/app.pid")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 应用进程运行中 (PID: $PID)"
        else
            echo "❌ 应用进程未运行"
        fi
    else
        echo "❌ 应用进程PID文件不存在"
    fi
    
    # 检查Web服务
    if curl -s http://localhost:8080/api/stats > /dev/null 2>&1; then
        echo "✅ Web服务正常响应"
    else
        echo "❌ Web服务无响应"
    fi
    
    echo "=========================================="
}

# 启动服务
start_service() {
    log "启动服务..."
    
    if launchctl start com.feishu.bot; then
        log "✅ 服务启动成功"
        sleep 3
        check_status
    else
        error "❌ 服务启动失败"
    fi
}

# 停止服务
stop_service() {
    log "停止服务..."
    
    # 停止 LaunchAgent
    launchctl stop com.feishu.bot 2>/dev/null
    
    # 停止应用进程
    if [ -f "$APP_DIR/app.pid" ]; then
        PID=$(cat "$APP_DIR/app.pid")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null
            sleep 2
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID" 2>/dev/null
            fi
        fi
        rm -f "$APP_DIR/app.pid"
    fi
    
    log "✅ 服务已停止"
}

# 重启服务
restart_service() {
    log "重启服务..."
    stop_service
    sleep 2
    start_service
}

# 查看日志
show_logs() {
    echo "📝 日志查看"
    echo "=========================================="
    
    # 自启动日志
    if [ -f "$APP_DIR/logs/autostart.log" ]; then
        echo "🔄 自启动日志 (最近20行):"
        echo "------------------------------------------"
        tail -20 "$APP_DIR/logs/autostart.log"
        echo ""
    else
        echo "❌ 自启动日志文件不存在"
    fi
    
    # LaunchAgent 日志
    if [ -f "$APP_DIR/logs/launchagent.log" ]; then
        echo "🚀 LaunchAgent 日志 (最近10行):"
        echo "------------------------------------------"
        tail -10 "$APP_DIR/logs/launchagent.log"
        echo ""
    fi
    
    # 错误日志
    if [ -f "$APP_DIR/logs/launchagent_error.log" ]; then
        echo "❌ 错误日志 (最近10行):"
        echo "------------------------------------------"
        tail -10 "$APP_DIR/logs/launchagent_error.log"
        echo ""
    fi
    
    # 应用日志
    if [ -f "$APP_DIR/logs/app.log" ]; then
        echo "📱 应用日志 (最近10行):"
        echo "------------------------------------------"
        tail -10 "$APP_DIR/logs/app.log"
    fi
    
    echo "=========================================="
}

# 安装开机自启动
install_autostart() {
    log "安装开机自启动..."
    
    if [ -f "./setup_autostart.sh" ]; then
        ./setup_autostart.sh
    else
        error "找不到安装脚本 setup_autostart.sh"
        exit 1
    fi
}

# 卸载开机自启动
uninstall_autostart() {
    log "卸载开机自启动..."
    
    if [ -f "./setup_autostart.sh" ]; then
        ./setup_autostart.sh uninstall
    else
        error "找不到安装脚本 setup_autostart.sh"
        exit 1
    fi
}

# 主函数
main() {
    case "${1:-help}" in
        "install")
            install_autostart
            ;;
        "uninstall")
            uninstall_autostart
            ;;
        "status")
            check_status
            ;;
        "start")
            start_service
            ;;
        "stop")
            stop_service
            ;;
        "restart")
            restart_service
            ;;
        "logs")
            show_logs
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 运行主函数
main "$@" 