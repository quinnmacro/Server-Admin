#!/bin/bash
# 服务器备份脚本 v1.0
# 用法: backup.sh [-q]  (-q 静默模式)

# 加载配置
source /etc/monitoring/config.conf 2>/dev/null

# 备份配置
BACKUP_DIR="/Users/liulu/Server-Admin/backups"
DAILY_DIR="${BACKUP_DIR}/daily"
WEEKLY_DIR="${BACKUP_DIR}/weekly"
MONTHLY_DIR="${BACKUP_DIR}/monthly"
KEY_FILE="/etc/monitoring/backup.key"
RETENTION_DAYS=7
QUIET=false

# 解析参数
while getopts "qs" opt; do
    case $opt in
        q) QUIET=true ;;
        s) STATUS=true ;;
    esac
done

# 日志函数
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    [ "$QUIET" = false ] && echo "$msg"
}

# 发送 Telegram 通知
notify() {
    if [ "$TELEGRAM_ENABLED" = "true" ] && [ -x /usr/local/sbin/monitoring/telegram-notify.sh ]; then
        /usr/local/sbin/monitoring/telegram-notify.sh "$1" "true" 2>/dev/null &
    fi
}

# 备份项目列表
BACKUP_ITEMS=(
    "/root/projects/SanctionList:data:SanctionList项目"
    "/root/projects/homepage:config:Homepage配置"
    "/etc/monitoring:config:监控配置"
    "/etc/fail2ban/jail.local:config:Fail2ban配置"
    "/etc/nginx/sites-enabled:config:Nginx配置"
    "/etc/ssh/sshd_config.d:config:SSH配置"
)

# 创建备份
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="${DAILY_DIR}/backup_${timestamp}.tar.gz"
    local temp_dir=$(mktemp -d)
    local total_size=0
    
    log "开始备份..."
    
    # 复制所有备份项
    for item in "${BACKUP_ITEMS[@]}"; do
        IFS=':' read -r path type name <<< "$item"
        if [ -e "$path" ]; then
            local dest="${temp_dir}/${type}"
            mkdir -p "$dest"
            cp -a "$path" "$dest/" 2>/dev/null
            log "  已备份: $name"
        fi
    done
    
    # 备份 Docker Compose 文件
    find /root -name "docker-compose*.yml" -exec cp {} "${temp_dir}/config/" \; 2>/dev/null
    
    # 备份 Docker 容器列表
    docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' > "${temp_dir}/config/docker_containers.txt" 2>/dev/null
    
    # 创建备份信息
    cat > "${temp_dir}/backup_info.txt" << INFO
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
主机名: $(hostname)
系统: $(lsb_release -d 2>/dev/null | cut -f2)
内核: $(uname -r)
备份项目: ${#BACKUP_ITEMS[@]}
INFO
    
    # 压缩（如果密钥文件存在则加密）
    if [ -f "$KEY_FILE" ]; then
        tar -czf - -C "$temp_dir" . | openssl enc -aes-256-cbc -salt -pbkdf2 -pass file:"$KEY_FILE" -out "$backup_file"
    else
        tar -czf "$backup_file" -C "$temp_dir" .
        log "警告: 未使用加密 (密钥文件不存在: $KEY_FILE)"
    fi
    
    local backup_size=$(du -h "$backup_file" | cut -f1)
    total_size=$backup_size
    
    # 清理临时文件
    rm -rf "$temp_dir"
    
    log "备份完成: $backup_file ($backup_size)"
    
    echo "$backup_file"
}

# 清理旧备份
cleanup_old_backups() {
    log "清理旧备份..."
    find "$DAILY_DIR" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null
    find "$WEEKLY_DIR" -name "*.tar.gz" -mtime +30 -delete 2>/dev/null
    find "$MONTHLY_DIR" -name "*.tar.gz" -mtime +365 -delete 2>/dev/null
}

# 创建周备份（周日）
create_weekly_backup() {
    if [ $(date +%u) -eq 7 ]; then
        local latest=$(ls -t "$DAILY_DIR"/*.tar.gz 2>/dev/null | head -1)
        if [ -n "$latest" ]; then
            cp "$latest" "$WEEKLY_DIR/"
            log "已创建周备份"
        fi
    fi
}

# 创建月备份（每月1号）
create_monthly_backup() {
    if [ $(date +%d) -eq 01 ]; then
        local latest=$(ls -t "$DAILY_DIR"/*.tar.gz 2>/dev/null | head -1)
        if [ -n "$latest" ]; then
            cp "$latest" "$MONTHLY_DIR/"
            log "已创建月备份"
        fi
    fi
}

# 显示备份状态
show_status() {
    echo "📊 *备份状态报告*"
    echo ""
    echo "📁 *备份目录:*"
    echo "• 每日备份: $DAILY_DIR"
    echo "• 每周备份: $WEEKLY_DIR"
    echo "• 每月备份: $MONTHLY_DIR"
    echo ""
    echo "📦 *备份统计:*"
    echo "• 每日备份数量: $(ls -1 "$DAILY_DIR"/*.tar.gz 2>/dev/null | wc -l) 个"
    echo "• 每周备份数量: $(ls -1 "$WEEKLY_DIR"/*.tar.gz 2>/dev/null | wc -l) 个"
    echo "• 每月备份数量: $(ls -1 "$MONTHLY_DIR"/*.tar.gz 2>/dev/null | wc -l) 个"
    echo ""
    echo "🔄 *最新备份:*"
    local latest_daily=$(ls -t "$DAILY_DIR"/*.tar.gz 2>/dev/null | head -1)
    if [ -n "$latest_daily" ]; then
        echo "• 每日: $(basename "$latest_daily") ($(du -h "$latest_daily" | cut -f1))"
        echo "• 创建时间: $(stat -f "%Sm" "$latest_daily" 2>/dev/null || echo "未知")"
    else
        echo "• 每日: 无备份"
    fi
    echo ""
    echo "⚙️ *配置信息:*"
    echo "• 备份项目数量: ${#BACKUP_ITEMS[@]} 个"
    echo "• 保留天数: $RETENTION_DAYS 天"
    echo "• 加密状态: $([ -f "$KEY_FILE" ] && echo "已启用" || echo "未启用")"
    echo "• Telegram通知: $([ "$TELEGRAM_ENABLED" = "true" ] && echo "已启用" || echo "未启用")"
}

# 主函数
main() {
    # 如果请求状态，显示状态并退出
    if [ "${STATUS:-false}" = "true" ]; then
        show_status
        exit 0
    fi

    log "========== 备份开始 =========="
    
    local backup_file=$(create_backup)
    
    if [ -f "$backup_file" ]; then
        cleanup_old_backups
        create_weekly_backup
        create_monthly_backup
        
        local backup_size=$(du -h "$backup_file" | cut -f1)
        local backup_count=$(ls -1 "$DAILY_DIR"/*.tar.gz 2>/dev/null | wc -l)
        
        notify "✅ 服务器备份完成

📦 备份大小: $backup_size
📁 备份文件: $(basename $backup_file)
📊 保留备份数: $backup_count 个

📅 $(date '+%Y-%m-%d %H:%M:%S')"
        
        log "备份成功"
    else
        notify "❌ 服务器备份失败"
        log "备份失败"
        exit 1
    fi
    
    log "========== 备份完成 =========="
}

main "$@"
