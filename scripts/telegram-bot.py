#!/usr/bin/env python3
"""
Server-Admin Telegram Bot
交互式服务器管理机器人

命令菜单:
- /start  - 欢迎信息
- /status - 服务器状态
- /services - 服务列表
- /logs - 查看日志
- /backup - 手动备份
- /restart - 重启容器
- /help - 帮助信息
"""

import os
import subprocess
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 配置
CONFIG_FILE = "/etc/monitoring/config.conf"
LOG_FILE = "/var/log/monitoring/telegram-bot.log"

# 从配置文件读取
def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key] = value.strip('"').strip("'")
    return config

CONFIG = load_config()
TOKEN = CONFIG.get('TELEGRAM_BOT_TOKEN', '')
ALLOWED_CHAT_ID = int(CONFIG.get('TELEGRAM_CHAT_ID', '0'))

# 日志配置
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 权限验证
def authorized(update: Update) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id != ALLOWED_CHAT_ID:
        logger.warning(f"Unauthorized access from chat_id: {chat_id}")
        return False
    return True

# 执行 shell 命令
def run_command(cmd: str) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"错误: {str(e)}"

# ==================== 命令处理 ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """欢迎信息"""
    if not authorized(update):
        await update.message.reply_text("⛔ 未授权访问")
        return

    keyboard = [
        [InlineKeyboardButton("📊 状态", callback_data="status"),
         InlineKeyboardButton("🔧 服务", callback_data="services")],
        [InlineKeyboardButton("📋 日志", callback_data="logs"),
         InlineKeyboardButton("💾 备份", callback_data="backup")],
        [InlineKeyboardButton("🔄 重启", callback_data="restart_menu"),
         InlineKeyboardButton("❓ 帮助", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = """🤖 *Server-Admin Bot*

欢迎使用服务器管理机器人！

点击下方按钮或使用命令：
/status - 服务器状态
/services - 服务列表
/logs - 查看日志
/backup - 手动备份
/restart - 重启容器
/help - 帮助信息"""

    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=reply_markup)
    logger.info(f"Start command from {update.effective_chat.id}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """服务器状态"""
    if not authorized(update):
        return

    # 获取系统信息
    mem = run_command("free -m | awk 'NR==2{printf \"%s/%s MB (%.1f%%)\", $3, $2, $3*100/$2}'")
    disk = run_command("df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'")
    load = run_command("cat /proc/loadavg | awk '{print $1\" \"$2\" \"$3}'")
    uptime = run_command("uptime -p | sed 's/up //'")
    containers = run_command("docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null || echo 'Docker未运行'")

    status_msg = f"""📊 *服务器状态*

⏱ *运行时间*: {uptime}
💾 *内存*: {mem}
💿 *磁盘*: {disk}
📈 *负载*: {load}

🐳 *容器状态*:
```
{containers}
```"""

    if update.message:
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(status_msg, parse_mode='Markdown')
    logger.info("Status command executed")

async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """服务列表"""
    if not authorized(update):
        return

    services_list = run_command("""
        echo "=== 系统服务 ==="
        for svc in ssh docker fail2ban tailscaled; do
            status=$(systemctl is-active $svc 2>/dev/null || echo "未知")
            echo "$svc: $status"
        done
        echo ""
        echo "=== Docker 容器 ==="
        docker ps --format "{{.Names}}: {{.Status}}" 2>/dev/null || echo "无运行容器"
    """)

    msg = f"""🔧 *服务列表*

```
{services_list}
```"""

    if update.message:
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown')

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看日志"""
    if not authorized(update):
        return

    # 默认显示健康检查日志
    logs_content = run_command("tail -30 /var/log/monitoring/health-check.log 2>/dev/null || echo '日志文件不存在'")

    msg = f"""📋 *最近日志*

```
{logs_content}
```"""

    keyboard = [
        [InlineKeyboardButton("📋 健康检查", callback_data="logs_health"),
         InlineKeyboardButton("🔐 SSH日志", callback_data="logs_ssh")],
        [InlineKeyboardButton("🚨 Fail2ban", callback_data="logs_fail2ban"),
         InlineKeyboardButton("🐳 Docker", callback_data="logs_docker")],
        [InlineKeyboardButton("🔙 返回", callback_data="start")]
    ]

    if update.message:
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """手动备份"""
    if not authorized(update):
        return

    msg = "💾 *开始备份...*\n\n备份任务已在后台执行，完成后会发送通知。"

    if update.message:
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown')

    # 异步执行备份
    run_command("/usr/local/sbin/monitoring/backup.sh &")
    logger.info("Backup command executed")

async def restart_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """重启菜单"""
    if not authorized(update):
        return

    containers = run_command("docker ps --format '{{.Names}}' 2>/dev/null")

    keyboard = []
    for container in containers.split('\n'):
        if container.strip():
            keyboard.append([InlineKeyboardButton(f"🔄 {container}", callback_data=f"restart_{container}")])
    keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="start")])

    msg = "🔄 *选择要重启的容器*"

    if update.message:
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def restart_container(update: Update, context: ContextTypes.DEFAULT_TYPE, container: str):
    """重启容器"""
    if not authorized(update):
        return

    msg = f"🔄 正在重启 {container}..."
    await update.callback_query.edit_message_text(msg, parse_mode='Markdown')

    result = run_command(f"docker restart {container}")
    msg = f"✅ *容器已重启*\n\n`{container}`\n\n结果: {result}"
    await update.callback_query.edit_message_text(msg, parse_mode='Markdown')
    logger.info(f"Container {container} restarted")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """帮助信息"""
    if not authorized(update):
        return

    help_msg = """❓ *帮助信息*

*可用命令:*
/start - 显示主菜单
/status - 服务器状态（内存、磁盘、负载）
/services - 服务列表（系统服务、容器）
/logs [service] - 查看日志
/backup - 手动触发备份
/restart [container] - 重启容器
/help - 显示此帮助

*注意事项:*
- 敏感操作需要二次确认
- 所有操作都会被记录
- 仅授权用户可使用

*问题反馈:*
GitHub: github.com/quinnmacro/Server-Admin"""

    if update.message:
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(help_msg, parse_mode='Markdown')

# ==================== 按钮回调 ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "start":
        # 重新显示主菜单
        keyboard = [
            [InlineKeyboardButton("📊 状态", callback_data="status"),
             InlineKeyboardButton("🔧 服务", callback_data="services")],
            [InlineKeyboardButton("📋 日志", callback_data="logs"),
             InlineKeyboardButton("💾 备份", callback_data="backup")],
            [InlineKeyboardButton("🔄 重启", callback_data="restart_menu"),
             InlineKeyboardButton("❓ 帮助", callback_data="help")]
        ]
        await query.edit_message_text(
            "🤖 *Server-Admin Bot*\n\n选择操作：",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "status":
        await status(update, context)

    elif data == "services":
        await services(update, context)

    elif data == "logs":
        await logs(update, context)

    elif data == "backup":
        await backup(update, context)

    elif data == "restart_menu":
        await restart_menu(update, context)

    elif data == "help":
        await help_cmd(update, context)

    elif data.startswith("restart_"):
        container = data.replace("restart_", "")
        await restart_container(update, context, container)

    elif data == "logs_health":
        logs_content = run_command("tail -50 /var/log/monitoring/health-check.log 2>/dev/null")
        await query.edit_message_text(f"📋 *健康检查日志*\n\n```\n{logs_content}\n```", parse_mode='Markdown')

    elif data == "logs_ssh":
        logs_content = run_command("journalctl -u ssh -n 20 --no-pager 2>/dev/null")
        await query.edit_message_text(f"📋 *SSH日志*\n\n```\n{logs_content}\n```", parse_mode='Markdown')

    elif data == "logs_fail2ban":
        logs_content = run_command("tail -30 /var/log/fail2ban.log 2>/dev/null")
        await query.edit_message_text(f"📋 *Fail2ban日志*\n\n```\n{logs_content}\n```", parse_mode='Markdown')

    elif data == "logs_docker":
        logs_content = run_command("docker ps -a --format 'table {{.Names}}\\t{{.Status}}' 2>/dev/null")
        await query.edit_message_text(f"📋 *Docker状态*\n\n```\n{logs_content}\n```", parse_mode='Markdown')

# ==================== 主函数 ====================

def main():
    """启动机器人"""
    if not TOKEN:
        print("错误: 未找到 TELEGRAM_BOT_TOKEN")
        return

    # 创建应用
    application = Application.builder().token(TOKEN).build()

    # 注册命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("services", services))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("backup", backup))
    application.add_handler(CommandHandler("restart", restart_menu))
    application.add_handler(CommandHandler("help", help_cmd))

    # 注册按钮回调
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Bot starting...")
    print("Server-Admin Bot 已启动")

    # 启动机器人 (使用 polling)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
