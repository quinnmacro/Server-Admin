#!/bin/bash
# Telegram 告警通知脚本
# 用法: telegram-notify.sh "消息内容" [silent]

# 加载配置
source /etc/monitoring/config.conf

# Telegram API
TELEGRAM_API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"

send_telegram() {
    local message="$1"
    local silent="${2:-false}"  # silent=true 时不发出声音
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
        echo "[ERROR] Telegram 未配置，请设置 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID"
        return 1
    fi
    
    # 发送消息
    curl -s -X POST "$TELEGRAM_API" \
        -d "chat_id=$TELEGRAM_CHAT_ID" \
        -d "text=$message" \
        -d "parse_mode=HTML" \
        -d "disable_notification=$silent" \
        > /dev/null 2>&1
    
    return $?
}

# 测试连接
test_telegram() {
    local test_msg="🔔 Telegram 通知测试成功

服务器: $(hostname)
时间: $(date '+%Y-%m-%d %H:%M:%S')"
    
    if send_telegram "$test_msg"; then
        echo "✅ Telegram 通知测试成功"
        return 0
    else
        echo "❌ Telegram 通知测试失败"
        return 1
    fi
}

# 格式化告警消息
format_alert() {
    local level="$1"
    local message="$2"
    local hostname=$(hostname)
    local time=$(date '+%Y-%m-%d %H:%M:%S')
    
    local emoji="⚠️"
    [ "$level" = "CRITICAL" ] && emoji="🚨"
    [ "$level" = "INFO" ] && emoji="ℹ️"
    
    echo "$emoji <b>[$level]</b> $hostname

$message

📅 $time"
}

# 主函数
case "$1" in
    --test)
        test_telegram
        ;;
    --alert)
        format_alert "ALERT" "$2" | send_telegram
        ;;
    --critical)
        format_alert "CRITICAL" "$2" | send_telegram "false"
        ;;
    --info)
        format_alert "INFO" "$2" | send_telegram "true"
        ;;
    *)
        send_telegram "$1" "$2"
        ;;
esac
