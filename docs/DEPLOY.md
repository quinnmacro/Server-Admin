# 部署流程文档

> 自动化部署与手动部署指南

---

## 一、部署架构

```
┌─────────────────┐      Push       ┌─────────────────┐
│  本地开发       │ ───────────────▶│  GitHub 仓库    │
└─────────────────┘                 └────────┬────────┘
                                             │
                                             │ Webhook
                                             ▼
                                    ┌─────────────────┐
                                    │  GitHub Actions │
                                    └────────┬────────┘
                                             │ SSH
                                             ▼
                                    ┌─────────────────┐
                                    │  服务器 deploy  │
                                    └─────────────────┘
```

---

## 二、自动部署

### 2.1 GitHub Actions 配置

**位置**: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Server
on:
  push:
    branches: [main, master]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: /usr/local/sbin/deploy.sh SanctionList
```

### 2.2 GitHub Secrets 配置

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 服务器 IP (149.28.25.78) |
| `SERVER_USER` | SSH 用户 (root) |
| `SSH_PRIVATE_KEY` | SSH 私钥 |

### 2.3 触发部署

```bash
# 推送到 main 分支自动触发
git push origin main
```

---

## 三、手动部署

### 3.1 部署脚本

**位置**: `/usr/local/sbin/deploy.sh`

**用法**:
```bash
# 部署指定项目
deploy SanctionList
deploy homepage

# 部署所有项目
deploy --all
```

### 3.2 部署流程

1. 拉取最新代码
2. 构建 Docker 镜像
3. 停止旧容器
4. 启动新容器
5. 健康检查
6. 发送 Telegram 通知

### 3.3 回滚

```bash
# 查看部署历史
cd /root/projects/SanctionList
git log --oneline -10

# 回滚到上一版本
git reset --hard HEAD~1
docker compose up -d --build
```

---

## 四、Docker 管理

### 4.1 管理脚本

**位置**: `/usr/local/sbin/docker-manage.sh`

**用法**:
```bash
# 查看所有容器状态
docker-manage status

# 查看容器详情
docker-manage ps

# 启动/停止/重启
docker-manage start [project]
docker-manage stop [project]
docker-manage restart [project]

# 查看日志
docker-manage logs [project]

# 更新镜像
docker-manage update [project]

# 清理无用资源
docker-manage prune

# 列出项目
docker-manage list
```

### 4.2 项目配置

**位置**: `/etc/docker/projects.conf`

```bash
# 格式: 路径:项目名
/root/projects/SanctionList:sanctionlist
/root/projects/homepage:homepage
```

---

## 五、容器资源限制

| 容器 | 内存限制 | CPU 限制 |
|------|----------|----------|
| sanctionlist-backend | 256MB | 0.5核 |
| sanctionlist-frontend | 64MB | 0.25核 |
| homepage | 64MB | 0.25核 |

---

## 六、健康检查

每个容器都配置了健康检查：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## 七、SSH 性能优化部署

### 7.1 SSH 性能优化系统概述

SSH 性能优化系统包含以下组件：

| 组件 | 文件 | 功能 |
|------|------|------|
| SSH 性能基准测试 | `ssh-benchmark.sh` | 测试 SSH 响应时间、传输速度、并发连接 |
| SSH 配置管理 | `ssh-optimize.sh` | 部署、验证、回滚 SSH 配置 |
| 部署测试 | `deploy-ssh-config-test.sh` | 部署前全面测试 |
| 服务器配置模板 | `ssh-performance.conf` | SSH 服务器性能优化配置 |

### 7.2 部署流程

#### 7.2.1 建立性能基准

```bash
# 进入脚本目录
cd ~/Server-Admin/scripts

# 建立原始性能基准
./ssh-benchmark.sh --baseline --save

# 查看基准结果
cat ~/Server-Admin/logs/monitoring/ssh-baseline.json
```

#### 7.2.2 运行部署前测试

```bash
# 运行完整的部署前测试
./deploy-ssh-config-test.sh

# 测试结果会显示所有检查项的状态
# 只有所有测试通过才能继续部署
```

#### 7.2.3 部署 SSH 性能配置

```bash
# 试运行模式（不实际修改配置）
./ssh-optimize.sh deploy --host=tokyo --dry-run

# 实际部署
./ssh-optimize.sh deploy --host=tokyo

# 部署过程包括：
# 1. 备份现有配置
# 2. 验证配置语法
# 3. 部署新配置
# 4. 重启 SSH 服务
# 5. 发送 Telegram 通知
```

#### 7.2.4 验证部署效果

```bash
# 验证配置语法和服务状态
./ssh-optimize.sh verify --host=tokyo

# 测试性能提升
./ssh-benchmark.sh --compare --report

# 生成详细性能报告
./ssh-benchmark.sh --report --format=telegram
```

### 7.3 配置管理命令

```bash
# 查看当前配置状态
./ssh-optimize.sh status --host=tokyo

# 查看配置差异
./ssh-optimize.sh diff --host=tokyo

# 回滚到上一个版本
./ssh-optimize.sh rollback --host=tokyo

# 查看备份列表
./ssh-optimize.sh backups --host=tokyo
```

### 7.4 性能监控集成

#### 7.4.1 健康检查集成

SSH 性能监控已集成到健康检查系统：

```bash
# 运行健康检查（包含 SSH 性能检查）
health-check

# 静默模式
health-check -q
```

#### 7.4.2 Telegram 监控

SSH 性能监控已集成到 Telegram：

```bash
# 手动触发 SSH 性能测试
/sshperformance

# 查看 SSH 状态
/sshstatus

# 获取优化建议
/sshoptimize

# 诊断 SSH 问题
/sshdiagnose
```

### 7.5 优化目标

| 指标 | 优化前 | 优化目标 | 监控方法 |
|------|--------|----------|----------|
| 连接建立时间 | ~600ms | <300ms | `ssh-benchmark.sh` |
| 传输速度 | 基准 | +20% | 100MB 文件传输测试 |
| 并发连接数 | 默认 | +50% | 并发连接测试 |
| Swap 使用率 | ~70% | <50% | `health-check.sh` |

### 7.6 安全注意事项

1. **配置备份**：部署前自动备份原有配置
2. **语法验证**：使用 `sshd -t` 验证配置语法
3. **回滚机制**：支持一键回滚到上一个版本
4. **连接保持**：部署过程中保持现有 SSH 连接
5. **安全验证**：确保安全配置（密钥认证、禁止 root 登录）保持不变

### 7.7 故障排除

#### 部署失败
```bash
# 查看部署日志
tail -f ~/Server-Admin/logs/monitoring/ssh-optimize.log

# 手动回滚
./ssh-optimize.sh rollback --host=tokyo --force

# 检查 SSH 服务状态
ssh tokyo "systemctl status ssh"
```

#### 性能未提升
```bash
# 重新运行性能测试
./ssh-benchmark.sh --full

# 检查配置是否生效
ssh tokyo "sshd -T | grep -E '(maxsessions|usedns|compression)'"

# 检查网络状况
mtr -r -c 10 149.28.25.78
```

#### Telegram 通知未发送
```bash
# 测试 Telegram 通知
telegram-notify --test "SSH 优化部署测试"

# 检查配置
cat /etc/monitoring/config.conf | grep TELEGRAM

# 查看 bot 状态
systemctl status telegram-bot
```

---

*更新于 2026-04-12*
