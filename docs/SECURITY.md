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

---

*更新于 2026-04-11*
