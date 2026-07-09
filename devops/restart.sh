#!/bin/bash
# 重启所有服务
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$PROJECT_ROOT/deploy/scripts/service_manager.py" restart all
