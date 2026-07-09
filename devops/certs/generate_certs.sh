#!/bin/bash
# ================================================================
# 幽灵协议 - 证书生成脚本 (Linux/Mac)
#
# 🔴 双指纹策略：同时生成主证书(A)和备用证书(B)
# ================================================================

set -e

# 配置参数 (请修改)
SERVER_IP="${1:-YOUR_SERVER_IP}"
CA_DAYS=3650
SERVER_DAYS=730
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CERT_DIR="$PROJECT_ROOT/backend/certs"

# 创建输出目录
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

echo "=========================================="
echo "Step 1: 生成 CA 根证书"
echo "=========================================="

openssl genrsa -aes256 -out ca.key 4096
echo "✓ CA 私钥: ca.key"

openssl req -new -x509 -days $CA_DAYS -key ca.key -sha256 -out ca.crt \
    -subj "/C=CN/ST=Private/L=Private/O=Stock Analysis CA/CN=Stock Analysis Root CA"
echo "✓ CA 证书: ca.crt"

# 创建扩展配置 (主证书和备用证书共用)
cat > server_ext.cnf << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
IP.1 = $SERVER_IP
IP.2 = 127.0.0.1
DNS.1 = stock.internal
DNS.2 = localhost
EOF

echo ""
echo "=========================================="
echo "Step 2: 生成主服务器证书 (Cert A - 当前使用)"
echo "=========================================="

openssl genrsa -out server_a.key 2048
echo "✓ 主证书私钥: server_a.key"

openssl req -new -key server_a.key -out server_a.csr \
    -subj "/C=CN/ST=Private/L=Private/O=Stock Analysis/CN=$SERVER_IP"
openssl x509 -req -in server_a.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server_a.crt -days $SERVER_DAYS -sha256 -extfile server_ext.cnf
echo "✓ 主证书: server_a.crt"

FP_A=$(openssl x509 -in server_a.crt -noout -fingerprint -sha256 | cut -d'=' -f2 | tr -d ':')
echo "✓ 主证书指纹: $FP_A"

echo ""
echo "=========================================="
echo "Step 3: 生成备用证书 (Cert B - 冷备)"
echo "=========================================="

openssl genrsa -out server_b.key 2048
echo "✓ 备用证书私钥: server_b.key"

openssl req -new -key server_b.key -out server_b.csr \
    -subj "/C=CN/ST=Private/L=Private/O=Stock Analysis/CN=$SERVER_IP"
openssl x509 -req -in server_b.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server_b.crt -days $SERVER_DAYS -sha256 -extfile server_ext.cnf
echo "✓ 备用证书: server_b.crt"

FP_B=$(openssl x509 -in server_b.crt -noout -fingerprint -sha256 | cut -d'=' -f2 | tr -d ':')
echo "✓ 备用证书指纹: $FP_B"

echo ""
echo "=========================================="
echo "Step 4: 创建部署文件"
echo "=========================================="

cp server_a.key server.key
cp server_a.crt server.crt
echo "✓ 当前部署证书: server.key, server.crt"

cat > fingerprints.txt << EOF
# 幽灵协议 - 证书指纹
# 请将两个指纹都配置到 ssl-pinning.js

PRIMARY_CERT_FINGERPRINT=$FP_A
BACKUP_CERT_FINGERPRINT=$FP_B
EOF
echo "✓ 指纹已保存: fingerprints.txt"

echo ""
echo "=========================================="
echo "🔐 生成完成！"
echo "=========================================="
echo ""
echo "📁 文件清单:"
echo "   server.key/crt   - 当前部署 (Cert A)"
echo "   server_a.key/crt - 主证书 (当前使用)"
echo "   server_b.key/crt - 备用证书 (冷备)"
echo "   fingerprints.txt - 双指纹配置"
echo ""
echo "🔴 重要：双指纹策略"
echo "   主证书指纹: $FP_A"
echo "   备用指纹:   $FP_B"
echo ""
echo "⚠️  安全提醒:"
echo "   1. server_b.key (备用私钥) 必须离线冷存储 (U盘/保险箱)"
echo "   2. 两个指纹都要配置到客户端 ssl-pinning.js"
echo "   3. 如果主证书泄露，换上备用证书即可，无需更新客户端"
echo ""
