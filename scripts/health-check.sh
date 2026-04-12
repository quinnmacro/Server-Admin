#!/bin/bash
# 系统健康检查脚本 v2.0
# 用法: /root/scripts/health-check.sh [-q]  (-q 静默模式，仅写日志)

# 加载配置
source /etc/monitoring/config.conf 2>/dev/null
LOG_FILE="/var/log/monitoring/health-check.log"
ALERT_LOG="/var/log/monitoring/health-alerts.log"
QUIET=false

# 解析参数
while getopts "q" opt; do
    case $opt in
        q) QUIET=true ;;
    esac
done

# 日志函数
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" >> "$LOG_FILE"
    [ "$QUIET" = false ] && echo "$msg"
}

alert() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [ALERT] $1"
    echo "$msg" >> "$ALERT_LOG"
    log "[ALERT] $1"
    
    # 发送 Telegram 通知
    if [ "$TELEGRAM_ENABLED" = "true" ] && [ -x /usr/local/sbin/monitoring/telegram-notify.sh ]; then
        /usr/local/sbin/monitoring/telegram-notify.sh --alert "$1" 2>/dev/null &
    fi
}

# ==================== 系统资源检查 ====================

# 检查内存
check_memory() {
    local mem_total=$(free -m | awk '/^Mem:/{print $2}')
    local mem_used=$(free -m | awk '/^Mem:/{print $3}')
    local mem_percent=$((mem_used * 100 / mem_total))

    if [ "$mem_percent" -gt 90 ]; then
        alert "内存使用率 ${mem_percent}% (${mem_used}MB/${mem_total}MB)"
    elif [ "$mem_percent" -gt 80 ]; then
        log "WARNING: 内存使用率 ${mem_percent}%"
    else
        log "内存使用率 ${mem_percent}% - 正常"
    fi
}

# 检查磁盘
check_disk() {
    local disk_percent=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')

    if [ "$disk_percent" -gt 80 ]; then
        alert "磁盘使用率 ${disk_percent}%"
    elif [ "$disk_percent" -gt 70 ]; then
        log "WARNING: 磁盘使用率 ${disk_percent}%"
    else
        log "磁盘使用率 ${disk_percent}% - 正常"
    fi
}

# 检查 Swap
check_swap() {
    local swap_total=$(free -m | awk '/^Swap:/{print $2}')
    if [ "$swap_total" -eq 0 ]; then
        log "Swap 未配置"
        return
    fi
    local swap_used=$(free -m | awk '/^Swap:/{print $3}')
    local swap_percent=$((swap_used * 100 / swap_total))

    if [ "$swap_percent" -gt 80 ]; then
        alert "Swap 使用率 ${swap_percent}% (${swap_used}MB/${swap_total}MB)"
    elif [ "$swap_percent" -gt 60 ]; then
        log "WARNING: Swap 使用率 ${swap_percent}%"
    fi
}

# 检查系统负载
check_load() {
    local load1=$(awk '{print $1}' /proc/loadavg)
    local cpus=$(nproc)
    local load_percent=$(echo "$load1 $cpus" | awk '{printf "%.0f", ($1/$2)*100}')

    if [ "$load_percent" -gt 150 ]; then
        alert "系统负载过高: ${load1} (CPU核心: ${cpus}, 负载率: ${load_percent}%)"
    elif [ "$load_percent" -gt 100 ]; then
        log "WARNING: 系统负载较高: ${load1} (负载率: ${load_percent}%)"
    else
        log "系统负载 ${load1} - 正常 (${cpus}核)"
    fi
}

# 检查磁盘IO等待
check_disk_io() {
    local iowait=$(iostat -c 1 2 2>/dev/null | tail -1 | awk '{print $4}')
    if [ -n "$iowait" ]; then
        local iowait_int=$(echo "$iowait" | awk '{printf "%.0f", $1}')
        if [ "$iowait_int" -gt 30 ]; then
            alert "磁盘IO等待过高: ${iowait}%"
        elif [ "$iowait_int" -gt 15 ]; then
            log "WARNING: 磁盘IO等待较高: ${iowait}%"
        else
            log "磁盘IO等待 ${iowait}% - 正常"
        fi
    fi
}

# ==================== 网络检查 ====================

# 检查网络连接数
check_connections() {
    local conn_count=$(ss -s 2>/dev/null | grep "TCP:" | awk '{print $2}')
    local established=$(ss -s 2>/dev/null | grep "TCP:" | awk '{print $3}')

    if [ "$conn_count" -gt 500 ]; then
        alert "网络连接数异常: ${conn_count} (已建立: ${established})"
    elif [ "$conn_count" -gt 200 ]; then
        log "WARNING: 网络连接数较多: ${conn_count}"
    else
        log "网络连接数 ${conn_count} - 正常"
    fi
}

# 检查 DNS 解析
check_dns() {
    if timeout 5 nslookup google.com >/dev/null 2>&1; then
        log "DNS解析 - 正常"
    else
        alert "DNS解析失败"
    fi
}

# 检查出站网络连通性
check_outbound_connectivity() {
    local test_endpoints=("1.1.1.1:53" "8.8.8.8:53")
    local success=0
    
    for endpoint in "${test_endpoints[@]}"; do
        if timeout 3 bash -c "echo >/dev/tcp/${endpoint/:/\/}" 2>/dev/null; then
            ((success++))
            break
        fi
    done
    
    if [ "$success" -eq 0 ]; then
        alert "出站网络连接异常"
    else
        log "出站网络连接 - 正常"
    fi
}

# ==================== 安全检查 ====================

# 检查安全更新
check_security_updates() {
    local security_count=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)

    if [ "$security_count" -gt 0 ]; then
        alert "发现 ${security_count} 个安全更新待安装"
    else
        log "无待安装的安全更新"
    fi
}

# 检查 SSH 暴力破解
check_ssh_attacks() {
    local recent_fails=$(journalctl -u ssh --since "1 hour ago" 2>/dev/null | grep -c "Failed\|Invalid\|Illegal" 2>/dev/null || echo "0")

    if [ "$recent_fails" -gt 20 ]; then
        alert "SSH暴力破解攻击: 最近1小时 ${recent_fails} 次失败尝试"
    elif [ "$recent_fails" -gt 10 ]; then
        log "WARNING: SSH异常: 最近1小时 ${recent_fails} 次失败尝试"
    else
        log "SSH登录尝试正常 (1h: ${recent_fails}次失败)"
    fi
}

# 检查 fail2ban 状态
check_fail2ban_status() {
    if command -v fail2ban-client &>/dev/null; then
        if fail2ban-client ping >/dev/null 2>&1; then
            local banned_count=$(fail2ban-client status sshd 2>/dev/null | grep "Currently banned" | awk '{print $4}')
            if [ -n "$banned_count" ] && [ "$banned_count" -gt 0 ]; then
                log "Fail2ban: 当前封禁 ${banned_count} 个IP"
            else
                log "Fail2ban: 当前无封禁IP"
            fi
        else
            alert "Fail2ban 服务无响应"
        fi
    fi
}

# 检查可疑端口
check_suspicious_ports() {
    # 已知的公网监听端口
    local known_public_ports="^22$|^3000$|^32001$|^32002$|^80$|^4433$|^8899$|^1022$|^2096$"

    local unknown_ports=$(ss -tlnp 2>/dev/null | grep -E "^\s*LISTEN.*\s+(0\.0\.0\.0|\*|\[::\]):[0-9]+" | \
        awk '{print $4}' | sed 's/.*://' | sort -u | grep -vE "$known_public_ports" | tr '\n' ' ')

    if [ -n "$unknown_ports" ]; then
        alert "发现非预期公网端口: ${unknown_ports}"
    else
        log "公网端口检查 - 正常"
    fi
}

# 检查僵尸进程
check_zombie_processes() {
    local zombie_count=$(ps aux | awk '$8 ~ /Z/ {count++} END {print count+0}')

    if [ "$zombie_count" -gt 10 ]; then
        alert "发现 ${zombie_count} 个僵尸进程"
    elif [ "$zombie_count" -gt 0 ]; then
        log "WARNING: 发现 ${zombie_count} 个僵尸进程"
    fi
}

# ==================== VPN/隧道检查 ====================

# 检查 Tailscale 状态
check_tailscale() {
    if command -v tailscale &>/dev/null; then
        local status=$(tailscale status --json 2>/dev/null)
        if [ -n "$status" ]; then
            local backend_state=$(echo "$status" | jq -r '.BackendState' 2>/dev/null)
            if [ "$backend_state" = "Running" ]; then
                log "Tailscale VPN - 连接正常"
            else
                alert "Tailscale VPN 状态异常: ${backend_state}"
            fi
        else
            log "Tailscale - 未配置或无响应"
        fi
    fi
}

# 检查 Cloudflare Tunnel 状态
check_cloudflared() {
    if pgrep -x "cloudflared" >/dev/null; then
        local tunnel_status=$(cloudflared tunnel list 2>/dev/null | head -1)
        if [ -n "$tunnel_status" ]; then
            log "Cloudflare Tunnel - 运行中"
        else
            log "Cloudflare Tunnel (cloudflared) - 运行中"
        fi
    else
        if command -v cloudflared &>/dev/null; then
            alert "Cloudflare Tunnel 未运行"
        fi
    fi
}

# ==================== 服务检查 ====================

# 检查服务
check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        log "服务 $service - 运行中"
    else
        alert "服务 $service - 已停止"
    fi
}

# 检查 Docker 容器
check_docker() {
    local container=$1
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        log "容器 $container - 运行中"
    else
        alert "容器 $container - 已停止"
    fi
}

# 检查 Docker 健康状态
check_docker_health() {
    local unhealthy=$(docker ps --filter "health=unhealthy" --format '{{.Names}}' 2>/dev/null)
    if [ -n "$unhealthy" ]; then
        alert "Docker容器不健康: $unhealthy"
    else
        log "Docker容器健康检查 - 正常"
    fi
}

# ==================== 时间/证书检查 ====================

# 检查 NTP 同步
check_time_sync() {
    if timedatectl show 2>/dev/null | grep -q "NTPSynchronized=yes"; then
        log "时间同步 - 正常"
    else
        log "WARNING: 时间同步未启用或未同步"
    fi
}

# 检查系统时间准确性
check_time_accuracy() {
    local offset=$(chronyc tracking 2>/dev/null | grep "Last offset" | awk '{print $4}')
    if [ -n "$offset" ]; then
        local offset_ms=$(echo "$offset" | awk '{printf "%.0f", $1 * 1000}')
        if [ "${offset_ms#-}" -gt 1000 ]; then
            alert "时间偏移过大: ${offset}秒"
        else
            log "时间偏移 ${offset}秒 - 正常"
        fi
    fi
}

# ==================== 数据库检查 ====================

# 检查 SQLite 数据库
check_sqlite() {
    local db_path="/root/projects/SanctionList/data/sanctions.db"
    if [ -f "$db_path" ]; then
        local db_size=$(du -h "$db_path" | cut -f1)
        local integrity=$(sqlite3 "$db_path" "PRAGMA integrity_check;" 2>/dev/null)
        if [ "$integrity" = "ok" ]; then
            log "SQLite数据库 ($db_size) - 完整性正常"
        else
            alert "SQLite数据库完整性异常"
        fi
    fi
}

# ==================== OOM 检查 ====================

# 检查 OOM 事件
check_oom() {
    local oom_count=$(dmesg 2>/dev/null | grep -ci "out of memory" 2>/dev/null)
    oom_count=${oom_count:-0}
    if [ "$oom_count" -gt 0 ]; then
        alert "检测到 ${oom_count} 次 OOM 事件"
        dmesg 2>/dev/null | grep -i "out of memory" | tail -3 | while read line; do
            log "OOM详情: $line"
        done
    else
        log "OOM检查 - 无内存溢出事件"
    fi
}

# 检查 TCP 连接状态
check_tcp_states() {
    local time_wait=$(ss -tan 2>/dev/null | grep -c "TIME-WAIT" 2>/dev/null)
    time_wait=${time_wait:-0}
    local close_wait=$(ss -tan 2>/dev/null | grep -c "CLOSE-WAIT" 2>/dev/null)
    close_wait=${close_wait:-0}

    if [ "$close_wait" -gt 50 ]; then
        alert "TCP CLOSE-WAIT 连接过多: ${close_wait} 个"
    fi
    log "TCP状态: TIME_WAIT=${time_wait}, CLOSE_WAIT=${close_wait}"
}

# 检查容器内存使用率
check_docker_memory() {
    local containers="homepage sanctionlist-backend-1 sanctionlist-frontend-1"
    for container in $containers; do
        local mem_percent=$(docker stats --no-stream --format "{{.MemPerc}}" "$container" 2>/dev/null | tr -d "%")
        if [ -n "$mem_percent" ]; then
            local mem_int=$(echo "$mem_percent" | awk '{printf "%.0f", $1}')
            if [ "$mem_int" -gt 90 ]; then
                alert "容器 $container 内存使用率 ${mem_int}%"
            elif [ "$mem_int" -gt 80 ]; then
                log "WARNING: 容器 $container 内存使用率 ${mem_int}%"
            fi
        fi
    done
}

# ==================== 日志检查 ====================

# 检查系统错误日志
check_system_errors() {
    local error_count=$(journalctl -p err --since "1 hour ago" 2>/dev/null | wc -l)
    if [ "$error_count" -gt 50 ]; then
        alert "系统错误日志过多: 最近1小时 ${error_count} 条"
    elif [ "$error_count" -gt 10 ]; then
        log "WARNING: 系统错误日志: 最近1小时 ${error_count} 条"
    else
        log "系统错误日志 (1h: ${error_count}条) - 正常"
    fi
}

# ==================== SSH性能检查 ====================

# 检查SSH响应时间
check_ssh_response_time() {
    local iterations=3
    local total_ms=0
    local success=0

    log "检查SSH响应时间..."

    for i in $(seq 1 $iterations); do
        local start_ms=$(get_timestamp_ms)

        if ssh -o ConnectTimeout=5 -o BatchMode=yes localhost "echo -n" 2>/dev/null; then
            local end_ms=$(get_timestamp_ms)
            local duration=$((end_ms - start_ms))
            total_ms=$((total_ms + duration))
            success=$((success + 1))
            [ "$QUIET" = false ] && log "  测试 $i: ${duration}ms"
        else
            [ "$QUIET" = false ] && log "  测试 $i: 失败"
        fi

        sleep 0.1
    done

    if [ $success -gt 0 ]; then
        local avg_ms=$((total_ms / success))

        if [ "$avg_ms" -gt 1000 ]; then
            alert "SSH响应时间过高: ${avg_ms}ms"
        elif [ "$avg_ms" -gt 500 ]; then
            log "WARNING: SSH响应时间较高: ${avg_ms}ms"
        else
            log "SSH响应时间 ${avg_ms}ms - 正常"
        fi
    else
        alert "SSH响应时间测试失败: 无法连接到SSH服务"
    fi
}

# 获取时间戳（毫秒）
get_timestamp_ms() {
    if command -v python3 &>/dev/null; then
        python3 -c 'import time; print(int(time.time() * 1000))'
    elif command -v python &>/dev/null; then
        python -c 'import time; print(int(time.time() * 1000))'
    else
        date +%s%3N 2>/dev/null || date +%s000
    fi
}

# 检查SSH连接数
check_ssh_connections() {
    log "检查SSH连接数..."

    # 获取当前SSH连接数
    local ssh_connections=$(ss -tan 2>/dev/null | grep ':22' | grep ESTAB | wc -l)
    ssh_connections=${ssh_connections:-0}

    # 获取SSH进程数
    local ssh_processes=$(ps aux | grep -E '[s]shd:' | wc -l)
    ssh_processes=${ssh_processes:-0}

    if [ "$ssh_connections" -gt 50 ]; then
        alert "SSH连接数过多: ${ssh_connections} 个活动连接"
    elif [ "$ssh_connections" -gt 20 ]; then
        log "WARNING: SSH连接数较多: ${ssh_connections} 个活动连接"
    else
        log "SSH连接数 ${ssh_connections} - 正常 (${ssh_processes}个SSH进程)"
    fi
}

# 检查SSH服务状态
check_ssh_uptime() {
    log "检查SSH服务状态..."

    if systemctl is-active --quiet ssh; then
        local uptime=$(systemctl show -p ActiveEnterTimestamp --value ssh 2>/dev/null)
        local status=$(systemctl show -p SubState --value ssh 2>/dev/null)

        log "SSH服务运行中 (状态: ${status}, 启动时间: ${uptime})"
    else
        alert "SSH服务未运行"
    fi
}

# 检查SSH配置优化状态
check_ssh_config() {
    log "检查SSH配置优化状态..."

    # 检查性能配置文件是否存在
    if [ -f "/etc/ssh/sshd_config.d/performance.conf" ]; then
        local config_age=$(($(date +%s) - $(stat -c %Y /etc/ssh/sshd_config.d/performance.conf 2>/dev/null || echo 0)))

        if [ "$config_age" -lt 86400 ]; then  # 24小时内
            log "SSH性能配置已部署 ($(($config_age / 3600))小时前)"

            # 检查关键配置项
            local max_sessions=$(sshd -T 2>/dev/null | grep maxsessions | awk '{print $2}')
            local use_dns=$(sshd -T 2>/dev/null | grep usedns | awk '{print $2}')

            if [ -n "$max_sessions" ] && [ "$max_sessions" -ge 20 ]; then
                log "  MaxSessions: ${max_sessions} (已优化)"
            fi

            if [ -n "$use_dns" ] && [ "$use_dns" = "no" ]; then
                log "  UseDNS: no (已优化)"
            fi
        else
            log "SSH性能配置已部署 ($(($config_age / 86400))天前)"
        fi
    else
        log "SSH性能配置未部署"
    fi
}

# ==================== 主流程 ====================

main() {
    log "========== 健康检查开始 =========="

    # === 系统资源 ===
    log "--- 系统资源 ---"
    check_memory
    check_disk
    check_swap
    check_load
    check_disk_io

    # === 网络状态 ===
    log "--- 网络状态 ---"
    check_connections
    check_tcp_states
    check_dns
    check_outbound_connectivity

    # === 安全检查 ===
    log "--- 安全检查 ---"
    check_security_updates
    check_ssh_attacks
    check_fail2ban_status
    check_suspicious_ports
    check_zombie_processes

    # === SSH性能检查 ===
    log "--- SSH性能 ---"
    check_ssh_response_time
    check_ssh_connections
    check_ssh_uptime
    check_ssh_config

    # === OOM 检查 ===
    log "--- 内存溢出 ---"
    check_oom

    # === VPN/隧道 ===
    log "--- VPN/隧道 ---"
    check_tailscale
    check_cloudflared

    # === 服务状态 ===
    log "--- 服务状态 ---"
    check_service "ssh"
    check_service "docker"
    check_service "x-ui"
    check_service "fail2ban"
    check_service "tailscaled"
    check_docker "homepage"
    check_docker "sanctionlist-backend-1"
    check_docker "sanctionlist-frontend-1"
    check_docker_health
    check_docker_memory

    # === 时间/证书 ===
    log "--- 时间/证书 ---"
    check_time_sync
    check_time_accuracy

    # === 数据库 ===
    log "--- 数据库 ---"
    check_sqlite

    # === 日志审计 ===
    log "--- 日志审计 ---"
    check_system_errors

    log "========== 健康检查完成 =========="
}

main "$@"
