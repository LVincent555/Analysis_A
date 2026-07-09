#!/bin/bash
# 查看服务状态
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$PROJECT_ROOT/deploy/scripts/service_manager.py" status
