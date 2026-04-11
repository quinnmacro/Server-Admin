#!/bin/bash
# 文档同步脚本
# 用法: sync-docs.sh [server]
# 将本地文档同步到服务器

SERVER="${1:-tokyo}"
DOC_DIR="/usr/local/share/doc/monitoring"

echo "=== 同步文档到 $SERVER ==="

# 确保目录存在
ssh "$SERVER" "mkdir -p $DOC_DIR/adr $DOC_DIR/scripts"

# 同步主文档
echo "同步主文档..."
scp README.md "$SERVER:$DOC_DIR/"
scp docs/*.md "$SERVER:$DOC_DIR/"

# 同步 ADR
echo "同步 ADR..."
scp adr/*.md "$SERVER:$DOC_DIR/adr/"

# 同步变更日志
echo "同步变更日志..."
scp changelogs/2026-04.md "$SERVER:$DOC_DIR/CHANGELOG.md"

# 同步脚本（如果有文档）
if ls scripts/*.md 1>/dev/null 2>&1; then
    echo "同步脚本文档..."
    scp scripts/*.md "$SERVER:$DOC_DIR/scripts/"
fi

# 删除旧的不需要的文档
ssh "$SERVER" "rm -f $DOC_DIR/TELEGRAM_SETUP.md $DOC_DIR/DEVOPS.md 2>/dev/null"

echo ""
echo "=== 同步完成 ==="
echo "文档位置: $SERVER:$DOC_DIR"
echo ""
echo "查看文档:"
echo "  ssh $SERVER 'ls -la $DOC_DIR'"
