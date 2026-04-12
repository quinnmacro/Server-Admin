# 安全配置文档

> 服务器安全加固措施

---

## 一、网络安全

### 1.1 防火墙 (UFW)

**状态**: 启用

**开放端口**:

| 端口 | 服务 | 说明 |
|------|------|------|
| 22 | SSH | 公网访问 |
| 3000 | Homepage | Web服务 |
| 32001 | SanctionList Frontend | Web服务 |
| 32002 | SanctionList Backend | API服务 |
| 443 | HTTPS | Web服务 |

**管理命令**:
```bash
# 查看状态
ufw status verbose

# 开放端口
ufw allow 80/tcp

# 删除规则
ufw delete allow 80/tcp
```

### 1.2 VPN 访问

**Tailscale**:
- 状态: 运行中
- 端口: 41641 (UDP)
- 用途: 内网访问

**Cloudflare Tunnel**:
- 状态: 运行中
- 用途: 无需开放端口的公网访问

---

## 二、SSH 安全

### 2.1 配置

**位置**: `/etc/ssh/sshd_config.d/custom.conf`

```
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
```

### 2.2 密钥管理

```bash
# 生成密钥对
ssh-keygen -t ed25519 -C "your_email@example.com"

# 复制公钥到服务器
ssh-copy-id root@149.28.25.78
```

### 2.3 SSH 登录监控

- 每日发送登录日报
- 异常登录检测
- Fail2ban 自动封禁

---

## 三、Fail2ban

### 3.1 配置

**位置**: `/etc/fail2ban/jail.local`

| Jail | 封禁时间 | 最大尝试 |
|------|----------|----------|
| sshd | 1 周 | 3 次 |
| nginx-http-auth | 1 周 | 5 次 |
| nginx-limit-req | 1 周 | 10 次 |

### 3.2 管理命令

```bash
# 查看状态
fail2ban-client status

# 查看 sshd jail
fail2ban-client status sshd

# 手动封禁 IP
fail2ban-client set sshd banip 1.2.3.4

# 解封 IP
fail2ban-client set sshd unbanip 1.2.3.4
```

### 3.3 Telegram 通知

封禁事件自动发送 Telegram 通知。

---

## 四、安全更新

### 4.1 自动更新

**位置**: `/etc/apt/apt.conf.d/20auto-upgrades`

```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

### 4.2 检查安全更新

```bash
# 查看待安装的安全更新
apt list --upgradable | grep -i security

# 安装安全更新
apt upgrade -y --with-new-pkgs
```

---

## 五、日志审计

### 5.1 审计日志

| 日志 | 位置 |
|------|------|
| SSH 登录 | `/var/log/auth.log` |
| Fail2ban | `/var/log/fail2ban.log` |
| 系统日志 | `journalctl` |

### 5.2 查看日志

```bash
# 查看SSH登录
journalctl -u ssh -f

# 查看Fail2ban日志
tail -f /var/log/fail2ban.log

# 查看系统错误
journalctl -p err
```

---

## 六、安全检查清单

- [x] SSH 密钥登录
- [x] 禁用密码登录
- [x] UFW 防火墙
- [x] Fail2ban 入侵防护
- [x] 自动安全更新
- [x] 定期备份
- [x] Telegram 告警
- [x] VPN 访问
- [x] SSH 性能优化安全验证

---

## 七、SSH 性能优化安全指南

### 7.1 安全原则

SSH 性能优化在提升性能的同时，必须保持或增强安全级别：

1. **安全性不妥协**：任何性能优化不得降低安全级别
2. **最小权限原则**：只授予必要的权限
3. **深度防御**：多层安全防护
4. **审计追踪**：所有变更都有记录和备份

### 7.2 SSH 性能优化安全配置

#### 7.2.1 加密算法选择

```bash
# 安全且高效的加密算法优先级
Ciphers chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com
MACs umac-64-etm@openssh.com,hmac-sha2-256-etm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org
```

**安全说明**：
- `chacha20-poly1305`：现代加密算法，性能优秀，安全性高
- `curve25519`：现代密钥交换算法，性能好，安全性高
- 禁用弱加密算法（CBC 模式、SHA1、MD5）

#### 7.2.2 连接管理安全

```bash
# 性能优化配置（同时保持安全）
MaxSessions 20                 # 限制单个连接的最大会话数
MaxStartups 30:10:100          # 控制并发连接，防止DoS
LoginGraceTime 60              # 登录超时时间（默认120秒）
MaxAuthTries 3                 # 最大认证尝试次数
```

**安全验证**：
```bash
# 验证关键安全配置未改变
ssh tokyo "sshd -T | grep -E '(PasswordAuthentication|PermitRootLogin|AllowUsers)'"
```

#### 7.2.3 性能与安全平衡

| 优化项 | 性能提升 | 安全影响 | 安全措施 |
|--------|----------|----------|----------|
| UseDNS no | 减少连接延迟 | 无影响 | 本地 hosts 文件解析 |
| Compression delayed | 提升传输速度 | 轻微风险（CRIME攻击） | 使用延迟压缩 |
| MaxSessions 20 | 提升并发处理 | 增加资源消耗 | 配合资源限制 |
| TCPKeepAlive yes | 保持连接 | 增加连接数 | 配合连接数限制 |

### 7.3 安全审计

#### 7.3.1 配置变更审计

```bash
# 部署前自动备份
./ssh-optimize.sh deploy --host=tokyo --dry-run

# 查看配置差异
./ssh-optimize.sh diff --host=tokyo

# 验证安全配置未改变
./ssh-optimize.sh verify --security --host=tokyo
```

#### 7.3.2 安全扫描

```bash
# 使用 ssh-audit 进行安全扫描
ssh-audit 149.28.25.78

# 检查加密算法强度
ssh -Q cipher tokyo
ssh -Q mac tokyo
ssh -Q kex tokyo
```

### 7.4 监控与告警

#### 7.4.1 安全事件监控

```bash
# SSH 异常登录监控
./log-monitor.sh --ssh

# Fail2ban 封禁监控
./log-monitor.sh --fail2ban

# 性能异常告警（可能的安全攻击迹象）
./ssh-monitor-telegram.sh --alert
```

#### 7.4.2 告警阈值

```bash
# 安全相关性能告警阈值
SSH_RESPONSE_TIME_CRITICAL=1500     # 响应时间 >1.5秒（可能为DoS攻击）
SSH_ACTIVE_CONNECTIONS_CRITICAL=25  # 活跃连接 >25（可能为暴力破解）
SSH_AUTH_FAILURE_RATE=10            # 认证失败率 >10%
```

### 7.5 应急响应

#### 7.5.1 安全事件响应

```bash
# 检测到异常时的响应流程
1. 立即发送 Telegram 告警
2. 自动增加 Fail2ban 封禁时间
3. 记录攻击源 IP 和模式
4. 启动 SSH 连接限制
```

#### 7.5.2 快速回滚

```bash
# 安全事件快速回滚
./ssh-optimize.sh rollback --host=tokyo --emergency

# 恢复最小安全配置
./ssh-optimize.sh restore --minimal --host=tokyo

# 封锁攻击源
fail2ban-client set sshd banip <攻击IP>
```

### 7.6 安全检查清单（SSH 性能优化后）

- [ ] 验证加密算法强度
- [ ] 确认密钥认证正常工作
- [ ] 测试 Fail2ban 集成
- [ ] 验证日志记录完整
- [ ] 测试 Telegram 安全告警
- [ ] 验证回滚功能正常
- [ ] 检查资源限制有效
- [ ] 确认监控系统覆盖所有安全指标

### 7.7 最佳实践

1. **渐进式部署**：先在测试环境验证，再部署到生产
2. **性能基线**：部署前建立性能基线，便于问题排查
3. **安全验证**：每次部署后运行安全扫描
4. **持续监控**：部署后持续监控性能和安全性
5. **定期审计**：每月审计 SSH 配置和日志
6. **备份策略**：保留多个版本的配置备份

### 7.8 工具推荐

| 工具 | 用途 | 安全等级 |
|------|------|----------|
| `ssh-audit` | SSH 安全审计 | 高 |
| `lynis` | 系统安全审计 | 高 |
| `fail2ban` | 入侵防护 | 中 |
| `telegram-notify` | 实时告警 | 中 |
| `ssh-benchmark.sh` | 性能测试 | 低 |
| `ssh-optimize.sh` | 配置管理 | 中 |

---

*更新于 2026-04-12*
