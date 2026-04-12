# Server-Admin

> 服务器运维管理中心 (AI增强版 + SSH性能监控)
> 最后更新：2026-04-12

---

## 📋 服务器概览

| 项目 | 信息 |
|------|------|
| 主机名 | vultr-tokyo-test |
| 提供商 | Vultr |
| 位置 | 东京 |
| IP | 149.28.25.78 |
| 配置 | 1 vCPU / 2GB RAM / 52GB SSD |
| 系统 | Ubuntu 24.04 LTS |

---

## 🗂️ 目录结构

```
Server-Admin/
├── README.md                   # 本文档
├── CLAUDE.md                   # Claude 协作指南
├── CHANGELOG.md                # 总变更日志
├── docs/                       # 详细文档
│   ├── SETUP.md               # 初始化配置
│   ├── MONITORING.md          # 监控系统
│   ├── BACKUP.md              # 备份恢复
│   ├── DEPLOY.md              # 部署流程
│   ├── SECURITY.md            # 安全配置
│   ├── SERVICES.md            # 服务列表
│   └── OPTIMIZATION.md        # 性能优化
├── scripts/                    # 运维脚本
│   ├── health-check.sh        # 健康检查 v2.1
│   ├── backup.sh              # 加密备份 v1.0
│   ├── log-monitor.sh         # 日志监控 v1.2
│   ├── ssh-daily-report.sh    # SSH日报
│   ├── telegram-notify.sh     # Telegram通知
│   ├── telegram-bot.py        # 交互式机器人 v3.0 (AI增强版)
│   ├── deploy.sh              # 部署脚本
│   ├── docker-manage.sh       # Docker管理
│   ├── ssh-benchmark.sh       # SSH性能基准测试
│   ├── ssh-optimize.sh        # SSH配置管理
│   ├── deploy-ssh-config-test.sh # SSH配置部署测试
│   └── sync-docs.sh           # 文档同步
├── changelogs/                 # 变更日志（按月归档）
│   └── 2026-04.md             # 2026年4月变更
├── incidents/                  # 故障记录
│   └── TEMPLATE.md            # 故障记录模板
├── adr/                        # 架构决策记录
│   ├── 001-monitoring-stack.md    # 监控方案选择
│   └── 002-performance-optimization.md  # 性能优化方案
├── backups/                    # 本地备份文件
├── configs/                    # 配置文件备份
└── logs/                       # 日志文件
```

---

## 🚀 快速命令

```bash
# SSH 连接
ssh tokyo

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

# SSH 性能优化
ssh-benchmark.sh --baseline     # 建立性能基准
ssh-optimize.sh deploy          # 部署 SSH 优化配置
ssh-optimize.sh status          # 查看配置状态
ssh-optimize.sh rollback        # 回滚配置

# Telegram 机器人
# 在 Telegram 中发送以下命令：
/start                          # 启动机器人，显示主菜单
/status                         # 服务器状态
/services                       # 服务列表
/logs                           # 查看日志
/backup                         # 手动触发备份
/sshstatus                      # SSH 性能状态
/sshperformance                 # SSH 性能测试
/sshoptimize                    # SSH 优化建议

# 测试通知
telegram-notify --test "测试消息"
```

---

## 📊 运行的服务

| 服务 | 端口 | 内存限制 | 状态 |
|------|------|----------|------|
| SanctionList Backend | 32002 | 256MB | ✅ |
| SanctionList Frontend | 32001 | 64MB | ✅ |
| Homepage | 3000 | 64MB | ✅ |
| X-UI | 自动 | - | ✅ |
| Tailscale VPN | 41641 | - | ✅ |
| Cloudflare Tunnel | - | - | ✅ |

---

## 📅 定时任务

| 时间 | 任务 | 说明 |
|------|------|------|
| */5 * * * * | log-monitor.sh | Fail2ban/容器异常监控 |
| 0 * * * * | health-check.sh -q | 每小时健康检查 |
| 0 2 * * * | backup.sh -q | 每日备份 |
| 0 8 * * * | health-check.sh | 完整健康检查 |
| 30 8 * * * | ssh-daily-report.sh | SSH登录日报 |
| 0 3 * * * | 日志清理 | 保留7天 |
| 0 4 * * 0 | 备份清理 | 保留4周 |

---

## 🔔 告警通知

所有告警通过 Telegram 发送：

| 类型 | 触发条件 |
|------|----------|
| 🚨 系统告警 | 内存>90%、磁盘>80%、负载>150% |
| 🚨 服务告警 | 容器停止、服务异常 |
| 🚨 安全告警 | OOM事件、可疑端口 |
| 🔐 Fail2ban | IP封禁 |
| 📊 SSH日报 | 每日登录统计 |
| ✅ 部署通知 | 部署成功/失败 |

---

## 📚 文档索引

### 基础配置
- [初始化配置](./docs/SETUP.md) - 服务器初始化步骤
- [服务列表](./docs/SERVICES.md) - 所有服务详情

### 运维管理
- [监控系统](./docs/MONITORING.md) - 健康检查与告警
- [备份恢复](./docs/BACKUP.md) - 备份策略与恢复
- [部署流程](./docs/DEPLOY.md) - 自动化部署
- [性能优化](./docs/OPTIMIZATION.md) - 内核与容器优化

### 安全
- [安全配置](./docs/SECURITY.md) - 防火墙、SSH、Fail2ban

### 记录
- [总变更日志](./CHANGELOG.md) - 完整变更历史
- [按月变更日志](./changelogs/2026-04.md) - 按月归档
- [故障记录模板](./incidents/TEMPLATE.md) - 故障记录格式
- [Claude协作指南](./CLAUDE.md) - Claude 使用指南

### 架构决策
- [ADR-001](./adr/001-monitoring-stack.md) - 监控方案选择
- [ADR-002](./adr/002-performance-optimization.md) - 性能优化方案

---

## 📝 维护记录

| 日期 | 操作 | 记录人 |
|------|------|--------|
| 2026-04-10 | 服务器初始化、部署服务 | Claude |
| 2026-04-11 | 监控系统、备份系统、安全加固 | Claude |
| 2026-04-11 | 日志聚合、自动化部署、容器管理 | Claude |
| 2026-04-11 | 性能优化（内核调优、资源限制） | Claude |
| 2026-04-11 | SSH通知改为每日汇总 | Claude |
| 2026-04-12 | SSH性能优化系统、Telegram机器人v3.0 | Claude |

---

## 🔗 相关链接

- [GitHub 仓库](https://github.com/quinnmacro/Server-Admin)
- [SanctionList 项目](https://github.com/quinnmacro/SanctionList)
- [Vultr 控制台](https://my.vultr.com/)

---

*此仓库与服务器脚本同步，服务器配置文件位于 `/etc/monitoring/`*
