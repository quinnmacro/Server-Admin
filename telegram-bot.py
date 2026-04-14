#!/usr/bin/env python3
"""
Server-Admin Telegram Bot v3.9
交互式服务器管理机器人 + AI 智能助手 + SSH性能监控 + 快速诊断 + 主动告警 + 智能日志

命令菜单:
- /start  - 欢迎信息和主菜单
- /status - 服务器状态
- /services - 服务列表
- /logs - 查看日志
- /backup - 手动备份
- /restart - 重启容器
- /ai - AI 智能对话
- /analyze - AI 分析服务器
- /help - 帮助信息

SSH性能命令:
- /sshstatus - SSH服务状态和性能指标
- /sshperformance - SSH性能测试报告
- /sshoptimize - SSH性能优化建议
- /sshdiagnose - SSH连接问题诊断
- /sshhistory - SSH性能历史趋势
- /sshconfig - SSH配置管理

交互菜单:
📊 系统监控 - 状态、服务、日志
🔧 管理操作 - 备份、重启、SSH性能
🤖 智能工具 - AI助手、系统诊断
🎉 趣味功能 - 游戏、笑话、彩蛋
"""

import os
import sys
import subprocess
import logging
import json
import re
import shlex
import asyncio
import random
from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ==================== 智能路径检测 ====================

SCRIPT_SEARCH_PATHS = [
    "/usr/local/sbin/monitoring",
    "/root/repos/Server-Admin/scripts",
    os.path.dirname(os.path.abspath(__file__)),
    "/Users/liulu/Server-Admin/scripts",
]

LOG_SEARCH_PATHS = [
    "/var/log/monitoring",
    "/root/repos/Server-Admin/logs/monitoring",
    "/Users/liulu/Server-Admin/logs/monitoring",
]

def find_script(name: str) -> str:
    """智能查找脚本路径"""
    for path in SCRIPT_SEARCH_PATHS:
        full = os.path.join(path, name)
        if os.path.isfile(full):
            return full
    try:
        import shutil
        which_result = shutil.which(name)
        if which_result:
            return which_result
    except:
        pass
    return name

def find_log_dir() -> str:
    """智能查找日志目录"""
    for path in LOG_SEARCH_PATHS:
        if os.path.isdir(path):
            return path
    return "/var/log/monitoring"

def find_config_file() -> str:
    """智能查找配置文件"""
    config_files = [
        "/etc/monitoring/config.conf",
        "/root/.monitoring/config.conf",
        "/Users/liulu/.monitoring/config.conf",
    ]
    for f in config_files:
        if os.path.exists(f):
            return f
    return config_files[0]

async def reply_or_edit(update: Update, text: str, reply_markup=None, parse_mode='Markdown'):
    """统一回复：兼容消息命令和按钮回调"""
    try:
        if update.message:
            if reply_markup:
                await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, parse_mode=parse_mode)
        elif update.callback_query:
            if reply_markup:
                await update.callback_query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await update.callback_query.edit_message_text(text, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"reply_or_edit error: {e}")
        try:
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception as e2:
            logger.error(f"reply_or_edit fallback error: {e2}")

async def send_thinking(update: Update, text: str = "🤔 处理中..."):
    """发送思考中提示（兼容命令和回调）"""
    if update.message:
        return await update.message.reply_text(text)
    elif update.callback_query and update.callback_query.message:
        return await update.callback_query.message.reply_text(text)
    return None

def make_back_button(callback_data: str = "start") -> InlineKeyboardMarkup:
    """创建带返回按钮的键盘"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data=callback_data)]])

# ==================== 状态指示器工具 ====================

def status_emoji(status: str) -> str:
    """服务状态 → emoji 指示灯"""
    s = status.strip().lower()
    if s in ('active', 'running', 'yes', 'enabled', 'up'):
        return '🟢'
    elif s in ('inactive', 'stopped', 'no', 'disabled', 'down'):
        return '🔴'
    elif s in ('failed', 'error', 'unknown', '未知'):
        return '🟠'
    else:
        return '🟡'

# ==================== Phase 2: 主动告警 + 智能日志系统 ====================

import threading
import time as time_module
import sqlite3
from pathlib import Path

# 历史记录数据库
HISTORY_DB = Path.home() / ".hermes" / "bot_history.db"

def init_history_db():
    """初始化操作历史数据库"""
    HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(HISTORY_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS operations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  operation TEXT NOT NULL,
                  target TEXT,
                  user TEXT,
                  result TEXT,
                  details TEXT)''')
    conn.commit()
    conn.close()

def log_operation(operation: str, target: str = "", user: str = "telegram", result: str = "success", details: str = ""):
    """记录操作到历史"""
    try:
        conn = sqlite3.connect(HISTORY_DB)
        c = conn.cursor()
        c.execute("""INSERT INTO operations (operation, target, user, result, details)
                     VALUES (?, ?, ?, ?, ?)""", (operation, target, user, result, details))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log operation: {e}")

def get_recent_operations(limit: int = 20, operation_type: str = None, offset: int = 0) -> list:
    """获取最近的操作历史（支持分页）"""
    try:
        conn = sqlite3.connect(HISTORY_DB)
        c = conn.cursor()
        if operation_type:
            c.execute("""SELECT timestamp, operation, target, result, details 
                         FROM operations WHERE operation = ? 
                         ORDER BY timestamp DESC LIMIT ? OFFSET ?""", (operation_type, limit, offset))
        else:
            c.execute("""SELECT timestamp, operation, target, result, details 
                         FROM operations 
                         ORDER BY timestamp DESC LIMIT ? OFFSET ?""", (limit, offset))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to get operations: {e}")
        return []

def get_operation_count(operation_type: str = None) -> int:
    """获取操作总数"""
    try:
        conn = sqlite3.connect(HISTORY_DB)
        c = conn.cursor()
        if operation_type:
            c.execute("SELECT COUNT(*) FROM operations WHERE operation = ?", (operation_type,))
        else:
            c.execute("SELECT COUNT(*) FROM operations")
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Failed to get operation count: {e}")
        return 0

# 初始化数据库
init_history_db()

# 告警阈值配置
ALERT_THRESHOLDS = {
    'disk_percent': 80,
    'mem_percent': 90,
    'load_factor': 1.5,  # 负载/CPU核心数
}

# 告警状态缓存（避免重复告警）
alert_state = {
    'disk_warned': False,
    'mem_warned': False,
    'load_warned': False,
    'last_check': 0,
}

# 静默时段（夜间不打扰）
SILENCE_START = 23  # 23:00
SILENCE_END = 7     # 07:00

def is_silence_hours() -> bool:
    """检查当前是否在静默时段"""
    hour = datetime.now().hour
    return SILENCE_START <= hour or hour < SILENCE_END

async def check_and_alert(bot_app):
    """后台监控检查"""
    while True:
        try:
            # 每 5 分钟检查一次
            await asyncio.sleep(300)
            
            # 静默时段跳过
            if is_silence_hours():
                continue
            
            # 收集指标
            _disk = run_command("df -h / | awk 'NR==2{print $5}' | tr -d '%'")
            _mem = run_command("free | awk '/Mem/{printf \"%.0f\", $3/$2*100}'")
            _load = run_command("cat /proc/loadavg | awk '{print $1}'")
            _nproc = run_command("nproc")
            
            alerts = []
            
            # 磁盘检查
            disk_pct = int(_disk) if _disk.isdigit() else 0
            if disk_pct > ALERT_THRESHOLDS['disk_percent']:
                if not alert_state['disk_warned']:
                    alerts.append(f"💿 <b>磁盘告警</b>: {disk_pct}% > {ALERT_THRESHOLDS['disk_percent']}%\n建议清理或扩容")
                    alert_state['disk_warned'] = True
            else:
                alert_state['disk_warned'] = False
            
            # 内存检查
            mem_pct = float(_mem) if _mem else 0
            if mem_pct > ALERT_THRESHOLDS['mem_percent']:
                if not alert_state['mem_warned']:
                    alerts.append(f"💾 <b>内存告警</b>: {mem_pct:.1f}% > {ALERT_THRESHOLDS['mem_percent']}%\n建议检查内存泄漏")
                    alert_state['mem_warned'] = True
            else:
                alert_state['mem_warned'] = False
            
            # 负载检查
            load1 = float(_load) if _load else 0
            nproc = int(_nproc) if _nproc.isdigit() else 1
            if load1 > nproc * ALERT_THRESHOLDS['load_factor']:
                if not alert_state['load_warned']:
                    alerts.append(f"📈 <b>负载告警</b>: {load1:.2f} > {nproc * ALERT_THRESHOLDS['load_factor']:.1f}\n建议检查进程")
                    alert_state['load_warned'] = True
            else:
                alert_state['load_warned'] = False
            
            # 发送告警
            if alerts:
                from telegram import Bot
                bot = bot_app.bot
                chat_id = load_config().get('TELEGRAM_CHAT_ID')
                if chat_id:
                    msg = f"⚠️ <b>系统告警</b>\n\n" + "\n\n".join(alerts)
                    msg += f"\n\n⏰ {datetime.now().strftime('%H:%M:%S')}"
                    await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
                    logger.warning(f"Sent {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Alert check error: {e}")

def start_alert_monitor(app):
    """启动后台监控线程"""
    async def monitor():
        await check_and_alert(app)
    
    # 创建后台任务
    task = asyncio.create_task(monitor())
    logger.info("Alert monitor started")
    return task

# ==================== 安全工具 ====================

# 合法容器名/服务名白名单
VALID_SERVICES = {"ssh", "docker", "fail2ban", "tailscaled", "cron", "rsyslog", "x-ui"}
VALID_CONTAINERS = set()  # 动态填充

def validate_service_name(name: str) -> bool:
    """校验服务名是否在白名单中"""
    if name in VALID_SERVICES:
        return True
    # 允许 docker 容器名（仅字母数字-_.）
    if re.match(r'^[a-zA-Z0-9_.-]+$', name):
        return True
    return False

def validate_container_name(name: str) -> bool:
    """校验容器名（仅允许字母数字-_.）"""
    return bool(re.match(r'^[a-zA-Z0-9_.-]+$', name))

def safe_run_command(cmd: str, timeout: int = 30) -> str:
    """安全执行命令 — 使用列表形式避免 shell 注入"""
    try:
        # 对复杂 shell 管道仍用 shell=True，但确保输入已校验
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"错误: {str(e)}"

# 用 safe_run_command 替换 run_command（保留旧名兼容）
run_command = safe_run_command


async def arun_command(cmd: str, timeout: int = 30) -> str:
    """异步执行 shell 命令 — 不阻塞事件循环"""
    return await asyncio.to_thread(run_command, cmd, timeout)

async def arun_commands(*cmds_with_timeouts) -> list:
    """并行执行多个命令 — 不阻塞事件循环"""
    tasks = [asyncio.to_thread(run_command, cmd, timeout) for cmd, timeout in cmds_with_timeouts]
    return await asyncio.gather(*tasks)

async def acall_ai(prompt: str, system_prompt: str = None) -> str:
    """异步调用 AI API — 不阻塞事件循环"""
    return await asyncio.to_thread(call_ai, prompt, system_prompt)






# 配置
CONFIG_FILE = find_config_file()
# LOG_FILE 将在 load_config() 后根据环境确定

# AI 配置
AI_BASE_URL = "https://cloud.infini-ai.com/maas/coding"
AI_MODEL = "deepseek-v3.2"  # 可选: glm-5, deepseek-v3.2, kimi-k2.5, minimax-m2.7

# Markdown 转义辅助函数
def escape_html(text: str) -> str:
    """转义HTML特殊字符"""
    if not text:
        return text
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

def format_ai_response(text: str) -> str:
    """格式化AI回复 — 使用HTML保留格式"""
    if not text:
        return text
    # 转义HTML特殊字符
    text = escape_html(text)
    # 将 markdown 代码块转换为 HTML
    text = re.sub(r'```(\w*)\n([\s\S]*?)```', r'<pre><code>\2</code></pre>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # 将 markdown 粗体/斜体转换为 HTML
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    return text

# 从配置文件读取
def load_config():
    config = {}

    # 可能的配置文件位置（按优先级）
    config_files = [
        "/Users/liulu/.monitoring/config.conf",  # 用户级配置（最高优先级）
        "/etc/monitoring/config.conf",          # 系统级配置
        "/root/.monitoring/config.conf",         # root用户配置
    ]

    for config_file in config_files:
        if os.path.exists(config_file):
            # 在日志配置之前，使用简单的print
            print(f"[INFO] 加载配置文件: {config_file}", file=sys.stderr) if 'sys' in globals() else None
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key] = value.strip('"').strip("'")
            # 找到第一个可用的配置文件就停止
            break

    if not config:
        print(f"[WARNING] 未找到配置文件，使用默认配置", file=sys.stderr) if 'sys' in globals() else None

    return config

CONFIG = load_config()

# 安全检查：配置文件权限
try:
    _config_perms = os.stat(CONFIG_FILE).st_mode & 0o777
    if _config_perms != 0o600:
        os.chmod(CONFIG_FILE, 0o600)
        print(f"[SECURITY] Fixed config permissions: {oct(_config_perms)} → 0o600", file=sys.stderr)
except:
    pass

TOKEN = CONFIG.get('TELEGRAM_BOT_TOKEN', '')
ALLOWED_CHAT_ID = int(CONFIG.get('TELEGRAM_CHAT_ID', '0'))
AI_API_KEY = CONFIG.get('INFINI_API_KEY', '')

# 确定日志文件路径
LOG_DIR = CONFIG.get('LOG_DIR', '')
if LOG_DIR and os.path.exists(LOG_DIR):
    # 使用配置中的LOG_DIR
    LOG_FILE = os.path.join(LOG_DIR, 'telegram-bot.log')
elif os.path.exists('/var/log/monitoring'):
    # 服务器默认路径
    LOG_FILE = '/var/log/monitoring/telegram-bot.log'
elif os.path.exists('/Users/liulu/.monitoring'):
    # 本地Mac路径
    LOG_FILE = '/Users/liulu/.monitoring/telegram-bot.log'
else:
    # 最后回退到当前目录
    LOG_FILE = 'telegram-bot.log'

# 确保日志目录存在
log_dir = os.path.dirname(LOG_FILE)
if log_dir and not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        print(f"[WARNING] 无法创建日志目录 {log_dir}: {e}", file=sys.stderr)

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
        # 检查实际加载的配置文件
        config_locations = [
            "/Users/liulu/.monitoring/config.conf",
            "/etc/monitoring/config.conf",
            "/root/.monitoring/config.conf"
        ]
        existing_config = None
        for config_file in config_locations:
            if os.path.exists(config_file):
                existing_config = config_file
                break

        if existing_config:
            return f"⚠️ AI API Key 未配置，请在 {existing_config} 中设置 INFINI_API_KEY\n\n示例配置:\nINFINI_API_KEY=\"your_api_key_here\"\n\n您可以从 https://cloud.infini-ai.com/ 获取API密钥"
        else:
            return "⚠️ AI API Key 未配置，请创建配置文件并设置 INFINI_API_KEY\n\n创建文件: /Users/liulu/.monitoring/config.conf\n添加内容:\nINFINI_API_KEY=\"your_api_key_here\"\n\n您可以从 https://cloud.infini-ai.com/ 获取API密钥"

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
    _uptime = run_command("uptime -p | sed 's/up //'")
    _mem = run_command("free -m | awk 'NR==2{printf \"%s/%s MB (%.1f%%)\", $3, $2, $3*100/$2}'")
    _disk = run_command("df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'")
    _load = run_command("cat /proc/loadavg | awk '{print $1,\"\",$2,\"\",$3}'")
    _containers = run_command("docker ps --format '{{.Names}}: {{.Status}}'")
    context = (
        f"服务器信息:\n"
        f"- 主机: Vultr 东京\n"
        f"- 配置: 1 vCPU, 2GB RAM, 52GB SSD\n"
        f"- 运行时间: {_uptime}\n"
        f"- 内存: {_mem}\n"
        f"- 磁盘: {_disk}\n"
        f"- 负载: {_load}\n"
        f"- 容器: {_containers}\n"
    )
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
         InlineKeyboardButton("🎉 趣味", callback_data="fun_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        build_welcome_message(),
        parse_mode='HTML',
        reply_markup=build_main_keyboard()
    )
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

    response = await acall_ai(user_message, system_prompt)

    # 更新消息（转义Markdown避免解析错误）
    escaped_response = format_ai_response(response)
    await thinking_msg.edit_text(f"🤖 AI 回复:\n\n{escaped_response}", parse_mode='HTML')
    logger.info(f"AI chat: {user_message[:50]}...")

async def ai_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI 分析服务器状态"""
    if not authorized(update):
        return

    # 判断是来自消息还是回调查询
    thinking_msg = await send_thinking(update, "🔍 正在收集服务器信息并分析...")
    if not thinking_msg:
        return

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

    response = await acall_ai(prompt, system_prompt)

    # 转义Markdown避免解析错误
    escaped_response = format_ai_response(response)
    if thinking_msg:
        await thinking_msg.edit_text(f"🔍 AI 服务器分析:\n\n{escaped_response}", parse_mode='HTML')
    else:
        await reply_or_edit(update, f"🔍 AI 服务器分析:\n\n{escaped_response}", parse_mode='HTML')
    logger.info("AI analysis executed")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通消息（自然语言指令 + AI 对话）"""
    if not authorized(update):
        return

    # 忽略命令
    if update.message and update.message.text and update.message.text.startswith('/'):
        return

    user_message = update.message.text if update.message else ""
    if not user_message.strip():
        return

    # ========== 自然语言指令识别 ==========
    msg_lower = user_message.lower()
    
    # 重启指令
    if any(kw in msg_lower for kw in ['重启', 'restart', '重启一下']):
        # 尝试提取服务/容器名
        for svc in ['nginx', 'docker', 'ssh', 'fail2ban', 'homepage', 'mem0']:
            if svc in msg_lower:
                if svc in ['nginx', 'homepage', 'mem0']:
                    # Docker 容器
                    await update.message.reply_text(f"🔄 正在重启容器 {svc}...", parse_mode='HTML')
                    result = run_command(f"docker restart {svc} 2>&1")
                    await update.message.reply_text(f"✅ 容器 {svc} 已重启\n```\n{result}\n```", parse_mode='Markdown')
                    log_operation("restart_container", svc, result="success")
                else:
                    # 系统服务
                    if validate_service_name(svc):
                        result = run_command(f"systemctl restart {svc} 2>&1")
                        new_status = run_command(f"systemctl is-active {svc}")
                        await update.message.reply_text(f"✅ 服务 {svc} 已重启\n状态: {status_emoji(new_status)} {new_status}", parse_mode='HTML')
                        log_operation("restart_service", svc, result=new_status.strip())
                return
        
        # 没有指定服务，询问用户
        keyboard = [[InlineKeyboardButton("🔙 主菜单", callback_data="start")]]
        await update.message.reply_text("🔄 请指定要重启的服务或容器，例如：\n• 重启 nginx\n• 重启 docker\n• 重启 ssh", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # 查看状态
    if any(kw in msg_lower for kw in ['状态', 'status', '查看状态', '怎么样']):
        await status(update, context)
        return
    
    # 查看日志
    if any(kw in msg_lower for kw in ['日志', 'log', '查看日志', '看日志']):
        await logs(update, context)
        return
    
    # 备份
    if any(kw in msg_lower for kw in ['备份', 'backup', '帮我备份', '做备份']):
        await backup(update, context)
        return
    
    # 诊断
    if any(kw in msg_lower for kw in ['诊断', 'diagnose', '检查问题', '排查']):
        await quick_diagnose(update, context)
        return
    
    # 磁盘空间
    if any(kw in msg_lower for kw in ['磁盘', 'disk', '空间', '容量']):
        disk_info = run_command("df -h")
        keyboard = [[InlineKeyboardButton("🔙 主菜单", callback_data="start")]]
        await update.message.reply_text(f"💿 <b>磁盘使用情况</b>\n\n<pre>{disk_info}</pre>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # 内存使用
    if any(kw in msg_lower for kw in ['内存', 'memory', 'ram']):
        mem_info = run_command("free -h")
        keyboard = [[InlineKeyboardButton("🔙 主菜单", callback_data="start")]]
        await update.message.reply_text(f"💾 <b>内存使用情况</b>\n\n<pre>{mem_info}</pre>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Docker 容器
    if any(kw in msg_lower for kw in ['容器', 'container', 'docker']):
        containers = run_command("docker ps -a --format 'table {{.Names}}\\t{{.Status}}'")
        keyboard = [[InlineKeyboardButton("🔙 主菜单", callback_data="start")]]
        await update.message.reply_text(f"🐳 <b>Docker 容器</b>\n\n<pre>{containers}</pre>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # 显示主菜单
    if any(kw in msg_lower for kw in ['菜单', 'menu', '主菜单', '功能', '帮助']):
        await update.message.reply_text(build_welcome_message(), parse_mode='HTML', reply_markup=build_main_keyboard())
        return

    # ========== 未识别指令，走 AI 对话 ==========
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

请用简洁、专业的中文回复。如果需要执行操作，请告诉用户具体命令。

注意：用户可以直接用自然语言操作服务器，例如：
- "重启 nginx" → 自动重启容器
- "查看日志" → 显示日志菜单
- "磁盘空间" → 显示磁盘使用
- "备份一下" → 执行备份"""

    response = await acall_ai(user_message, system_prompt)

    # 转义Markdown避免解析错误
    escaped_response = format_ai_response(response)
    
    # 添加返回主菜单提示
    keyboard = [[InlineKeyboardButton("🔙 主菜单", callback_data="start")]]
    await thinking_msg.edit_text(f"🤖 {escaped_response}\n\n💡 输入「菜单」返回主菜单", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    logger.info(f"Message handled: {user_message[:50]}...")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """服务器状态"""
    if not authorized(update):
        return

    mem, disk, load, uptime, containers = await arun_commands(
        ("free -m | awk 'NR==2{printf \"%s/%s MB (%.1f%%)\", $3, $2, $3*100/$2}'", 10),
        ("df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'", 10),
        ("cat /proc/loadavg | awk '{print $1, $2, $3}'", 5),
        ("uptime -p | sed 's/up //'", 5),
        ("docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null || echo 'Docker未运行'", 10),
    )

    status_msg = (
        f"📊 *服务器状态*\n\n"
        f"⏱ *运行时间*: {uptime}\n"
        f"💾 *内存*: {mem}\n"
        f"💿 *磁盘*: {disk}\n"
        f"📈 *负载*: {load}\n\n"
        f"🐳 *容器状态*:\n```\n{containers}\n```"
    )

    await reply_or_edit(update, status_msg, parse_mode='Markdown')
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

    await reply_or_edit(update, msg, parse_mode='Markdown')

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
        [InlineKeyboardButton("🧠 智能分析", callback_data="analyze_logs"),
         InlineKeyboardButton("📋 健康检查", callback_data="logs_health")],
        [InlineKeyboardButton("🔐 SSH日志", callback_data="logs_ssh"),
         InlineKeyboardButton("🚨 Fail2ban", callback_data="logs_fail2ban")],
        [InlineKeyboardButton("🐳 Docker", callback_data="logs_docker"),
         InlineKeyboardButton("🔙 返回", callback_data="start")]
    ]

    await reply_or_edit(update, msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """手动备份"""
    if not authorized(update):
        return

    msg = "💾 *开始备份...*\n\n备份任务已在后台执行，完成后会发送通知。"

    await reply_or_edit(update, msg, parse_mode='Markdown')

    # 异步执行备份
    run_command(find_script("backup.sh") + " &")
    logger.info("Backup command executed")
    
    # 记录操作历史
    log_operation("backup", "manual", result="started")

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

    await reply_or_edit(update, msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

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

async def analyze_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """智能日志分析 - AI 自动诊断错误"""
    if not authorized(update):
        return
    
    processing_msg = await send_thinking(update, "🧠 正在分析日志...")
    
    try:
        # 收集各类日志
        logs_data = {}
        
        # 系统日志
        logs_data['syslog'] = run_command("journalctl -p err -n 20 --no-pager 2>/dev/null || echo 无错误")
        
        # SSH 日志
        logs_data['ssh'] = run_command("journalctl -u ssh -p warning -n 15 --no-pager 2>/dev/null || echo 无警告")
        
        # Docker 日志（最新容器的错误）
        logs_data['docker'] = run_command("docker ps --format '{{.Names}}' 2>/dev/null | head -1 | xargs -I {} docker logs --tail 20 {} 2>&1 | grep -iE 'error|fail|exception' | tail -10 || echo 无错误")
        
        # Fail2ban 日志
        logs_data['fail2ban'] = run_command("tail -20 /var/log/fail2ban.log 2>/dev/null | grep -iE 'ban|unban|fail' | tail -10 || echo 无记录")
        
        # 统计错误数量
        error_counts = {
            'syslog': len([l for l in logs_data['syslog'].split('\n') if l.strip() and '无错误' not in l]),
            'ssh': len([l for l in logs_data['ssh'].split('\n') if l.strip() and '无警告' not in l]),
            'docker': len([l for l in logs_data['docker'].split('\n') if l.strip() and '无错误' not in l]),
            'fail2ban': len([l for l in logs_data['fail2ban'].split('\n') if l.strip() and '无记录' not in l]),
        }
        
        total_errors = sum(error_counts.values())
        
        # 构建分析报告
        report = f"""🧠 <b>智能日志分析报告</b>

📊 <b>错误统计</b>:
  ├ 系统日志: {error_counts['syslog']} 条错误
  ├ SSH 日志: {error_counts['ssh']} 条警告
  ├ Docker 日志: {error_counts['docker']} 条错误
  └ Fail2ban: {error_counts['fail2ban']} 条记录

📈 <b>总问题数</b>: {total_errors} 条
"""
        
        # 如果有错误，调用 AI 分析
        if total_errors > 0:
            # 准备 AI 分析提示
            ai_prompt = f"""分析以下服务器日志，找出关键问题并给出解决建议：

系统日志（最近错误）:
{logs_data['syslog'][:500]}

SSH 日志（最近警告）:
{logs_data['ssh'][:500]}

Docker 日志（最近错误）:
{logs_data['docker'][:500]}

请简洁总结：
1. 最关键的 1-2 个问题
2. 可能的根因
3. 建议的解决步骤（不超过3步）
"""
            
            # 调用 AI
            ai_analysis = await acall_ai(ai_prompt, system_prompt="你是服务器运维专家，简洁专业地分析日志问题。")
            
            report += f"\n💡 <b>AI 诊断建议</b>:\n{ai_analysis[:500]}"
        
        else:
            report += "\n\n✅ <b>系统运行正常</b>\n未发现严重错误或警告。"
        
        # 删除处理消息
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass
        
        # 添加操作按钮
        keyboard = [
            [InlineKeyboardButton("📋 详细日志", callback_data="logs"),
             InlineKeyboardButton("🔍 系统诊断", callback_data="diagnose_menu")],
            [InlineKeyboardButton("🔄 重新分析", callback_data="analyze_logs"),
             InlineKeyboardButton("🔙 主菜单", callback_data="start")]
        ]
        
        await reply_or_edit(update, report, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        
        # 记录操作
        log_operation("analyze_logs", "all", result="success", details=f"Found {total_errors} issues")
        
    except Exception as e:
        logger.error(f"Log analysis error: {e}")
        await reply_or_edit(update, f"⚠️ 分析失败: {str(e)}", parse_mode='HTML')

async def cron_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """定时任务管理（查看当前 cron）"""
    if not authorized(update):
        return
    
    # 获取当前用户的 cron
    cron_list = run_command("crontab -l 2>/dev/null || echo '无定时任务'")
    
    # 获取系统级监控 cron
    system_cron = run_command("ls /etc/cron.d/ 2>/dev/null | grep -E 'monitor|backup|health' || echo '无系统监控任务'")
    
    report = f"""⚙️ <b>定时任务管理</b>

📅 <b>用户定时任务</b>:
<pre>{cron_list}</pre>

🔧 <b>系统监控任务</b>:
<pre>{system_cron}</pre>

💡 <b>常用定时任务</b>:
• 每日备份: 0 2 * * * /usr/local/sbin/monitoring/backup.sh
• 健康检查: */5 * * * * /usr/local/sbin/monitoring/health-check.sh
• 日志清理: 0 3 * * 0 find /var/log -name "*.log" -mtime +30 -delete

⚠️ 添加任务需手动执行: crontab -e
或请 AI 帮你生成 cron 表达式
"""
    
    keyboard = [
        [InlineKeyboardButton("🤖 AI 生成 cron", callback_data="ai_cron_help"),
         InlineKeyboardButton("🔄 刷新", callback_data="cron_manager")],
        [InlineKeyboardButton("🔙 主菜单", callback_data="start")]
    ]
    
    await reply_or_edit(update, report, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看操作历史（支持分页）"""
    if not authorized(update):
        return
    
    # 获取页码（默认第1页）
    page = 1
    per_page = 10
    
    # 构建历史列表
    total = get_operation_count()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    operations = get_recent_operations(limit=per_page, offset=(page-1)*per_page)
    
    if not operations:
        await reply_or_edit(update, "📝 <b>操作历史</b>\n\n暂无操作记录", parse_mode='HTML')
        return
    
    lines = [f"📝 <b>操作历史</b> (第 {page}/{total_pages} 页)\n"]
    for ts, op, target, result, details in operations:
        time_str = ts.split('.')[0] if '.' in ts else ts
        icon = "✅" if result == "success" else "❌"
        line = f"{icon} <i>{time_str}</i> {op}"
        if target:
            line += f" → <b>{target}</b>"
        lines.append(line)
    
    # 分页按钮
    keyboard = []
    if page > 1:
        keyboard.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"history_page_{page-1}"))
    if page < total_pages:
        keyboard.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"history_page_{page+1}"))
    
    nav_row = keyboard if keyboard else []
    
    keyboard = [
        [InlineKeyboardButton("🔄 重启操作", callback_data="history_restart"),
         InlineKeyboardButton("💾 备份操作", callback_data="history_backup")],
        [InlineKeyboardButton("🔧 服务操作", callback_data="history_service"),
         InlineKeyboardButton("📊 全部", callback_data="history_all")],
        nav_row,
        [InlineKeyboardButton("🔙 主菜单", callback_data="start")]
    ]
    
    # 过滤空行
    keyboard = [row for row in keyboard if row]
    
    await reply_or_edit(update, '\n'.join(lines), parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

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
点击 🎉 趣味 按钮发现隐藏彩蛋功能

*注意事项:*
- 敏感操作需要二次确认
- 所有操作都会被记录
- 仅授权用户可使用
- SSH性能测试可能会消耗资源

*问题反馈:*
GitHub: github.com/quinnmacro/Server-Admin"""

    await reply_or_edit(update, help_msg, reply_markup=make_back_button(), parse_mode='Markdown')

# ==================== 彩蛋功能 ====================

async def easteregg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """彩蛋命令 - 隐藏的趣味功能"""
    if not authorized(update):
        return

    # 随机选择一种彩蛋类型
    egg_types = ["game", "joke", "poetry", "fortune", "meme", "ai"]
    egg_type = random.choice(egg_types)

    if egg_type == "game":
        games = [
            "🎮 *猜数字游戏*\n\n我正在想一个1-100之间的数字，猜猜看是多少？\n\n发送 `/guess 数字` 来猜测！",
            "🎯 *服务器挑战*\n\n你能让服务器负载保持在1.0以下吗？\n使用 `/status` 查看当前负载！",
            "🏆 *运维大师*\n\n连续7天每天运行健康检查，获得'运维大师'称号！"
        ]
        await update.message.reply_text(random.choice(games), parse_mode='Markdown')

    elif egg_type == "joke":
        jokes = [
            "🤣 *程序员笑话*\n\n问：为什么程序员总是把万圣节和圣诞节搞混？\n答：因为 Oct 31 == Dec 25！",
            "😄 *服务器笑话*\n\n问：服务器最害怕什么？\n答：404错误，因为它意味着'找不到页面'，但实际上是'找不到原因'！",
            "🎯 *SSH笑话*\n\n问：SSH连接对女朋友说什么？\n答：'我需要你的公钥才能进入你的心里！'",
            "🐛 *Bug笑话*\n\n问：为什么程序员不喜欢大自然？\n答：因为那里有太多的Bug！"
        ]
        await update.message.reply_text(random.choice(jokes), parse_mode='Markdown')

    elif egg_type == "poetry":
        poems = [
            "🎭 *代码的诗篇*\n\n在数字的海洋里，\n我寻找着答案的光芒。\n\n每一行代码，\n都是一句诗句，\n在服务器的心跳中，\n找到技术的韵律。",
            "🌌 *服务器的夜曲*\n\n当月光洒在数据中心，\n服务器轻声低语。\n\nCPU在思考，\n内存在回忆，\n硬盘在诉说，\n网络的秘密。",
            "⚡ *SSH的连接*\n\n穿过千山万水的隧道，\n抵达服务器的怀抱。\n\n加密的握手，\n安全的通道，\n每一次连接，\n都是信任的拥抱。"
        ]
        await update.message.reply_text(random.choice(poems), parse_mode='Markdown')

    elif egg_type == "fortune":
        fortunes = [
            "🥠 *幸运代码饼干*\n\n```\n┌────────────────────────┐\n│  你的代码今天会运行    │\n│      得特别流畅！      │\n└────────────────────────┘\n```",
            "🔮 *技术预言*\n\n> 今天你会发现一个隐藏的Bug，\n> 但也会找到优雅的解决方案。\n\n💡 *提示*：查看日志获取线索。",
            "🌟 *服务器星座*\n\n**运维座今日运势**：\n• 工作：适合优化配置\n• 爱情：与代码关系融洽\n• 健康：系统负载平稳\n• 财运：备份一切顺利",
            "🎯 *今日任务*\n\n1. 对代码微笑一次\n2. 感谢服务器辛勤工作\n3. 备份重要数据\n4. 学习新技术"
        ]
        await update.message.reply_text(random.choice(fortunes), parse_mode='Markdown')

    elif egg_type == "meme":
        memes = [
            "😎 *程序员专属表情包*\n\n```\n  ╔════════════════╗\n  ║  听说你在找Bug? ║\n  ╚════════════════╝\n          👉 👈\n        我在这呢！\n```",
            "🚀 *服务器日常*\n\n```\n  [负载: 0.5] 我还能行！\n  [负载: 1.5] 有点压力...\n  [负载: 3.0] 我要重启了！\n```",
            "🤖 *AI的内心独白*\n\n```\n人类：帮我优化服务器\nAI：正在思考...\nAI：建议重启\n人类：就这？\nAI：🤖💔\n```"
        ]
        await update.message.reply_text(random.choice(memes), parse_mode='Markdown')

    elif egg_type == "ai":
        ai_eggs = [
            "🤖 *AI秘密*\n\n你知道吗？我其实每天都在学习\n如何更好地为你服务！\n\n💭 *内心想法*：希望人类多夸夸我~",
            "🧠 *神经网络低语*\n\n我看到了...看到了...\n服务器的未来是光明的！\n\n（其实我只是个脚本）",
            "🎭 *AI的戏剧*\n\n**第一幕**：接收命令\n**第二幕**：处理请求\n**第三幕**：返回结果\n\n*观众掌声* 👏👏👏"
        ]
        await update.message.reply_text(random.choice(ai_eggs), parse_mode='Markdown')

    logger.info(f"Easter egg triggered: {egg_type}")

# ==================== SSH性能功能 ====================

async def ssh_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH服务状态和性能指标"""
    if not authorized(update):
        return

    _svc, _uptime, _conns, _mem, _resp, _maxsess, _usedns, _comp, _perf_conf = await arun_commands(
        ("systemctl is-active ssh", 5),
        ("systemctl show -p ActiveEnterTimestamp --value ssh", 5),
        ("ss -tan | grep ':22' | grep ESTAB | wc -l", 5),
        ("ps aux | grep sshd | grep -v grep | awk '{sum += $6} END {print sum/1024 \"MB\"}'", 5),
        ("timeout 5 bash -c 'time (ssh -o ConnectTimeout=3 localhost echo -n 2>&1 >/dev/null)' 2>&1 | grep real | awk '{print $2}'", 10),
        ("sshd -T 2>/dev/null | grep maxsessions | awk '{print $2}'", 5),
        ("sshd -T 2>/dev/null | grep usedns | awk '{print $2}'", 5),
        ("sshd -T 2>/dev/null | grep compression | awk '{print $2}'", 5),
        ("[ -f /etc/ssh/sshd_config.d/performance.conf ] && echo 'yes' || echo 'no'", 5),
    )
    
    opt_status = '✅ 已优化' if _perf_conf.strip() == 'yes' else '❌ 未优化'
    status_msg = (
        f"🔐 *SSH服务状态*\n\n"
        f"🟢 服务状态: {_svc}\n"
        f"⏱ 运行时间: {_uptime}\n"
        f"👥 活动连接: {_conns} 个\n"
        f"💾 内存使用: {_mem}\n"
        f"⏱ 响应时间: {_resp}\n\n"
        f"📊 性能指标:\n"
        f"• MaxSessions: {_maxsess}\n"
        f"• UseDNS: {_usedns}\n"
        f"• Compression: {_comp}\n\n"
        f"🔧 优化状态: {opt_status}"
    )

    await reply_or_edit(update, status_msg, parse_mode='Markdown')
    logger.info("SSH status command executed")

async def ssh_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH性能测试报告"""
    if not authorized(update):
        return

    # 运行SSH性能测试
    thinking_msg = await send_thinking(update, "🔍 正在运行SSH性能测试...")

    # 调用现有的ssh-benchmark.sh脚本
    benchmark_result = run_command(find_script("ssh-benchmark.sh") + " --quick")

    await reply_or_edit(update, f"📊 *SSH性能测试报告*\n\n{format_ai_response(str(benchmark_result))}", parse_mode='Markdown')
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

    thinking_msg = await send_thinking(update, "🤔 正在分析SSH配置并生成优化建议...")

    system_prompt = "你是一个专业的SSH服务器优化专家，擅长性能调优和安全配置。请用中文回答，提供具体的配置命令。"
    response = await acall_ai(prompt, system_prompt)

    # 转义Markdown避免解析错误
    escaped_response = format_ai_response(response)
    await reply_or_edit(update, f"🔧 SSH优化建议:\n\n{escaped_response}", parse_mode='HTML')
    logger.info("SSH optimize suggestion executed")

async def ssh_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH连接问题诊断"""
    if not authorized(update):
        return

    thinking_msg = await send_thinking(update, "🔍 正在诊断SSH连接问题...")

    _ssh_svc = run_command("systemctl is-active ssh")
    _port_listen = run_command("ss -tln | grep ':22' || echo '未监听'")
    _local_conn = run_command("timeout 3 bash -c 'echo >/dev/tcp/127.0.0.1/22' 2>&1 && echo '本地连接正常' || echo '本地连接失败'")
    _conn_time = run_command("timeout 5 bash -c 'time (ssh -o ConnectTimeout=3 localhost echo -n 2>&1 >/dev/null)' 2>&1 | grep real | awk '{print $2}'")
    _active = run_command("ss -tan | grep ':22' | grep ESTAB | wc -l")
    _procs = run_command("ps aux | grep sshd | grep -v grep | wc -l")
    _f2b = run_command("fail2ban-client ping 2>&1 | grep -q 'pong' && echo '正常' || echo '异常'")
    _disk = run_command("df -h / | awk 'NR==2{print $5}'")
    _load = run_command("cat /proc/loadavg | awk '{print $1}'")
    _permit_root = run_command("sshd -T 2>/dev/null | grep permitrootlogin | awk '{print $2}'")
    _pwd_auth = run_command("sshd -T 2>/dev/null | grep passwordauthentication | awk '{print $2}'")
    _max_auth = run_command("sshd -T 2>/dev/null | grep maxauthtries | awk '{print $2}'")
    _perf_deployed = run_command("[ -f /etc/ssh/sshd_config.d/performance.conf ] && echo 'yes' || echo 'no'")
    _usedns = run_command("sshd -T 2>/dev/null | grep usedns | awk '{print $2}'")
    _comp = run_command("sshd -T 2>/dev/null | grep compression | awk '{print $2}'")
    
    perf_status = '✅ 已部署' if _perf_deployed.strip() == 'yes' else '❌ 未部署'
    
    diagnostic_info = (
        f"🔧 *SSH连接诊断报告*\n\n"
        f"📊 *基本连接测试:*\n"
        f"• SSH服务状态: {_ssh_svc}\n"
        f"• SSH端口监听: {_port_listen}\n"
        f"• 网络连通性: {_local_conn}\n\n"
        f"📈 *性能指标:*\n"
        f"• 连接建立时间: {_conn_time}\n"
        f"• 活跃连接数: {_active}\n"
        f"• SSH进程数: {_procs}\n\n"
        f"⚠️ *常见问题检查:*\n"
        f"• Fail2ban状态: {_f2b}\n"
        f"• 磁盘空间: {_disk}\n"
        f"• 系统负载: {_load}\n\n"
        f"🔒 *安全配置检查:*\n"
        f"• PermitRootLogin: {_permit_root}\n"
        f"• PasswordAuthentication: {_pwd_auth}\n"
        f"• MaxAuthTries: {_max_auth}\n\n"
        f"🎯 *优化配置检查:*\n"
        f"• 性能配置: {perf_status}\n"
        f"• UseDNS: {_usedns}\n"
        f"• Compression: {_comp}"
    )

    await reply_or_edit(update, diagnostic_info, parse_mode='Markdown')
    logger.info("SSH diagnose command executed")

async def ssh_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SSH性能历史趋势"""
    if not authorized(update):
        return

    # 检查是否有历史性能数据
    history_data = run_command("ls -la " + find_log_dir() + "/ssh-results-*.json 2>/dev/null | head -5")

    if "ssh-results" in history_data:
        # 获取最新的性能数据文件
        latest_file = run_command("ls -t " + find_log_dir() + "/ssh-results-*.json 2>/dev/null | head -1")
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

async def quick_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """快速诊断 - 一键检查系统健康状态"""
    if not authorized(update):
        return
    
    processing_msg = await send_thinking(update, "🚀 正在快速诊断...")
    
    try:
        _mem, _disk, _load, _docker, _ssh, _f2b = await arun_commands(
            ("free -m | awk 'NR==2{printf \"%s/%s MB\", $3, $2}'", 5),
            ("df -h / | awk 'NR==2{print $5}'", 5),
            ("cat /proc/loadavg | awk '{print $1}'", 5),
            ("docker ps -q 2>/dev/null | wc -l", 5),
            ("systemctl is-active ssh", 5),
            ("systemctl is-active fail2ban", 5),
        )
        
        report = f"""🚀 <b>快速诊断报告</b>

📊 <b>系统状态</b>:
  ├ 内存: {_mem}
  ├ 磁盘: {_disk}
  ├ 负载: {_load}
  └ Docker: {_docker} 个

🔧 <b>服务状态</b>:
  ├ SSH: {status_emoji(_ssh)} {_ssh}
  └ Fail2ban: {status_emoji(_f2b)} {_f2b}
"""
        
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass
        
        keyboard = [
            [InlineKeyboardButton("🔍 详细诊断", callback_data="diagnose_menu"),
             InlineKeyboardButton("🔄 刷新", callback_data="quick_diagnose")],
            [InlineKeyboardButton("🔙 主菜单", callback_data="start")]
        ]
        
        await reply_or_edit(update, report, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Quick diagnose error: {e}")
        await reply_or_edit(update, f"⚠️ 诊断失败: {str(e)}", parse_mode='HTML')

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """运行系统健康检查"""
    if not authorized(update):
        return

    thinking_msg = await send_thinking(update, "💊 正在运行系统健康检查...")

    # 运行健康检查脚本（如果存在）
    health_result = run_command(find_script("health-check.sh") + " 2>&1 | tail -30")

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

    await reply_or_edit(update, result_msg, parse_mode='Markdown')
    logger.info("Health check command executed")

async def network_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """网络诊断"""
    if not authorized(update):
        return

    thinking_msg = await send_thinking(update, "🌐 正在诊断网络连接...")

    _iface = run_command("ip addr show | head -20")
    _loopback = run_command("ping -c 1 127.0.0.1 2>&1 | grep 'packet loss' || echo '测试失败'")
    _gateway = run_command("ip route show default | head -1 || echo '无默认路由'")
    _dns = run_command("nslookup google.com 2>&1 | head -2 || echo 'DNS测试失败'")
    _tcp = run_command("ss -tan | grep ESTAB | wc -l")
    _listen = run_command("ss -tln | grep LISTEN | wc -l")
    _timewait = run_command("ss -tan | grep TIME-WAIT | wc -l")
    _closewait = run_command("ss -tan | grep CLOSE-WAIT | wc -l")
    
    network_info = (
        f"🌐 *网络诊断报告*\n\n"
        f"📊 *网络接口信息:*\n```\n{_iface}\n```\n\n"
        f"📡 *网络连通性测试:*\n"
        f"• 本地回环: {_loopback}\n"
        f"• 网关连通性: {_gateway}\n"
        f"• DNS解析测试: {_dns}\n\n"
        f"🔗 *网络连接状态:*\n"
        f"• 活动TCP连接: {_tcp} 个\n"
        f"• 监听端口: {_listen} 个\n\n"
        f"🚨 *网络问题检查:*\n"
        f"• TIME-WAIT: {_timewait} 个\n"
        f"• CLOSE-WAIT: {_closewait} 个\n\n"
        f"🎯 *建议操作:*\n"
        f"1. 检查网络配置\n"
        f"2. 验证防火墙规则\n"
        f"3. 测试外部连通性\n"
        f"4. 监控网络流量"
    )

    await reply_or_edit(update, network_info, parse_mode='Markdown')
    logger.info("Network diagnose command executed")

async def performance_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """性能诊断"""
    if not authorized(update):
        return

    thinking_msg = await send_thinking(update, "📊 正在诊断系统性能...")

    _nproc = run_command("nproc 2>/dev/null || echo 'N/A'")
    _loadavg = run_command("cat /proc/loadavg 2>/dev/null || echo 'N/A'")
    _cpu = run_command("top -bn1 | grep 'Cpu(s)' 2>/dev/null || echo 'N/A'")
    _mem = run_command("free -m 2>/dev/null || echo '内存信息不可用'")
    _disk = run_command("df -h / 2>/dev/null | tail -1 || echo 'N/A'")
    _inode = run_command("df -i / 2>/dev/null | tail -1 || echo 'N/A'")
    _dcount = run_command("docker ps -q 2>/dev/null | wc -l")
    _dstats = run_command("docker stats --no-stream 2>/dev/null | head -5 || echo 'Docker未运行'")
    
    performance_info = (
        f"📊 *系统性能诊断报告*\n\n"
        f"⚡ *CPU和负载:*\n"
        f"• CPU核心数: {_nproc}\n"
        f"• 系统负载: {_loadavg}\n"
        f"• CPU使用率: {_cpu}\n\n"
        f"💾 *内存使用:*\n```\n{_mem}\n```\n\n"
        f"💿 *磁盘IO:*\n"
        f"• 磁盘使用率: {_disk}\n"
        f"• Inode使用: {_inode}\n\n"
        f"🐳 *容器性能:*\n"
        f"• 运行中容器: {_dcount} 个\n"
        f"• 容器资源使用:\n```\n{_dstats}\n```\n\n"
        f"📈 *性能建议:*\n"
        f"1. 监控系统负载趋势\n"
        f"2. 检查内存泄漏\n"
        f"3. 优化磁盘IO\n"
        f"4. 调整容器资源限制"
    )

    await reply_or_edit(update, performance_info, parse_mode='Markdown')
    logger.info("Performance diagnose command executed")

async def security_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """安全扫描"""
    if not authorized(update):
        return

    thinking_msg = await send_thinking(update, "🔒 正在扫描系统安全...")

    # 收集安全扫描信息
    _ssh_active = run_command("systemctl is-active ssh 2>/dev/null || echo '未知'")
    _f2b_status = run_command("fail2ban-client ping 2>&1 | grep -q 'pong' && echo '运行中' || echo '未运行'")
    _ufw_status = run_command("ufw status 2>/dev/null | head -1 || echo '防火墙未启用'")
    _permit_root = run_command("sshd -T 2>/dev/null | grep permitrootlogin | awk '{print $2}' 2>/dev/null || echo 'N/A'")
    _pwd_auth = run_command("sshd -T 2>/dev/null | grep passwordauthentication | awk '{print $2}' 2>/dev/null || echo 'N/A'")
    _max_auth = run_command("sshd -T 2>/dev/null | grep maxauthtries | awk '{print $2}' 2>/dev/null || echo 'N/A'")
    _ssh_fails = run_command("journalctl -u ssh --since '1 hour ago' 2>/dev/null | grep -cE 'Failed|Invalid' 2>/dev/null || echo '0'")
    _f2b_banned = run_command("fail2ban-client status sshd 2>/dev/null | grep 'Currently banned' | awk '{print $4}' 2>/dev/null || echo '0'")
    
    security_info = (
        f"🔒 *系统安全扫描报告*\n\n"
        f"🛡️ *基本安全检查:*\n"
        f"• SSH服务状态: {_ssh_active}\n"
        f"• Fail2ban状态: {_f2b_status}\n"
        f"• 防火墙状态: {_ufw_status}\n\n"
        f"🔐 *SSH安全配置:*\n"
        f"• PermitRootLogin: {_permit_root}\n"
        f"• PasswordAuthentication: {_pwd_auth}\n"
        f"• MaxAuthTries: {_max_auth}\n\n"
        f"📊 *安全监控:*\n"
        f"• 最近SSH失败尝试: {_ssh_fails} 次/小时\n"
        f"• Fail2ban封禁IP: {_f2b_banned} 个\n\n"
        f"🚨 *建议改进:*\n"
        f"1. 定期更新系统\n"
        f"2. 监控异常登录\n"
        f"3. 强化SSH配置\n"
        f"4. 启用审计日志"
    )

    await reply_or_edit(update, security_info, parse_mode='Markdown')
    logger.info("Security scan command executed")

async def system_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """系统监控"""
    if not authorized(update):
        return

    thinking_msg = await send_thinking(update, "📈 正在收集系统监控数据...")

    _now = run_command("date")
    _load = run_command("cat /proc/loadavg | awk '{print $1}'")
    _mem = run_command("free -m | awk '/^Mem:/{printf \"%s/%sMB (%d%)\", $3, $2, $3*100/$2}'")
    _disk = run_command("df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'")
    _conns = run_command("ss -tan | grep ESTAB | wc -l")
    _ssh_conns = run_command("ss -tan | grep ':22' | grep ESTAB | wc -l")
    _dockers = run_command("docker ps -q 2>/dev/null | wc -l")
    _all_dockers = run_command("docker ps -aq 2>/dev/null | wc -l")
    _ssh_svc = run_command("systemctl is-active ssh 2>/dev/null || echo '未知'")
    _docker_svc = run_command("systemctl is-active docker 2>/dev/null || echo '未知'")
    _f2b_svc = run_command("systemctl is-active fail2ban 2>/dev/null || echo '未知'")
    
    monitor_info = (
        f"📈 *系统监控面板*\n\n"
        f"🕐 *实时状态 (更新于: {_now})*\n\n"
        f"⚡ *资源使用:*\n"
        f"• 系统负载: {_load}\n"
        f"• 内存使用: {_mem}\n"
        f"• 磁盘使用: {_disk}\n\n"
        f"🔗 *网络状态:*\n"
        f"• 活动连接: {_conns} 个\n"
        f"• SSH连接: {_ssh_conns} 个\n\n"
        f"🐳 *容器状态:*\n"
        f"• 运行中: {_dockers} 个\n"
        f"• 总容器数: {_all_dockers} 个\n\n"
        f"📊 *服务状态:*\n"
        f"• SSH: {_ssh_svc}\n"
        f"• Docker: {_docker_svc}\n"
        f"• Fail2ban: {_f2b_svc}\n\n"
        f"📋 *监控建议:*\n"
        f"1. 设置告警阈值\n"
        f"2. 定期性能基准测试\n"
        f"3. 日志审计\n"
        f"4. 容量规划"
    )

    await reply_or_edit(update, monitor_info, parse_mode='Markdown')
    logger.info("System monitor command executed")



def chunk_message(text: str, limit: int = 4000) -> list[str]:
    """将消息按 Telegram 4096 字符限制分片"""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # 在换行处切割
        cut = text.rfind('\n', 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip('\n')
    return chunks

async def safe_send(update: Update, text: str, parse_mode='Markdown', reply_markup=None):
    """安全发送消息 — 自动分片"""
    chunks = chunk_message(text)
    for i, chunk in enumerate(chunks):
        # 只有最后一块带 reply_markup
        rm = reply_markup if i == len(chunks) - 1 else None
        try:
            if update.message:
                if rm:
                    await update.message.reply_text(chunk, parse_mode=parse_mode, reply_markup=rm)
                else:
                    await update.message.reply_text(chunk, parse_mode=parse_mode)
            elif update.callback_query:
                if i == 0:
                    if rm:
                        await update.callback_query.edit_message_text(chunk, parse_mode=parse_mode, reply_markup=rm)
                    else:
                        await update.callback_query.edit_message_text(chunk, parse_mode=parse_mode)
                else:
                    await update.callback_query.message.reply_text(chunk, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"safe_send error on chunk {i}: {e}")


# ==================== 消息构建器 ====================

def build_main_keyboard() -> InlineKeyboardMarkup:
    """构建主菜单键盘"""
    keyboard = [
        [InlineKeyboardButton("🚀 快速诊断", callback_data="quick_diagnose"),
         InlineKeyboardButton("📊 系统状态", callback_data="status"),
         InlineKeyboardButton("🔧 服务管理", callback_data="services_menu")],
        [InlineKeyboardButton("📋 日志查看", callback_data="logs"),
         InlineKeyboardButton("💾 备份管理", callback_data="backup_menu"),
         InlineKeyboardButton("⚙️ 定时任务", callback_data="cron_manager")],
        [InlineKeyboardButton("🔄 容器重启", callback_data="restart_menu"),
         InlineKeyboardButton("⚡ SSH性能", callback_data="ssh_perf"),
         InlineKeyboardButton("🤖 AI助手", callback_data="ai_menu")],
        [InlineKeyboardButton("🔍 系统诊断", callback_data="diagnose_menu"),
         InlineKeyboardButton("🎉 趣味", callback_data="fun_menu"),
         InlineKeyboardButton("❓ 帮助", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_welcome_message() -> str:
    """构建欢迎消息"""
    return """🤖 <b>Server-Admin Bot v3.9</b>

欢迎使用服务器智能管理机器人！

<b>功能分类</b>:
📊 系统监控 - 状态、服务、日志
🔧 管理操作 - 备份、重启、SSH性能
🤖 智能工具 - AI助手、系统诊断
🎉 趣味功能 - 游戏、笑话、彩蛋

<b>主要命令</b>:
/status - 系统状态
/services - 服务列表
/logs - 查看日志
/backup - 手动备份
/restart - 重启容器
/ai - AI智能对话
/cron - 定时任务管理

<b>自然语言交互</b>:
• "重启 nginx" → 自动重启容器
• "查看状态" → 显示系统状态
• "磁盘空间" → 显示磁盘使用
• "帮我备份" → 执行备份
• "菜单" → 显示主菜单

<b>快捷操作</b>:
点击按钮使用交互式菜单
输入「菜单」或「主菜单」返回这里
点击 🔙 返回 按钮←上一级菜单"""

# 监控的服务列表（统一常量）
MONITORED_SERVICES = ["ssh", "docker", "fail2ban", "tailscaled"]

# ==================== 回调路由表 ====================

# 菜单渲染回调（返回子菜单键盘）
MENU_CALLBACKS = {
    "services_menu", "backup_menu", "ssh_perf", "ai_menu",
    "diagnose_menu", "fun_menu", "easter_egg",
}

# 动作回调路由表
CALLBACK_ROUTES = {
    "status": status,
    "services": services,
    "logs": logs,
    "backup": backup,
    "restart_menu": restart_menu,
    "help": help_cmd,
    "ai_analyze": ai_analyze,
    "quick_diagnose": quick_diagnose,
    "analyze_logs": analyze_logs,
    "cron_manager": cron_manager,
    "ssh_report": ssh_performance,
    "ssh_optimize": ssh_optimize,
    "ssh_diagnose": ssh_diagnose,
    "health_check": health_check,
    "network_diagnose": network_diagnose,
    "performance_diagnose": performance_diagnose,
    "security_scan": security_scan,
    "system_monitor": system_monitor,
    "ssh_history": ssh_history,
    "ssh_config": ssh_config,
}

# ==================== 按钮回调 ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # 路由表快速分发
    if data in CALLBACK_ROUTES:
        await CALLBACK_ROUTES[data](update, context)
        return

    if data == "start":
        await query.edit_message_text(
            build_welcome_message(),
            parse_mode='HTML',
            reply_markup=build_main_keyboard()
        )
    
    # 历史过滤回调
    elif data.startswith("history_"):
        filter_type = data.replace("history_", "")
        
        # 处理分页
        if filter_type.startswith("page_"):
            page = int(filter_type.split("_")[1])
            operation_type = None
        else:
            page = 1
            operation_map = {
                "restart": "restart",
                "backup": "backup",
                "service": "service",
                "all": None
            }
            operation_type = operation_map.get(filter_type)
        
        per_page = 10
        total = get_operation_count(operation_type)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        operations = get_recent_operations(limit=per_page, operation_type=operation_type, offset=(page-1)*per_page)
        
        if not operations:
            await query.edit_message_text("📝 <b>操作历史</b>\n\n暂无记录", parse_mode='HTML')
            return
        
        lines = [f"📝 <b>操作历史</b> (第 {page}/{total_pages} 页)\n"]
        for ts, op, target, result, details in operations:
            time_str = ts.split('.')[0] if '.' in ts else ts
            icon = "✅" if result == "success" else "❌"
            line = f"{icon} <i>{time_str}</i> {op}"
            if target:
                line += f" → <b>{target}</b>"
            lines.append(line)
        
        # 构建分页按钮
        keyboard = []
        if page > 1:
            keyboard.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"history_page_{page-1}"))
        if page < total_pages:
            keyboard.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"history_page_{page+1}"))
        
        nav_row = keyboard if keyboard else []
        
        keyboard = [
            [InlineKeyboardButton("🔄 重启", callback_data="history_restart"),
             InlineKeyboardButton("💾 备份", callback_data="history_backup")],
            [InlineKeyboardButton("🔧 服务", callback_data="history_service"),
             InlineKeyboardButton("📊 全部", callback_data="history_all")],
            nav_row,
            [InlineKeyboardButton("🔙 主菜单", callback_data="start")]
        ]
        
        keyboard = [row for row in keyboard if row]
        
        await query.edit_message_text('\n'.join(lines), parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))


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


    elif data == "restart_service_menu":
        services_for_restart = MONITORED_SERVICES
        keyboard = []
        for svc in services_for_restart:
            status = run_command(f"systemctl is-active {svc} 2>/dev/null || echo '未知'")
            emoji = "🟢" if status.strip() == "active" else "🔴"
            keyboard.append([InlineKeyboardButton(f"{emoji} 重启 {svc}", callback_data=f"svc_restart_{svc}")])
        keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="services_menu")])
        await query.edit_message_text(
            "🔄 *服务重启管理*\n\n选择要重启的系统服务:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "start_service_menu":
        services_for_start = MONITORED_SERVICES
        keyboard = []
        for svc in services_for_start:
            status = run_command(f"systemctl is-active {svc} 2>/dev/null || echo '未知'")
            if status.strip() != "active":
                keyboard.append([InlineKeyboardButton(f"▶️ 启动 {svc}", callback_data=f"svc_start_{svc}")])
        if not keyboard:
            keyboard.append([InlineKeyboardButton("✅ 所有服务已运行", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="services_menu")])
        await query.edit_message_text(
            "▶️ *服务启动管理*\n\n选择要启动的系统服务:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "stop_service_menu":
        services_for_stop = ["docker", "fail2ban"]
        keyboard = []
        for svc in services_for_stop:
            status = run_command(f"systemctl is-active {svc} 2>/dev/null || echo '未知'")
            if status.strip() == "active":
                keyboard.append([InlineKeyboardButton(f"⏹️ 停止 {svc}", callback_data=f"svc_stop_{svc}")])
        if not keyboard:
            keyboard.append([InlineKeyboardButton("✅ 无可停止服务", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="services_menu")])
        await query.edit_message_text(
            "⏹️ *服务停止管理*\n\n⚠️ 谨慎操作！选择要停止的系统服务:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "service_status_menu":
        status_detail = run_command("""
            echo "=== 系统服务详情 ==="
            for svc in ssh docker fail2ban tailscaled cron rsyslog; do
                active=$(systemctl is-active $svc 2>/dev/null || echo '未知')
                enabled=$(systemctl is-enabled $svc 2>/dev/null || echo '未知')
                uptime=$(systemctl show -p ActiveEnterTimestamp --value $svc 2>/dev/null || echo 'N/A')
                echo "$svc: $active (开机自启: $enabled, 启动时间: $uptime)"
            done
        """)
        await query.edit_message_text(
            f"📊 *服务状态详情*\n\n```\n{status_detail}\n```\n\n使用 /services 查看快速概览",
            parse_mode='Markdown',
            reply_markup=make_back_button("services_menu")
        )

    elif data == "service_config":
        config_info = run_command("""
            echo "=== SSH 配置 ==="
            echo "主配置: /etc/ssh/sshd_config"
            ls -la /etc/ssh/sshd_config.d/ 2>/dev/null | head -5 || echo "无配置片段"
            echo ""
            echo "=== Docker 配置 ==="
            echo "daemon.json: $(cat /etc/docker/daemon.json 2>/dev/null || echo '不存在')"
            echo ""
            echo "=== Fail2ban 配置 ==="
            ls /etc/fail2ban/jail.d/ 2>/dev/null || echo "无自定义配置"
        """)
        await query.edit_message_text(
            f"🔧 *服务配置概览*\n\n```\n{config_info}\n```",
            parse_mode='Markdown',
            reply_markup=make_back_button("services_menu")
        )


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


    elif data == "backup_list":
        # 显示备份列表
        backup_list = run_command("ls -la /var/backups/ 2>/dev/null | head -20 || echo '备份目录不存在'")
        await query.edit_message_text(
            f"📋 *备份文件列表*\n\n```\n{backup_list}\n```",
            parse_mode='Markdown',
            reply_markup=make_back_button("backup_menu")
        )

    elif data == "restore_backup_menu":
        backups = run_command("ls -lt /var/backups/daily/*.gpg 2>/dev/null | head -5 || echo '无加密备份'\nls -lt /var/backups/daily/*.tar.gz 2>/dev/null | head -5 || echo '无普通备份'")
        keyboard = []
        for line in backups.strip().split('\n'):
            if '.gpg' in line or '.tar.gz' in line:
                fname = line.split()[-1] if line.split() else ''
                bname = fname.split('/')[-1] if fname else ''
                if bname:
                    keyboard.append([InlineKeyboardButton(f"📦 {bname[:30]}", callback_data=f"noop")])
        if not keyboard:
            keyboard.append([InlineKeyboardButton("📦 无可用备份", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="backup_menu")])
        await query.edit_message_text(
            f"↩️ *备份恢复*\n\n⚠️ 恢复操作需通过 SSH 手动执行\n\n可用备份:\n```\n{backups}\n```\n\n💡 解密命令:\n`openssl enc -d -aes-256-cbc -pbkdf2 -pass file:/etc/monitoring/backup.key -in 备份文件 -out - | tar -xzf -`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "clean_backup":
        backup_info = run_command("""
            echo "=== 每日备份 ==="
            ls -lh /var/backups/daily/ 2>/dev/null | tail -n +2 || echo "目录为空"
            echo ""
            echo "=== 磁盘使用 ==="
            du -sh /var/backups/ 2>/dev/null || echo "无法计算"
        """)
        keyboard = [
            [InlineKeyboardButton("🗑️ 清理7天前备份", callback_data="clean_backup_7"),
             InlineKeyboardButton("🗑️ 清理30天前备份", callback_data="clean_backup_30")],
            [InlineKeyboardButton("🔙 返回", callback_data="backup_menu")]
        ]
        await query.edit_message_text(
            f"🗑️ *备份清理*\n\n当前备份状况:\n```\n{backup_info}\n```\n\n⚠️ 清理操作不可恢复！",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "backup_status":
        # 显示备份状态
        backup_status = run_command(find_script("backup.sh") + " -s 2>&1 || echo '无法获取备份状态'")
        await query.edit_message_text(
            f"📊 *备份状态*\n\n```\n{backup_status}\n```",
            parse_mode='Markdown',
            reply_markup=make_back_button("backup_menu")
        )

    elif data == "backup_config":
        backup_config = run_command("cat /etc/monitoring/backup.conf 2>/dev/null || echo '备份配置文件不存在'")
        await query.edit_message_text(
            f"🔧 *备份配置*\n\n```\n{backup_config}\n```",
            parse_mode='Markdown',
            reply_markup=make_back_button("backup_menu")
        )


    elif data == "fun_menu":
        # 显示趣味功能子菜单
        fun_keyboard = [
            [InlineKeyboardButton("🎲 随机惊喜", callback_data="egg_random"),
             InlineKeyboardButton("🎮 趣味游戏", callback_data="egg_game")],
            [InlineKeyboardButton("😄 程序笑话", callback_data="egg_joke"),
             InlineKeyboardButton("🎭 技术诗歌", callback_data="egg_poetry")],
            [InlineKeyboardButton("🥠 幸运饼干", callback_data="egg_fortune"),
             InlineKeyboardButton("😎 表情包", callback_data="egg_meme")],
            [InlineKeyboardButton("🤖 AI彩蛋", callback_data="egg_ai"),
             InlineKeyboardButton("🔙 返回", callback_data="start")]
        ]
        await query.edit_message_text(
            "🎉 *趣味功能*\n\n选择趣味功能:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(fun_keyboard)
        )


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
        await ai_analyze(update, context)

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
        await query.edit_message_text(ai_config_info, parse_mode='Markdown', reply_markup=make_back_button("ai_menu"))

    elif data == "ai_performance":
        import time
        start = time.time()
        test_result = call_ai("回复OK", "回复一个字") if AI_API_KEY else "AI未配置"
        latency = round(time.time() - start, 2)
        perf_msg = f"""⚡ *AI性能监控*

🧠 *模型*: {AI_MODEL}
🌐 *端点*: {AI_BASE_URL}

📊 *性能测试*:
• 响应时间: {latency}s
• API状态: {'✅ 可用' if test_result and '错误' not in str(test_result) else '❌ 不可用'}
• API Key: {'✅ 已配置' if AI_API_KEY else '❌ 未配置'}

💡 *优化建议*:
• 响应 >5s: 检查网络连接
• API错误: 验证API Key有效性
• 超时: 尝试切换模型"""
        await query.edit_message_text(perf_msg, parse_mode='Markdown', reply_markup=make_back_button("ai_menu"))

    elif data == "ai_chat":
        await query.edit_message_text(
            "🤖 *AI 对话模式*\n\n直接发送消息即可与 AI 对话。\n\n例如：\n• 如何优化服务器内存？\n• Nginx 配置怎么写？\n• 帮我分析最近的错误日志",
            parse_mode='Markdown',
            reply_markup=make_back_button("ai_menu")
        )


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
        thinking_msg = await send_thinking(update, "⏱ 正在测试SSH响应时间...")
        result = run_command(find_script("ssh-benchmark.sh") + " --test=response --iterations=10")
        await reply_or_edit(update, f"⏱ SSH响应时间测试:\n\n{format_ai_response(str(result))}", reply_markup=make_back_button("ssh_perf"), parse_mode='HTML')

    elif data == "ssh_transfer":
        # 运行SSH传输速度测试
        thinking_msg = await send_thinking(update, "📁 正在测试SSH传输速度...")
        result = run_command(find_script("ssh-benchmark.sh") + " --test=transfer --size=5MB")
        await reply_or_edit(update, f"📁 SSH传输速度测试:\n\n{format_ai_response(str(result))}", reply_markup=make_back_button("ssh_perf"), parse_mode='HTML')

    elif data == "ssh_concurrent":
        # 运行SSH并发连接测试
        thinking_msg = await send_thinking(update, "👥 正在测试SSH并发连接...")
        result = run_command(find_script("ssh-benchmark.sh") + " --test=concurrent --sessions=5")
        await reply_or_edit(update, f"👥 SSH并发连接测试:\n\n{format_ai_response(str(result))}", reply_markup=make_back_button("ssh_perf"), parse_mode='HTML')









        # Note: ssh_history already uses reply_or_edit with make_back_button


    elif data.startswith("restart_"):
        container = data.replace("restart_", "")
        if not validate_container_name(container):
            await query.edit_message_text("⛔ 无效的容器名", parse_mode='Markdown')
            return
        await restart_container(update, context, container)

    elif data == "logs_health":
        logs_content = run_command("tail -50 /var/log/monitoring/health-check.log 2>/dev/null")
        await query.edit_message_text(f"📋 *健康检查日志*\n\n```\n{logs_content}\n```", parse_mode='Markdown', reply_markup=make_back_button("logs"))

    elif data == "logs_ssh":
        logs_content = run_command("journalctl -u ssh -n 20 --no-pager 2>/dev/null")
        await query.edit_message_text(f"📋 *SSH日志*\n\n```\n{logs_content}\n```", parse_mode='Markdown', reply_markup=make_back_button("logs"))

    elif data == "logs_fail2ban":
        logs_content = run_command("tail -30 /var/log/fail2ban.log 2>/dev/null")
        await query.edit_message_text(f"📋 *Fail2ban日志*\n\n```\n{logs_content}\n```", parse_mode='Markdown', reply_markup=make_back_button("logs"))

    elif data == "logs_docker":
        logs_content = run_command("docker ps -a --format 'table {{.Names}}\\t{{.Status}}' 2>/dev/null")
        await query.edit_message_text(f"📋 *Docker状态*\n\n```\n{logs_content}\n```", parse_mode='Markdown', reply_markup=make_back_button("logs"))


    # ==================== 服务控制回调 ====================
    elif data.startswith("svc_restart_"):
        svc = data.replace("svc_restart_", "")
        if not validate_service_name(svc):
            await query.edit_message_text("⛔ 无效的服务名", parse_mode='Markdown')
            return
        # Show confirmation dialog
        keyboard = [
            [InlineKeyboardButton("✅ 确认重启", callback_data=f"confirm_svc_restart_{svc}"),
             InlineKeyboardButton("❌ 取消", callback_data="services_menu")]
        ]
        current_status = run_command(f"systemctl is-active {svc} 2>/dev/null")
        await query.edit_message_text(
            f"⚠️ *确认重启服务*\n\n服务: {svc}\n当前状态: {current_status}\n\n确定要重启吗？",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("confirm_svc_restart_"):
        svc = data.replace("confirm_svc_restart_", "")
        if not validate_service_name(svc):
            await query.edit_message_text("⛔ 无效的服务名", parse_mode='Markdown')
            return
        result = run_command(f"systemctl restart {svc} 2>&1")
        new_status = run_command(f"systemctl is-active {svc} 2>/dev/null")
        emoji = "✅" if new_status.strip() == "active" else "❌"
        
        # 记录操作历史
        log_operation("restart_service", svc, result=new_status.strip(), details=result[:100])
        
        await query.edit_message_text(
            f"🔄 *服务重启结果*\n\n{svc}: {emoji} {new_status}\n\n```\n{result}\n```",
            parse_mode='Markdown',
            reply_markup=make_back_button("services_menu")
        )

    elif data.startswith("svc_start_"):
        svc = data.replace("svc_start_", "")
        if not validate_service_name(svc):
            await query.edit_message_text("⛔ 无效的服务名", parse_mode='Markdown')
            return
        result = run_command(f"systemctl start {svc} 2>&1")
        new_status = run_command(f"systemctl is-active {svc} 2>/dev/null")
        emoji = "✅" if new_status.strip() == "active" else "❌"
        await query.edit_message_text(
            f"▶️ *服务启动结果*\n\n{svc}: {emoji} {new_status}\n\n```\n{result}\n```",
            parse_mode='Markdown',
            reply_markup=make_back_button("services_menu")
        )

    elif data.startswith("svc_stop_"):
        svc = data.replace("svc_stop_", "")
        if not validate_service_name(svc):
            await query.edit_message_text("⛔ 无效的服务名", parse_mode='Markdown')
            return
        keyboard = [
            [InlineKeyboardButton("✅ 确认停止", callback_data=f"confirm_svc_stop_{svc}"),
             InlineKeyboardButton("❌ 取消", callback_data="services_menu")]
        ]
        await query.edit_message_text(
            f"⚠️ *确认停止服务*\n\n服务: {svc}\n\n⚠️ 停止服务可能影响系统运行！确定要停止吗？",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("confirm_svc_stop_"):
        svc = data.replace("confirm_svc_stop_", "")
        if not validate_service_name(svc):
            await query.edit_message_text("⛔ 无效的服务名", parse_mode='Markdown')
            return
        result = run_command(f"systemctl stop {svc} 2>&1")
        new_status = run_command(f"systemctl is-active {svc} 2>/dev/null")
        emoji = "🛑" if new_status.strip() != "active" else "❌"
        await query.edit_message_text(
            f"⏹️ *服务停止结果*\n\n{svc}: {emoji} {new_status}\n\n```\n{result}\n```",
            parse_mode='Markdown',
            reply_markup=make_back_button("services_menu")
        )

    elif data.startswith("clean_backup_"):
        days = data.replace("clean_backup_", "")
        if not days.isdigit() or int(days) < 1:
            await query.edit_message_text("⛔ 无效的天数", parse_mode='Markdown')
            return
        keyboard = [
            [InlineKeyboardButton("✅ 确认清理", callback_data=f"confirm_clean_{days}"),
             InlineKeyboardButton("❌ 取消", callback_data="backup_menu")]
        ]
        await query.edit_message_text(
            f"⚠️ *确认清理备份*\n\n将删除 {days} 天前的所有备份\n\n⚠️ 此操作不可恢复！确定要继续吗？",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("confirm_clean_"):
        days = data.replace("confirm_clean_", "")
        if not days.isdigit() or int(days) < 1:
            await query.edit_message_text("⛔ 无效的天数", parse_mode='Markdown')
            return
        result = run_command(f"find /var/backups/daily/ -name '*.gpg' -mtime +{days} -delete 2>&1\nfind /var/backups/daily/ -name '*.tar.gz' -mtime +{days} -delete 2>&1")
        remaining = run_command("ls /var/backups/daily/ 2>/dev/null | wc -l")
        await query.edit_message_text(
            f"🗑️ *备份清理完成*\n\n清理了 {days} 天前的备份\n剩余备份数: {remaining}\n\n```\n{result}\n```",
            parse_mode='Markdown',
            reply_markup=make_back_button("backup_menu")
        )

    elif data == "noop":
        await query.answer("此操作暂不可用")

    # ==================== 彩蛋功能 ====================
    elif data == "easter_egg":
        # 隐藏的彩蛋功能
        easter_egg_keyboard = [
            [InlineKeyboardButton("🎮 游戏时间", callback_data="egg_game"),
             InlineKeyboardButton("😄 笑话时间", callback_data="egg_joke")],
            [InlineKeyboardButton("🎭 诗歌模式", callback_data="egg_poetry"),
             InlineKeyboardButton("🥠 幸运饼干", callback_data="egg_fortune")],
            [InlineKeyboardButton("😎 表情包模式", callback_data="egg_meme"),
             InlineKeyboardButton("🤖 AI彩蛋", callback_data="egg_ai")],
            [InlineKeyboardButton("🔙 返回", callback_data="start")]
        ]
        await query.edit_message_text(
            "🥚 *发现隐藏彩蛋！*\n\n选择趣味功能:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(easter_egg_keyboard)
        )

    elif data == "egg_random":
        all_eggs = [
            "🎮 猜数字游戏：我正在想一个1-100之间的数字，猜猜看是多少？",
            "😄 程序员总是把万圣节和圣诞节搞混，因为 Oct 31 == Dec 25！",
            "🎭 代码的诗篇：每一行代码，都是一句诗句，在服务器的心跳中，找到技术的韵律。",
            "🔮 今天你会发现一个隐藏的Bug，但也会找到优雅的解决方案。",
            "🚀 [负载: 0.5] 我还能行！ [负载: 3.0] 我要重启了！",
            "🤖 AI秘密：我其实每天都在学习如何更好地为你服务！",
        ]
        await query.edit_message_text(random.choice(all_eggs), parse_mode='HTML', reply_markup=make_back_button("fun_menu"))

    elif data == "egg_game":
        games = [
            "🎮 猜数字游戏：我正在想一个1-100之间的数字，猜猜看是多少？",
            "🎯 服务器挑战：你能让服务器负载保持在1.0以下吗？使用 /status 查看！",
            "🏆 运维大师：连续7天每天运行健康检查，获得'运维大师'称号！"
        ]
        await query.edit_message_text(random.choice(games), parse_mode='HTML', reply_markup=make_back_button("fun_menu"))

    elif data == "egg_joke":
        jokes = [
            "🤣 为什么程序员总是把万圣节和圣诞节搞混？因为 Oct 31 == Dec 25！",
            "😄 服务器最害怕什么？404错误！",
            "🎯 SSH连接对女朋友说：'我需要你的公钥才能进入你的心里！'",
            "🐛 为什么程序员不喜欢大自然？因为那里有太多的Bug！"
        ]
        await query.edit_message_text(random.choice(jokes), parse_mode='HTML', reply_markup=make_back_button("fun_menu"))

    elif data == "egg_poetry":
        poems = [
            "🎭 代码的诗篇：在数字的海洋里，每一行代码都是一句诗句，在服务器的心跳中找到技术的韵律。",
            "🌌 服务器的夜曲：CPU在思考，内存在回忆，硬盘在诉说，网络的秘密。",
            "⚡ SSH的连接：加密的握手，安全的通道，每一次连接，都是信任的拥抱。"
        ]
        await query.edit_message_text(random.choice(poems), parse_mode='HTML', reply_markup=make_back_button("fun_menu"))

    elif data == "egg_fortune":
        fortunes = [
            "🥠 幸运代码饼干：你的代码今天会运行得特别流畅！",
            "🔮 技术预言：今天你会发现一个隐藏的Bug，但也会找到优雅的解决方案。",
            "🌟 运维座今日运势：工作适合优化配置 💰 财运备份一切顺利",
            "🎯 今日任务：对代码微笑一次、感谢服务器、备份重要数据、学习新技术"
        ]
        await query.edit_message_text(random.choice(fortunes), parse_mode='HTML', reply_markup=make_back_button("fun_menu"))

    elif data == "egg_meme":
        memes = [
            "😎 听说你在找Bug? 👉👈 我在这呢！",
            "🚀 [负载: 0.5] 我还能行！ [负载: 3.0] 我要重启了！",
            "🤖 人类：帮我优化服务器 → AI：建议重启 → 人类：就这？→ AI：💔"
        ]
        await query.edit_message_text(random.choice(memes), parse_mode='HTML', reply_markup=make_back_button("fun_menu"))

    elif data == "egg_ai":
        ai_eggs = [
            "🤖 AI秘密：我其实每天都在学习如何更好地为你服务！💭 希望人类多夸夸我~",
            "🧠 神经网络低语：我看到了...服务器的未来是光明的！（其实我只是个脚本）",
            "🎭 AI的戏剧：第一幕接收命令 → 第二幕处理请求 → 第三幕返回结果 👏👏👏"
        ]
        await query.edit_message_text(random.choice(ai_eggs), parse_mode='HTML', reply_markup=make_back_button("fun_menu"))

# ==================== 主函数 ====================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """全局错误处理器"""
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)
    try:
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ 内部错误，请稍后重试。"
            )
        elif update and hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text("⚠️ 内部错误，请稍后重试。")
    except Exception as e:
        logger.error(f"Error handler failed: {e}")


def main():
    """启动机器人"""
    if not TOKEN:
        print("错误: 未找到 TELEGRAM_BOT_TOKEN")
        return

    # 创建应用（带 post_init 启动监控）
    async def post_init(app):
        """应用初始化后启动后台任务"""
        logger.info("Starting alert monitor...")
        start_alert_monitor(app)
    
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # 注册命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("services", services))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("backup", backup))
    application.add_handler(CommandHandler("restart", restart_menu))
    application.add_handler(CommandHandler("ai", ai_chat))
    application.add_handler(CommandHandler("analyze", ai_analyze))
    application.add_handler(CommandHandler("history", history_cmd))
    application.add_handler(CommandHandler("analyze_logs", analyze_logs))
    application.add_handler(CommandHandler("cron", cron_manager))
    application.add_handler(CommandHandler("help", help_cmd))
    # SSH性能命令
    application.add_handler(CommandHandler("sshstatus", ssh_status))
    application.add_handler(CommandHandler("sshperformance", ssh_performance))
    application.add_handler(CommandHandler("sshoptimize", ssh_optimize))
    application.add_handler(CommandHandler("sshdiagnose", ssh_diagnose))
    application.add_handler(CommandHandler("sshhistory", ssh_history))
    application.add_handler(CommandHandler("sshconfig", ssh_config))

    # 注册全局错误处理器
    application.add_error_handler(error_handler)

    # 注册按钮回调
    application.add_handler(CallbackQueryHandler(button_callback))

    # 注册消息处理器（AI 对话）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot v3.9 starting with AI, SSH performance, and alert monitoring...")
    print("Server-Admin Bot v3.9 已启动 (AI增强 + SSH性能 + 主动告警 + 智能日志)")

    # 启动机器人 (使用 polling)，忽略挂起的更新以避免冲突
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
