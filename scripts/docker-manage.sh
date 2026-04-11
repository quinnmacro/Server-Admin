#!/bin/bash
# Docker Compose 管理脚本 v1.0
# 用法: docker-manage.sh <command> [options]

PROJECTS_FILE="/etc/docker/projects.conf"

# 加载项目配置
declare -A PROJECTS
if [ -f "$PROJECTS_FILE" ]; then
    while IFS=: read -r path name; do
        PROJECTS[$name]=$path
    done < <(grep -v '^#' "$PROJECTS_FILE")
fi

# 默认项目（如果配置文件不存在）
if [ ${#PROJECTS[@]} -eq 0 ]; then
    PROJECTS[sanctionlist]="/root/projects/SanctionList"
    PROJECTS[homepage]="/root/projects/homepage"
fi

# 显示帮助
show_help() {
    echo "Docker Compose 管理工具"
    echo ""
    echo "用法: docker-manage.sh <command> [project]"
    echo ""
    echo "命令:"
    echo "  status          显示所有项目状态"
    echo "  start [name]    启动项目（不指定则启动全部）"
    echo "  stop [name]     停止项目"
    echo "  restart [name]  重启项目"
    echo "  logs [name]     查看项目日志"
    echo "  update [name]   更新项目镜像并重启"
    echo "  ps              显示所有容器状态"
    echo "  prune           清理无用镜像和容器"
    echo "  list            列出所有项目"
}

# 获取项目状态
get_status() {
    local path=$1
    cd "$path" 2>/dev/null || return 1
    docker compose ps 2>/dev/null
}

# 启动项目
start_project() {
    local name=$1
    local path=${PROJECTS[$name]}
    
    if [ -z "$path" ]; then
        echo "项目不存在: $name"
        return 1
    fi
    
    echo "启动项目: $name"
    cd "$path" && docker compose up -d
}

# 停止项目
stop_project() {
    local name=$1
    local path=${PROJECTS[$name]}
    
    if [ -z "$path" ]; then
        echo "项目不存在: $name"
        return 1
    fi
    
    echo "停止项目: $name"
    cd "$path" && docker compose down
}

# 重启项目
restart_project() {
    local name=$1
    local path=${PROJECTS[$name]}
    
    if [ -z "$path" ]; then
        echo "项目不存在: $name"
        return 1
    fi
    
    echo "重启项目: $name"
    cd "$path" && docker compose restart
}

# 查看日志
logs_project() {
    local name=$1
    local path=${PROJECTS[$name]}
    
    if [ -z "$path" ]; then
        echo "项目不存在: $name"
        return 1
    fi
    
    cd "$path" && docker compose logs -f --tail=100
}

# 更新项目
update_project() {
    local name=$1
    local path=${PROJECTS[$name]}
    
    if [ -z "$path" ]; then
        echo "项目不存在: $name"
        return 1
    fi
    
    echo "更新项目: $name"
    cd "$path"
    docker compose pull
    docker compose up -d
    docker image prune -f
}

# 显示所有状态
show_status() {
    echo "项目状态:"
    echo "===================="
    for name in "${!PROJECTS[@]}"; do
        echo ""
        echo "📁 $name (${PROJECTS[$name]})"
        get_status "${PROJECTS[$name]}" 2>/dev/null | tail -n +1
    done
}

# 启动所有项目
start_all() {
    for name in "${!PROJECTS[@]}"; do
        start_project "$name"
    done
}

# 停止所有项目
stop_all() {
    for name in "${!PROJECTS[@]}"; do
        stop_project "$name"
    done
}

# 重启所有项目
restart_all() {
    for name in "${!PROJECTS[@]}"; do
        restart_project "$name"
    done
}

# 更新所有项目
update_all() {
    for name in "${!PROJECTS[@]}"; do
        update_project "$name"
    done
}

# 列出所有项目
list_projects() {
    echo "已配置的项目:"
    echo "===================="
    for name in "${!PROJECTS[@]}"; do
        echo "  $name -> ${PROJECTS[$name]}"
    done
}

# 清理
prune() {
    echo "清理无用资源..."
    docker system prune -f
    docker image prune -a -f --filter "until=24h"
}

# 主函数
case "$1" in
    status)
        show_status
        ;;
    start)
        if [ -n "$2" ]; then
            start_project "$2"
        else
            start_all
        fi
        ;;
    stop)
        if [ -n "$2" ]; then
            stop_project "$2"
        else
            stop_all
        fi
        ;;
    restart)
        if [ -n "$2" ]; then
            restart_project "$2"
        else
            restart_all
        fi
        ;;
    logs)
        logs_project "$2"
        ;;
    update)
        if [ -n "$2" ]; then
            update_project "$2"
        else
            update_all
        fi
        ;;
    ps)
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;
    prune)
        prune
        ;;
    list)
        list_projects
        ;;
    *)
        show_help
        ;;
esac
