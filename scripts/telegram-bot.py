#!/usr/bin/env python3
"""
Server-Admin Telegram Bot v2.0
交互式服务器管理机器人 + AI 智能助手

命令菜单:
- /start  - 欢迎信息
- /status - 服务器状态
- /services - 服务列表
- /logs - 查看日志
- /backup - 手动备份
- /restart - 重启容器
- /ai - AI 智能对话
- /analyze - AI 分析服务器
- /help - 帮助信息
"""

import os
import subprocess
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# 配置
CONFIG_FILE = "/etc/monitoring/config.conf"
LOG_FILE = "/var/log/monitoring/telegram-bot.log"

# AI 配置
AI_BASE_URL = "https://cloud.infini-ai.com/maas/coding"
AI_MODEL = "deepseek-v3.2"  # 可选: glm-5, deepseek-v3.2, kimi-k2.5, minimax-m2.7

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
AI_API_KEY = CONFIG.get('INFINI_API_KEY', '')

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
def run_command(cmd: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"错误: {str(e)}"

# ==================== AI 功能 ====================

def call_ai(prompt: str, system_prompt: str = None) -> str:
    """调用 Infini AI API"""
    if not AI_API_KEY:
        return "⚠️ AI API Key 未配置，请在 /etc/monitoring/config.conf 中设置 INFINI_API_KEY"

    try:
        import urllib.request
        import urllib.error

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = json.dumps({
            "model": AI_MODEL,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.7
        }).encode('utf-8')

        req = urllib.request.Request(
            f"{AI_BASE_URL}/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}"
            }
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"AI API HTTP Error: {e.code} - {error_body}")
        return f"⚠️ AI API 错误 ({e.code}): {error_body[:200]}"
    except Exception as e:
        logger.error(f"AI API Error: {str(e)}")
        return f"⚠️ AI 调用失败: {str(e)}"

def get_server_context() -> str:
    """获取服务器上下文信息用于 AI 分析"""
    context = f"""
服务器信息:
- 主机: Vultr 东京
- 配置: 1 vCPU, 2GB RAM, 52GB SSD
- 系统: Ubuntu 24.04 LTS
- 运行时间: {run_command("uptime -p | sed 's/up //'")}
- 内存: {run_command("free -m | awk 'NR==2{printf \"%s/%s MB (%.1f%%)\", $3, $2, $3*100/$2}'")}
- 磁盘: {run_command("df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'")}
- 负载: {run_command("cat /proc/loadavg | awk '{print $1\",\"$2\",\"$3}'")}
- 容器: {run_command("docker ps --format '{{.Names}}: {{.Status}}' | tr '\\n' ', '")}
"""
    return context

# ==================== 命令处理 ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """欢迎信息"""
    if not authorized(update):
        await update.message.reply_text("⛔ 未授权访问")
        return

    keyboard = [
        [InlineKeyboardButton("📊 系统状态", callback_data="status"),
         InlineKeyboardButton("🔧 服务管理", callback_data="services_menu"),
         InlineKeyboardButton("📋 日志查看", callback_data="logs")],
        [InlineKeyboardButton("💾 备份管理", callback_data="backup_menu"),
         InlineKeyboardButton("🔄 容器重启", callback_data="restart_menu"),
         InlineKeyboardButton("⚡ SSH性能", callback_data="ssh_perf")],
        [InlineKeyboardButton("🤖 AI助手", callback_data="ai_menu"),
         InlineKeyboardButton("🔍 系统诊断", callback_data="diagnose_menu"),
         InlineKeyboardButton("❓ 帮助", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = """🤖 *Server-Admin Bot v3.0*

欢迎使用服务器智能管理机器人！

*功能分类*:
📊 系统监控 - 状态、服务、日志
🔧 管理操作 - 备份、重启、SSH性能
🤖 智能工具 - AI助手、系统诊断

*主要命令*:
/status - 系统状态
/services - 服务列表
/logs - 查看日志
/backup - 手动备份
/restart - 重启容器
/ai - AI智能对话
/analyze - AI系统分析

*SSH性能监控*:
/sshstatus - SSH服务状态
/sshperformance - SSH性能测试
/sshoptimize - SSH优化建议
/sshdiagnose - SSH问题诊断

*快捷操作*:
直接发送消息即可与 AI 对话
点击按钮使用交互式菜单
使用 /help 查看完整命令列表"""

    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=reply_markup)
    logger.info(f"Start command from {update.effective_chat.id}")

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI 对话"""
    if not authorized(update):
        return

    # 获取用户消息
    if context.args:
        user_message = ' '.join(context.args)
    elif update.message:
        user_message = update.message.text
        # 如果是命令形式 /ai xxx，需要去掉命令前缀
        if user_message.startswith('/ai '):
            user_message = user_message[4:]
    else:
        await update.message.reply_text("🤖 请输入您的问题，例如：\n`/ai 如何优化服务器内存？`", parse_mode='Markdown')
        return

    if not user_message.strip():
        await update.message.reply_text("🤖 请输入您的问题")
        return

    # 发送思考中提示
    thinking_msg = await update.message.reply_text("🤔 思考中...")

    # 调用 AI
    system_prompt = """你是一个专业的服务器运维助手，擅长 Linux 系统管理、Docker 容器管理、网络安全等领域。
请用简洁、专业的中文回答用户问题。如果涉及具体命令，请给出完整的命令示例。"""

    response = call_ai(user_message, system_prompt)

    # 更新消息
    await thinking_msg.edit_text(f"🤖 *AI 回复:*\n\n{response}", parse_mode='Markdown')
    logger.info(f"AI chat: {user_message[:50]}...")

async def ai_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI 分析服务器状态"""
    if not authorized(update):
        return

    thinking_msg = await update.message.reply_text("🔍 正在收集服务器信息并分析...")

    # 获取服务器上下文
    server_context = get_server_context()

    # AI 分析
    prompt = f"""请分析以下服务器状态，给出：
1. 当前状态评估（健康/警告/危险）
2. 发现的问题
3. 优化建议

{server_context}"""

    system_prompt = """你是一个专业的服务器运维专家。请分析服务器状态并给出专业建议。
用简洁的中文回复，使用 Markdown 格式。"""

    response = call_ai(prompt, system_prompt)

    await thinking_msg.edit_text(f"🔍 *AI 服务器分析*\n\n{response}", parse_mode='Markdown')
    logger.info("AI analysis executed")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通消息（AI 对话）"""
    if not authorized(update):
        return

    # 忽略命令
    if update.message and update.message.text and update.message.text.startswith('/'):
        return

    # 当作 AI 对话处理
    user_message = update.message.text if update.message else ""
    if not user_message.strip():
        return

    thinking_msg = await update.message.reply_text("🤔 思考中...")

    # 获取服务器上下文
    server_context = get_server_context()

    system_prompt = f"""你是一个智能服务器运维助手。你可以：
1. 回答技术问题
2. 分析服务器状态
3. 提供运维建议
4. 帮助排查问题

当前服务器信息:
{server_context}

请用简洁、专业的中文回复。如果需要执行操作，请告诉用户具体命令。"""

    response = call_ai(user_message, system_prompt)

    await thinking_msg.edit_text(f"🤖 {response}", parse_mode='Markdown')
    logger.info(f"Message handled: {user_message[:50]}...")

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

*基础命令:*
/start - 显示主菜单
/status - 服务器状态（内存、磁盘、负载）
/services - 服务列表（系统服务、容器）
/logs [service] - 查看日志
/backup - 手动触发备份
/restart [container] - 重启容器
/help - 显示此帮助

*AI 命令:*
/ai [问题] - AI 智能对话
/analyze - AI 分析服务器状态

*SSH性能命令:*
/sshstatus - SSH服务状态和性能指标
/sshperformance - SSH性能测试报告
/sshoptimize - SSH性能优化建议
/sshdiagnose - SSH连接问题诊断
/sshhistory - SSH性能历史趋势
/sshconfig - SSH配置管理

*快捷操作:*
直接发送消息即可与 AI 对话
点击按钮使用交互式菜单

*注意事项:*
- 敏感操作需要二次确认
- 所有操作都会被记录
- 仅授权用户可使用
- SSH性能测试可能会消耗资源

*问题反馈:*
GitHub: github.com/quinnmacro/Server-Admin"""

    if update.message:
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(help_msg, parse_mode='Markdown')

# ==================== SSH性能功能 ====================

async def ssh_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH服务状态和性能指标"""
    if not authorized(update):
        return

    # 获取SSH服务状态
    ssh_service = run_command("systemctl is-active ssh")
    ssh_uptime = run_command("systemctl show -p ActiveEnterTimestamp --value ssh")

    # 获取SSH连接数
    ssh_connections = run_command("ss -tan | grep ':22' | grep ESTAB | wc -l")

    # 获取SSH进程内存使用
    ssh_memory = run_command("ps aux | grep sshd | grep -v grep | awk '{sum += $6} END {print sum/1024 \"MB\"}'")

    # 获取SSH响应时间（简单测试）
    response_time = run_command("timeout 5 bash -c 'time (ssh -o ConnectTimeout=3 localhost echo -n 2>&1 >/dev/null)' 2>&1 | grep real | awk '{print $2}'")

    status_msg = f"""🔐 *SSH服务状态*

🟢 服务状态: {ssh_service}
⏱ 运行时间: {ssh_uptime}
👥 活动连接: {ssh_connections} 个
💾 内存使用: {ssh_memory}
⏱ 响应时间: {response_time}

📊 性能指标:
• MaxSessions: {run_command("sshd -T 2>/dev/null | grep maxsessions | awk '{print $2}'")}
• UseDNS: {run_command("sshd -T 2>/dev/null | grep usedns | awk '{print $2}'")}
• Compression: {run_command("sshd -T 2>/dev/null | grep compression | awk '{print $2}'")}

🔧 优化状态: {'✅ 已优化' if run_command("[ -f /etc/ssh/sshd_config.d/performance.conf ] && echo 'yes'") == 'yes' else '❌ 未优化'}"""

    if update.message:
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(status_msg, parse_mode='Markdown')
    logger.info("SSH status command executed")

async def ssh_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH性能测试报告"""
    if not authorized(update):
        return

    # 运行SSH性能测试
    thinking_msg = await update.message.reply_text("🔍 正在运行SSH性能测试...")

    # 调用现有的ssh-benchmark.sh脚本
    benchmark_result = run_command("/Users/liulu/Server-Admin/scripts/ssh-benchmark.sh --quick")

    await thinking_msg.edit_text(f"📊 *SSH性能测试报告*\n\n{benchmark_result}", parse_mode='Markdown')
    logger.info("SSH performance test executed")

async def ssh_optimize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH优化建议"""
    if not authorized(update):
        return

    # 分析当前SSH配置
    current_config = run_command("sshd -T 2>/dev/null | head -20")

    # 调用AI分析优化建议
    prompt = f"""分析以下SSH配置，给出优化建议:

当前配置:
{current_config}

服务器信息:
- 主机: Vultr东京服务器
- 配置: 1 vCPU, 2GB RAM
- 用途: 个人开发服务器，SSH连接频繁

请给出:
1. 当前配置评估
2. 性能优化建议
3. 安全优化建议
4. 具体的配置修改命令"""

    thinking_msg = await update.message.reply_text("🤔 正在分析SSH配置并生成优化建议...")

    system_prompt = "你是一个专业的SSH服务器优化专家，擅长性能调优和安全配置。请用中文回答，提供具体的配置命令。"
    response = call_ai(prompt, system_prompt)

    await thinking_msg.edit_text(f"🔧 *SSH优化建议*\n\n{response}", parse_mode='Markdown')
    logger.info("SSH optimize suggestion executed")

async def ssh_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH连接问题诊断"""
    if not authorized(update):
        return

    # 收集诊断信息
    thinking_msg = await update.message.reply_text("🔍 正在诊断SSH连接问题...")

    diagnostic_info = f"""🔧 *SSH连接诊断报告*

📊 *基本连接测试:*
• SSH服务状态: {run_command("systemctl is-active ssh")}
• SSH端口监听: {run_command("ss -tln | grep ':22' || echo '未监听'")}
• 网络连通性: {run_command("timeout 3 bash -c 'echo >/dev/tcp/127.0.0.1/22' 2>&1 && echo '本地连接正常' || echo '本地连接失败'")}

📈 *性能指标:*
• 连接建立时间: {run_command("timeout 5 bash -c 'time (ssh -o ConnectTimeout=3 localhost echo -n 2>&1 >/dev/null)' 2>&1 | grep real | awk '{print $2}'")}
• 活跃连接数: {run_command("ss -tan | grep ':22' | grep ESTAB | wc -l")}
• SSH进程数: {run_command("ps aux | grep sshd | grep -v grep | wc -l")}

⚠️ *常见问题检查:*
• Fail2ban状态: {run_command("fail2ban-client ping 2>&1 | grep -q 'pong' && echo '正常' || echo '异常'")}
• 磁盘空间: {run_command("df -h / | awk 'NR==2{print $5}'")}
• 系统负载: {run_command("cat /proc/loadavg | awk '{print $1}'")}

🔒 *安全配置检查:*
• PermitRootLogin: {run_command("sshd -T 2>/dev/null | grep permitrootlogin | awk '{print $2}'")}
• PasswordAuthentication: {run_command("sshd -T 2>/dev/null | grep passwordauthentication | awk '{print $2}'")}
• MaxAuthTries: {run_command("sshd -T 2>/dev/null | grep maxauthtries | awk '{print $2}'")}

🎯 *优化配置检查:*
• 性能配置: {'✅ 已部署' if run_command("[ -f /etc/ssh/sshd_config.d/performance.conf ] && echo 'yes'") == 'yes' else '❌ 未部署'}
• UseDNS: {run_command("sshd -T 2>/dev/null | grep usedns | awk '{print $2}'")}
• Compression: {run_command("sshd -T 2>/dev/null | grep compression | awk '{print $2}'")}"""

    await thinking_msg.edit_text(diagnostic_info, parse_mode='Markdown')
    logger.info("SSH diagnose command executed")

async def ssh_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH性能历史趋势"""
    if not authorized(update):
        return

    # 检查是否有历史性能数据
    history_data = run_command("ls -la /Users/liulu/Server-Admin/logs/monitoring/ssh-results-*.json 2>/dev/null | head -5")

    if "ssh-results" in history_data:
        # 获取最新的性能数据文件
        latest_file = run_command("ls -t /Users/liulu/Server-Admin/logs/monitoring/ssh-results-*.json 2>/dev/null | head -1")
        file_content = run_command(f"cat {latest_file} 2>/dev/null | head -40")

        history_msg = f"""📊 *SSH性能历史数据*

📁 最新数据文件: {latest_file.split('/')[-1]}

📈 性能指标快照:
```
{file_content}
```

💡 *分析建议:*
• 比较历史性能数据，观察趋势变化
• 注意响应时间、传输速度的稳定性
• 关注内存使用和并发连接数的变化
• 使用 /sshperformance 命令进行完整测试"""
    else:
        history_msg = """📊 *SSH性能历史数据*

⚠️ 尚未发现历史性能数据文件。

💡 *建议操作:*
1. 运行首次性能基准测试:
   `/sshperformance` 或点击 SSH性能 → 性能报告

2. 设置定期性能监控:
   • 每日基准测试
   • 历史趋势分析

3. 查看实时性能指标:
   • 使用 /sshstatus 查看当前状态
   • 使用 /sshdiagnose 进行问题诊断"""

    if update.message:
        await update.message.reply_text(history_msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(history_msg, parse_mode='Markdown')
    logger.info("SSH history command executed")

async def ssh_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH配置管理"""
    if not authorized(update):
        return

    # 获取当前SSH配置摘要
    config_summary = run_command("""
    echo "📋 SSH配置摘要"
    echo "================"
    echo ""
    echo "🔧 主配置文件:"
    ls -la /etc/ssh/sshd_config
    echo ""
    echo "📁 配置片段目录:"
    ls -la /etc/ssh/sshd_config.d/ 2>/dev/null || echo "目录不存在"
    echo ""
    echo "⚙️ 关键配置项:"
    sshd -T 2>/dev/null | grep -E "(maxsessions|maxstartups|usedns|compression|tcpkeepalive)" | head -10
    echo ""
    echo "🔄 性能配置状态:"
    if [ -f /etc/ssh/sshd_config.d/performance.conf ]; then
        echo "✅ 性能配置已部署"
        ls -la /etc/ssh/sshd_config.d/performance.conf
    else
        echo "❌ 性能配置未部署"
    fi
    """)

    config_msg = f"""⚙️ *SSH配置管理*

{config_summary}

🔧 *可用操作:*
• 查看完整配置: `sshd -T`
• 部署性能配置: 使用 ssh-optimize.sh 脚本
• 验证配置语法: `sshd -t`
• 重启SSH服务: `systemctl restart ssh`

📋 *配置说明:*
• 主配置: /etc/ssh/sshd_config
• 性能配置: /etc/ssh/sshd_config.d/performance.conf
• 备份位置: /var/backups/ssh/"""

    if update.message:
        await update.message.reply_text(config_msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(config_msg, parse_mode='Markdown')
    logger.info("SSH config management command executed")

# ==================== 系统诊断功能 ====================

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """运行系统健康检查"""
    if not authorized(update):
        return

    thinking_msg = await update.message.reply_text("💊 正在运行系统健康检查...")

    # 运行健康检查脚本（如果存在）
    health_result = run_command("/Users/liulu/Server-Admin/scripts/health-check.sh 2>&1 | tail -30")

    if "健康检查开始" in health_result:
        result_msg = f"""💊 *系统健康检查报告*

```
{health_result}
```

✅ 健康检查完成
📅 检查时间: $(date '+%Y-%m-%d %H:%M:%S')"""
    else:
        result_msg = f"""💊 *系统健康检查*

⚠️ 无法运行完整健康检查脚本

📊 *快速检查结果:*
• 系统时间: {run_command("date")}
• 系统负载: {run_command("uptime")}
• 内存使用: {run_command("free -m 2>/dev/null | head -2 || echo 'N/A'")}
• 磁盘空间: {run_command("df -h / 2>/dev/null | tail -1 || echo 'N/A'")}

💡 *建议:* 确保 health-check.sh 脚本存在并具有执行权限"""

    if update.message:
        await update.message.reply_text(result_msg, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(result_msg, parse_mode='Markdown')
    logger.info("Health check command executed")

async def network_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """网络诊断"""
    if not authorized(update):
        return

    thinking_msg = await update.message.reply_text("🌐 正在诊断网络连接...")

    # 收集网络诊断信息
    network_info = f"""🌐 *网络诊断报告*

📊 *网络接口信息:*
{run_command("ip addr show 2>/dev/null | head -20 || ifconfig 2>/dev/null | head -20 || echo '无法获取网络接口信息'")}

📡 *网络连通性测试:*
• 本地回环: {run_command("ping -c 1 127.0.0.1 2>&1 | grep 'packet loss' || echo '测试失败'")}
• 网关连通性: {run_command("ip route show default 2>/dev/null | head -1 || echo '无默认路由'")}
• DNS解析测试: {run_command("nslookup google.com 2>&1 | head -2 || echo 'DNS测试失败'")}

🔗 *网络连接状态:*
• 活动TCP连接: {run_command("ss -tan 2>/dev/null | grep ESTAB | wc -l")} 个
• 监听端口: {run_command("ss -tln 2>/dev/null | grep LISTEN | wc -l")} 个

🚨 *网络问题检查:*
• 高延迟连接: {run_command("ss -tan 2>/dev/null | grep TIME-WAIT | wc -l")} 个 TIME-WAIT
• 关闭等待: {run_command("ss -tan 2>/dev/null | grep CLOSE-WAIT | wc -l")} 个 CLOSE-WAIT

🎯 *建议操作:*
1. 检查网络配置
2. 验证防火墙规则
3. 测试外部连通性
4. 监控网络流量"""

    if update.message:
        await update.message.reply_text(network_info, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(network_info, parse_mode='Markdown')
    logger.info("Network diagnose command executed")

async def performance_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """性能诊断"""
    if not authorized(update):
        return

    thinking_msg = await update.message.reply_text("📊 正在诊断系统性能...")

    # 收集性能诊断信息
    performance_info = f"""📊 *系统性能诊断报告*

⚡ *CPU和负载:*
• CPU核心数: {run_command("nproc 2>/dev/null || echo 'N/A'")}
• 系统负载: {run_command("cat /proc/loadavg 2>/dev/null || uptime 2>/dev/null || echo 'N/A'")}
• CPU使用率: {run_command("top -bn1 2>/dev/null | grep 'Cpu(s)' || echo 'N/A'")}

💾 *内存使用:*
{run_command("free -m 2>/dev/null || echo '内存信息不可用'")}

💿 *磁盘IO:*
• 磁盘使用率: {run_command("df -h / 2>/dev/null | tail -1 || echo 'N/A'")}
• Inode使用: {run_command("df -i / 2>/dev/null | tail -1 || echo 'N/A'")}

🐳 *容器性能:*
• 运行中容器: {run_command("docker ps -q 2>/dev/null | wc -l")} 个
• 容器资源使用: {run_command("docker stats --no-stream 2>/dev/null | head -5 || echo 'Docker未运行'")}

📈 *性能建议:*
1. 监控系统负载趋势
2. 检查内存泄漏
3. 优化磁盘IO
4. 调整容器资源限制"""

    if update.message:
        await update.message.reply_text(performance_info, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(performance_info, parse_mode='Markdown')
    logger.info("Performance diagnose command executed")

async def security_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """安全扫描"""
    if not authorized(update):
        return

    thinking_msg = await update.message.reply_text("🔒 正在扫描系统安全...")

    # 收集安全扫描信息
    security_info = f"""🔒 *系统安全扫描报告*

🛡️ *基本安全检查:*
• SSH服务状态: {run_command("systemctl is-active ssh 2>/dev/null || echo '未知'")}
• Fail2ban状态: {run_command("fail2ban-client ping 2>&1 | grep -q 'pong' && echo '运行中' || echo '未运行'")}
• 防火墙状态: {run_command("ufw status 2>/dev/null | head -1 || echo '防火墙未启用'")}

🔐 *SSH安全配置:*
• PermitRootLogin: {run_command("sshd -T 2>/dev/null | grep permitrootlogin | awk '{print $2}' 2>/dev/null || echo 'N/A'")}
• PasswordAuthentication: {run_command("sshd -T 2>/dev/null | grep passwordauthentication | awk '{print $2}' 2>/dev/null || echo 'N/A'")}
• MaxAuthTries: {run_command("sshd -T 2>/dev/null | grep maxauthtries | awk '{print $2}' 2>/dev/null || echo 'N/A'")}

📊 *安全监控:*
• 最近SSH失败尝试: {run_command("journalctl -u ssh --since '1 hour ago' 2>/dev/null | grep -c 'Failed\\|Invalid' 2>/dev/null || echo '0'")} 次/小时
• Fail2ban封禁IP: {run_command("fail2ban-client status sshd 2>/dev/null | grep 'Currently banned' | awk '{print $4}' 2>/dev/null || echo '0'")} 个

🚨 *建议改进:*
1. 定期更新系统
2. 监控异常登录
3. 强化SSH配置
4. 启用审计日志"""

    if update.message:
        await update.message.reply_text(security_info, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(security_info, parse_mode='Markdown')
    logger.info("Security scan command executed")

async def system_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """系统监控"""
    if not authorized(update):
        return

    thinking_msg = await update.message.reply_text("📈 正在收集系统监控数据...")

    # 收集系统监控信息
    monitor_info = f"""📈 *系统监控面板*

🕐 *实时状态 (更新于: {run_command("date")})*

⚡ *资源使用:*
• 系统负载: {run_command("cat /proc/loadavg 2>/dev/null | awk '{print $1}' || echo 'N/A'")}
• 内存使用: {run_command("free -m 2>/dev/null | awk '/^Mem:/{print $3\"/\"$2\"MB (\"int($3*100/$2)\"%)'}' || echo 'N/A'")}
• 磁盘使用: {run_command("df -h / 2>/dev/null | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}' || echo 'N/A'")}

🔗 *网络状态:*
• 活动连接: {run_command("ss -tan 2>/dev/null | grep ESTAB | wc -l")} 个
• 入站流量: {run_command("ss -tan 2>/dev/null | grep ':22' | grep ESTAB | wc -l")} 个SSH连接

🐳 *容器状态:*
• 运行中: {run_command("docker ps -q 2>/dev/null | wc -l")} 个容器
• 总容器数: {run_command("docker ps -aq 2>/dev/null | wc -l")} 个

📊 *服务状态:*
• SSH: {run_command("systemctl is-active ssh 2>/dev/null || echo '未知'")}
• Docker: {run_command("systemctl is-active docker 2>/dev/null || echo '未知'")}
• Fail2ban: {run_command("systemctl is-active fail2ban 2>/dev/null || echo '未知'")}

📋 *监控建议:*
1. 设置告警阈值
2. 定期性能基准测试
3. 日志审计
4. 容量规划"""

    if update.message:
        await update.message.reply_text(monitor_info, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(monitor_info, parse_mode='Markdown')
    logger.info("System monitor command executed")

# ==================== 按钮回调 ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "start":
        # 重新显示主菜单
        keyboard = [
            [InlineKeyboardButton("📊 系统状态", callback_data="status"),
             InlineKeyboardButton("🔧 服务管理", callback_data="services_menu"),
             InlineKeyboardButton("📋 日志查看", callback_data="logs")],
            [InlineKeyboardButton("💾 备份管理", callback_data="backup_menu"),
             InlineKeyboardButton("🔄 容器重启", callback_data="restart_menu"),
             InlineKeyboardButton("⚡ SSH性能", callback_data="ssh_perf")],
            [InlineKeyboardButton("🤖 AI助手", callback_data="ai_menu"),
             InlineKeyboardButton("🔍 系统诊断", callback_data="diagnose_menu"),
             InlineKeyboardButton("❓ 帮助", callback_data="help")]
        ]
        await query.edit_message_text(
            "🤖 *Server-Admin Bot v3.0*\n\n选择操作：",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "status":
        await status(update, context)

    elif data == "services_menu":
        # 显示服务管理子菜单
        services_keyboard = [
            [InlineKeyboardButton("📋 服务列表", callback_data="services"),
             InlineKeyboardButton("🔄 重启服务", callback_data="restart_service_menu")],
            [InlineKeyboardButton("▶️ 启动服务", callback_data="start_service_menu"),
             InlineKeyboardButton("⏹️ 停止服务", callback_data="stop_service_menu")],
            [InlineKeyboardButton("📊 服务状态", callback_data="service_status_menu"),
             InlineKeyboardButton("🔧 服务配置", callback_data="service_config")],
            [InlineKeyboardButton("🔙 返回", callback_data="start")]
        ]
        await query.edit_message_text(
            "🔧 *服务管理*\n\n选择服务管理操作:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(services_keyboard)
        )

    elif data == "services":
        await services(update, context)

    elif data == "restart_service_menu":
        await query.edit_message_text(
            "🔄 *服务重启管理*\n\n此功能正在开发中。\n\n当前可通过以下方式重启服务：\n• SSH登录服务器执行命令\n• 使用系统命令控制面板\n• 联系系统管理员",
            parse_mode='Markdown'
        )

    elif data == "start_service_menu":
        await query.edit_message_text(
            "▶️ *服务启动管理*\n\n此功能正在开发中。\n\n当前可通过以下方式启动服务：\n• SSH登录服务器执行命令\n• 使用系统命令控制面板\n• 联系系统管理员",
            parse_mode='Markdown'
        )

    elif data == "stop_service_menu":
        await query.edit_message_text(
            "⏹️ *服务停止管理*\n\n此功能正在开发中。\n\n当前可通过以下方式停止服务：\n• SSH登录服务器执行命令\n• 使用系统命令控制面板\n• 联系系统管理员",
            parse_mode='Markdown'
        )

    elif data == "service_status_menu":
        await query.edit_message_text(
            "📊 *服务状态详情*\n\n此功能正在开发中。\n\n当前可通过以下方式查看服务状态：\n• 使用 /services 命令\n• SSH登录服务器执行命令\n• 查看系统监控面板",
            parse_mode='Markdown'
        )

    elif data == "service_config":
        await query.edit_message_text(
            "🔧 *服务配置管理*\n\n此功能正在开发中。\n\n当前可通过以下方式管理服务配置：\n• SSH登录服务器编辑配置文件\n• 使用配置管理工具\n• 联系系统管理员",
            parse_mode='Markdown'
        )

    elif data == "logs":
        await logs(update, context)

    elif data == "backup_menu":
        # 显示备份管理子菜单
        backup_keyboard = [
            [InlineKeyboardButton("💾 手动备份", callback_data="backup"),
             InlineKeyboardButton("📋 备份列表", callback_data="backup_list")],
            [InlineKeyboardButton("↩️ 恢复备份", callback_data="restore_backup_menu"),
             InlineKeyboardButton("🗑️ 清理备份", callback_data="clean_backup")],
            [InlineKeyboardButton("📊 备份状态", callback_data="backup_status"),
             InlineKeyboardButton("🔧 备份配置", callback_data="backup_config")],
            [InlineKeyboardButton("🔙 返回", callback_data="start")]
        ]
        await query.edit_message_text(
            "💾 *备份管理*\n\n选择备份管理操作:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(backup_keyboard)
        )

    elif data == "backup":
        await backup(update, context)

    elif data == "backup_list":
        # 显示备份列表
        backup_list = run_command("ls -la /var/backups/ 2>/dev/null | head -20 || echo '备份目录不存在'")
        await query.edit_message_text(
            f"📋 *备份文件列表*\n\n```\n{backup_list}\n```",
            parse_mode='Markdown'
        )

    elif data == "restore_backup_menu":
        await query.edit_message_text(
            "↩️ *备份恢复管理*\n\n此功能正在开发中。\n\n当前可通过以下方式恢复备份：\n• SSH登录服务器执行恢复脚本\n• 手动解压备份文件\n• 联系系统管理员",
            parse_mode='Markdown'
        )

    elif data == "clean_backup":
        await query.edit_message_text(
            "🗑️ *备份清理*\n\n此功能正在开发中。\n\n当前可通过以下方式清理备份：\n• SSH登录服务器手动删除旧备份\n• 设置自动清理策略\n• 联系系统管理员",
            parse_mode='Markdown'
        )

    elif data == "backup_status":
        # 显示备份状态
        backup_status = run_command("/usr/local/sbin/monitoring/backup.sh --status 2>&1 || echo '无法获取备份状态'")
        await query.edit_message_text(
            f"📊 *备份状态*\n\n```\n{backup_status}\n```",
            parse_mode='Markdown'
        )

    elif data == "backup_config":
        backup_config = run_command("cat /etc/monitoring/backup.conf 2>/dev/null || echo '备份配置文件不存在'")
        await query.edit_message_text(
            f"🔧 *备份配置*\n\n```\n{backup_config}\n```",
            parse_mode='Markdown'
        )

    elif data == "restart_menu":
        await restart_menu(update, context)

    elif data == "help":
        await help_cmd(update, context)

    elif data == "ai_menu":
        # 显示AI助手子菜单
        ai_keyboard = [
            [InlineKeyboardButton("💬 AI对话", callback_data="ai_chat"),
             InlineKeyboardButton("🔍 AI分析", callback_data="ai_analyze")],
            [InlineKeyboardButton("🔧 AI优化建议", callback_data="ssh_optimize"),
             InlineKeyboardButton("📊 AI诊断", callback_data="ai_diagnose")],
            [InlineKeyboardButton("📝 AI配置", callback_data="ai_config"),
             InlineKeyboardButton("⚡ AI性能", callback_data="ai_performance")],
            [InlineKeyboardButton("🔙 返回", callback_data="start")]
        ]
        await query.edit_message_text(
            "🤖 *AI助手*\n\n选择AI功能:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(ai_keyboard)
        )

    elif data == "ai_diagnose":
        await query.edit_message_text(
            "📊 *AI系统诊断*\n\n此功能正在开发中。\n\n当前可通过以下方式诊断系统：\n• 使用 /analyze 命令进行AI分析\n• 使用 /health_check 命令进行健康检查\n• 使用系统诊断子菜单",
            parse_mode='Markdown'
        )

    elif data == "ai_config":
        ai_config_info = f"""📝 *AI配置信息*

🤖 *AI服务提供商*: Infini AI
🧠 *AI模型*: {AI_MODEL}
🌐 *API端点*: {AI_BASE_URL}

⚙️ *配置状态*:
• API Key: {'✅ 已配置' if AI_API_KEY else '❌ 未配置'}
• 模型可用性: {'✅ 已测试' if AI_API_KEY else '❌ 未测试'}

🔧 *配置位置*: {CONFIG_FILE}
💡 *使用说明*: 编辑配置文件以更改AI设置"""
        await query.edit_message_text(ai_config_info, parse_mode='Markdown')

    elif data == "ai_performance":
        await query.edit_message_text(
            "⚡ *AI性能监控*\n\n此功能正在开发中。\n\n当前AI性能：\n• 响应时间: 通常在2-5秒内\n• 可用性: 依赖网络连接\n• 准确性: 基于训练数据和提示词质量\n\n💡 *优化建议*:\n• 确保网络连接稳定\n• 使用清晰的提示词\n• 分段处理复杂问题",
            parse_mode='Markdown'
        )

    elif data == "ai_chat":
        await query.edit_message_text(
            "🤖 *AI 对话模式*\n\n直接发送消息即可与 AI 对话。\n\n例如：\n• 如何优化服务器内存？\n• Nginx 配置怎么写？\n• 帮我分析最近的错误日志",
            parse_mode='Markdown'
        )

    elif data == "ai_analyze":
        # 模拟调用 ai_analyze
        class FakeUpdate:
            def __init__(self, original_update):
                self.message = None
                self.callback_query = original_update.callback_query
                self.effective_chat = original_update.effective_chat
        await ai_analyze(FakeUpdate(update), context)

    elif data == "diagnose_menu":
        # 显示系统诊断子菜单
        diagnose_keyboard = [
            [InlineKeyboardButton("🔍 SSH诊断", callback_data="ssh_diagnose"),
             InlineKeyboardButton("💊 健康检查", callback_data="health_check")],
            [InlineKeyboardButton("🌐 网络诊断", callback_data="network_diagnose"),
             InlineKeyboardButton("📊 性能诊断", callback_data="performance_diagnose")],
            [InlineKeyboardButton("🔒 安全扫描", callback_data="security_scan"),
             InlineKeyboardButton("📈 系统监控", callback_data="system_monitor")],
            [InlineKeyboardButton("🔙 返回", callback_data="start")]
        ]
        await query.edit_message_text(
            "🔍 *系统诊断*\n\n选择诊断类型:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(diagnose_keyboard)
        )

    elif data == "ssh_perf":
        # 显示SSH性能子菜单
        ssh_perf_keyboard = [
            [InlineKeyboardButton("⏱ 响应时间", callback_data="ssh_response"),
             InlineKeyboardButton("📁 传输速度", callback_data="ssh_transfer")],
            [InlineKeyboardButton("👥 并发测试", callback_data="ssh_concurrent"),
             InlineKeyboardButton("📈 性能报告", callback_data="ssh_report")],
            [InlineKeyboardButton("🔧 优化建议", callback_data="ssh_optimize"),
             InlineKeyboardButton("🔍 问题诊断", callback_data="ssh_diagnose")],
            [InlineKeyboardButton("📊 历史趋势", callback_data="ssh_history"),
             InlineKeyboardButton("⚙️ 配置管理", callback_data="ssh_config")],
            [InlineKeyboardButton("🔙 返回", callback_data="start")]
        ]
        await query.edit_message_text(
            "⚡ *SSH性能监控*\n\n选择要查看的性能指标或测试类型:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(ssh_perf_keyboard)
        )

    elif data == "ssh_response":
        # 运行SSH响应时间测试
        thinking_msg = await query.message.reply_text("⏱ 正在测试SSH响应时间...")
        result = run_command("/Users/liulu/Server-Admin/scripts/ssh-benchmark.sh --test=response --iterations=10")
        await thinking_msg.edit_text(f"⏱ *SSH响应时间测试*\n\n{result}", parse_mode='Markdown')

    elif data == "ssh_transfer":
        # 运行SSH传输速度测试
        thinking_msg = await query.message.reply_text("📁 正在测试SSH传输速度...")
        result = run_command("/Users/liulu/Server-Admin/scripts/ssh-benchmark.sh --test=transfer --size=5MB")
        await thinking_msg.edit_text(f"📁 *SSH传输速度测试*\n\n{result}", parse_mode='Markdown')

    elif data == "ssh_concurrent":
        # 运行SSH并发连接测试
        thinking_msg = await query.message.reply_text("👥 正在测试SSH并发连接...")
        result = run_command("/Users/liulu/Server-Admin/scripts/ssh-benchmark.sh --test=concurrent --sessions=5")
        await thinking_msg.edit_text(f"👥 *SSH并发连接测试*\n\n{result}", parse_mode='Markdown')

    elif data == "ssh_report":
        # 显示完整SSH性能报告
        await ssh_performance(update, context)

    elif data == "ssh_optimize":
        # 显示SSH优化建议
        await ssh_optimize(update, context)

    elif data == "ssh_diagnose":
        # 运行SSH问题诊断
        await ssh_diagnose(update, context)

    elif data == "health_check":
        # 运行健康检查
        await health_check(update, context)

    elif data == "network_diagnose":
        # 运行网络诊断
        await network_diagnose(update, context)

    elif data == "performance_diagnose":
        # 运行性能诊断
        await performance_diagnose(update, context)

    elif data == "security_scan":
        # 运行安全扫描
        await security_scan(update, context)

    elif data == "system_monitor":
        # 运行系统监控
        await system_monitor(update, context)

    elif data == "ssh_history":
        # 显示SSH历史趋势
        await ssh_history(update, context)

    elif data == "ssh_config":
        # 显示SSH配置管理
        await ssh_config(update, context)

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
    application.add_handler(CommandHandler("ai", ai_chat))
    application.add_handler(CommandHandler("analyze", ai_analyze))
    application.add_handler(CommandHandler("help", help_cmd))
    # SSH性能命令
    application.add_handler(CommandHandler("sshstatus", ssh_status))
    application.add_handler(CommandHandler("sshperformance", ssh_performance))
    application.add_handler(CommandHandler("sshoptimize", ssh_optimize))
    application.add_handler(CommandHandler("sshdiagnose", ssh_diagnose))
    application.add_handler(CommandHandler("sshhistory", ssh_history))
    application.add_handler(CommandHandler("sshconfig", ssh_config))

    # 注册按钮回调
    application.add_handler(CallbackQueryHandler(button_callback))

    # 注册消息处理器（AI 对话）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot v2.0 starting with AI support...")
    print("Server-Admin Bot v2.0 已启动 (AI 增强版)")

    # 启动机器人 (使用 polling)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
