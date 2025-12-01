/**
 * 加密API服务
 * 所有业务请求通过加密通道发送
 */
import axios from 'axios';
import { API_BASE_URL } from '../constants';
import authService from './authService';
import AESCrypto, { generateNonce } from '../utils/crypto';

/**
 * 加密API服务类
 */
class SecureApiService {
  constructor() {
    this.crypto = null;
    this.initialized = false;
    this.sessionExpiredTriggered = false; // 防止重复触发会话过期事件
  }

  /**
   * 初始化加密器
   * 登录成功后调用
   */
  initCrypto(sessionKeyBase64) {
    try {
      this.crypto = new AESCrypto(sessionKeyBase64);
      this.initialized = true;
      this.sessionExpiredTriggered = false; // 登录成功，重置会话过期标志
      console.log('加密器初始化成功');
    } catch (error) {
      console.error('加密器初始化失败:', error);
      this.initialized = false;
    }
  }

  /**
   * 检查是否已初始化
   */
  isReady() {
    return this.initialized && this.crypto !== null;
  }

  /**
   * 发送加密请求
   */
  async request({ path, method = 'GET', params = {}, body = null, retried = false }) {
    // 检查登录状态
    const token = authService.getToken();
    if (!token) {
      throw new Error('未登录');
    }

    // 如果加密器未初始化，尝试从存储恢复
    if (!this.isReady()) {
      const sessionKey = authService.getSessionKey();
      if (sessionKey) {
        this.initCrypto(sessionKey);
      } else {
        throw new Error('会话密钥不存在，请重新登录');
      }
    }

    // 构造请求对象
    const requestData = {
      path,
      method: method.toUpperCase(),
      params,
      body,
      timestamp: Date.now(),
      nonce: generateNonce()
    };

    try {
      // 加密请求
      const encryptedData = this.crypto.encrypt(requestData);

      // 发送到加密网关
      const response = await axios.post(
        `${API_BASE_URL}/api/secure`,
        { data: encryptedData },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 30000
        }
      );

      // 解密响应
      const decryptedResponse = this.crypto.decrypt(response.data.data);
      return decryptedResponse;

    } catch (error) {
      // Token过期处理（只重试一次，避免无限循环）
      if (error.response?.status === 401 && !retried) {
        console.log('Token过期，尝试刷新...');
        const refreshed = await authService.refreshAccessToken();
        if (refreshed) {
          // 重试请求（标记已重试）
          return this.request({ path, method, params, body, retried: true });
        } else {
          // 触发会话过期事件（只触发一次）
          if (!this.sessionExpiredTriggered) {
            this.sessionExpiredTriggered = true;
            console.log('触发会话过期事件');
            // 同时使用 alert 和事件，确保用户能看到提示
            alert('会话已过期，请重新登录');
            window.dispatchEvent(new CustomEvent('session-expired'));
          }
          throw new Error('会话已过期，请重新登录');
        }
      }
      
      // 401错误但已重试过，直接提示
      if (error.response?.status === 401 && retried) {
        if (!this.sessionExpiredTriggered) {
          this.sessionExpiredTriggered = true;
          alert('会话已过期，请重新登录');
          window.dispatchEvent(new CustomEvent('session-expired'));
        }
        throw new Error('会话已过期，请重新登录');
      }

      // 其他错误
      const message = error.response?.data?.detail || error.message || '请求失败';
      throw new Error(message);
    }
  }

  /**
   * GET请求
   */
  get(path, params = {}) {
    return this.request({ path, method: 'GET', params });
  }

  /**
   * POST请求
   */
  post(path, body = null, params = {}) {
    return this.request({ path, method: 'POST', params, body });
  }

  /**
   * PUT请求
   */
  put(path, body = null, params = {}) {
    return this.request({ path, method: 'PUT', params, body });
  }

  /**
   * DELETE请求
   */
  delete(path, params = {}) {
    return this.request({ path, method: 'DELETE', params });
  }

  /**
   * 重置加密器（登出时调用）
   */
  reset() {
    this.crypto = null;
    this.initialized = false;
    this.sessionExpiredTriggered = false; // 重置会话过期标志
  }
}

// 导出单例
const secureApi = new SecureApiService();
export default secureApi;
