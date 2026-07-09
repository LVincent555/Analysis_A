#!/bin/bash
# 查看日志
SERVICE=${1:-backend}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$PROJECT_ROOT/deploy/scripts/service_manager.py" logs "$SERVICE"
