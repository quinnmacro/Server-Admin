#!/bin/bash
# 日志监控脚本 v1.1
# 用法: log-monitor.sh [-q]  (-q 静默模式)

# 加载配置
source /etc/monitoring/config.conf 2>/dev/null

STATE_FILE="/var/lib/monitoring/log-monitor.state"
QUIET=false

# 解析参数
while getopts "q" opt; do
    case $opt in
        q) QUIET=true ;;
    esac
done

# 确保状态目录存在
mkdir -p /var/lib/monitoring

# 日志函数
log() {
    [ "$QUIET" = false ] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 发送 Telegram 通知
notify() {
    if [ "$TELEGRAM_ENABLED" = "true" ] && [ -x /usr/local/sbin/monitoring/telegram-notify.sh ]; then
        /usr/local/sbin/monitoring/telegram-notify.sh "$1" "true" 2>/dev/null &
    fi
}

# 获取上次检查时间
get_last_check() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        date -d "5 minutes ago" '+%Y-%m-%d %H:%M:%S'
    fi
}

# 更新检查时间
update_last_check() {
    date '+%Y-%m-%d %H:%M:%S' > "$STATE_FILE"
}

# 检查 SSH 登录
check_ssh_logins() {
    local last_check=$(get_last_check)
    local new_logins=$(journalctl -u ssh --since "$last_check" 2>/dev/null | grep -c "Accepted password\|Accepted publickey" 2>/dev/null || echo "0")
    local failed_attempts=$(journalctl -u ssh --since "$last_check" 2>/dev/null | grep -c "Failed password\|Invalid user\|Connection closed by authenticating user" 2>/dev/null || echo "0")
    
    # 确保是数字
    new_logins=${new_logins:-0}
    failed_attempts=${failed_attempts:-0}
    
    if [ "$new_logins" -gt 0 ]; then
        log "SSH: $new_logins 次成功登录"
        notify "🔐 SSH 登录通知

成功登录: $new_logins 次
失败尝试: $failed_attempts 次

📅 $(date '+%Y-%m-%d %H:%M:%S')"
    fi
}

# 检查 Fail2ban 封禁
check_fail2ban() {
    local last_check=$(get_last_check)
    local bans=$(journalctl -u fail2ban --since "$last_check" 2>/dev/null | grep -c "Ban " 2>/dev/null || echo "0")
    bans=${bans:-0}
    
    if [ "$bans" -gt 0 ]; then
        local banned_ips=$(journalctl -u fail2ban --since "$last_check" 2>/dev/null | grep "Ban " | tail -5 | awk '{print $NF}')
        log "Fail2ban: 封禁 $bans 个IP"
        notify "🚨 Fail2ban 封禁通知

新封禁 IP: $bans 个
最近封禁:
$banned_ips

📅 $(date '+%Y-%m-%d %H:%M:%S')"
    fi
}

# 检查系统错误日志
check_system_errors() {
    local last_check=$(get_last_check)
    local errors=$(journalctl -p err --since "$last_check" 2>/dev/null | wc -l 2>/dev/null || echo "0")
    errors=${errors:-0}
    
    if [ "$errors" -gt 20 ]; then
        log "系统: $errors 个错误日志"
        local recent_errors=$(journalctl -p err --since "$last_check" -n 5 --no-pager 2>/dev/null | awk '{print substr($0, 1, 100)}')
        notify "⚠️ 系统错误日志告警

错误数量: $errors

最近错误:
$recent_errors

📅 $(date '+%Y-%m-%d %H:%M:%S')"
    fi
}

# 检查 Docker 容器状态（只检查运行中容器的状态变化）
check_docker_containers() {
    # 检查不健康的容器（只通知运行中但不健康的）
    local unhealthy=$(docker ps --filter "health=unhealthy" --format '{{.Names}}' 2>/dev/null || true)
    
    if [ -n "$unhealthy" ]; then
        log "Docker: 发现不健康的容器"
        notify "🚨 Docker 容器不健康

不健康的容器:
$unhealthy

📅 $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 检查最近退出的容器（只检查最近5分钟内退出的）
    local last_check=$(get_last_check)
    local recently_exited=$(docker ps -a --filter "status=exited" --format '{{.Names}} {{.FinishedAt}}' 2>/dev/null | while read name time; do
        # 简单比较：如果退出时间是最近的
        if [[ "$time" > "$(date -d '10 minutes ago' '+%Y-%m-%dT%H:%M')" ]]; then
            echo "$name"
        fi
    done)
    
    if [ -n "$recently_exited" ]; then
        log "Docker: 发现最近退出的容器"
        notify "⚠️ Docker 容器退出

最近退出的容器:
$recently_exited

📅 $(date '+%Y-%m-%d %H:%M:%S')"
    fi
}

# 主函数
main() {
    log "========== 日志监控开始 =========="
    
    check_ssh_logins
    check_fail2ban
    check_system_errors
    check_docker_containers
    
    update_last_check
    
    log "========== 日志监控完成 =========="
}

main "$@"
