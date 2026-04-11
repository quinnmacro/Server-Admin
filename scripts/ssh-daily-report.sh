#!/bin/bash
# SSH 登录每日汇总脚本 v1.0
# 用法: ssh-daily-report.sh
# 说明: 每天早上发送前一天的SSH登录汇总

# 加载配置
source /etc/monitoring/config.conf 2>/dev/null

# 发送 Telegram 通知
notify() {
    if [ "$TELEGRAM_ENABLED" = "true" ] && [ -x /usr/local/sbin/monitoring/telegram-notify.sh ]; then
        /usr/local/sbin/monitoring/telegram-notify.sh "$1" "true" 2>/dev/null
    fi
}

# 获取昨天的日期
YESTERDAY=$(date -d "yesterday" '+%Y-%m-%d')

# 统计成功登录
SUCCESS_LOGINS=$(journalctl -u ssh --since "$YESTERDAY 00:00:00" --until "$YESTERDAY 23:59:59" 2>/dev/null | grep -c "Accepted password\|Accepted publickey" 2>/dev/null || echo "0")
SUCCESS_LOGINS=${SUCCESS_LOGINS:-0}

# 统计失败尝试
FAILED_ATTEMPTS=$(journalctl -u ssh --since "$YESTERDAY 00:00:00" --until "$YESTERDAY 23:59:59" 2>/dev/null | grep -c "Failed password\|Invalid user" 2>/dev/null || echo "0")
FAILED_ATTEMPTS=${FAILED_ATTEMPTS:-0}

# 获取登录来源IP
LOGIN_IPS=$(journalctl -u ssh --since "$YESTERDAY 00:00:00" --until "$YESTERDAY 23:59:59" 2>/dev/null | grep "Accepted" | awk '{print $NF}' | sort | uniq -c | sort -rn | head -5)

# 获取当前封禁IP数
BANNED_COUNT=$(fail2ban-client status sshd 2>/dev/null | grep "Currently banned" | awk '{print $4}' || echo "0")
BANNED_COUNT=${BANNED_COUNT:-0}

# 发送汇总
notify "📊 SSH 登录日报 ($YESTERDAY)

✅ 成功登录: $SUCCESS_LOGINS 次
❌ 失败尝试: $FAILED_ATTEMPTS 次
🔒 当前封禁: $BANNED_COUNT 个IP

$( [ -n "$LOGIN_IPS" ] && echo "登录来源:" && echo "$LOGIN_IPS" )

📅 报告时间: $(date '+%Y-%m-%d %H:%M:%S')"
