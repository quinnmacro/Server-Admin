# 服务列表

> 服务器上运行的所有服务

---

## 一、系统服务

| 服务 | 说明 | 状态 | 自启动 |
|------|------|------|--------|
| ssh | SSH 服务 | ✅ 运行中 | ✅ |
| docker | Docker 守护进程 | ✅ 运行中 | ✅ |
| fail2ban | 入侵防护 | ✅ 运行中 | ✅ |
| tailscaled | Tailscale VPN | ✅ 运行中 | ✅ |
| x-ui | X-UI 面板 | ✅ 运行中 | ✅ |

---

## 二、Docker 容器

### SanctionList

**位置**: `/root/projects/SanctionList`

**功能**: 制裁名单搜索系统

| 容器 | 镜像 | 端口 | 内存限制 | CPU限制 |
|------|------|------|----------|---------|
| sanctionlist-backend-1 | 自建 | 32002:8000 | 256MB | 0.5核 |
| sanctionlist-frontend-1 | 自建 | 32001:3000 | 64MB | 0.25核 |

**数据库**: SQLite (`/root/projects/SanctionList/data/sanctions.db`)

**启动**:
```bash
cd /root/projects/SanctionList && docker compose up -d
```

### Homepage

**位置**: `/root/projects/homepage`

**功能**: 服务器导航页

| 容器 | 镜像 | 端口 | 内存限制 | CPU限制 |
|------|------|------|----------|---------|
| homepage | ghcr.io/gethomepage/homepage:latest | 3000:3000 | 64MB | 0.25核 |

**启动**:
```bash
cd /root/projects/homepage && docker compose up -d
```

---

## 三、网络服务

### Tailscale VPN

- **状态**: 运行中
- **端口**: 41641 (UDP)
- **用途**: 安全内网访问

**命令**:
```bash
tailscale status
tailscale up
```

### Cloudflare Tunnel

- **状态**: 运行中
- **配置**: `/etc/cloudflared/config.yml`
- **用途**: 无需开放端口的外网访问

**命令**:
```bash
cloudflared tunnel list
cloudflared tunnel login
```

---

## 四、端口映射

| 端口 | 服务 | 公网访问 | 说明 |
|------|------|----------|------|
| 22 | SSH | ✅ | 管理访问 |
| 3000 | Homepage | ✅ | 导航页 |
| 32001 | Frontend | ✅ | Web界面 |
| 32002 | Backend | ✅ | API服务 |
| 41641 | Tailscale | ✅ | VPN |

---

## 五、资源使用

### 内存分配

| 服务 | 内存占用 |
|------|----------|
| 系统基础 | ~400MB |
| Docker 服务 | ~150MB |
| 可用内存 | ~400MB |
| Swap | ~1.5GB/2.4GB |

### 磁盘使用

| 目录 | 使用量 |
|------|--------|
| 系统 | ~8GB |
| Docker | ~5GB |
| 项目 | ~200MB |
| 备份 | ~500MB |
| 可用 | ~38GB |

---

## 六、管理命令

```bash
# 查看所有服务状态
systemctl status ssh docker fail2ban tailscaled x-ui

# 查看所有容器状态
docker-manage status

# 重启服务
systemctl restart <service>
docker-manage restart <project>

# 查看资源使用
docker stats --no-stream
free -m
df -h
```

---

## 七、健康检查

每个容器都配置了健康检查：

```bash
# 查看容器健康状态
docker ps --format "table {{.Names}}\t{{.Status}}"
```

健康检查配置：
- 检查间隔: 30秒
- 超时时间: 10秒
- 重试次数: 3次

---

*更新于 2026-04-11*
