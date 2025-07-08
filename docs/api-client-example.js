/**
 * API 客户端示例实现
 * 提供完整的前端API调用封装
 * 支持认证、错误处理、请求重试等功能
 */

// ============= 配置常量 =============

const API_CONFIG = {
  BASE_URL: "http://localhost:8000/api/v1",
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
  TOKEN_STORAGE_KEY: "access_token",
  REFRESH_TOKEN_STORAGE_KEY: "refresh_token",
};

const ERROR_CODES = {
  UNAUTHORIZED: "UNAUTHORIZED",
  TOKEN_EXPIRED: "TOKEN_EXPIRED",
  FORBIDDEN: "FORBIDDEN",
  NOT_FOUND: "NOT_FOUND",
  VALIDATION_ERROR: "VALIDATION_ERROR",
  RATE_LIMIT_EXCEEDED: "RATE_LIMIT_EXCEEDED",
  NETWORK_ERROR: "NETWORK_ERROR",
};

// ============= 工具函数 =============

/**
 * 延迟函数
 */
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * 生成请求ID
 */
const generateRequestId = () => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

/**
 * 存储管理
 */
const storage = {
  get: (key) => {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.warn("localStorage不可用:", error);
      return null;
    }
  },

  set: (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      console.warn("localStorage不可用:", error);
    }
  },

  remove: (key) => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn("localStorage不可用:", error);
    }
  },
};

// ============= API 客户端类 =============

class ApiClient {
  constructor(config = {}) {
    this.config = { ...API_CONFIG, ...config };
    this.requestInterceptors = [];
    this.responseInterceptors = [];
    this.isRefreshing = false;
    this.failedQueue = [];
  }

  // ============= 拦截器管理 =============

  /**
   * 添加请求拦截器
   */
  addRequestInterceptor(interceptor) {
    this.requestInterceptors.push(interceptor);
  }

  /**
   * 添加响应拦截器
   */
  addResponseInterceptor(interceptor) {
    this.responseInterceptors.push(interceptor);
  }

  // ============= 认证相关 =============

  /**
   * 获取访问令牌
   */
  getAccessToken() {
    return storage.get(this.config.TOKEN_STORAGE_KEY);
  }

  /**
   * 获取刷新令牌
   */
  getRefreshToken() {
    return storage.get(this.config.REFRESH_TOKEN_STORAGE_KEY);
  }

  /**
   * 设置令牌
   */
  setTokens(accessToken, refreshToken) {
    storage.set(this.config.TOKEN_STORAGE_KEY, accessToken);
    if (refreshToken) {
      storage.set(this.config.REFRESH_TOKEN_STORAGE_KEY, refreshToken);
    }
  }

  /**
   * 清除令牌
   */
  clearTokens() {
    storage.remove(this.config.TOKEN_STORAGE_KEY);
    storage.remove(this.config.REFRESH_TOKEN_STORAGE_KEY);
  }

  /**
   * 获取认证头
   */
  getAuthHeaders() {
    const token = this.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /**
   * 刷新访问令牌
   */
  async refreshAccessToken() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error("没有刷新令牌");
    }

    try {
      const response = await fetch(`${this.config.BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      const result = await response.json();

      if (result.success) {
        this.setTokens(result.data.access_token, result.data.refresh_token);
        return result.data.access_token;
      } else {
        throw new Error(result.error?.message || "刷新令牌失败");
      }
    } catch (error) {
      this.clearTokens();
      throw error;
    }
  }

  /**
   * 处理认证错误
   */
  handleAuthError() {
    this.clearTokens();
    // 触发登录页面跳转事件
    window.dispatchEvent(new CustomEvent("auth:logout"));
  }

  // ============= 请求处理 =============

  /**
   * 处理令牌刷新队列
   */
  async processQueue(error, token = null) {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve(token);
      }
    });

    this.failedQueue = [];
  }

  /**
   * 构建请求配置
   */
  buildRequestConfig(endpoint, options = {}) {
    const url = endpoint.startsWith("http")
      ? endpoint
      : `${this.config.BASE_URL}${endpoint}`;

    const config = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...this.getAuthHeaders(),
        ...options.headers,
      },
      ...options,
    };

    // 添加请求ID
    config.headers["X-Request-ID"] = generateRequestId();

    // 处理查询参数
    if (options.params && config.method === "GET") {
      const searchParams = new URLSearchParams();
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          if (Array.isArray(value)) {
            value.forEach((v) => searchParams.append(key, v));
          } else {
            searchParams.append(key, value);
          }
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        const separator = url.includes("?") ? "&" : "?";
        return { url: `${url}${separator}${queryString}`, config };
      }
    }

    return { url, config };
  }

  /**
   * 执行请求拦截器
   */
  async executeRequestInterceptors(config) {
    let modifiedConfig = config;

    for (const interceptor of this.requestInterceptors) {
      try {
        modifiedConfig = await interceptor(modifiedConfig);
      } catch (error) {
        console.error("请求拦截器错误:", error);
      }
    }

    return modifiedConfig;
  }

  /**
   * 执行响应拦截器
   */
  async executeResponseInterceptors(response) {
    let modifiedResponse = response;

    for (const interceptor of this.responseInterceptors) {
      try {
        modifiedResponse = await interceptor(modifiedResponse);
      } catch (error) {
        console.error("响应拦截器错误:", error);
      }
    }

    return modifiedResponse;
  }

  /**
   * 发送HTTP请求
   */
  async makeRequest(endpoint, options = {}, retryCount = 0) {
    try {
      const { url, config } = this.buildRequestConfig(endpoint, options);

      // 执行请求拦截器
      const finalConfig = await this.executeRequestInterceptors(config);

      // 设置超时
      const controller = new AbortController();
      const timeoutId = setTimeout(
        () => controller.abort(),
        this.config.TIMEOUT
      );
      finalConfig.signal = controller.signal;

      // 发送请求
      const response = await fetch(url, finalConfig);
      clearTimeout(timeoutId);

      // 解析响应
      let result;
      const contentType = response.headers.get("content-type");

      if (contentType && contentType.includes("application/json")) {
        result = await response.json();
      } else {
        result = {
          success: response.ok,
          data: await response.text(),
          message: response.ok ? "Success" : "Request failed",
        };
      }

      // 执行响应拦截器
      const finalResult = await this.executeResponseInterceptors(result);

      // 处理认证错误
      if (response.status === 401) {
        return this.handleUnauthorized(endpoint, options, finalResult);
      }

      // 处理其他HTTP错误
      if (!response.ok && !finalResult.success) {
        throw new ApiError(
          finalResult.error?.code || "HTTP_ERROR",
          finalResult.error?.message || `HTTP ${response.status}`,
          response.status,
          finalResult
        );
      }

      return finalResult;
    } catch (error) {
      // 处理网络错误和超时
      if (error.name === "AbortError") {
        throw new ApiError("TIMEOUT", "请求超时", 408);
      }

      if (error instanceof TypeError && error.message.includes("fetch")) {
        // 网络错误，尝试重试
        if (retryCount < this.config.RETRY_ATTEMPTS) {
          await delay(this.config.RETRY_DELAY * Math.pow(2, retryCount));
          return this.makeRequest(endpoint, options, retryCount + 1);
        }
        throw new ApiError("NETWORK_ERROR", "网络连接失败", 0);
      }

      // 重新抛出其他错误
      throw error;
    }
  }

  /**
   * 处理401未授权错误
   */
  async handleUnauthorized(originalEndpoint, originalOptions, result) {
    const errorCode = result.error?.code;

    // 如果是令牌过期，尝试刷新
    if (errorCode === "TOKEN_EXPIRED" || errorCode === "UNAUTHORIZED") {
      if (this.isRefreshing) {
        // 如果正在刷新，将请求加入队列
        return new Promise((resolve, reject) => {
          this.failedQueue.push({ resolve, reject });
        }).then(() => {
          return this.makeRequest(originalEndpoint, originalOptions);
        });
      }

      this.isRefreshing = true;

      try {
        await this.refreshAccessToken();
        this.isRefreshing = false;
        await this.processQueue(null);

        // 重试原始请求
        return this.makeRequest(originalEndpoint, originalOptions);
      } catch (refreshError) {
        this.isRefreshing = false;
        await this.processQueue(refreshError);
        this.handleAuthError();
        throw new ApiError("AUTH_FAILED", "认证失败", 401, result);
      }
    }

    // 其他认证错误
    this.handleAuthError();
    throw new ApiError(
      "UNAUTHORIZED",
      result.error?.message || "未授权访问",
      401,
      result
    );
  }

  // ============= HTTP 方法 =============

  /**
   * GET 请求
   */
  async get(endpoint, params = {}, options = {}) {
    return this.makeRequest(endpoint, {
      method: "GET",
      params,
      ...options,
    });
  }

  /**
   * POST 请求
   */
  async post(endpoint, data = {}, options = {}) {
    return this.makeRequest(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
      ...options,
    });
  }

  /**
   * PUT 请求
   */
  async put(endpoint, data = {}, options = {}) {
    return this.makeRequest(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
      ...options,
    });
  }

  /**
   * PATCH 请求
   */
  async patch(endpoint, data = {}, options = {}) {
    return this.makeRequest(endpoint, {
      method: "PATCH",
      body: JSON.stringify(data),
      ...options,
    });
  }

  /**
   * DELETE 请求
   */
  async delete(endpoint, options = {}) {
    return this.makeRequest(endpoint, {
      method: "DELETE",
      ...options,
    });
  }

  /**
   * 文件上传
   */
  async upload(endpoint, file, metadata = {}, onProgress = null) {
    const formData = new FormData();
    formData.append("file", file);

    // 添加元数据
    Object.entries(metadata).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        formData.append(key, value);
      }
    });

    const options = {
      method: "POST",
      body: formData,
      headers: {
        // 不设置 Content-Type，让浏览器自动设置
        ...this.getAuthHeaders(),
      },
    };

    // 如果提供了进度回调，使用 XMLHttpRequest
    if (onProgress) {
      return this.uploadWithProgress(endpoint, formData, options, onProgress);
    }

    return this.makeRequest(endpoint, options);
  }

  /**
   * 带进度的文件上传
   */
  uploadWithProgress(endpoint, formData, options, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const url = `${this.config.BASE_URL}${endpoint}`;

      // 设置上传进度监听
      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
          const progress = {
            loaded: event.loaded,
            total: event.total,
            percentage: Math.round((event.loaded / event.total) * 100),
          };
          onProgress(progress);
        }
      });

      // 设置完成监听
      xhr.addEventListener("load", () => {
        try {
          const result = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(result);
          } else {
            reject(
              new ApiError(
                result.error?.code || "UPLOAD_ERROR",
                result.error?.message || "上传失败",
                xhr.status,
                result
              )
            );
          }
        } catch (error) {
          reject(new ApiError("PARSE_ERROR", "响应解析失败", xhr.status));
        }
      });

      // 设置错误监听
      xhr.addEventListener("error", () => {
        reject(new ApiError("NETWORK_ERROR", "网络错误", 0));
      });

      // 设置超时监听
      xhr.addEventListener("timeout", () => {
        reject(new ApiError("TIMEOUT", "上传超时", 408));
      });

      // 配置请求
      xhr.open("POST", url);
      xhr.timeout = this.config.TIMEOUT;

      // 设置请求头
      Object.entries(options.headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });

      // 发送请求
      xhr.send(formData);
    });
  }
}

// ============= 错误类 =============

class ApiError extends Error {
  constructor(code, message, status = 0, response = null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.response = response;
  }

  /**
   * 判断是否为网络错误
   */
  isNetworkError() {
    return this.code === "NETWORK_ERROR" || this.code === "TIMEOUT";
  }

  /**
   * 判断是否为认证错误
   */
  isAuthError() {
    return (
      this.code === "UNAUTHORIZED" ||
      this.code === "TOKEN_EXPIRED" ||
      this.code === "AUTH_FAILED"
    );
  }

  /**
   * 判断是否为验证错误
   */
  isValidationError() {
    return this.code === "VALIDATION_ERROR";
  }

  /**
   * 获取用户友好的错误消息
   */
  getUserMessage() {
    const messages = {
      NETWORK_ERROR: "网络连接失败，请检查网络设置",
      TIMEOUT: "请求超时，请稍后重试",
      UNAUTHORIZED: "登录已过期，请重新登录",
      FORBIDDEN: "权限不足，无法执行此操作",
      NOT_FOUND: "请求的资源不存在",
      VALIDATION_ERROR: "输入数据有误，请检查后重试",
      RATE_LIMIT_EXCEEDED: "请求过于频繁，请稍后再试",
    };

    return messages[this.code] || this.message || "操作失败，请稍后重试";
  }
}

// ============= 业务API封装 =============

/**
 * 认证API
 */
class AuthAPI {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * 用户登录
   */
  async login(credentials) {
    const result = await this.client.post("/auth/login", credentials);
    if (result.success) {
      this.client.setTokens(
        result.data.access_token,
        result.data.refresh_token
      );
    }
    return result;
  }

  /**
   * 用户注册
   */
  async register(userData) {
    return this.client.post("/auth/register", userData);
  }

  /**
   * 用户登出
   */
  async logout() {
    try {
      await this.client.post("/auth/logout");
    } finally {
      this.client.clearTokens();
    }
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser() {
    return this.client.get("/auth/me");
  }

  /**
   * 修改密码
   */
  async changePassword(passwordData) {
    return this.client.post("/auth/change-password", passwordData);
  }

  /**
   * 忘记密码
   */
  async forgotPassword(email) {
    return this.client.post("/auth/forgot-password", { email });
  }

  /**
   * 重置密码
   */
  async resetPassword(resetData) {
    return this.client.post("/auth/reset-password", resetData);
  }

  /**
   * 验证令牌
   */
  async verifyToken() {
    return this.client.get("/auth/verify-token");
  }
}

/**
 * 用户API
 */
class UserAPI {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * 获取用户列表
   */
  async getUsers(params = {}) {
    return this.client.get("/users", params);
  }

  /**
   * 获取用户详情
   */
  async getUser(userId) {
    return this.client.get(`/users/${userId}`);
  }

  /**
   * 创建用户
   */
  async createUser(userData) {
    return this.client.post("/users", userData);
  }

  /**
   * 更新用户
   */
  async updateUser(userId, userData) {
    return this.client.put(`/users/${userId}`, userData);
  }

  /**
   * 删除用户
   */
  async deleteUser(userId) {
    return this.client.delete(`/users/${userId}`);
  }

  /**
   * 获取用户统计信息
   */
  async getUserStatistics() {
    return this.client.get("/users/statistics/overview");
  }

  /**
   * 获取当前用户权限
   */
  async getCurrentUserPermissions() {
    return this.client.get("/users/me/permissions");
  }
}

/**
 * 音频API
 */
class AudioAPI {
  constructor(apiClient) {
    this.client = apiClient;
  }

  /**
   * 获取音频列表
   */
  async getAudios(params = {}) {
    return this.client.get("/audios", params);
  }

  /**
   * 上传音频
   */
  async uploadAudio(file, metadata = {}, onProgress = null) {
    return this.client.upload("/audios/upload", file, metadata, onProgress);
  }

  /**
   * 获取音频详情
   */
  async getAudio(audioId) {
    return this.client.get(`/audios/${audioId}`);
  }

  /**
   * 更新音频
   */
  async updateAudio(audioId, audioData) {
    return this.client.put(`/audios/${audioId}`, audioData);
  }

  /**
   * 删除音频
   */
  async deleteAudio(audioId) {
    return this.client.delete(`/audios/${audioId}`);
  }

  /**
   * 搜索音频
   */
  async searchAudios(params = {}) {
    return this.client.get("/audios/search", params);
  }
}

// ============= API 管理器 =============

class APIManager {
  constructor(config = {}) {
    this.client = new ApiClient(config);
    this.auth = new AuthAPI(this.client);
    this.users = new UserAPI(this.client);
    this.audios = new AudioAPI(this.client);

    this.setupInterceptors();
  }

  /**
   * 设置拦截器
   */
  setupInterceptors() {
    // 请求拦截器：添加时间戳
    this.client.addRequestInterceptor((config) => {
      config.headers["X-Timestamp"] = Date.now().toString();
      return config;
    });

    // 响应拦截器：日志记录
    this.client.addResponseInterceptor((response) => {
      if (process.env.NODE_ENV === "development") {
        console.log("API Response:", response);
      }
      return response;
    });
  }

  /**
   * 获取API客户端
   */
  getClient() {
    return this.client;
  }
}

// ============= 导出 =============

// 创建默认实例
const apiManager = new APIManager();

// 导出API管理器和相关类
if (typeof module !== "undefined" && module.exports) {
  // Node.js 环境
  module.exports = {
    APIManager,
    ApiClient,
    ApiError,
    AuthAPI,
    UserAPI,
    AudioAPI,
    apiManager,
  };
} else {
  // 浏览器环境
  window.APIManager = APIManager;
  window.ApiClient = ApiClient;
  window.ApiError = ApiError;
  window.AuthAPI = AuthAPI;
  window.UserAPI = UserAPI;
  window.AudioAPI = AudioAPI;
  window.apiManager = apiManager;
}

// ============= 使用示例 =============

/*
// 基础使用
const api = new APIManager();

// 登录
try {
  const result = await api.auth.login({
    username: 'user@example.com',
    password: 'password123'
  });
  
  if (result.success) {
    console.log('登录成功:', result.data.user);
  }
} catch (error) {
  console.error('登录失败:', error.getUserMessage());
}

// 获取用户列表
try {
  const result = await api.users.getUsers({
    page: 1,
    size: 20,
    keyword: '搜索关键词'
  });
  
  if (result.success) {
    console.log('用户列表:', result.data);
    console.log('分页信息:', result.pagination);
  }
} catch (error) {
  if (error.isAuthError()) {
    // 处理认证错误
    console.log('需要重新登录');
  } else {
    console.error('获取用户列表失败:', error.getUserMessage());
  }
}

// 上传音频文件
const fileInput = document.getElementById('audioFile');
const file = fileInput.files[0];

if (file) {
  try {
    const result = await api.audios.uploadAudio(
      file,
      {
        script_id: 1,
        role_name: '主角',
        notes: '第一次录制'
      },
      (progress) => {
        console.log(`上传进度: ${progress.percentage}%`);
      }
    );
    
    if (result.success) {
      console.log('上传成功:', result.data);
    }
  } catch (error) {
    console.error('上传失败:', error.getUserMessage());
  }
}

// 错误处理
window.addEventListener('auth:logout', () => {
  // 用户被登出，跳转到登录页
  window.location.href = '/login';
});
*/
