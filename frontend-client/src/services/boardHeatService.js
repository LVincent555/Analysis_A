/**
 * 板块热度 API 服务
 * 封装外部板块多对多系统的所有 API 调用
 */
import apiClient from './api';

const normalizeTradeDate = (val) => {
  if (!val) return val;
  if (typeof val !== 'string') return val;
  const s = val.trim();
  if (/^\d{8}$/.test(s)) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  }
  return s;
};

const boardHeatService = {
  /**
   * 获取板块热度榜单
   * @param {Object} params - 查询参数
   * @param {string} params.trade_date - 交易日期 YYYY-MM-DD
   * @param {string} params.board_type - 板块类型: industry/concept/null
   * @param {number} params.limit - 返回数量限制
   * @param {number} params.offset - 分页偏移
   */
  async getRanking(params = {}) {
    const { trade_date, board_type, limit = 50, offset = 0, max_stock_count } = params;
    const queryParams = { trade_date: normalizeTradeDate(trade_date), board_type, limit, offset };
    if (max_stock_count !== null && max_stock_count !== undefined && max_stock_count !== '') {
      queryParams.max_stock_count = max_stock_count;
    }
    const result = await apiClient.get('/api/board-heat/ranking', {
      params: queryParams
    });
    return result;
  },

  /**
   * 获取个股板块信号
   * @param {string} stockCode - 股票代码
   * @param {string} tradeDate - 交易日期
   */
  async getStockSignal(stockCode, tradeDate = null) {
    const result = await apiClient.get(`/api/board-heat/stock/${stockCode}`, {
      params: { trade_date: normalizeTradeDate(tradeDate) }
    });
    return result;
  },

  /**
   * 批量获取个股板块信号
   * @param {string[]} stockCodes - 股票代码列表
   * @param {string} tradeDate - 交易日期
   */
  async getStockSignalsBatch(stockCodes, tradeDate = null) {
    let minPrice;
    if (arguments.length >= 3) {
      minPrice = arguments[2];
    }
    const queryParams = { trade_date: normalizeTradeDate(tradeDate) };
    if (minPrice !== null && minPrice !== undefined && minPrice !== '') {
      queryParams.min_price = minPrice;
    }
    const result = await apiClient.post('/api/board-heat/stocks/batch', stockCodes, {
      params: queryParams
    });
    return result;
  },

  /**
   * 获取板块详情
   * @param {number} boardId - 板块ID
   * @param {string} tradeDate - 交易日期
   */
  async getBoardDetail(boardId, tradeDate = null) {
    let minPrice;
    let limit;
    let offset;
    if (arguments.length >= 3) minPrice = arguments[2];
    if (arguments.length >= 4) limit = arguments[3];
    if (arguments.length >= 5) offset = arguments[4];

    const queryParams = { trade_date: normalizeTradeDate(tradeDate) };
    if (minPrice !== null && minPrice !== undefined && minPrice !== '') {
      queryParams.min_price = minPrice;
    }
    if (limit !== null && limit !== undefined && limit !== '') {
      queryParams.limit = limit;
    }
    if (offset !== null && offset !== undefined && offset !== '') {
      queryParams.offset = offset;
    }
    const result = await apiClient.get(`/api/board-heat/board/${boardId}`, {
      params: queryParams
    });
    return result;
  },

  /**
   * 获取可用日期列表
   */
  async getAvailableDates() {
    const result = await apiClient.get('/api/board-heat/dates');
    return result;
  },

  /**
   * 【V4.0】获取全市场热力云图数据
   */
  async getMarketTreemap(tradeDate = null, minSize = 0) {
    let maxStockCount;
    if (arguments.length >= 3) {
      maxStockCount = arguments[2];
    }
    const queryParams = { trade_date: normalizeTradeDate(tradeDate), min_size: minSize };
    if (maxStockCount !== null && maxStockCount !== undefined && maxStockCount !== '') {
      queryParams.max_stock_count = maxStockCount;
    }
    const result = await apiClient.get('/api/board-heat/market/treemap', {
      params: queryParams
    });
    return result;
  },

  /**
   * 【V4.0】获取市场信号体检仪数据
   */
  async getMarketSignalBar(tradeDate = null) {
    const result = await apiClient.get('/api/board-heat/market/signal-bar', {
      params: { trade_date: normalizeTradeDate(tradeDate) }
    });
    return result;
  },

  /**
   * 【V4.0】获取板块风格罗盘数据
   */
  async getSectorMatrix(tradeDate = null, limit = 100) {
    const result = await apiClient.get('/api/board-heat/market/sector-matrix', {
      params: { trade_date: normalizeTradeDate(tradeDate), limit }
    });
    return result;
  },

  /**
   * 【V4.0】获取双S级共振猎手
   */
  async getMiningResonance(tradeDate = null, limit = 50) {
    const result = await apiClient.get('/api/board-heat/mining/resonance', {
      params: { trade_date: normalizeTradeDate(tradeDate), limit }
    });
    return result;
  },

  /**
   * 【V4.0】获取隐形冠军挖掘机
   */
  async getMiningHiddenGems(tradeDate = null, minScore = 85, minRank = 500, limit = 50) {
    const result = await apiClient.get('/api/board-heat/mining/hidden-gems', {
      params: { trade_date: normalizeTradeDate(tradeDate), min_score: minScore, min_rank: minRank, limit }
    });
    return result;
  },

  /**
   * 【V4.0】获取个股DNA诊断
   */
  async getStockDNA(stockCode, tradeDate = null) {
    let minPrice;
    if (arguments.length >= 3) {
      minPrice = arguments[2];
    }
    const queryParams = { trade_date: normalizeTradeDate(tradeDate) };
    if (minPrice !== null && minPrice !== undefined && minPrice !== '') {
      queryParams.min_price = minPrice;
    }
    const result = await apiClient.get(`/api/board-heat/stock/${stockCode}/dna`, {
      params: queryParams
    });
    return result;
  },

  /**
   * 【V4.0】获取板块历史走势
   */
  async getBoardHistory(boardId, days = 30, endDate = null) {
    const result = await apiClient.get(`/api/board-heat/board/${boardId}/history`, {
      params: { days, end_date: normalizeTradeDate(endDate) }
    });
    return result;
  },

  /**
   * 辅助方法：根据信号等级获取样式类
   */
  getSignalStyleClass(level) {
    const styles = {
      S: 'bg-gradient-to-r from-orange-500 to-pink-500 text-white',
      A: 'bg-gradient-to-r from-purple-500 to-pink-500 text-white',
      B: 'bg-gray-200 text-gray-600',
      NONE: 'hidden'
    };
    return styles[level] || styles.NONE;
  },

  /**
   * 辅助方法：格式化热度百分比
   */
  formatHeatPct(pct) {
    if (pct === null || pct === undefined) return '-';
    return `${(pct * 100).toFixed(1)}%`;
  }
};

export default boardHeatService;
