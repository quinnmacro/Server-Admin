# ADR-002: 服务器性能优化方案

## 状态

已接受

## 背景

服务器（1 vCPU, 2GB RAM）内存使用率约 75%，Swap 使用率约 40%。需要优化以：
- 防止内存耗尽导致 OOM
- 提高系统稳定性
- 优化网络性能

## 决策

采用轻量级内核调优 + Docker 资源限制方案，而非增加硬件资源。

## 理由

1. **内核调优零成本**: sysctl 配置无需额外资源
2. **资源限制有效**: 防止容器抢占过多内存
3. **Swap 优化**: 减少频繁交换导致的性能下降
4. **TCP 优化**: 提升网络连接效率

## 实施内容

### 内核优化

```bash
# 内存管理
vm.swappiness = 10              # 降低 swap 使用倾向
vm.vfs_cache_pressure = 50      # 优化缓存回收

# 网络优化
net.ipv4.tcp_fastopen = 3       # 开启 TCP Fast Open
net.ipv4.tcp_tw_reuse = 1       # 复用 TIME_WAIT 连接
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_max_syn_backlog = 4096
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
```

### 容器资源限制

| 容器 | 内存限制 | CPU 限制 |
|------|----------|----------|
| backend | 256MB | 0.5核 |
| frontend | 64MB | 0.25核 |
| homepage | 64MB | 0.25核 |

### 日志管理

- Docker 日志: 最大 10MB/文件，保留 7 天
- Journal 日志: 最大 100MB，保留 7 天

## 替代方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| 内核调优 | 零成本、即时生效 | 效果有限 |
| 升级到 4GB | 彻底解决 | 增加成本 |
| Kubernetes | 企业级管理 | 资源消耗大 |

## 后果

- 系统稳定性提高
- 单个容器故障不会影响其他服务
- 内存压力降低
- 无额外成本

---

*决策日期: 2026-04-11*
