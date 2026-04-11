# 服务列表

> 服务器上运行的所有服务

---

## 一、系统服务

| 服务 | 说明 | 状态 |
|------|------|------|
| ssh | SSH 服务 | ✅ 运行中 |
| docker | Docker 守护进程 | ✅ 运行中 |
| fail2ban | 入侵防护 | ✅ 运行中 |
| tailscaled | Tailscale VPN | ✅ 运行中 |
| x-ui | X-UI 面板 | ✅ 运行中 |
| nginx | Web 服务器 | ✅ 运行中 |

---

## 二、Docker 容器

### SanctionList

| 容器 | 镜像 | 端口 | 内存 |
|------|------|------|------|
| sanctionlist-frontend-1 | sanctionlist-frontend | 32001:3000 | ~18MB |
| sanctionlist-backend-1 | sanctionlist-backend | 32002:8000 | ~84MB |

**位置**: `/root/projects/SanctionList`

**启动**: `cd /root/projects/SanctionList && docker compose up -d`

### Homepage

| 容器 | 镜像 | 端口 | 内存 |
|------|------|------|------|
| homepage | ghcr.io/gethomepage/homepage:latest | 3000:3000 | ~21MB |

**位置**: `/root/projects/homepage`

**启动**: `cd /root/projects/homepage && docker compose up -d`

---

## 三、网络服务

### Tailscale VPN

- **状态**: 连接中
- **端口**: 41641 (UDP)

### Cloudflare Tunnel

- **状态**: 运行中
- **配置**: `/etc/cloudflared/config.yml`

---

## 四、端口映射

| 端口 | 服务 | 公网访问 |
|------|------|----------|
| 22 | SSH | ✅ |
| 3000 | Homepage | ✅ |
| 32001 | SanctionList Frontend | ✅ |
| 32002 | SanctionList Backend | ✅ |
| 443 | HTTPS | ✅ |

---

## 五、管理命令

```bash
# 查看所有服务状态
systemctl status ssh docker fail2ban tailscaled x-ui nginx

# 查看所有容器状态
docker-manage status

# 重启服务
systemctl restart <service>
docker-manage restart <project>
```

---

*更新于 2026-04-11*
