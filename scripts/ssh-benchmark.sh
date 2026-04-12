#!/bin/bash
# SSH性能基准测试脚本 v1.0
# 功能：建立SSH性能基准，测试连接时间、传输速度、并发处理能力
# 与现有健康检查系统集成
# 用法: ssh-benchmark.sh [选项]
#   --baseline          建立原始性能基准并保存
#   --test=TYPE         运行特定测试: response, concurrent, transfer, memory
#   --iterations=N      测试迭代次数（默认：10）
#   --sessions=N        并发会话数（默认：5）
#   --size=SIZE         传输测试文件大小（默认：1MB）
#   --compare           与保存的基准比较
#   --report            生成详细性能报告
#   --save              保存当前结果为基准
#   --host=HOST         目标主机（默认：tokyo）
#   --help              显示帮助信息

# 加载配置（如果存在）
source /etc/monitoring/config.conf 2>/dev/null

# 设置PATH以确保找到jq等工具
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# 配置参数
DEFAULT_HOST="tokyo"
DEFAULT_ITERATIONS=10
DEFAULT_SESSIONS=5
DEFAULT_SIZE="1MB"
BASELINE_FILE="/Users/liulu/Server-Admin/logs/monitoring/ssh-baseline.json"
LOG_FILE="/Users/liulu/Server-Admin/logs/monitoring/ssh-benchmark.log"
RESULT_FILE="/tmp/ssh-benchmark-results.json"
QUIET=false
VERBOSE=false

# 解析参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --baseline)
                MODE="baseline"
                ;;
            --test=*)
                MODE="test"
                TEST_TYPE="${1#*=}"
                ;;
            --iterations=*)
                DEFAULT_ITERATIONS="${1#*=}"
                ;;
            --sessions=*)
                DEFAULT_SESSIONS="${1#*=}"
                ;;
            --size=*)
                DEFAULT_SIZE="${1#*=}"
                ;;
            --compare)
                MODE="compare"
                ;;
            --report)
                MODE="report"
                ;;
            --save)
                SAVE_RESULTS=true
                ;;
            --host=*)
                DEFAULT_HOST="${1#*=}"
                ;;
            --quiet)
                QUIET=true
                ;;
            --verbose)
                VERBOSE=true
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done

    # 默认模式：运行完整测试套件
    if [ -z "$MODE" ]; then
        MODE="full"
    fi
}

# 显示帮助
show_help() {
    cat << EOF
SSH性能基准测试脚本 v1.0

用法: ssh-benchmark.sh [选项]

选项:
  --baseline           建立原始性能基准并保存到 $BASELINE_FILE
  --test=TYPE          运行特定测试:
                        response  - SSH响应时间测试
                        concurrent - 并发连接处理能力测试
                        transfer  - 文件传输速度测试
                        memory    - 内存使用测试
  --iterations=N       测试迭代次数（默认: $DEFAULT_ITERATIONS）
  --sessions=N         并发会话数（默认: $DEFAULT_SESSIONS）
  --size=SIZE          传输测试文件大小（默认: $DEFAULT_SIZE）
                       支持格式: 1MB, 10MB, 100MB
  --compare            与保存的基准比较
  --report             生成详细性能报告
  --save               保存当前结果为基准
  --host=HOST          目标主机（默认: $DEFAULT_HOST）
  --quiet              静默模式，仅写日志
  --verbose            详细输出模式
  --help, -h           显示此帮助信息

示例:
  # 建立原始性能基准
  ssh-benchmark.sh --baseline --save

  # 测试SSH响应时间
  ssh-benchmark.sh --test=response --iterations=100

  # 测试并发处理能力
  ssh-benchmark.sh --test=concurrent --sessions=20

  # 测试传输速度
  ssh-benchmark.sh --test=transfer --size=10MB

  # 生成性能报告
  ssh-benchmark.sh --report --compare

与现有监控系统集成:
  - 日志位置: $LOG_FILE
  - 基准数据: $BASELINE_FILE
  - 集成到健康检查脚本 health-check.sh
EOF
}

# 日志函数
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [SSH-BENCHMARK] $1"
    echo "$msg" >> "$LOG_FILE"
    [ "$QUIET" = false ] && echo "$msg"
}

# 发送 Telegram 通知
notify() {
    if [ "$TELEGRAM_ENABLED" = "true" ] && [ -x /usr/local/sbin/monitoring/telegram-notify.sh ]; then
        /usr/local/sbin/monitoring/telegram-notify.sh "$1" "true" 2>/dev/null &
    fi
}

# 获取当前时间戳（毫秒）
get_timestamp_ms() {
    if command -v python3 &>/dev/null; then
        python3 -c 'import time; print(int(time.time() * 1000))'
    elif command -v python &>/dev/null; then
        python -c 'import time; print(int(time.time() * 1000))'
    else
        date +%s%3N 2>/dev/null || date +%s000
    fi
}

# 测试SSH响应时间
test_response_time() {
    local iterations=${1:-$DEFAULT_ITERATIONS}
    local host=${2:-$DEFAULT_HOST}
    local total_ms=0
    local min_ms=999999
    local max_ms=0
    local successes=0

    log "开始SSH响应时间测试 ($iterations 次迭代, 目标: $host)"

    for i in $(seq 1 $iterations); do
        local start_ms=$(get_timestamp_ms)

        # 测试SSH连接（执行简单命令）
        if ssh -o ConnectTimeout=5 -o BatchMode=yes "$host" "echo -n" 2>/dev/null; then
            local end_ms=$(get_timestamp_ms)
            local duration=$((end_ms - start_ms))

            total_ms=$((total_ms + duration))
            successes=$((successes + 1))

            # 更新最小/最大值
            [ $duration -lt $min_ms ] && min_ms=$duration
            [ $duration -gt $max_ms ] && max_ms=$duration

            [ "$VERBOSE" = true ] && log "  迭代 $i: ${duration}ms"
        else
            log "  迭代 $i: 连接失败"
        fi

        # 短暂延迟，避免压垮服务器
        sleep 0.1
    done

    if [ $successes -gt 0 ]; then
        local avg_ms=$((total_ms / successes))
        log "响应时间测试完成: 平均 ${avg_ms}ms, 最小 ${min_ms}ms, 最大 ${max_ms}ms, 成功率 $successes/$iterations"

        # 保存结果
        echo "{
            \"test\": \"response_time\",
            \"host\": \"$host\",
            \"iterations\": $iterations,
            \"successes\": $successes,
            \"avg_ms\": $avg_ms,
            \"min_ms\": $min_ms,
            \"max_ms\": $max_ms,
            \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S')\"
        }" >> "$RESULT_FILE"

        echo $avg_ms
    else
        log "响应时间测试失败: 所有连接尝试都失败"
        echo 0
    fi
}

# 测试文件传输速度
test_transfer_speed() {
    local size=${1:-$DEFAULT_SIZE}
    local host=${2:-$DEFAULT_HOST}
    local temp_file="/tmp/ssh-benchmark-${size}.dat"
    local remote_temp_file="/tmp/ssh-benchmark-remote-${size}.dat"

    # 创建测试文件
    log "创建 ${size} 测试文件..."
    case $size in
        *MB)
            local size_mb=${size%MB}
            dd if=/dev/urandom of="$temp_file" bs=1M count=$size_mb 2>/dev/null
            ;;
        *KB)
            local size_kb=${size%KB}
            dd if=/dev/urandom of="$temp_file" bs=1K count=$size_kb 2>/dev/null
            ;;
        *)
            dd if=/dev/urandom of="$temp_file" bs=1M count=1 2>/dev/null
            ;;
    esac

    local file_size=$(stat -f%z "$temp_file" 2>/dev/null || stat -c%s "$temp_file" 2>/dev/null)
    local file_size_mb=$(echo "scale=2; $file_size / 1024 / 1024" | bc)

    log "测试文件大小: ${file_size_mb}MB"

    # 测试SCP上传速度
    local start_ms=$(get_timestamp_ms)
    if scp -o ConnectTimeout=10 "$temp_file" "${host}:${remote_temp_file}" 2>/dev/null; then
        local end_ms=$(get_timestamp_ms)
        local duration_ms=$((end_ms - start_ms))

        # 计算速度（MB/s）
        local duration_sec=$(echo "scale=3; $duration_ms / 1000" | bc)
        local speed_mbps=$(echo "scale=2; $file_size_mb / $duration_sec" | bc)

        log "SCP上传速度: ${speed_mbps}MB/s (${duration_ms}ms 传输 ${file_size_mb}MB)"

        # 清理远程文件
        ssh -o ConnectTimeout=5 "$host" "rm -f '$remote_temp_file'" 2>/dev/null

        # 保存结果
        echo "{
            \"test\": \"transfer_speed\",
            \"host\": \"$host\",
            \"direction\": \"upload\",
            \"size_bytes\": $file_size,
            \"size_mb\": $file_size_mb,
            \"duration_ms\": $duration_ms,
            \"speed_mbps\": $speed_mbps,
            \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S')\"
        }" >> "$RESULT_FILE"

        echo $speed_mbps
    else
        log "文件传输测试失败"
        echo 0
    fi

    # 清理本地文件
    rm -f "$temp_file"
}

# 测试并发连接处理能力
test_concurrent_connections() {
    local sessions=${1:-$DEFAULT_SESSIONS}
    local host=${2:-$DEFAULT_HOST}
    local success_count=0
    local pids=()

    log "开始并发连接测试 ($sessions 个并发会话)"

    # 启动并发会话
    for i in $(seq 1 $sessions); do
        (
            local start_ms=$(get_timestamp_ms)
            if ssh -o ConnectTimeout=5 -o BatchMode=yes "$host" "echo -n" 2>/dev/null; then
                local end_ms=$(get_timestamp_ms)
                local duration=$((end_ms - start_ms))
                echo "success:$duration" > "/tmp/ssh-concurrent-$i.result"
            else
                echo "failed:0" > "/tmp/ssh-concurrent-$i.result"
            fi
        ) &
        pids+=($!)
    done

    # 等待所有会话完成
    local timeout=$((sessions * 2 + 5))
    local waited=0
    for pid in "${pids[@]}"; do
        while kill -0 "$pid" 2>/dev/null && [ $waited -lt $timeout ]; do
            sleep 0.1
            waited=$((waited + 1))
        done

        # 如果进程还在运行，杀死它
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "failed:timeout" > "/tmp/ssh-concurrent-$pid.result"
        fi
    done

    # 收集结果
    local total_duration=0
    for i in $(seq 1 $sessions); do
        if [ -f "/tmp/ssh-concurrent-$i.result" ]; then
            local result=$(cat "/tmp/ssh-concurrent-$i.result")
            rm -f "/tmp/ssh-concurrent-$i.result"

            if [[ "$result" == success:* ]]; then
                local duration=${result#success:}
                success_count=$((success_count + 1))
                total_duration=$((total_duration + duration))
                [ "$VERBOSE" = true ] && log "  会话 $i: 成功 (${duration}ms)"
            else
                [ "$VERBOSE" = true ] && log "  会话 $i: 失败"
            fi
        fi
    done

    # 清理可能的残留文件
    rm -f /tmp/ssh-concurrent-*.result

    if [ $success_count -gt 0 ]; then
        local avg_duration=$((total_duration / success_count))
        local success_rate=$(echo "scale=1; $success_count * 100 / $sessions" | bc)

        log "并发测试完成: $success_count/$sessions 成功 (${success_rate}%), 平均响应时间 ${avg_duration}ms"

        # 保存结果
        echo "{
            \"test\": \"concurrent_connections\",
            \"host\": \"$host\",
            \"sessions\": $sessions,
            \"successes\": $success_count,
            \"success_rate\": $success_rate,
            \"avg_duration_ms\": $avg_duration,
            \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S')\"
        }" >> "$RESULT_FILE"

        echo $success_count
    else
        log "并发测试失败: 所有会话都失败"
        echo 0
    fi
}

# 测试SSH内存使用
test_memory_usage() {
    local host=${1:-$DEFAULT_HOST}

    log "测试SSH服务内存使用 (目标: $host)"

    # 获取服务器SSH进程内存使用
    local memory_info=$(ssh -o ConnectTimeout=5 "$host" \
        "ps aux | grep -E '[s]shd:.*@' | head -5 | awk '{sum += \$6} END {print sum, NR}'" 2>/dev/null)

    if [ -n "$memory_info" ]; then
        local total_kb=$(echo "$memory_info" | awk '{print $1}')
        local process_count=$(echo "$memory_info" | awk '{print $2}')
        local avg_kb=0

        if [ $process_count -gt 0 ]; then
            avg_kb=$((total_kb / process_count))
        fi

        local total_mb=$(echo "scale=2; $total_kb / 1024" | bc)
        local avg_mb=$(echo "scale=2; $avg_kb / 1024" | bc)

        log "SSH内存使用: ${total_mb}MB (${process_count}个进程, 平均${avg_mb}MB/进程)"

        # 保存结果
        echo "{
            \"test\": \"memory_usage\",
            \"host\": \"$host\",
            \"process_count\": $process_count,
            \"total_kb\": $total_kb,
            \"total_mb\": $total_mb,
            \"avg_kb\": $avg_kb,
            \"avg_mb\": $avg_mb,
            \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S')\"
        }" >> "$RESULT_FILE"

        echo $total_kb
    else
        log "内存使用测试失败: 无法获取服务器内存信息"
        echo 0
    fi
}

# 建立性能基准
establish_baseline() {
    local host=${1:-$DEFAULT_HOST}

    log "开始建立SSH性能基准 (目标: $host)"

    # 清空结果文件
    > "$RESULT_FILE"

    # 运行完整测试套件
    local response_time=$(test_response_time 20 "$host")
    sleep 1

    local transfer_speed=$(test_transfer_speed "1MB" "$host")
    sleep 1

    local concurrent_connections=$(test_concurrent_connections 10 "$host")
    sleep 1

    local memory_usage=$(test_memory_usage "$host")

    # 生成基准文件
    if [ -f "$RESULT_FILE" ]; then
        local baseline_data="{\"baseline\": {\"host\": \"$host\", \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S')\"}, \"tests\": ["

        # 读取所有测试结果
        while IFS= read -r line; do
            baseline_data+="$line,"
        done < "$RESULT_FILE"

        # 移除最后一个逗号
        baseline_data="${baseline_data%,}"
        baseline_data+="]}"

        # 保存基准文件
        echo "$baseline_data" | jq . 2>/dev/null > "$BASELINE_FILE"

        if [ $? -eq 0 ]; then
            log "性能基准已保存到: $BASELINE_FILE"

            # 发送通知
            notify "📊 SSH性能基准建立完成
✅ 响应时间: ${response_time}ms
📁 传输速度: ${transfer_speed}MB/s
👥 并发能力: ${concurrent_connections}/10 成功
💾 内存使用: ${memory_usage}KB

📅 $(date '+%Y-%m-%d %H:%M:%S')"

            echo "$BASELINE_FILE"
        else
            log "保存基准文件失败: 需要安装 jq 工具"
            return 1
        fi
    else
        log "建立基准失败: 无测试结果"
        return 1
    fi
}

# 与基准比较
compare_with_baseline() {
    if [ ! -f "$BASELINE_FILE" ]; then
        log "无法比较: 基准文件不存在 $BASELINE_FILE"
        log "请先运行: ssh-benchmark.sh --baseline --save"
        return 1
    fi

    log "与基准比较: $BASELINE_FILE"

    # 运行当前测试
    > "$RESULT_FILE"
    local current_response=$(test_response_time 10)
    sleep 1

    local current_transfer=$(test_transfer_speed "1MB")
    sleep 1

    local current_concurrent=$(test_concurrent_connections 5)
    sleep 1

    # 读取基准数据
    local baseline_response=$(jq -r '.tests[] | select(.test=="response_time") | .avg_ms' "$BASELINE_FILE" 2>/dev/null)
    local baseline_transfer=$(jq -r '.tests[] | select(.test=="transfer_speed") | .speed_mbps' "$BASELINE_FILE" 2>/dev/null)
    local baseline_concurrent=$(jq -r '.tests[] | select(.test=="concurrent_connections") | .successes' "$BASELINE_FILE" 2>/dev/null)

    # 计算变化百分比
    local response_change="N/A"
    local transfer_change="N/A"
    local concurrent_change="N/A"

    if [ -n "$baseline_response" ] && [ "$baseline_response" != "null" ] && [ "$current_response" -gt 0 ]; then
        local change=$(echo "scale=1; ($current_response - $baseline_response) * 100 / $baseline_response" | bc)
        response_change="${change}%"
    fi

    if [ -n "$baseline_transfer" ] && [ "$baseline_transfer" != "null" ] && [ "$(echo "$current_transfer > 0" | bc)" -eq 1 ]; then
        local change=$(echo "scale=1; ($current_transfer - $baseline_transfer) * 100 / $baseline_transfer" | bc)
        transfer_change="${change}%"
    fi

    if [ -n "$baseline_concurrent" ] && [ "$baseline_concurrent" != "null" ] && [ "$current_concurrent" -gt 0 ]; then
        local change=$(echo "scale=1; ($current_concurrent - $baseline_concurrent) * 100 / $baseline_concurrent" | bc)
        concurrent_change="${change}%"
    fi

    # 生成报告
    cat << REPORT
========================================
          SSH性能比较报告
========================================
基准文件: $(basename "$BASELINE_FILE")
比较时间: $(date '+%Y-%m-%d %H:%M:%S')

测试项目         | 基准值       | 当前值       | 变化
-----------------|--------------|--------------|-----------
响应时间 (ms)    | ${baseline_response}ms | ${current_response}ms | ${response_change}
传输速度 (MB/s)  | ${baseline_transfer}MB/s | ${current_transfer}MB/s | ${transfer_change}
并发成功率       | ${baseline_concurrent}/5 | ${current_concurrent}/5 | ${concurrent_change}

性能评估:
REPORT

    # 性能评估
    if [ "$response_change" != "N/A" ] && [[ "$response_change" == -* ]]; then
        echo "✅ 响应时间改善: 减少 ${response_change#-}"
    elif [ "$response_change" != "N/A" ]; then
        echo "⚠️  响应时间变差: 增加 ${response_change}"
    fi

    if [ "$transfer_change" != "N/A" ] && [[ "$transfer_change" != -* ]]; then
        echo "✅ 传输速度提升: 增加 ${transfer_change}"
    elif [ "$transfer_change" != "N/A" ]; then
        echo "⚠️  传输速度下降: 减少 ${transfer_change#-}"
    fi
}

# 生成详细报告
generate_report() {
    log "生成SSH性能报告"

    if [ ! -f "$RESULT_FILE" ] || [ ! -s "$RESULT_FILE" ]; then
        log "无测试结果可生成报告"
        log "请先运行测试: ssh-benchmark.sh --test=response"
        return 1
    fi

    cat << REPORT
========================================
        SSH性能测试报告
========================================
生成时间: $(date '+%Y-%m-%d %H:%M:%S')
目标主机: $DEFAULT_HOST
日志文件: $LOG_FILE

测试结果概览:
REPORT

    # 读取并显示结果
    while IFS= read -r line; do
        local test_type=$(echo "$line" | jq -r '.test' 2>/dev/null)
        if [ -n "$test_type" ]; then
            case $test_type in
                response_time)
                    local avg_ms=$(echo "$line" | jq -r '.avg_ms')
                    local min_ms=$(echo "$line" | jq -r '.min_ms')
                    local max_ms=$(echo "$line" | jq -r '.max_ms')
                    echo "📊 响应时间: ${avg_ms}ms (最小: ${min_ms}ms, 最大: ${max_ms}ms)"
                    ;;
                transfer_speed)
                    local speed_mbps=$(echo "$line" | jq -r '.speed_mbps')
                    local size_mb=$(echo "$line" | jq -r '.size_mb')
                    echo "📁 传输速度: ${speed_mbps}MB/s (文件大小: ${size_mb}MB)"
                    ;;
                concurrent_connections)
                    local successes=$(echo "$line" | jq -r '.successes')
                    local sessions=$(echo "$line" | jq -r '.sessions')
                    local success_rate=$(echo "$line" | jq -r '.success_rate')
                    echo "👥 并发连接: ${successes}/${sessions} 成功 (${success_rate}%)"
                    ;;
                memory_usage)
                    local total_mb=$(echo "$line" | jq -r '.total_mb')
                    local process_count=$(echo "$line" | jq -r '.process_count')
                    echo "💾 内存使用: ${total_mb}MB (${process_count}个SSH进程)"
                    ;;
            esac
        fi
    done < "$RESULT_FILE"

    echo ""
    echo "建议:"
    echo "1. 响应时间 < 500ms 为优秀"
    echo "2. 传输速度 > 5MB/s 为良好"
    echo "3. 并发成功率 > 80% 为稳定"
    echo "4. 定期运行基准测试监控性能变化"
}

# 主函数
main() {
    parse_args "$@"

    # 确保日志目录存在
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$(dirname "$BASELINE_FILE")"

    log "========== SSH性能基准测试开始 =========="

    # 清空临时结果文件
    > "$RESULT_FILE"

    case $MODE in
        baseline)
            establish_baseline "$DEFAULT_HOST"
            ;;
        test)
            case $TEST_TYPE in
                response)
                    test_response_time "$DEFAULT_ITERATIONS" "$DEFAULT_HOST"
                    ;;
                transfer)
                    test_transfer_speed "$DEFAULT_SIZE" "$DEFAULT_HOST"
                    ;;
                concurrent)
                    test_concurrent_connections "$DEFAULT_SESSIONS" "$DEFAULT_HOST"
                    ;;
                memory)
                    test_memory_usage "$DEFAULT_HOST"
                    ;;
                *)
                    log "未知测试类型: $TEST_TYPE"
                    show_help
                    exit 1
                    ;;
            esac
            ;;
        compare)
            compare_with_baseline
            ;;
        report)
            generate_report
            ;;
        full)
            # 运行完整测试套件
            log "运行完整SSH性能测试套件"
            test_response_time "$DEFAULT_ITERATIONS" "$DEFAULT_HOST"
            sleep 1
            test_transfer_speed "$DEFAULT_SIZE" "$DEFAULT_HOST"
            sleep 1
            test_concurrent_connections "$DEFAULT_SESSIONS" "$DEFAULT_HOST"
            sleep 1
            test_memory_usage "$DEFAULT_HOST"

            log "完整测试套件完成"
            generate_report
            ;;
    esac

    # 保存结果（如果指定）
    if [ "$SAVE_RESULTS" = true ] && [ -s "$RESULT_FILE" ]; then
        local timestamp=$(date '+%Y%m%d_%H%M%S')
        local save_file="/Users/liulu/Server-Admin/logs/monitoring/ssh-results-${timestamp}.json"
        cp "$RESULT_FILE" "$save_file"
        log "测试结果已保存到: $save_file"
    fi

    log "========== SSH性能基准测试完成 =========="
}

# 检查依赖
check_dependencies() {
    local missing_deps=()

    # 检查必需工具
    for cmd in ssh scp bc; do
        if ! command -v "$cmd" &>/dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    # 检查可选工具
    if ! command -v jq &>/dev/null; then
        log "警告: jq 未安装，部分功能受限"
        log "安装命令: brew install jq (macOS) 或 apt install jq (Linux)"
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log "错误: 缺少必需工具: ${missing_deps[*]}"
        exit 1
    fi
}

# 脚本入口
check_dependencies
main "$@"