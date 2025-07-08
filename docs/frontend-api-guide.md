# 前端项目 API 接口使用指南

## 1. 基础配置

### API 基础信息

- **基础URL**: `http://localhost:8000/api/v1`
- **文档地址**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc文档**: `http://localhost:8000/redoc`
- **OpenAPI规范**: `http://localhost:8000/api/v1/openapi.json`

### 响应格式

所有API接口都遵循统一的响应格式：

```typescript
// 成功响应
interface SuccessResponse<T> {
  success: true;
  message: string;
  data: T;
  timestamp: string;
  request_id?: string;
}

// 分页响应
interface PaginatedResponse<T> {
  success: true;
  message: string;
  data: T[];
  pagination: {
    page: number;
    size: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
  timestamp: string;
  request_id?: string;
}

// 错误响应
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
  request_id?: string;
}
```

## 2. 认证系统

### 2.1 用户注册

```javascript
// POST /api/v1/auth/register
const registerUser = async (userData) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: userData.username,
      email: userData.email,
      password: userData.password,
      confirm_password: userData.confirmPassword,
      full_name: userData.fullName
    })
  });
  
  const result = await response.json();
  return result;
};
```

### 2.2 用户登录

```javascript
// POST /api/v1/auth/login
const loginUser = async (credentials) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: credentials.username, // 可以是用户名或邮箱
      password: credentials.password
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    // 保存token到localStorage
    localStorage.setItem('access_token', result.data.access_token);
    localStorage.setItem('refresh_token', result.data.refresh_token);
  }
  
  return result;
};
```

### 2.3 获取当前用户信息

```javascript
// GET /api/v1/auth/me
const getCurrentUser = async () => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:8000/api/v1/auth/me', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  });
  
  const result = await response.json();
  return result;
};
```

### 2.4 刷新Token

```javascript
// POST /api/v1/auth/refresh
const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch('http://localhost:8000/api/v1/auth/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refresh_token: refreshToken
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    localStorage.setItem('access_token', result.data.access_token);
  }
  
  return result;
};
```

## 3. API 请求封装

### 3.1 基础请求封装

```javascript
class ApiClient {
  constructor(baseURL = 'http://localhost:8000/api/v1') {
    this.baseURL = baseURL;
  }
  
  // 获取认证头
  getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }
  
  // 通用请求方法
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...options.headers,
      },
      ...options,
    };
    
    try {
      const response = await fetch(url, config);
      const result = await response.json();
      
      // 处理token过期
      if (response.status === 401 && result.error?.code === 'TOKEN_EXPIRED') {
        const refreshResult = await this.refreshToken();
        if (refreshResult.success) {
          // 重试原请求
          config.headers.Authorization = `Bearer ${localStorage.getItem('access_token')}`;
          const retryResponse = await fetch(url, config);
          return await retryResponse.json();
        } else {
          // 刷新失败，跳转到登录页
          this.handleAuthError();
          return result;
        }
      }
      
      return result;
    } catch (error) {
      console.error('API请求失败:', error);
      throw error;
    }
  }
  
  // GET请求
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url, { method: 'GET' });
  }
  
  // POST请求
  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  // PUT请求
  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
  
  // DELETE请求
  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
  
  // 处理认证错误
  handleAuthError() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    // 跳转到登录页
    window.location.href = '/login';
  }
  
  // 刷新token
  async refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      this.handleAuthError();
      return { success: false };
    }
    
    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      
      const result = await response.json();
      
      if (result.success) {
        localStorage.setItem('access_token', result.data.access_token);
      } else {
        this.handleAuthError();
      }
      
      return result;
    } catch (error) {
      console.error('刷新token失败:', error);
      this.handleAuthError();
      return { success: false };
    }
  }
}

// 创建API客户端实例
const apiClient = new ApiClient();
```

### 3.2 具体业务API封装

```javascript
// 用户相关API
class UserAPI {
  // 获取用户列表
  static async getUsers(params = {}) {
    return apiClient.get('/users', params);
  }
  
  // 获取用户详情
  static async getUser(userId) {
    return apiClient.get(`/users/${userId}`);
  }
  
  // 更新用户信息
  static async updateUser(userId, userData) {
    return apiClient.put(`/users/${userId}`, userData);
  }
  
  // 删除用户
  static async deleteUser(userId) {
    return apiClient.delete(`/users/${userId}`);
  }
  
  // 获取用户统计信息
  static async getUserStatistics() {
    return apiClient.get('/users/statistics/overview');
  }
  
  // 获取当前用户权限
  static async getCurrentUserPermissions() {
    return apiClient.get('/users/me/permissions');
  }
}

// 角色权限相关API
class RoleAPI {
  // 获取角色列表
  static async getRoles(params = {}) {
    return apiClient.get('/roles', params);
  }
  
  // 创建角色
  static async createRole(roleData) {
    return apiClient.post('/roles', roleData);
  }
  
  // 更新角色
  static async updateRole(roleId, roleData) {
    return apiClient.put(`/roles/${roleId}`, roleData);
  }
  
  // 删除角色
  static async deleteRole(roleId) {
    return apiClient.delete(`/roles/${roleId}`);
  }
  
  // 获取权限列表
  static async getPermissions(params = {}) {
    return apiClient.get('/roles/permissions', params);
  }
}

// 音频相关API
class AudioAPI {
  // 获取音频列表
  static async getAudios(params = {}) {
    return apiClient.get('/audios', params);
  }
  
  // 上传音频文件
  static async uploadAudio(file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);
    
    // 添加元数据
    Object.keys(metadata).forEach(key => {
      formData.append(key, metadata[key]);
    });
    
    return apiClient.request('/audios/upload', {
      method: 'POST',
      body: formData,
      headers: {
        // 不设置Content-Type，让浏览器自动设置
        ...apiClient.getAuthHeaders()
      }
    });
  }
  
  // 搜索音频
  static async searchAudios(params = {}) {
    return apiClient.get('/audios/search', params);
  }
  
  // 获取音频详情
  static async getAudio(audioId) {
    return apiClient.get(`/audios/${audioId}`);
  }
  
  // 删除音频
  static async deleteAudio(audioId) {
    return apiClient.delete(`/audios/${audioId}`);
  }
}
```

## 4. React Hook 封装示例

### 4.1 认证Hook

```javascript
import { useState, useEffect, useContext, createContext } from 'react';

// 认证上下文
const AuthContext = createContext();

// 认证Provider
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  
  // 检查认证状态
  useEffect(() => {
    checkAuthStatus();
  }, []);
  
  const checkAuthStatus = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    
    try {
      const result = await apiClient.get('/auth/me');
      if (result.success) {
        setUser(result.data);
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
    } catch (error) {
      console.error('检查认证状态失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const login = async (credentials) => {
    try {
      const result = await apiClient.post('/auth/login', credentials);
      if (result.success) {
        localStorage.setItem('access_token', result.data.access_token);
        localStorage.setItem('refresh_token', result.data.refresh_token);
        setUser(result.data.user);
        setIsAuthenticated(true);
      }
      return result;
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  };
  
  const logout = async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch (error) {
      console.error('登出失败:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
      setIsAuthenticated(false);
    }
  };
  
  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    checkAuthStatus
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// 使用认证Hook
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

### 4.2 数据获取Hook

```javascript
import { useState, useEffect } from 'react';

// 通用数据获取Hook
export const useApi = (apiCall, dependencies = []) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    let isMounted = true;
    
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await apiCall();
        
        if (isMounted) {
          if (result.success) {
            setData(result.data);
          } else {
            setError(result.error);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    
    fetchData();
    
    return () => {
      isMounted = false;
    };
  }, dependencies);
  
  return { data, loading, error, refetch: () => fetchData() };
};

// 分页数据Hook
export const usePaginatedApi = (apiCall, initialParams = {}) => {
  const [data, setData] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [params, setParams] = useState({ page: 1, size: 20, ...initialParams });
  
  useEffect(() => {
    fetchData();
  }, [params]);
  
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiCall(params);
      
      if (result.success) {
        setData(result.data);
        setPagination(result.pagination);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };
  
  const updateParams = (newParams) => {
    setParams(prev => ({ ...prev, ...newParams }));
  };
  
  return {
    data,
    pagination,
    loading,
    error,
    params,
    updateParams,
    refetch: fetchData
  };
};
```

## 5. 使用示例

### 5.1 用户列表组件

```javascript
import React from 'react';
import { usePaginatedApi } from './hooks/useApi';
import { UserAPI } from './api/userAPI';

const UserList = () => {
  const {
    data: users,
    pagination,
    loading,
    error,
    updateParams
  } = usePaginatedApi(UserAPI.getUsers);
  
  const handlePageChange = (page) => {
    updateParams({ page });
  };
  
  const handleSearch = (keyword) => {
    updateParams({ page: 1, keyword });
  };
  
  if (loading) return <div>加载中...</div>;
  if (error) return <div>错误: {error.message}</div>;
  
  return (
    <div>
      <h2>用户列表</h2>
      
      {/* 搜索框 */}
      <input
        type="text"
        placeholder="搜索用户..."
        onChange={(e) => handleSearch(e.target.value)}
      />
      
      {/* 用户列表 */}
      <div>
        {users.map(user => (
          <div key={user.id}>
            <h3>{user.full_name}</h3>
            <p>用户名: {user.username}</p>
            <p>邮箱: {user.email}</p>
            <p>状态: {user.is_active ? '激活' : '禁用'}</p>
          </div>
        ))}
      </div>
      
      {/* 分页 */}
      {pagination && (
        <div>
          <button
            disabled={!pagination.has_prev}
            onClick={() => handlePageChange(pagination.page - 1)}
          >
            上一页
          </button>
          
          <span>
            第 {pagination.page} 页，共 {pagination.pages} 页
          </span>
          
          <button
            disabled={!pagination.has_next}
            onClick={() => handlePageChange(pagination.page + 1)}
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
};

export default UserList;
```

### 5.2 登录组件

```javascript
import React, { useState } from 'react';
import { useAuth } from './hooks/useAuth';

const Login = () => {
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const { login } = useAuth();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const result = await login(credentials);
      if (!result.success) {
        setError(result.error.message);
      }
    } catch (err) {
      setError('登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <h2>用户登录</h2>
      
      {error && <div style={{color: 'red'}}>{error}</div>}
      
      <div>
        <label>用户名或邮箱:</label>
        <input
          type="text"
          value={credentials.username}
          onChange={(e) => setCredentials({
            ...credentials,
            username: e.target.value
          })}
          required
        />
      </div>
      
      <div>
        <label>密码:</label>
        <input
          type="password"
          value={credentials.password}
          onChange={(e) => setCredentials({
            ...credentials,
            password: e.target.value
          })}
          required
        />
      </div>
      
      <button type="submit" disabled={loading}>
        {loading ? '登录中...' : '登录'}
      </button>
    </form>
  );
};

export default Login;
```

## 6. 错误处理

### 6.1 常见错误码

- `BAD_REQUEST`: 请求参数错误
- `UNAUTHORIZED`: 未认证或token无效
- `FORBIDDEN`: 权限不足
- `NOT_FOUND`: 资源不存在
- `VALIDATION_ERROR`: 数据验证失败
- `RATE_LIMIT_EXCEEDED`: 请求频率超限
- `INTERNAL_ERROR`: 服务器内部错误

### 6.2 错误处理最佳实践

```javascript
// 全局错误处理
const handleApiError = (error) => {
  switch (error.code) {
    case 'UNAUTHORIZED':
      // 跳转到登录页
      window.location.href = '/login';
      break;
    case 'FORBIDDEN':
      // 显示权限不足提示
      alert('权限不足');
      break;
    case 'VALIDATION_ERROR':
      // 显示验证错误详情
      console.error('验证错误:', error.details);
      break;
    case 'RATE_LIMIT_EXCEEDED':
      // 显示限流提示
      alert('请求过于频繁，请稍后再试');
      break;
    default:
      // 显示通用错误信息
      alert(error.message || '操作失败');
  }
};
```

## 7. 性能优化建议

1. **请求缓存**: 对于不经常变化的数据，可以使用缓存
2. **防抖处理**: 对于搜索等频繁操作，使用防抖
3. **分页加载**: 大量数据使用分页或虚拟滚动
4. **错误重试**: 网络错误时自动重试
5. **Loading状态**: 提供良好的加载状态反馈
6. **Token自动刷新**: 实现token自动刷新机制

这份指南涵盖了前端项目使用后端API的所有关键方面，包括认证、数据获取、错误处理和性能优化等。根据具体的前端框架（React、Vue、Angular等），可以相应调整实现方式。
