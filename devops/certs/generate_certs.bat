@echo off
REM ================================================================
REM 幽灵协议 - 证书生成脚本 (Windows)
REM 需要安装 OpenSSL: winget install ShiningLight.OpenSSL
REM
REM 🔴 双指纹策略：同时生成主证书(A)和备用证书(B)
REM ================================================================

setlocal enabledelayedexpansion

REM 配置参数 (请修改)
set SERVER_IP=YOUR_SERVER_IP
set CA_DAYS=3650
set SERVER_DAYS=730
set "PROJECT_ROOT=%~dp0\..\.."
set "CERT_DIR=%PROJECT_ROOT%\backend\certs"

REM 检查 OpenSSL
where openssl >nul 2>&1
if errorlevel 1 (
    echo ❌ OpenSSL 未安装
    echo 请运行: winget install ShiningLight.OpenSSL
    pause
    exit /b 1
)

REM 创建输出目录
if not exist %CERT_DIR% mkdir %CERT_DIR%
cd %CERT_DIR%

echo ==========================================
echo Step 1: 生成 CA 根证书
echo ==========================================

REM 生成 CA 私钥
openssl genrsa -aes256 -out ca.key 4096
echo ✓ CA 私钥已生成: ca.key

REM 生成 CA 证书
openssl req -new -x509 -days %CA_DAYS% -key ca.key -sha256 -out ca.crt -subj "/C=CN/ST=Private/L=Private/O=Stock Analysis CA/CN=Stock Analysis Root CA"
echo ✓ CA 根证书已生成: ca.crt

REM 创建扩展配置 (主证书和备用证书共用)
(
echo authorityKeyIdentifier=keyid,issuer
echo basicConstraints=CA:FALSE
echo keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
echo subjectAltName = @alt_names
echo.
echo [alt_names]
echo IP.1 = %SERVER_IP%
echo IP.2 = 127.0.0.1
echo DNS.1 = stock.internal
echo DNS.2 = localhost
) > server_ext.cnf

echo.
echo ==========================================
echo Step 2: 生成主服务器证书 (Cert A - 当前使用)
echo ==========================================

REM 生成主服务器私钥
openssl genrsa -out server_a.key 2048
echo ✓ 主证书私钥: server_a.key

REM 创建 CSR 并签发
openssl req -new -key server_a.key -out server_a.csr -subj "/C=CN/ST=Private/L=Private/O=Stock Analysis/CN=%SERVER_IP%"
openssl x509 -req -in server_a.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server_a.crt -days %SERVER_DAYS% -sha256 -extfile server_ext.cnf
echo ✓ 主证书: server_a.crt

REM 计算主证书指纹
for /f "tokens=2 delims==" %%a in ('openssl x509 -in server_a.crt -noout -fingerprint -sha256') do (
    set FP_A=%%a
)
set FP_A=!FP_A::=!
echo ✓ 主证书指纹: !FP_A!

echo.
echo ==========================================
echo Step 3: 生成备用证书 (Cert B - 冷备)
echo ==========================================

REM 生成备用服务器私钥
openssl genrsa -out server_b.key 2048
echo ✓ 备用证书私钥: server_b.key

REM 创建 CSR 并签发
openssl req -new -key server_b.key -out server_b.csr -subj "/C=CN/ST=Private/L=Private/O=Stock Analysis/CN=%SERVER_IP%"
openssl x509 -req -in server_b.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server_b.crt -days %SERVER_DAYS% -sha256 -extfile server_ext.cnf
echo ✓ 备用证书: server_b.crt

REM 计算备用证书指纹
for /f "tokens=2 delims==" %%a in ('openssl x509 -in server_b.crt -noout -fingerprint -sha256') do (
    set FP_B=%%a
)
set FP_B=!FP_B::=!
echo ✓ 备用证书指纹: !FP_B!

echo.
echo ==========================================
echo Step 4: 创建部署文件
echo ==========================================

REM 创建当前使用的证书 (软链接/复制)
copy server_a.key server.key >nul
copy server_a.crt server.crt >nul
echo ✓ 当前部署证书: server.key, server.crt

REM 保存指纹到文件
(
echo # 幽灵协议 - 证书指纹
echo # 请将两个指纹都配置到 ssl-pinning.js
echo.
echo PRIMARY_CERT_FINGERPRINT=!FP_A!
echo BACKUP_CERT_FINGERPRINT=!FP_B!
) > fingerprints.txt
echo ✓ 指纹已保存: fingerprints.txt

echo.
echo ==========================================
echo 🔐 生成完成！
echo ==========================================
echo.
echo 📁 文件清单:
echo    server.key/crt   - 当前部署 (Cert A)
echo    server_a.key/crt - 主证书 (当前使用)
echo    server_b.key/crt - 备用证书 (冷备，私钥离线存储)
echo    fingerprints.txt - 双指纹配置
echo.
echo 🔴 重要：双指纹策略
echo    主证书指纹: !FP_A!
echo    备用指纹:   !FP_B!
echo.
echo ⚠️  安全提醒:
echo    1. server_b.key (备用私钥) 必须离线冷存储 (U盘/保险箱)
echo    2. 两个指纹都要配置到客户端 ssl-pinning.js
echo    3. 如果主证书泄露，换上备用证书即可，无需更新客户端
echo.

pause
