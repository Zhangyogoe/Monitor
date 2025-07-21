#!/bin/bash

# 竞品监控守护进程启动脚本
# 功能：监控应用状态，自动重启崩溃的应用

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
LOG_DIR="$APP_DIR/logs"
PID_FILE="$APP_DIR/daemon.pid"
APP_LOG="$LOG_DIR/daemon.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 记录日志函数
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$APP_LOG"
}

# 检查应用是否运行
check_app() {
    # 检查端口是否被占用（更准确的检测方式）
    if lsof -ti:8080 > /dev/null 2>&1; then
        return 0  # 运行中
    else
        return 1  # 未运行
    fi
}

# 启动应用
start_app() {
    cd "$APP_DIR"
    log_message "🚀 启动竞品监控应用..."
    
    # 设置环境变量
    export PYTHONPATH="$APP_DIR:$PYTHONPATH"
    export FLASK_ENV=production
    
    # 启动应用（后台运行）
    nohup python3 competitor_app.py >> "$LOG_DIR/app.log" 2>&1 &
    
    # 等待应用启动
    sleep 5
    
    if check_app; then
        log_message "✅ 应用启动成功"
        return 0
    else
        log_message "❌ 应用启动失败"
        return 1
    fi
}

# 停止应用
stop_app() {
    log_message "🛑 停止竞品监控应用..."
    pkill -f "python.*competitor_app.py"
    sleep 2
    
    if ! check_app; then
        log_message "✅ 应用已停止"
    else
        log_message "❌ 强制终止应用"
        pkill -9 -f "python.*competitor_app.py"
    fi
}

# 监控循环
monitor_loop() {
    log_message "🔄 开始监控应用状态..."
    
    while true; do
        if ! check_app; then
            log_message "⚠️  检测到应用未运行，正在重启..."
            start_app
            
            if ! check_app; then
                log_message "❌ 重启失败，等待30秒后再次尝试..."
                sleep 30
            fi
        else
            log_message "✅ 应用运行正常"
        fi
        
        # 每60秒检查一次
        sleep 60
    done
}

# 处理退出信号
cleanup() {
    log_message "🛑 收到退出信号，正在停止守护进程..."
    stop_app
    rm -f "$PID_FILE"
    exit 0
}

# 注册信号处理器
trap cleanup SIGINT SIGTERM

# 主程序
case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                log_message "⚠️  守护进程已在运行 (PID: $PID)"
                exit 1
            else
                rm -f "$PID_FILE"
            fi
        fi
        
        log_message "🚀 启动守护进程..."
        echo $$ > "$PID_FILE"
        
        # 确保应用运行
        if ! check_app; then
            start_app
        fi
        
        # 开始监控
        monitor_loop
        ;;
        
    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                log_message "🛑 停止守护进程 (PID: $PID)..."
                kill "$PID"
                rm -f "$PID_FILE"
                stop_app
                log_message "✅ 守护进程已停止"
            else
                log_message "⚠️  守护进程未运行"
                rm -f "$PID_FILE"
                stop_app
            fi
        else
            log_message "⚠️  守护进程未运行"
            stop_app
        fi
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                log_message "✅ 守护进程运行中 (PID: $PID)"
                if check_app; then
                    log_message "✅ 应用运行中"
                else
                    log_message "❌ 应用未运行"
                fi
            else
                log_message "❌ 守护进程未运行"
                rm -f "$PID_FILE"
            fi
        else
            log_message "❌ 守护进程未运行"
        fi
        
        if check_app; then
            log_message "✅ 应用运行中"
        else
            log_message "❌ 应用未运行"
        fi
        ;;
        
    *)
        echo "使用方法: $0 {start|stop|restart|status}"
        echo "  start   - 启动守护进程"
        echo "  stop    - 停止守护进程"
        echo "  restart - 重启守护进程"
        echo "  status  - 查看状态"
        exit 1
        ;;
esac 