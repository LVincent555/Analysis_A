#!/bin/bash
# 查看日志
SERVICE=${1:-backend}
python3 deploy/scripts/service_manager.py logs $SERVICE
