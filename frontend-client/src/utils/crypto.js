/**
 * AES-256-GCM 加密工具
 * 使用 node-forge（支持HTTP环境，无需HTTPS）
 * 与后端 Python cryptography 库完全兼容
 */
import forge from 'node-forge';

// PBKDF2 参数（必须与后端一致）
const PBKDF2_SALT = 'stock-analysis-salt';
const PBKDF2_ITERATIONS = 10000;

/**
 * 从密码派生密钥
 * 必须与后端 Python 的 PBKDF2 参数完全一致
 * @param {string} password - 密码
 * @param {string} salt - 盐值
 * @returns {string} Base64编码的密钥
 */
export function deriveKeyFromPassword(password, salt = PBKDF2_SALT) {
  // 使用 forge 的 PBKDF2
  const key = forge.pkcs5.pbkdf2(
    password,
    salt,
    PBKDF2_ITERATIONS,
    32, // 32 bytes = 256 bits
    forge.md.sha256.create()
  );
  // 转为 Base64
  return forge.util.encode64(key);
}

/**
 * AES-256-GCM 加密类
 * 使用 node-forge
 */
class AESCrypto {
  constructor(keyBase64) {
    // 将 Base64 密钥解码为二进制字符串
    this.key = forge.util.decode64(keyBase64);
  }

  /**
   * 加密数据
   * @param {Object|string} data - 要加密的数据
   * @returns {string} Base64编码的加密字符串（nonce + ciphertext + tag）
   */
  encrypt(data) {
    // 转换为JSON字符串
    const plaintext = typeof data === 'string' ? data : JSON.stringify(data);
    
    // 生成随机 nonce（12字节，GCM推荐）
    const nonce = forge.random.getBytesSync(12);
    
    // 创建加密器
    const cipher = forge.cipher.createCipher('AES-GCM', this.key);
    cipher.start({ iv: nonce });
    cipher.update(forge.util.createBuffer(plaintext, 'utf8'));
    cipher.finish();
    
    // 获取密文和认证标签
    const ciphertext = cipher.output.getBytes();
    const tag = cipher.mode.tag.getBytes();
    
    // 组合：nonce(12) + ciphertext + tag(16)
    const combined = nonce + ciphertext + tag;
    
    return forge.util.encode64(combined);
  }

  /**
   * 解密数据
   * @param {string} encryptedBase64 - Base64编码的加密字符串
   * @returns {Object|string} 解密后的数据
   */
  decrypt(encryptedBase64) {
    try {
      // Base64 解码
      const combined = forge.util.decode64(encryptedBase64);
      
      // 分离 nonce(12字节)、ciphertext、tag(16字节)
      const nonce = combined.slice(0, 12);
      const tag = combined.slice(-16);
      const ciphertext = combined.slice(12, -16);
      
      // 创建解密器
      const decipher = forge.cipher.createDecipher('AES-GCM', this.key);
      decipher.start({
        iv: nonce,
        tag: forge.util.createBuffer(tag)
      });
      decipher.update(forge.util.createBuffer(ciphertext));
      
      // 完成解密并验证 tag
      const pass = decipher.finish();
      
      if (!pass) {
        throw new Error('认证失败：Tag 不匹配或数据被篡改');
      }
      
      // 获取明文
      const plaintext = decipher.output.toString('utf8');
      
      // 尝试解析为 JSON
      try {
        return JSON.parse(plaintext);
      } catch {
        return plaintext;
      }
    } catch (error) {
      console.error('解密失败:', error);
      throw new Error('解密失败: ' + error.message);
    }
  }
}

/**
 * 生成随机字符串（用于nonce）
 */
export function generateNonce() {
  return forge.util.bytesToHex(forge.random.getBytesSync(16));
}

export default AESCrypto;
