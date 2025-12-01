/**
 * API基础配置
 * v0.4.0: 全部走加密通道
 * 
 * 所有API请求通过 /api/secure 加密网关发送
 * 请求体和响应体都使用AES-256-GCM加密
 */
import secureApi from './secureApi';

/**
 * 加密API客户端
 * 提供与axios兼容的接口，但所有请求都走加密通道
 */
const apiClient = {
  /**
   * GET请求
   * @param {string} url - API路径（如 /api/dates）
   * @param {object} config - 配置（可选，提取params）
   */
  async get(url, config = {}) {
    // 从URL中提取查询参数
    const [path, queryString] = url.split('?');
    let params = config.params || {};
    
    // 解析URL中的查询参数
    if (queryString) {
      const urlParams = new URLSearchParams(queryString);
      urlParams.forEach((value, key) => {
        params[key] = value;
      });
    }
    
    return secureApi.get(path, params);
  },

  /**
   * POST请求
   */
  async post(url, data = null, config = {}) {
    const [path] = url.split('?');
    return secureApi.post(path, data, config.params || {});
  },

  /**
   * PUT请求
   */
  async put(url, data = null, config = {}) {
    const [path] = url.split('?');
    return secureApi.put(path, data, config.params || {});
  },

  /**
   * DELETE请求
   */
  async delete(url, config = {}) {
    const [path] = url.split('?');
    return secureApi.delete(path, config.params || {});
  }
};

export default apiClient;

