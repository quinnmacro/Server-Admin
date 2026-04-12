#!/bin/bash
# 自动化部署脚本 v2.0
# 用法: deploy.sh <project_name> [-q] [--detailed]

# 加载配置
source /etc/monitoring/config.conf 2>/dev/null

PROJECTS_DIR="/root/projects"
QUIET=false
DETAILED_NOTIFICATION=false

# 设置PATH以确保找到jq等工具
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# 解析参数
PROJECT_NAME=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -q) QUIET=true ;;
        --detailed) DETAILED_NOTIFICATION=true ;;
        *) PROJECT_NAME="$1" ;;
    esac
    shift
done

# 日志函数
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    [ "$QUIET" = false ] && echo "$msg"
}

# 发送通知
notify() {
    if [ "$TELEGRAM_ENABLED" = "true" ] && [ -x /usr/local/sbin/monitoring/telegram-notify.sh ]; then
        /usr/local/sbin/monitoring/telegram-notify.sh "$1" "true" 2>/dev/null &
    fi
}

# 格式化详细部署消息
format_detailed_deployment_message() {
    local success_count=$1
    local failed_count=$2
    local deployment_infos=$3
    local total_projects=$4

    local message="🚀 *部署完成报告*

📊 *部署摘要*:
• 总项目数: $total_projects 个
• 成功部署: $success_count 个
• 部分成功: $(echo "$deployment_infos" | grep -c '"status":"partial"' || echo 0) 个
• 部署失败: $failed_count 个
• 开始时间: $(date '+%Y-%m-%d %H:%M:%S')
"

    # 如果有失败项目，添加失败详情
    if [ $failed_count -gt 0 ]; then
        message="$message
🔴 *失败项目*:"
        echo "$deployment_infos" | while read -r info; do
            if echo "$info" | grep -q '"status":"failed"'; then
                local name=$(echo "$info" | jq -r '.name // "unknown"' 2>/dev/null || echo "unknown")
                local error=$(echo "$info" | jq -r '.error // "未知错误"' 2>/dev/null || echo "未知错误")
                message="$message
• $name: $error"
            fi
        done
    fi

    # 添加成功项目详情
    local success_infos=$(echo "$deployment_infos" | grep -v '"status":"failed"' || true)
    if [ -n "$success_infos" ]; then
        message="$message
🟢 *项目详情*:"

        echo "$success_infos" | while read -r info; do
            local name=$(echo "$info" | jq -r '.name // "unknown"' 2>/dev/null || echo "unknown")
            local status=$(echo "$info" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
            local git_changes=$(echo "$info" | jq -r '.git_changes // "false"' 2>/dev/null || echo "false")
            local old_hash=$(echo "$info" | jq -r '.old_hash // ""' 2>/dev/null)
            local new_hash=$(echo "$info" | jq -r '.new_hash // ""' 2>/dev/null)
            local container_status=$(echo "$info" | jq -r '.container_status // ""' 2>/dev/null)

            local status_icon="🟢"
            [ "$status" = "partial" ] && status_icon="🟡"
            [ "$status" = "failed" ] && status_icon="🔴"

            message="$message
$status_icon *$name*"

            if [ "$git_changes" = "true" ] && [ -n "$old_hash" ] && [ -n "$new_hash" ] && [ "$old_hash" != "$new_hash" ]; then
                message="$message
   • 代码更新: \`$old_hash\` → \`$new_hash\`"
            elif [ "$git_changes" = "true" ]; then
                message="$message
   • 代码版本: \`$new_hash\`"
            fi

            if [ -n "$container_status" ]; then
                message="$message
   • 容器状态: $container_status"
            fi
        done
    fi

    # 添加系统信息
    message="$message

📈 *系统状态*:"

    # 获取Docker状态
    local docker_containers=$(docker ps -q 2>/dev/null | wc -l || echo "0")
    local docker_images=$(docker images -q 2>/dev/null | wc -l || echo "0")

    message="$message
• Docker容器: $docker_containers 个运行中
• Docker镜像: $docker_images 个"

    # 获取系统负载（如果可用）
    if command -v uptime &>/dev/null; then
        local load_avg=$(uptime | awk -F'load average:' '{print $2}' | xargs)
        message="$message
• 系统负载: $load_avg"
    fi

    # 添加后续建议
    message="$message

🎯 *后续操作*:
1. 检查服务状态: \`docker-manage status\`
2. 查看部署日志: \`docker-manage logs [项目名]\`
3. 验证服务健康: 访问相应端口
4. 监控性能: 使用 \`/sshstatus\` 命令

⏱ *部署耗时*: 约 $((SECONDS)) 秒
📅 *报告时间*: $(date '+%Y-%m-%d %H:%M:%S')"

    echo "$message"
}

# 发送详细通知
notify_detailed() {
    local success_count=$1
    local failed_count=$2
    local deployment_infos=$3
    local total_projects=$4

    local message=$(format_detailed_deployment_message "$success_count" "$failed_count" "$deployment_infos" "$total_projects")
    notify "$message"
}

# 部署单个项目
deploy_project() {
    local project_path=$1
    local project_name=$(basename "$project_path")
    local deployment_info=""

    log "部署项目: $project_name"

    cd "$project_path" || {
        echo "{\"name\":\"$project_name\",\"status\":\"failed\",\"error\":\"无法进入项目目录\"}"
        return 1
    }

    # 初始化部署信息
    local old_git_hash=""
    local new_git_hash=""
    local has_git_changes=false
    local container_status=""
    local deployment_status="success"
    local error_message=""

    # 检查是否有 .git
    if [ -d ".git" ]; then
        log "  拉取最新代码..."
        git fetch origin

        old_git_hash=$(git rev-parse HEAD --short 2>/dev/null || echo "unknown")
        local remote_branch=$(git remote show origin 2>/dev/null | grep "HEAD branch" | cut -d: -f2 | tr -d ' ')
        if [ -z "$remote_branch" ]; then
            remote_branch="main"
        fi

        local remote_hash=$(git rev-parse "origin/$remote_branch" 2>/dev/null)

        if [ -n "$remote_hash" ]; then
            if [ "$(git rev-parse HEAD)" = "$remote_hash" ]; then
                log "  代码已是最新，跳过部署"
                new_git_hash="$old_git_hash"
                has_git_changes=false
            else
                old_git_hash=$(git rev-parse HEAD --short 2>/dev/null || echo "unknown")
                if git pull origin "$remote_branch"; then
                    new_git_hash=$(git rev-parse HEAD --short 2>/dev/null || echo "unknown")
                    has_git_changes=true
                    log "  代码更新: $old_git_hash → $new_git_hash"
                else
                    error_message="Git拉取失败"
                    deployment_status="failed"
                fi
            fi
        else
            log "  无法获取远程分支信息"
        fi
    else
        log "  非Git项目"
    fi

    # 检查是否有 docker-compose.yml
    if [ "$deployment_status" = "success" ] && { [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; }; then
        log "  重建并启动容器..."

        # 记录部署前的容器状态
        local old_containers=$(docker ps --filter "name=${project_name}" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "无法获取容器状态")

        if docker compose pull 2>/dev/null; then
            log "  镜像拉取完成"
        else
            log "  镜像拉取失败，继续部署"
        fi

        if docker compose up -d --build 2>&1; then
            # 等待容器启动
            sleep 2

            # 检查容器状态
            local container_output=$(docker compose ps --services 2>/dev/null)
            local running_count=0
            local total_count=0

            for service in $container_output; do
                ((total_count++))
                local status=$(docker compose ps "$service" --format json 2>/dev/null | jq -r '.[0].State' 2>/dev/null || echo "unknown")
                if [ "$status" = "running" ]; then
                    ((running_count++))
                fi
            done

            if [ $total_count -gt 0 ]; then
                container_status="$running_count/$total_count 个容器运行中"
                if [ $running_count -eq $total_count ]; then
                    log "  所有容器正常运行"
                else
                    log "  警告: $((total_count - running_count)) 个容器未运行"
                    deployment_status="partial"
                fi
            else
                container_status="无容器定义"
            fi

            # 清理旧镜像
            docker image prune -f 2>/dev/null
        else
            error_message="Docker Compose启动失败"
            deployment_status="failed"
        fi
    elif [ "$deployment_status" = "success" ]; then
        log "  非Docker项目，跳过容器部署"
        container_status="非容器项目"
    fi

    # 生成部署信息JSON
    if [ "$deployment_status" = "failed" ]; then
        deployment_info="{\"name\":\"$project_name\",\"status\":\"failed\",\"error\":\"${error_message:-未知错误}\"}"
    elif [ "$deployment_status" = "partial" ]; then
        deployment_info="{\"name\":\"$project_name\",\"status\":\"partial\",\"git_changes\":$has_git_changes,\"old_hash\":\"$old_git_hash\",\"new_hash\":\"$new_git_hash\",\"container_status\":\"$container_status\"}"
    else
        deployment_info="{\"name\":\"$project_name\",\"status\":\"success\",\"git_changes\":$has_git_changes,\"old_hash\":\"$old_git_hash\",\"new_hash\":\"$new_git_hash\",\"container_status\":\"$container_status\"}"
    fi

    log "  部署完成: $project_name ($deployment_status)"
    echo "$deployment_info"
}

# 主函数
main() {
    local start_time=$SECONDS
    log "========== 部署开始 =========="

    local success=0
    local failed=0
    local deployment_infos=()
    local total_projects=0

    if [ -n "$PROJECT_NAME" ]; then
        # 部署指定项目
        local project_path="${PROJECTS_DIR}/${PROJECT_NAME}"
        if [ -d "$project_path" ]; then
            total_projects=1
            log "部署单个项目: $PROJECT_NAME"

            local project_info=$(deploy_project "$project_path")
            deployment_infos+=("$project_info")

            if echo "$project_info" | grep -q '"status":"success"'; then
                ((success++))
            elif echo "$project_info" | grep -q '"status":"partial"'; then
                ((success++))
            else
                ((failed++))
            fi
        else
            log "项目不存在: $PROJECT_NAME"
            exit 1
        fi
    else
        # 部署所有项目
        log "部署所有项目..."
        for project_path in "$PROJECTS_DIR"/*; do
            if [ -d "$project_path" ]; then
                ((total_projects++))
                local project_name=$(basename "$project_path")
                log "处理项目 ($total_projects): $project_name"

                local project_info=$(deploy_project "$project_path")
                deployment_infos+=("$project_info")

                if echo "$project_info" | grep -q '"status":"success"'; then
                    ((success++))
                elif echo "$project_info" | grep -q '"status":"partial"'; then
                    ((success++))
                else
                    ((failed++))
                fi
            fi
        done
    fi

    local deployment_duration=$((SECONDS - start_time))
    log "========== 部署完成 =========="
    log "总项目: $total_projects, 成功: $success, 失败: $failed"
    log "部署耗时: ${deployment_duration}秒"

    # 合并部署信息
    local all_deployment_infos=$(printf "%s\n" "${deployment_infos[@]}")

    # 发送通知
    if [ "$DETAILED_NOTIFICATION" = true ] || [ $failed -gt 0 ]; then
        # 总是为失败部署发送详细通知，或者当指定--detailed时
        log "发送详细部署通知..."
        notify_detailed "$success" "$failed" "$all_deployment_infos" "$total_projects"
    else
        # 简单通知（向后兼容）
        log "发送简单部署通知..."
        if [ $failed -eq 0 ]; then
            notify "✅ 部署完成

成功部署: $success 个项目
失败: $failed 个

📅 $(date '+%Y-%m-%d %H:%M:%S')"
        else
            notify "⚠️ 部署部分失败

成功: $success 个
失败: $failed 个

📅 $(date '+%Y-%m-%d %H:%M:%S')"
        fi
    fi

    # 返回适当的退出码
    if [ $failed -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

main "$@"
