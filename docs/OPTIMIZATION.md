# 服务器性能优化配置

> 记录所有性能优化相关的配置和参数

---

## 一、内核优化

### 1.1 配置文件

**位置**: `/etc/sysctl.d/99-server-optimize.conf`

### 1.2 优化项说明

| 参数 | 默认值 | 优化值 | 说明 |
|------|--------|--------|------|
| `vm.swappiness` | 60 | 10 | 降低 swap 使用倾向 |
| `vm.vfs_cache_pressure` | 100 | 50 | 提高缓存回收效率 |
| `net.ipv4.tcp_fastopen` | 0 | 3 | 开启 TCP Fast Open |
| `net.ipv4.tcp_tw_reuse` | 0 | 1 | 复用 TIME_WAIT 连接 |
| `net.ipv4.tcp_keepalive_time` | 7200 | 600 | 减少无效连接 |
| `net.ipv4.tcp_max_syn_backlog` | 128 | 4096 | 提高 SYN 队列 |
| `net.core.rmem_max` | 212992 | 16777216 | TCP 读缓冲区 |
| `net.core.wmem_max` | 212992 | 16777216 | TCP 写缓冲区 |

### 1.3 应用配置

```bash
# 应用配置
sysctl -p /etc/sysctl.d/99-server-optimize.conf

# 验证配置
sysctl vm.swappiness net.ipv4.tcp_fastopen
```

---

## 二、Docker 资源限制

### 2.1 当前配置

| 容器 | 内存限制 | CPU 限制 | 预留内存 |
|------|----------|----------|----------|
| sanctionlist-backend | 256MB | 0.5核 | 64MB |
| sanctionlist-frontend | 64MB | 0.25核 | 16MB |
| homepage | 64MB | 0.25核 | 16MB |

### 2.2 配置方式

在 `docker-compose.yml` 中添加：

```yaml
deploy:
  resources:
    limits:
      memory: 256M
      cpus: '0.5'
    reservations:
      memory: 64M
```

### 2.3 查看资源使用

```bash
# 实时监控
docker stats

# 单次快照
docker stats --no-stream
```

---

## 三、日志管理

### 3.1 Docker 日志轮转

**位置**: `/etc/logrotate.d/docker-containers`

```
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
```

### 3.2 Systemd Journal 限制

**位置**: `/etc/systemd/journald.conf.d/override.conf`

```ini
[Journal]
SystemMaxUse=100M
MaxRetentionSec=7day
```

应用：`systemctl restart systemd-journald`

---

## 四、监控指标

### 4.1 新增监控项

| 检查项 | 阈值 | 说明 |
|--------|------|------|
| OOM 事件 | >0 | 检测内存溢出 |
| TCP CLOSE_WAIT | >50 | 连接泄漏风险 |
| 容器内存使用率 | >80% | 资源告警 |

### 4.2 健康检查

```bash
# 手动运行
/usr/local/sbin/monitoring/health-check.sh

# 静默模式
/usr/local/sbin/monitoring/health-check.sh -q
```

---

## 五、回滚方案

### 5.1 恢复内核配置

```bash
rm /etc/sysctl.d/99-server-optimize.conf
sysctl --system
```

### 5.2 恢复容器配置

移除 docker-compose.yml 中的 `deploy` 部分，然后重启容器。

---

*更新于 2026-04-11*
