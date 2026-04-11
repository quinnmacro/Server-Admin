# 监控系统文档

> 系统健康检查与告警通知

---

## 一、监控架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  health-check   │     │  log-monitor    │     │  ssh-report     │
│  (每小时)        │     │  (每5分钟)       │     │  (每日)          │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────┐
                    │  Telegram 通知      │
                    └─────────────────────┘
```

---

## 二、监控脚本

### 2.1 health-check.sh

**位置**: `/usr/local/sbin/monitoring/health-check.sh`

**运行频率**: 每小时（静默）、每天8:00（完整）

**检查项目**:

| 类别 | 检查项 | 告警阈值 |
|------|--------|----------|
| 系统 | 内存使用率 | >90% 告警，>80% 警告 |
| 系统 | 磁盘使用率 | >80% 告警 |
| 系统 | Swap使用率 | >80% 告警 |
| 系统 | 系统负载 | >150% 告警 |
| 系统 | 磁盘IO等待 | >30% 告警 |
| 网络 | 连接数 | >500 告警 |
| 网络 | DNS解析 | 失败告警 |
| 安全 | 安全更新 | 有更新告警 |
| 安全 | SSH攻击 | 1小时>20次告警 |
| 安全 | 可疑端口 | 发现告警 |
| 内存 | OOM事件 | 有事件告警 |
| 服务 | Docker容器 | 停止告警 |
| 服务 | 系统服务 | 停止告警 |

**用法**:
```bash
# 完整输出
/usr/local/sbin/monitoring/health-check.sh

# 静默模式（仅写日志）
/usr/local/sbin/monitoring/health-check.sh -q
```

---

### 2.2 log-monitor.sh

**位置**: `/usr/local/sbin/monitoring/log-monitor.sh`

**运行频率**: 每5分钟

**检查项目**:
- Fail2ban 封禁事件
- 系统错误日志（>20条）
- Docker 容器异常退出
- Docker 容器健康状态

**用法**:
```bash
/usr/local/sbin/monitoring/log-monitor.sh -q
```

---

### 2.3 ssh-daily-report.sh

**位置**: `/usr/local/sbin/monitoring/ssh-daily-report.sh`

**运行频率**: 每天 8:30

**报告内容**:
- 成功登录次数
- 失败尝试次数
- 当前封禁IP数
- 登录来源IP Top 5

---

## 三、Telegram 机器人

### 3.1 功能概述

Server-Admin 提供交互式 Telegram 机器人，支持：

- 命令菜单查询服务器状态
- 交互按钮快捷操作
- 远程重启容器
- 手动触发备份

### 3.2 可用命令

| 命令 | 功能 | 说明 |
|------|------|------|
| `/start` | 主菜单 | 显示交互按钮 |
| `/status` | 服务器状态 | 内存、磁盘、负载、容器 |
| `/services` | 服务列表 | 系统服务和容器状态 |
| `/logs` | 查看日志 | 多种日志选择 |
| `/backup` | 手动备份 | 触发备份任务 |
| `/restart` | 重启容器 | 选择容器重启 |
| `/help` | 帮助信息 | 命令说明 |

### 3.3 配置

**位置**: `/etc/monitoring/config.conf`

```bash
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"
TELEGRAM_ENABLED=true
```

### 3.4 服务管理

```bash
# 启动机器人
systemctl start telegram-bot

# 停止机器人
systemctl stop telegram-bot

# 查看状态
systemctl status telegram-bot

# 查看日志
tail -f /var/log/monitoring/telegram-bot.log
```

### 3.5 设置命令菜单

在 Telegram 中向 @BotFather 发送：

```
/setcommands
```

然后选择你的机器人，发送：

```
start - 显示主菜单
status - 服务器状态
services - 服务列表
logs - 查看日志
backup - 手动备份
restart - 重启容器
help - 帮助信息
```

---

## 四、日志位置

| 日志 | 路径 |
|------|------|
| 健康检查 | `/var/log/monitoring/health-check.log` |
| 告警记录 | `/var/log/monitoring/health-alerts.log` |
| 状态文件 | `/var/lib/monitoring/log-monitor.state` |

---

## 五、定时任务

**位置**: `/etc/cron.d/monitoring`

```
# 每小时检查
0 * * * * root /usr/local/sbin/monitoring/health-check.sh -q

# 每天8:00完整检查
0 8 * * * root /usr/local/sbin/monitoring/health-check.sh

# 每天8:30 SSH日报
30 8 * * * root /usr/local/sbin/monitoring/ssh-daily-report.sh

# 每5分钟日志监控
*/5 * * * * root /usr/local/sbin/monitoring/log-monitor.sh -q
```

---

*更新于 2026-04-11*
