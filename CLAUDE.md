# CLAUDE.md - Claude 协作指南

> Server-Admin 项目的 Claude 协作指南
> 最后更新：2026-04-12

---

## 📋 项目概述

**Server-Admin** 是一个完整的服务器运维管理系统，运行在 Vultr 东京服务器上。系统包含健康检查、备份恢复、日志监控、自动化部署、安全加固和 Telegram 集成等功能。

### 核心目标
1. **自动化运维**：减少手动操作，提高运维效率
2. **实时监控**：及时发现和解决问题
3. **安全加固**：保护服务器免受攻击
4. **性能优化**：确保服务稳定高效运行
5. **智能集成**：通过 Telegram 提供便捷的管理界面

### 服务器信息
- **主机名**: vultr-tokyo-test
- **提供商**: Vultr
- **位置**: 东京
- **IP**: 149.28.25.78
- **配置**: 1 vCPU / 2GB RAM / 52GB SSD
- **系统**: Ubuntu 24.04 LTS

---

## 🗂️ 项目结构

```
Server-Admin/
├── README.md                    # 项目总览
├── CLAUDE.md                    # 本文件 - Claude 协作指南
├── CHANGELOG.md                 # 总变更日志
├── docs/                        # 详细文档
│   ├── SETUP.md                # 初始化配置
│   ├── MONITORING.md           # 监控系统
│   ├── BACKUP.md               # 备份恢复
│   ├── DEPLOY.md               # 部署流程
│   ├── SECURITY.md             # 安全配置
│   ├── SERVICES.md             # 服务列表
│   └── OPTIMIZATION.md         # 性能优化
├── scripts/                     # 运维脚本
│   ├── health-check.sh         # 健康检查 v2.1
│   ├── backup.sh               # 加密备份
│   ├── log-monitor.sh          # 日志监控 v1.2
│   ├── ssh-daily-report.sh     # SSH 日报
│   ├── telegram-notify.sh      # Telegram 通知
│   ├── telegram-bot.py         # 交互式机器人 v3.0
│   ├── deploy.sh               # 部署脚本
│   ├── docker-manage.sh        # Docker 管理
│   ├── ssh-benchmark.sh        # SSH 性能基准测试
│   ├── ssh-optimize.sh         # SSH 配置管理
│   ├── deploy-ssh-config-test.sh # SSH 配置部署测试
│   └── sync-docs.sh            # 文档同步
├── changelogs/                  # 变更日志（按月归档）
│   └── 2026-04.md              # 2026年4月变更
├── incidents/                   # 故障记录
│   └── TEMPLATE.md             # 故障记录模板
├── adr/                         # 架构决策记录
│   ├── 001-monitoring-stack.md    # 监控方案选择
│   └── 002-performance-optimization.md # 性能优化方案
├── backups/                     # 本地备份文件
├── configs/                     # 配置文件备份
└── logs/                        # 日志文件
```

---

## 🚀 快速开始

### SSH 连接
```bash
ssh tokyo  # 使用 ~/.ssh/config 中的配置
```

### 常用命令
```bash
# 健康检查
health-check                    # 完整输出
health-check -q                 # 静默模式

# Docker 管理
docker-manage status            # 查看状态
docker-manage logs sanctionlist # 查看日志
docker-manage restart homepage  # 重启服务

# 部署
deploy SanctionList             # 部署项目
deploy --all                    # 部署全部

# 备份
backup                          # 执行备份
backup -q                       # 静默模式

# SSH 性能测试
ssh-benchmark.sh --baseline     # 建立性能基准
ssh-optimize.sh deploy          # 部署 SSH 优化配置

# Telegram 测试
telegram-notify --test "测试消息"
```

---

## 🛠️ 开发约定

### 脚本开发规范
1. **文件头注释**：每个脚本必须包含文件头注释，说明用途、版本、用法
2. **错误处理**：使用 `set -euo pipefail` 和适当的错误检查
3. **日志记录**：使用统一的日志函数，格式：`[YYYY-MM-DD HH:MM:SS] 消息`
4. **Telegram 集成**：使用统一的 `notify_telegram` 函数
5. **配置管理**：配置文件统一放在 `/etc/monitoring/` 或用户级目录

### 脚本模板
```bash
#!/bin/bash
# 脚本名称 vX.Y
# 功能描述
# 用法: script.sh [选项]

set -euo pipefail

# 加载配置
source /etc/monitoring/config.conf 2>/dev/null || true

# 日志函数
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
}

# Telegram 通知函数
notify_telegram() {
    local level="$1"
    local message="$2"
    
    if [ "$TELEGRAM_ENABLED" = "true" ] && [ -x /usr/local/sbin/monitoring/telegram-notify.sh ]; then
        case $level in
            alert)
                /usr/local/sbin/monitoring/telegram-notify.sh --alert "$message" &
                ;;
            critical)
                /usr/local/sbin/monitoring/telegram-notify.sh --critical "$message" &
                ;;
            info|*)
                /usr/local/sbin/monitoring/telegram-notify.sh --info "$message" &
                ;;
        esac
    fi
}

# 主函数
main() {
    log "脚本开始执行"
    
    # 主要逻辑
    
    log "脚本执行完成"
}

# 执行主函数
main "$@"
```

### Python 脚本规范
1. **类型提示**：使用 Python 3.10+ 类型提示
2. **错误处理**：适当的异常处理，避免程序崩溃
3. **日志记录**：使用 logging 模块，配置适当的日志级别
4. **异步处理**：Telegram bot 使用异步处理
5. **配置管理**：从配置文件或环境变量读取配置

---

## 🤖 Telegram 机器人集成

### 机器人版本
- **当前版本**: v3.0 (AI 增强版 + SSH 性能监控)
- **Token**: 8756987669:AAHHHTDwH7L5XeM2yvg1TpmKv_1xPt7PRrw
- **Chat ID**: 7909421858

### 核心功能
1. **服务器管理命令**：
   - `/start` - 显示欢迎消息和主菜单
   - `/status` - 服务器状态（内存、磁盘、负载、容器）
   - `/services` - 服务列表（系统服务和 Docker 容器）
   - `/logs` - 查看日志（健康检查、SSH、Fail2ban、Docker）
   - `/backup` - 手动触发备份
   - `/restart` - 重启 Docker 容器

2. **SSH 性能监控命令**：
   - `/sshstatus` - SSH 服务状态和性能指标
   - `/sshperformance` - SSH 性能测试报告
   - `/sshoptimize` - SSH 优化建议和配置
   - `/sshdiagnose` - SSH 连接问题诊断
   - `/sshhistory` - SSH 性能历史趋势
   - `/sshconfig` - SSH 配置管理

3. **AI 智能助手功能**：
   - `/ai [问题]` - AI 智能对话（Infini AI API 集成）
   - `/analyze` - AI 分析服务器状态
   - 普通消息自动当作 AI 对话处理

4. **趣味功能**（"🎉 趣味" 菜单）：
   - 笑话、彩蛋、游戏、幸运饼干、诗歌、梗图、表情包、随机建议

### 开发注意事项
1. **菜单更新**：修改菜单后需要重启 bot 服务
2. **权限控制**：只允许配置的 Chat ID 访问
3. **错误处理**：避免 bot 崩溃，记录所有错误
4. **异步处理**：耗时操作使用异步处理，避免阻塞

---

## 🔧 SSH 性能优化系统

### 系统架构
```
SSH 性能优化系统
├── 客户端优化 (~/.ssh/config)
├── 服务器优化 (/etc/ssh/sshd_config.d/performance.conf)
├── TCP 内核优化 (/etc/sysctl.d/99-ssh-optimize.conf)
├── 性能监控 (ssh-benchmark.sh, ssh-monitor-telegram.sh)
└── 配置管理 (ssh-optimize.sh)
```

### 优化目标
1. **连接速度**：减少 SSH 连接建立时间 50%（600ms → 300ms）
2. **并发能力**：提升服务器并发处理能力 50%
3. **传输性能**：提升文件传输速度 20%
4. **监控覆盖**：100% 关键性能指标监控
5. **安全保持**：不降低现有安全级别

### 关键文件
1. **客户端配置**：`/Users/liulu/.ssh/config` - 已优化，包含连接复用和现代加密算法
2. **服务器配置**：`/etc/ssh/sshd_config.d/performance.conf` - SSH 服务器性能配置
3. **基准测试**：`ssh-benchmark.sh` - SSH 性能基准测试脚本
4. **配置管理**：`ssh-optimize.sh` - SSH 配置管理脚本（部署、验证、回滚）

### 部署流程
```bash
# 1. 建立性能基准
./ssh-benchmark.sh --baseline --save

# 2. 运行部署前测试
./deploy-ssh-config-test.sh

# 3. 部署性能配置
./ssh-optimize.sh deploy --host=tokyo

# 4. 验证部署效果
./ssh-optimize.sh verify --host=tokyo
./ssh-benchmark.sh --compare --report
```

---

## 📊 监控与告警

### 监控指标
1. **系统资源**：CPU、内存、磁盘、负载
2. **服务状态**：Docker 容器、系统服务
3. **网络状态**：SSH 连接、端口监听
4. **安全事件**：Fail2ban 封禁、异常登录
5. **SSH 性能**：响应时间、并发连接、传输速度

### 告警阈值
```bash
# 配置文件: /etc/monitoring/config.conf
# SSH 性能告警阈值
SSH_RESPONSE_TIME_WARNING=1000      # 警告阈值 (ms)
SSH_RESPONSE_TIME_CRITICAL=1500     # 严重阈值 (ms)
SSH_ACTIVE_CONNECTIONS_WARNING=20   # 活跃连接警告
SSH_ACTIVE_CONNECTIONS_CRITICAL=25  # 活跃连接严重
SSH_MEMORY_USAGE_WARNING=80         # 内存使用警告 (MB)
SSH_MEMORY_USAGE_CRITICAL=100       # 内存使用严重 (MB)
SWAP_USAGE_WARNING=70               # Swap 使用警告 (%)
SWAP_USAGE_CRITICAL=80              # Swap 使用严重 (%)
```

### 定时任务
```bash
# 每日性能报告 (早上8点)
0 8 * * * /Users/liulu/Server-Admin/scripts/ssh-monitor-telegram.sh --daily

# 实时监控 (每5分钟)
*/5 * * * * /Users/liulu/Server-Admin/scripts/ssh-monitor-telegram.sh --monitor

# 周度报告 (周一早上9点)
0 9 * * 1 /Users/liulu/Server-Admin/scripts/ssh-monitor-telegram.sh --weekly

# 性能数据收集 (每小时)
0 * * * * /Users/liulu/Server-Admin/scripts/ssh-metrics-collector.sh
```

---

## 🔐 安全注意事项

### 敏感信息保护
1. **API Token**：Telegram bot token 存储在配置文件中，不提交到版本控制
2. **SSH 密钥**：私钥不存储在本项目中
3. **密码**：不使用密码认证，全部使用密钥或 Token
4. **配置文件**：敏感配置使用 `.gitignore` 排除

### 访问控制
1. **SSH 访问**：仅允许密钥认证，禁止 root 密码登录
2. **Telegram bot**：仅允许配置的 Chat ID 访问
3. **服务端口**：仅开放必要的端口
4. **防火墙**：UFW 配置严格的规则

### 安全审计
1. **日志审计**：所有操作都有日志记录
2. **变更审计**：所有配置变更都有备份和记录
3. **安全更新**：启用自动安全更新
4. **漏洞扫描**：定期检查已知漏洞

---

## 📝 文档维护

### 文档结构
1. **README.md**：项目总览，快速开始指南
2. **CLAUDE.md**：Claude 协作指南（本文件）
3. **CHANGELOG.md**：总变更日志
4. **docs/**：详细技术文档
5. **changelogs/**：按月归档的变更日志
6. **adr/**：架构决策记录
7. **incidents/**：故障记录

### 文档更新流程
1. **代码变更**：代码变更时同步更新相关文档
2. **功能新增**：新增功能时创建或更新文档
3. **配置变更**：配置变更时更新配置文档
4. **定期审查**：每月审查文档，确保与代码同步

### 文档标准
1. **Markdown 格式**：使用标准的 Markdown 语法
2. **中文为主**：技术文档使用中文，代码注释使用英文
3. **实用导向**：文档应包含实际用例和命令
4. **版本信息**：文档包含最后更新日期和版本

---

## 🚨 故障处理

### 常见问题
1. **SSH 连接失败**：
   ```bash
   # 检查 SSH 服务状态
   ssh -v tokyo
   # 检查防火墙规则
   ufw status
   # 检查 SSH 配置
   ssh -G tokyo
   ```

2. **Telegram bot 不响应**：
   ```bash
   # 检查 bot 服务状态
   systemctl status telegram-bot
   # 检查日志
   journalctl -u telegram-bot -f
   # 重启服务
   systemctl restart telegram-bot
   ```

3. **Docker 容器异常**：
   ```bash
   # 查看容器状态
   docker-manage status
   # 查看容器日志
   docker-manage logs [容器名]
   # 重启容器
   docker-manage restart [容器名]
   ```

### 紧急恢复
1. **SSH 配置回滚**：
   ```bash
   ./ssh-optimize.sh rollback --host=tokyo
   ```

2. **服务恢复**：
   ```bash
   # 重启所有服务
   docker-manage restart --all
   # 重启系统服务
   systemctl restart ssh docker
   ```

3. **数据恢复**：
   ```bash
   # 从备份恢复
   backup.sh --restore [备份文件]
   ```

---

## 🔗 相关资源

### 项目链接
- **GitHub 仓库**: https://github.com/quinnmacro/Server-Admin
- **SanctionList 项目**: https://github.com/quinnmacro/SanctionList
- **Vultr 控制台**: https://my.vultr.com/

### 技术文档
- **OpenSSH 文档**: https://www.openssh.com/manual.html
- **Docker 文档**: https://docs.docker.com/
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Ubuntu 文档**: https://ubuntu.com/server/docs

### 工具推荐
- **SSH 性能测试**: `ssh-benchmark.sh`, `iperf3`, `mtr`
- **网络诊断**: `tcpdump`, `netstat`, `ss`
- **安全审计**: `ssh-audit`, `lynis`, `fail2ban`
- **监控工具**: `htop`, `iftop`, `nethogs`

---

## 📞 联系信息

### 项目维护者
- **GitHub**: quinnmacro
- **服务器**: Vultr 东京服务器 (149.28.25.78)

### 技术支持
- **Telegram**: 通过 bot 直接联系
- **GitHub Issues**: 提交问题或功能请求
- **文档**: 查阅相关技术文档

---

*此文档由 Claude 维护，最后更新于 2026-04-12*