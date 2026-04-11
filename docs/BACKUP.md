# 备份恢复文档

> 数据备份策略与恢复流程

---

## 一、备份策略

### 1.1 备份内容

| 类型 | 内容 | 大小预估 |
|------|------|----------|
| 项目 | SanctionList 代码和数据库 | ~150MB |
| 项目 | Homepage 配置 | ~5MB |
| 配置 | 监控配置 | ~1MB |
| 配置 | Fail2ban 配置 | ~100KB |
| 配置 | Nginx 配置 | ~50KB |
| 配置 | SSH 配置 | ~10KB |

### 1.2 保留策略

| 周期 | 频率 | 保留数量 | 存储位置 |
|------|------|----------|----------|
| 每日 | 凌晨 2:00 | 7 个 | /var/backups/daily/ |
| 每周 | 周日凌晨 4:00 | 4 个 | /var/backups/weekly/ |
| 每月 | 1号凌晨 4:00 | 12 个 | /var/backups/monthly/ |

---

## 二、备份脚本

### 2.1 backup.sh

**位置**: `/usr/local/sbin/monitoring/backup.sh`

**用法**:
```bash
# 执行备份
/usr/local/sbin/monitoring/backup.sh

# 静默模式
/usr/local/sbin/monitoring/backup.sh -q

# 测试模式（不删除旧备份）
/usr/local/sbin/monitoring/backup.sh --test
```

### 2.2 加密方式

- 算法: AES-256-CBC
- 密钥派生: PBKDF2
- 密钥位置: `/etc/monitoring/backup.key`

**生成新密钥**:
```bash
openssl rand -base64 32 > /etc/monitoring/backup.key
chmod 600 /etc/monitoring/backup.key
```

---

## 三、恢复流程

### 3.1 解密备份

```bash
# 解密备份文件
openssl enc -d -aes-256-cbc -pbkdf2 \
  -in backup-2026-04-11.tar.gz.gpg \
  -out backup.tar.gz \
  -pass file:/etc/monitoring/backup.key

# 解压
tar -xzf backup.tar.gz
```

### 3.2 恢复数据库

```bash
# 恢复 SQLite 数据库
cp backup/data/sanctions.db /root/projects/SanctionList/data/

# 恢复权限
chown root:root /root/projects/SanctionList/data/sanctions.db
```

### 3.3 恢复配置

```bash
# 恢复监控配置
cp backup/etc/monitoring/* /etc/monitoring/

# 恢复 Fail2ban 配置
cp backup/etc/fail2ban/* /etc/fail2ban/
systemctl restart fail2ban
```

---

## 四、验证备份

### 4.1 检查备份完整性

```bash
# 列出备份内容（不解密）
gpg --list-packets backup-2026-04-11.tar.gz.gpg

# 测试解密
openssl enc -d -aes-256-cbc -pbkdf2 \
  -in backup-2026-04-11.tar.gz.gpg \
  -pass file:/etc/monitoring/backup.key | tar -tzf -
```

### 4.2 定期验证

每月1号手动验证最新备份的可恢复性。

---

## 五、异地备份

### 5.1 Vultr 快照

- 自动快照: 每周
- 手动快照: 重大变更前
- 保留: 2 个快照

### 5.2 下载到本地

```bash
# 从服务器下载备份
scp tokyo:/var/backups/daily/backup-latest.tar.gz.gpg ./backups/
```

---

## 六、存储使用

```bash
# 查看备份占用
du -sh /var/backups/*

# 清理旧备份（保留策略外）
find /var/backups/daily -name "*.gpg" -mtime +7 -delete
find /var/backups/weekly -name "*.gpg" -mtime +28 -delete
find /var/backups/monthly -name "*.gpg" -mtime +365 -delete
```

---

*更新于 2026-04-11*
