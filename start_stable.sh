#!/bin/bash

# 竞品监控系统稳定启动脚本
# 包含错误处理和自动重启功能

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$APP_DIR/logs/app.log"
PID_FILE="$APP_DIR/app.pid"

# 创建日志目录
mkdir -p "$APP_DIR/logs"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 停止现有进程
stop_app() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log "🛑 停止现有进程 (PID: $PID)"
            kill "$PID"
            sleep 2
            if ps -p "$PID" > /dev/null 2>&1; then
                log "⚠️  强制停止进程"
                kill -9 "$PID"
            fi
        fi
        rm -f "$PID_FILE"
    fi
}

# 启动应用
start_app() {
    log "🚀 启动竞品监控系统..."
    
    # 切换到应用目录
    cd "$APP_DIR"
    
    # 启动应用
    /usr/bin/python3 start_competitor.py > "$LOG_FILE" 2>&1 &
    APP_PID=$!
    
    # 保存PID
    echo "$APP_PID" > "$PID_FILE"
    
    log "✅ 应用已启动 (PID: $APP_PID)"
    
    # 等待应用启动
    sleep 5
    
    # 检查应用是否正常启动
    if curl -s http://localhost:8080/api/stats > /dev/null 2>&1; then
        log "✅ 应用启动成功，Web服务正常"
        return 0
    else
        log "❌ 应用启动失败，Web服务无响应"
        return 1
    fi
}

# 监控应用状态
monitor_app() {
    while true; do
        if [ ! -f "$PID_FILE" ]; then
            log "⚠️  PID文件不存在，重新启动应用"
            start_app
            continue
        fi
        
        PID=$(cat "$PID_FILE")
        if ! ps -p "$PID" > /dev/null 2>&1; then
            log "❌ 应用进程已停止 (PID: $PID)，重新启动"
            start_app
            continue
        fi
        
        # 检查Web服务
        if ! curl -s http://localhost:8080/api/stats > /dev/null 2>&1; then
            log "⚠️  Web服务无响应，重启应用"
            stop_app
            start_app
            continue
        fi
        
        log "✅ 应用运行正常 (PID: $PID)"
        sleep 30  # 每30秒检查一次
    done
}

# 主函数
main() {
    log "=========================================="
    log "竞品监控系统稳定启动脚本"
    log "=========================================="
    
    # 停止现有进程
    stop_app
    
    # 启动应用
    if start_app; then
        log "🎉 应用启动成功！"
        log "🌐 访问地址: http://localhost:8080"
        log "📊 状态检查: http://localhost:8080/api/stats"
        log ""
        log "开始监控应用状态..."
        log "按 Ctrl+C 停止监控"
        log "=========================================="
        
        # 开始监控
        monitor_app
    else
        log "❌ 应用启动失败，请检查日志: $LOG_FILE"
        exit 1
    fi
}

# 信号处理
trap 'log "收到停止信号，正在关闭..."; stop_app; exit 0' INT TERM

# 运行主函数
main 