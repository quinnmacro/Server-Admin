#!/bin/bash
# 自动化部署脚本 v1.0
# 用法: deploy.sh <project_name> [-q]

# 加载配置
source /etc/monitoring/config.conf 2>/dev/null

PROJECTS_DIR="/root/projects"
QUIET=false

# 解析参数
PROJECT_NAME=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -q) QUIET=true ;;
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

# 部署单个项目
deploy_project() {
    local project_path=$1
    local project_name=$(basename "$project_path")
    
    log "部署项目: $project_name"
    
    cd "$project_path" || return 1
    
    # 检查是否有 .git
    if [ -d ".git" ]; then
        log "  拉取最新代码..."
        git fetch origin
        local local_hash=$(git rev-parse HEAD)
        local remote_hash=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)
        
        if [ "$local_hash" = "$remote_hash" ]; then
            log "  代码已是最新，跳过部署"
            return 0
        fi
        
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null
    fi
    
    # 检查是否有 docker-compose.yml
    if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then
        log "  重建并启动容器..."
        docker compose pull 2>/dev/null
        docker compose up -d --build
        docker image prune -f 2>/dev/null
    fi
    
    log "  部署完成: $project_name"
}

# 主函数
main() {
    log "========== 部署开始 =========="
    
    local success=0
    local failed=0
    
    if [ -n "$PROJECT_NAME" ]; then
        # 部署指定项目
        local project_path="${PROJECTS_DIR}/${PROJECT_NAME}"
        if [ -d "$project_path" ]; then
            if deploy_project "$project_path"; then
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
        for project_path in "$PROJECTS_DIR"/*; do
            if [ -d "$project_path" ]; then
                if deploy_project "$project_path"; then
                    ((success++))
                else
                    ((failed++))
                fi
            fi
        done
    fi
    
    log "========== 部署完成 =========="
    log "成功: $success, 失败: $failed"
    
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
}

main "$@"
