/**
 * 认证服务
 * 处理登录、登出、Token管理
 */
import axios from 'axios';
import { API_BASE_URL } from '../constants';
import AESCrypto, { deriveKeyFromPassword } from '../utils/crypto';

// Token存储键名
const TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const SESSION_KEY = 'session_key';
const USER_KEY = 'user_info';

/**
 * 认证服务类
 */
class AuthService {
  constructor() {
    this.token = localStorage.getItem(TOKEN_KEY);
    this.refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    this.sessionKey = localStorage.getItem(SESSION_KEY);
    this.user = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
  }

  /**
   * 用户登录
   */
  async login(username, password, deviceId = null) {
    // 生成设备ID
    if (!deviceId) {
      deviceId = this.getDeviceId();
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
        username,
        password,
        device_id: deviceId,
        device_name: this.getDeviceName()
      });

      const { token, refresh_token, session_key: encryptedSessionKey, user } = response.data;

      // 用密码派生密钥解密会话密钥（node-forge，同步）
      let decryptedSessionKey = null;
      try {
        const passwordKey = deriveKeyFromPassword(password);
        const passwordCrypto = new AESCrypto(passwordKey);
        const decryptedData = passwordCrypto.decrypt(encryptedSessionKey);
        decryptedSessionKey = decryptedData.key || decryptedData;
        console.log('会话密钥解密成功');
      } catch (e) {
        console.error('会话密钥解密失败:', e);
        // 降级：直接使用（开发模式）
        decryptedSessionKey = encryptedSessionKey;
      }

      // 存储认证信息
      this.token = token;
      this.refreshToken = refresh_token;
      this.sessionKey = decryptedSessionKey;
      this.user = user;

      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
      localStorage.setItem(SESSION_KEY, decryptedSessionKey);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      return {
        success: true,
        user
      };
    } catch (error) {
      const message = error.response?.data?.detail || '登录失败，请检查网络连接';
      return {
        success: false,
        message
      };
    }
  }

  /**
   * 用户注册
   */
  async register(username, password) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
        username,
        password
      });

      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      const message = error.response?.data?.detail || '注册失败';
      return {
        success: false,
        message
      };
    }
  }

  /**
   * 刷新Token
   */
  async refreshAccessToken() {
    if (!this.refreshToken) {
      return false;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
        refresh_token: this.refreshToken
      });

      const { token } = response.data;
      this.token = token;
      localStorage.setItem(TOKEN_KEY, token);

      return true;
    } catch (error) {
      console.error('刷新Token失败:', error);
      this.logout();
      return false;
    }
  }

  /**
   * 登出
   */
  async logout() {
    try {
      if (this.token) {
        await axios.post(
          `${API_BASE_URL}/api/auth/logout`,
          {},
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
      }
    } catch (error) {
      console.error('登出请求失败:', error);
    }

    // 清除本地存储
    this.token = null;
    this.refreshToken = null;
    this.sessionKey = null;
    this.user = null;

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(USER_KEY);
  }

  /**
   * 检查是否已登录
   */
  isLoggedIn() {
    return !!this.token;
  }

  /**
   * 获取当前用户
   */
  getUser() {
    return this.user;
  }

  /**
   * 获取Token
   */
  getToken() {
    return this.token;
  }

  /**
   * 获取会话密钥
   */
  getSessionKey() {
    return this.sessionKey;
  }

  /**
   * 获取设备ID
   */
  getDeviceId() {
    let deviceId = localStorage.getItem('device_id');
    if (!deviceId) {
      deviceId = 'device_' + Math.random().toString(36).substring(2) + Date.now().toString(36);
      localStorage.setItem('device_id', deviceId);
    }
    return deviceId;
  }

  /**
   * 获取设备名称
   */
  getDeviceName() {
    // 尝试从Electron获取
    if (window.electronAPI && window.electronAPI.platform) {
      return `${window.electronAPI.platform} Client`;
    }
    return navigator.userAgent.substring(0, 50);
  }

  /**
   * 获取带认证头的axios配置
   */
  getAuthHeaders() {
    if (!this.token) {
      return {};
    }
    return {
      Authorization: `Bearer ${this.token}`
    };
  }
}

// 导出单例
const authService = new AuthService();
export default authService;

// 便捷导出
export const getToken = () => authService.getToken();
export const getSessionKey = () => authService.getSessionKey();
export const isLoggedIn = () => authService.isLoggedIn();
export const getUser = () => authService.getUser();
