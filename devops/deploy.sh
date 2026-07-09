#!/bin/bash
# 部署快捷命令
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$PROJECT_ROOT/deploy/scripts/deploy_smart.py" "$@"
