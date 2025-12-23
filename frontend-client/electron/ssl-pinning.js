/**
 * SSL Pinning 模块
 * 幽灵协议 - 客户端证书锁定
 * 
 * 功能:
 * - 验证服务器证书指纹
 * - 防止中间人攻击
 * - 支持证书轮换 (多指纹)
 */
const { session } = require('electron');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

/**
 * SSL Pinning 配置
 * ⚠️ 部署前请修改以下配置
 * 
 * 🔴 重要：双指纹策略
 * 为防止证书过期或紧急吊销导致客户端"变砖"，
 * 必须同时配置主证书和备用证书的指纹。
 * 备用证书私钥应离线冷存储。
 */
const SSL_CONFIG = {
  // 是否启用 (环境变量控制)
  enabled: process.env.SSL_PINNING !== 'false',
  
  // 服务器地址列表
  pinnedHosts: [
    'YOUR_SERVER_IP',  // ⚠️ 替换为实际服务器IP
    '127.0.0.1',
    'localhost'
  ],
  
  // 证书指纹 (SHA256, 无冒号, 小写)
  // 生成: openssl x509 -in server.crt -noout -fingerprint -sha256
  // 
  // 🔴 双指纹策略：同时配置主证书和备用证书指纹
  // - 主证书 (Cert A): 当前线上使用
  // - 备用证书 (Cert B): 提前生成，私钥离线存储
  // 如果 Cert A 泄露或过期，服务端换上 Cert B，客户端无需更新
  pinnedFingerprints: [
    'PRIMARY_CERT_FINGERPRINT',   // ⚠️ 主证书指纹 (当前使用)
    'BACKUP_CERT_FINGERPRINT',    // ⚠️ 备用证书指纹 (冷备)
  ],
  
  // 开发模式使用本地证书
  useLocalCert: process.env.NODE_ENV === 'development',
  localCertPath: path.join(__dirname, '..', 'assets', 'certs', 'server.crt')
};

/**
 * 计算证书 SHA256 指纹
 */
function calculateFingerprint(certData) {
  let derData = certData;
  
  // PEM 转 DER
  if (typeof certData === 'string' || certData.toString().includes('BEGIN CERTIFICATE')) {
    const pem = certData.toString();
    const b64 = pem
      .replace(/-----BEGIN CERTIFICATE-----/g, '')
      .replace(/-----END CERTIFICATE-----/g, '')
      .replace(/\s/g, '');
    derData = Buffer.from(b64, 'base64');
  }
  
  return crypto.createHash('sha256').update(derData).digest('hex');
}

/**
 * 加载本地证书指纹
 */
function loadLocalCertFingerprint() {
  try {
    if (fs.existsSync(SSL_CONFIG.localCertPath)) {
      const cert = fs.readFileSync(SSL_CONFIG.localCertPath);
      return calculateFingerprint(cert);
    }
  } catch (e) {
    console.error('加载本地证书失败:', e);
  }
  return null;
}

/**
 * 初始化 SSL Pinning
 * 在 app.whenReady() 中调用
 */
function initSSLPinning() {
  if (!SSL_CONFIG.enabled) {
    console.log('⚠️  SSL Pinning 已禁用');
    return;
  }
  
  console.log('🔐 初始化 SSL Pinning...');
  
  // 加载本地证书指纹
  if (SSL_CONFIG.useLocalCert) {
    const localFp = loadLocalCertFingerprint();
    if (localFp && !SSL_CONFIG.pinnedFingerprints.includes(localFp)) {
      SSL_CONFIG.pinnedFingerprints.push(localFp);
      console.log(`   添加本地证书: ${localFp.substring(0, 16)}...`);
    }
  }
  
  // 设置证书验证
  session.defaultSession.setCertificateVerifyProc((request, callback) => {
    const { hostname, certificate, verificationResult } = request;
    
    // 检查是否是目标服务器
    if (SSL_CONFIG.pinnedHosts.includes(hostname)) {
      const serverFp = calculateFingerprint(certificate.data);
      
      const isPinned = SSL_CONFIG.pinnedFingerprints.some(
        fp => fp.toLowerCase() === serverFp.toLowerCase()
      );
      
      if (isPinned) {
        console.log(`✅ SSL Pinning 通过: ${hostname}`);
        callback(0);  // 成功
      } else {
        console.error(`❌ SSL Pinning 失败: ${hostname}`);
        console.error(`   期望: ${SSL_CONFIG.pinnedFingerprints[0]?.substring(0, 16)}...`);
        console.error(`   实际: ${serverFp.substring(0, 16)}...`);
        callback(-2); // 失败 - 可能是中间人攻击
      }
    } else {
      // 其他域名使用默认验证
      callback(verificationResult);
    }
  });
  
  console.log(`✅ SSL Pinning 已启用`);
  console.log(`   锁定: ${SSL_CONFIG.pinnedHosts.join(', ')}`);
}

/**
 * 添加新指纹 (证书轮换)
 */
function addFingerprint(fingerprint) {
  if (!SSL_CONFIG.pinnedFingerprints.includes(fingerprint)) {
    SSL_CONFIG.pinnedFingerprints.push(fingerprint);
    console.log(`📝 添加指纹: ${fingerprint.substring(0, 16)}...`);
  }
}

/**
 * 移除旧指纹
 */
function removeFingerprint(fingerprint) {
  const idx = SSL_CONFIG.pinnedFingerprints.indexOf(fingerprint);
  if (idx > -1) {
    SSL_CONFIG.pinnedFingerprints.splice(idx, 1);
    console.log(`🗑️  移除指纹: ${fingerprint.substring(0, 16)}...`);
  }
}

module.exports = {
  initSSLPinning,
  addFingerprint,
  removeFingerprint,
  calculateFingerprint,
  SSL_CONFIG
};
