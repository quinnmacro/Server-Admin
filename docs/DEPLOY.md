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

*更新于 2026-04-11*
