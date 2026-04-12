# 变更日志

本文件记录 Server-Admin 项目的所有重要变更。

## 版本策略

采用语义化版本控制（Semantic Versioning）：
- **主版本号**：不兼容的 API 变更
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

## [Unreleased]

### 新增
- **SSH 性能优化系统**：完整的 SSH 性能优化框架
  - `ssh-benchmark.sh`：SSH 性能基准测试脚本
  - `ssh-optimize.sh`：SSH 配置管理脚本
  - `deploy-ssh-config-test.sh`：部署测试脚本
  - `ssh-performance.conf`：SSH 服务器性能配置模板

- **Telegram 机器人 v3.0**：AI 增强版 + SSH 性能监控
  - 重新设计的 3×3 主菜单布局
  - 新增 "🎉 趣味" 菜单，替代原有的 "❓ 帮助"
  - 新增 8 个趣味功能（笑话、彩蛋、游戏等）
  - 新增 SSH 性能监控命令 (`/sshstatus`, `/sshperformance`, `/sshoptimize`, `/sshdiagnose`, `/sshhistory`, `/sshconfig`)
  - 改进的菜单导航和回调系统

### 优化
- **SSH 客户端配置优化**：全面的 SSH 连接性能提升
  - 启用连接复用（ControlMaster auto）
  - 配置现代加密算法（chacha20-poly1305, curve25519 优先）
  - 性能参数调优（Compression yes, TCPKeepAlive yes, IPQoS lowdelay throughput）
  - 测试结果：连接复用改进 91%，后续连接速度提升 11 倍

- **系统监控增强**：
  - 扩展健康检查系统，支持 SSH 性能监控
  - 改进的 Telegram 通知格式
  - 统一的配置管理系统

### 修复
- **Telegram 机器人菜单显示问题**：修复返回主菜单时不显示完整欢迎消息的问题
- **备份脚本路径问题**：修正备份目录路径和文件扩展名
- **配置路径问题**：统一配置到用户级目录，避免权限问题

### 文档
- 创建完整的 SSH 性能优化开发计划文档
- 更新所有相关文档以反映新功能
- 建立新的文档结构

## [1.0.0] - 2026-04-12

### 新增
- **完整的运维管理系统**：Server-Admin 核心框架
  - 健康检查系统 (`health-check.sh` v2.1)
  - 备份恢复系统 (`backup.sh` v1.0)
  - 日志监控系统 (`log-monitor.sh` v1.2)
  - 自动化部署系统 (`deploy.sh`)
  - Docker 管理系统 (`docker-manage.sh`)

- **Telegram 集成**：
  - 通知系统 (`telegram-notify.sh`)
  - 交互式机器人 (`telegram-bot.py` v2.0)
  - SSH 登录日报 (`ssh-daily-report.sh`)

- **安全加固**：
  - Fail2ban 配置优化（封禁时间延长至 1 周）
  - SSH 安全配置（密钥认证，禁用密码）
  - UFW 防火墙规则
  - 自动安全更新

### 服务部署
- SanctionList 项目（前端 32001，后端 32002）
- Homepage 导航页（端口 3000）
- X-UI 管理面板
- Tailscale VPN
- Cloudflare Tunnel

### 系统优化
- 内核性能调优 (`/etc/sysctl.d/99-server-optimize.conf`)
- Docker 容器资源限制
- 日志轮转和清理策略
- 定时任务管理系统

### 文档
- 完整的文档系统（docs/ 目录）
- 架构决策记录（adr/ 目录）
- 变更日志（changelogs/ 目录）
- 故障记录模板

## [0.9.0] - 2026-04-11

### 新增
- **服务器初始化完成**：
  - Vultr 东京服务器部署
  - Docker 和 Docker Compose 安装
  - 基础安全配置
  - 服务容器化部署

### 配置
- SSH 密钥认证配置
- 基础防火墙规则
- 系统监控基线配置

## 变更类型说明

每个变更条目使用以下标签标识：

- `[新增]`：新增功能
- `[优化]`：性能优化或用户体验改进
- `[修复]`：Bug 修复
- `[文档]`：文档更新
- `[安全]`：安全相关变更
- `[重构]`：代码重构或架构变更
- `[测试]`：测试相关变更
- `[配置]`：配置文件变更

## 记录格式

```markdown
## [版本号] - YYYY-MM-DD

### [新增/优化/修复/...]

- **组件名**：变更说明
  - 详细描述
  - 相关文件：`path/to/file`
```

## 维护指南

1. 每次重要变更都应更新此文件
2. 变更描述应简洁明了，说明「做了什么」和「为什么做」
3. 涉及安全、性能、兼容性的变更必须记录
4. 定期回顾变更历史，评估技术债务

---

*此变更日志遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范*