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
