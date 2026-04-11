# 服务器初始化配置

> 记录服务器从零开始的所有配置步骤

---

## 一、基础系统配置

### 1.1 时区设置

```bash
timedatectl set-timezone Asia/Hong_Kong
```

### 1.2 系统更新

```bash
apt update && apt upgrade -y
apt install -y curl wget git vim htop net-tools
```

### 1.3 自动安全更新

```bash
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

---

## 二、用户与 SSH

### 2.1 SSH 配置

编辑 `/etc/ssh/sshd_config.d/custom.conf`：

```
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
```

### 2.2 添加 SSH 公钥

```bash
# 本地生成密钥（如果没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 复制公钥到服务器
ssh-copy-id root@149.28.25.78
```

---

## 三、防火墙

```bash
# 安装 UFW
apt install -y ufw

# 默认策略
ufw default deny incoming
ufw default allow outgoing

# 开放端口
ufw allow 22/tcp      # SSH
ufw allow 3000/tcp    # Homepage
ufw allow 32001/tcp   # SanctionList Frontend
ufw allow 32002/tcp   # SanctionList Backend
ufw allow 443/tcp     # HTTPS

# 启用
ufw enable
```

---

## 四、Fail2ban

```bash
apt install -y fail2ban

# 配置 /etc/fail2ban/jail.local
```

---

## 五、Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
apt install -y docker-compose-plugin
```

---

## 六、监控与备份

详见 [MONITORING.md](./MONITORING.md) 和 [BACKUP.md](./BACKUP.md)

---

## 七、网络工具

### 7.1 Tailscale VPN

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
```

### 7.2 Cloudflare Tunnel

```bash
# 下载 cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared-linux-amd64.deb

# 配置隧道
cloudflared tunnel login
cloudflared tunnel create <name>
cloudflared tunnel route dns <name> <hostname>
```

---

*记录于 2026-04-11*
