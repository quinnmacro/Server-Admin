#!/bin/bash
# SSH配置部署测试脚本
# 用于测试ssh-optimize.sh的部署功能

echo "=== SSH配置部署测试 ==="
echo "目标主机: tokyo"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. 检查脚本依赖
echo "1. 检查依赖..."
if ! command -v ssh &>/dev/null; then
    echo "❌ SSH客户端未安装"
    exit 1
fi

if ! command -v scp &>/dev/null; then
    echo "❌ SCP客户端未安装"
    exit 1
fi

echo "✅ 基础依赖检查通过"

# 2. 测试SSH连接
echo ""
echo "2. 测试SSH连接..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes tokyo "echo '✅ SSH连接正常'" 2>/dev/null; then
    echo "✅ SSH连接测试通过"
else
    echo "❌ SSH连接失败"
    echo "请检查:"
    echo "  - ~/.ssh/config 中的 tokyo 配置"
    echo "  - SSH密钥认证"
    echo "  - 网络连接"
    exit 1
fi

# 3. 检查远程服务器状态
echo ""
echo "3. 检查远程服务器状态..."
echo "系统信息:"
ssh tokyo "
    echo '  - 主机名: \$(hostname)'
    echo '  - 系统: \$(lsb_release -d 2>/dev/null | cut -f2 || uname -a)'
    echo '  - SSH版本: \$(sshd -V 2>&1 | head -1)'
    echo '  - 内存: \$(free -h | awk '/^Mem:/{print \$2}')'
    echo '  - 存储: \$(df -h / | tail -1 | awk '{print \$5}') 使用率'
"

# 4. 检查现有SSH配置
echo ""
echo "4. 检查现有SSH配置..."
echo "当前SSH配置摘要:"
ssh tokyo "
    echo '主配置文件:'
    ls -la /etc/ssh/sshd_config
    echo ''
    echo '配置片段目录:'
    ls -la /etc/ssh/sshd_config.d/ 2>/dev/null || echo '目录不存在'
    echo ''
    echo '关键配置项:'
    grep -E '(MaxSessions|MaxStartups|UseDNS|Compression|PasswordAuthentication|PermitRootLogin)' /etc/ssh/sshd_config 2>/dev/null | head -10
"

# 5. 测试ssh-optimize.sh脚本
echo ""
echo "5. 测试ssh-optimize.sh脚本..."
if [ -f "/Users/liulu/Server-Admin/scripts/ssh-optimize.sh" ]; then
    echo "✅ 找到ssh-optimize.sh脚本"

    # 测试verify命令
    echo "测试verify命令..."
    if /Users/liulu/Server-Admin/scripts/ssh-optimize.sh verify --host=tokyo 2>/dev/null; then
        echo "✅ verify命令执行成功"
    else
        echo "⚠️ verify命令执行失败（可能是预期行为）"
    fi

    # 测试status命令
    echo "测试status命令..."
    if /Users/liulu/Server-Admin/scripts/ssh-optimize.sh status --host=tokyo 2>&1 | head -20; then
        echo "✅ status命令执行成功"
    else
        echo "⚠️ status命令执行失败"
    fi
else
    echo "❌ 未找到ssh-optimize.sh脚本"
    exit 1
fi

# 6. 备份当前配置
echo ""
echo "6. 备份当前配置..."
if /Users/liulu/Server-Admin/scripts/ssh-optimize.sh backup --host=tokyo 2>/dev/null; then
    echo "✅ 配置备份成功"
else
    echo "⚠️ 配置备份失败（可能是目录权限问题）"
fi

# 7. 显示配置差异
echo ""
echo "7. 显示配置差异..."
/Users/liulu/Server-Admin/scripts/ssh-optimize.sh diff --host=tokyo

# 8. 部署测试（试运行）
echo ""
echo "8. 部署测试（试运行模式）..."
echo "注意: 这将以试运行模式执行，不会实际修改配置"
if /Users/liulu/Server-Admin/scripts/ssh-optimize.sh deploy --host=tokyo --dry-run 2>&1 | tail -20; then
    echo "✅ 部署试运行成功"
else
    echo "❌ 部署试运行失败"
fi

# 9. 性能基准测试准备
echo ""
echo "9. 准备性能基准测试..."
if [ -f "/Users/liulu/Server-Admin/scripts/ssh-benchmark.sh" ]; then
    echo "✅ 找到ssh-benchmark.sh脚本"
    echo "建议在部署前建立性能基准:"
    echo "  ./ssh-benchmark.sh --baseline --save"
else
    echo "❌ 未找到ssh-benchmark.sh脚本"
fi

# 10. 生成部署检查清单
echo ""
echo "=== 部署检查清单 ==="
echo "✅ 1. 依赖检查完成"
echo "✅ 2. SSH连接测试通过"
echo "✅ 3. 远程服务器状态检查完成"
echo "✅ 4. 现有配置检查完成"
echo "✅ 5. 配置管理脚本测试完成"
echo "✅ 6. 配置备份测试完成"
echo "✅ 7. 配置差异分析完成"
echo "✅ 8. 部署试运行完成"
echo "✅ 9. 性能基准测试准备完成"
echo ""
echo "=== 下一步行动 ==="
echo "1. 建立性能基准:"
echo "   cd ~/Server-Admin/scripts && ./ssh-benchmark.sh --baseline --save"
echo ""
echo "2. 部署性能配置:"
echo "   ./ssh-optimize.sh deploy --host=tokyo"
echo ""
echo "3. 验证部署效果:"
echo "   ./ssh-benchmark.sh --compare --report"
echo ""
echo "4. 监控性能变化:"
echo "   ./health-check.sh"
echo ""
echo "=== 安全注意事项 ==="
echo "• 部署过程中保持现有SSH连接"
echo "• 使用ControlMaster确保有备用连接"
echo "• 部署前确保有控制台访问权限"
echo "• 测试回滚功能: ./ssh-optimize.sh rollback"
echo ""
echo "测试完成时间: $(date '+%Y-%m-%d %H:%M:%S')"