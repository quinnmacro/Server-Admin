# Server-Admin

> 服务器运维管理中心  
> 最后更新：2026-04-11

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
├── README.md              # 本文档
├── docs/                  # 详细文档
│   ├── SETUP.md           # 初始化配置
│   ├── MONITORING.md      # 监控系统
│   ├── BACKUP.md          # 备份恢复
│   ├── DEPLOY.md          # 部署流程
│   ├── SECURITY.md        # 安全配置
│   └── SERVICES.md        # 服务列表
├── scripts/               # 运维脚本
│   ├── health-check.sh    # 健康检查
│   ├── backup.sh          # 备份脚本
│   ├── log-monitor.sh     # 日志监控
│   ├── deploy.sh          # 部署脚本
│   └── docker-manage.sh   # Docker管理
├── changelogs/            # 变更日志
│   └── 2026-04.md         # 按月归档
├── incidents/             # 故障记录
│   └── YYYY-MM-DD-title.md
└── adr/                   # 架构决策记录
    └── NNN-title.md
```

---

## 🚀 快速连接

```bash
# SSH 连接
ssh tokyo

# 查看状态
health-check

# 查看容器
docker-manage status

# 部署
deploy SanctionList

# 备份
backup
```

---

## 📊 运行的服务

| 服务 | 端口 | 状态 |
|------|------|------|
| SanctionList Frontend | 32001 | ✅ |
| SanctionList Backend | 32002 | ✅ |
| Homepage | 3000 | ✅ |
| X-UI | 自动 | ✅ |
| Tailscale VPN | 41641 | ✅ |
| Cloudflare Tunnel | - | ✅ |

---

## 📅 定时任务

| 时间 | 任务 |
|------|------|
| 每 5 分钟 | 日志监控 |
| 每小时 | 健康检查 |
| 每天 2:00 | 自动备份 |
| 每天 8:00 | 完整检查 |

---

## 🔔 告警通知

所有告警通过 Telegram 发送：
- 健康检查异常
- 安全事件（SSH、Fail2ban）
- 容器异常
- 部署结果

---

## 📚 文档

- [初始化配置](./docs/SETUP.md)
- [监控系统](./docs/MONITORING.md)
- [备份恢复](./docs/BACKUP.md)
- [部署流程](./docs/DEPLOY.md)
- [安全配置](./docs/SECURITY.md)
- [服务列表](./docs/SERVICES.md)
- [变更日志](./changelogs/2026-04.md)

---

## 📝 维护记录

| 日期 | 操作 | 记录人 |
|------|------|--------|
| 2026-04-11 | 初始化监控系统、备份系统 | Claude |
| 2026-04-11 | 添加日志聚合、自动化部署 | Claude |

---

*此仓库与服务器 `/usr/local/share/doc/monitoring/` 同步*
