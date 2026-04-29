# CLAUDE.md — Server-Admin

## Project
Server operations for Vultr Tokyo (149.28.25.78). Health checks, backups, Telegram bot, Docker management. Ubuntu 24.04, 1 vCPU / 2GB RAM.

## Commands
- Health check: `health-check` or `health-check -q`
- Docker: `docker-manage status|logs|restart <service>`
- Deploy: `deploy <project>` or `deploy --all`
- Backup: `backup` or `backup -q`
- SSH benchmark: `ssh-benchmark.sh --baseline`
- Bot restart: `systemctl restart telegram-bot`
- Bot syntax check: `python3 -m py_compile /usr/local/sbin/monitoring/telegram-bot.py`

## Architecture
- `scripts/telegram-bot.py` — Bot v4.0 (python-telegram-bot, CALLBACK_ROUTES, arun_command async, @safe_handler)
- `scripts/health-check.sh` — System health v2.1
- `scripts/backup.sh` — Encrypted backup
- `/etc/monitoring/config.conf` — Bot config (perms 600)
- `~/.hermes/bot_performance.db` — Performance baselines
- `~/.hermes/bot_history.db` — Operation history

## Rules
- Bot code: Python f-strings cannot contain backslashes — extract to variable first.
- Bot code: Use arun_commands() for parallel, status_emoji() for visual, @safe_handler for error handling.
- IMPORTANT: Never expose server IP or API keys in commits.
- IMPORTANT: Bot config file permissions must be 600.
- Monitoring interval: 5 minutes. Silent hours: 23:00-07:00.
- Single server — no Prometheus/Grafana needed, Bot is sufficient.

## What NOT To Do
- Do NOT add Prometheus/Grafana — Bot handles monitoring for single server.
- Do NOT modify /etc/monitoring/config.conf without backing up first.
- Do NOT restart telegram-bot without running py_compile first.

## Out of Scope
- Multi-server orchestration (single VPS only)
- Windows server management (separate project)
- Detailed deployment docs (see docs/ directory)
