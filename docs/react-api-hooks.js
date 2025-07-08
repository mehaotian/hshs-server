/**
 * React Hooks 示例
 * 提供完整的React Hook封装，用于调用后端API
 */

import { useState, useEffect, useCallback, useRef, useContext, createContext } from 'react';
import { apiManager } from './api-client-example.js';

// ============= 认证上下文 =============

const AuthContext = createContext(null);

/**
 * 认证Provider组件
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  
  const checkAuthStatus = useCallback(async () => {
    try {
      setLoading(true);
      const token = apiManager.client.getAccessToken();
      
      if (!token) {
        setUser(null);
        setIsAuthenticated(false);
        return;
      }
      
      const result = await apiManager.auth.getCurrentUser();
      if (result.success) {
        setUser(result.data);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
        apiManager.client.clearTokens();
      }
    } catch (error) {
      console.error('检查认证状态失败:', error);
      setUser(null);
      setIsAuthenticated(false);
      apiManager.client.clearTokens();
    } finally {
      setLoading(false);
    }
  }, []);
  
  const login = useCallback(async (credentials) => {
    try {
      const result = await apiManager.auth.login(credentials);
      if (result.success) {
        setUser(result.data.user);
        setIsAuthenticated(true);
      }
      return result;
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  }, []);
  
  const logout = useCallback(async () => {
    try {
      await apiManager.auth.logout();
    } catch (error) {
      console.error('登出失败:', error);
    } finally {
      setUser(null);
      setIsAuthenticated(false);
    }
  }, []);
  
  const register = useCallback(async (userData) => {
    try {
      const result = await apiManager.auth.register(userData);
      return result;
    } catch (error) {
      console.error('注册失败:', error);
      throw error;
    }
  }, []);
  
  // 监听认证状态变化
  useEffect(() => {
    const handleAuthLogout = () => {
      setUser(null);
      setIsAuthenticated(false);
    };
    
    checkAuthStatus();
    window.addEventListener('auth:logout', handleAuthLogout);
    
    return () => {
      window.removeEventListener('auth:logout', handleAuthLogout);
    };
  }, [checkAuthStatus]);
  
  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    register,
    checkAuthStatus
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * 使用认证Hook
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// ============= 基础API Hooks =============

/**
 * 通用API请求Hook
 * @param {Function} apiCall - API调用函数
 * @param {Array} dependencies - 依赖数组
 * @param {Object} options - 配置选项
 */
export const useApi = (apiCall, dependencies = [], options = {}) => {
  const {
    immediate = true,
    onSuccess = null,
    onError = null,
    transform = null
  } = options;
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);
  
  const isMountedRef = useRef(true);
  
  const execute = useCallback(async (...args) => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await apiCall(...args);
      
      if (!isMountedRef.current) return result;
      
      if (result.success) {
        const transformedData = transform ? transform(result.data) : result.data;
        setData(transformedData);
        setLastFetch(new Date());
        
        if (onSuccess) {
          onSuccess(transformedData, result);
        }
      } else {
        throw new Error(result.error?.message || '请求失败');
      }
      
      return result;
    } catch (err) {
      if (isMountedRef.current) {
        setError(err);
        if (onError) {
          onError(err);
        }
      }
      throw err;
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [apiCall, transform, onSuccess, onError]);
  
  const refresh = useCallback(() => execute(), [execute]);
  
  // 依赖变化时重新请求
  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [execute, immediate, ...dependencies]);
  
  // 清理函数
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);
  
  return {
    data,
    loading,
    error,
    lastFetch,
    execute,
    refresh
  };
};

/**
 * 分页API请求Hook
 * @param {Function} apiCall - API调用函数
 * @param {Object} initialParams - 初始参数
 * @param {Object} options - 配置选项
 */
export const usePaginatedApi = (apiCall, initialParams = {}, options = {}) => {
  const {
    immediate = true,
    onSuccess = null,
    onError = null
  } = options;
  
  const [data, setData] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [params, setParams] = useState({
    page: 1,
    size: 20,
    ...initialParams
  });
  
  const isMountedRef = useRef(true);
  
  const execute = useCallback(async (newParams = {}) => {
    try {
      setLoading(true);
      setError(null);
      
      const requestParams = { ...params, ...newParams };
      const result = await apiCall(requestParams);
      
      if (!isMountedRef.current) return result;
      
      if (result.success) {
        setData(result.data);
        setPagination(result.pagination);
        
        if (onSuccess) {
          onSuccess(result.data, result.pagination);
        }
      } else {
        throw new Error(result.error?.message || '请求失败');
      }
      
      return result;
    } catch (err) {
      if (isMountedRef.current) {
        setError(err);
        if (onError) {
          onError(err);
        }
      }
      throw err;
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [apiCall, params, onSuccess, onError]);
  
  const updateParams = useCallback((newParams) => {
    setParams(prev => ({ ...prev, ...newParams }));
  }, []);
  
  const nextPage = useCallback(() => {
    if (pagination?.has_next) {
      updateParams({ page: params.page + 1 });
    }
  }, [pagination, params.page, updateParams]);
  
  const prevPage = useCallback(() => {
    if (pagination?.has_prev) {
      updateParams({ page: params.page - 1 });
    }
  }, [pagination, params.page, updateParams]);
  
  const goToPage = useCallback((page) => {
    updateParams({ page });
  }, [updateParams]);
  
  const refresh = useCallback(() => execute(), [execute]);
  
  // 参数变化时重新请求
  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [execute, immediate]);
  
  // 清理函数
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);
  
  return {
    data,
    pagination,
    loading,
    error,
    params,
    execute,
    updateParams,
    nextPage,
    prevPage,
    goToPage,
    refresh
  };
};

/**
 * 文件上传Hook
 * @param {Function} uploadFn - 上传函数
 * @param {Object} options - 配置选项
 */
export const useFileUpload = (uploadFn, options = {}) => {
  const {
    onSuccess = null,
    onError = null,
    onProgress = null,
    multiple = false,
    accept = '*/*',
    maxSize = 100 * 1024 * 1024 // 100MB
  } = options;
  
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  
  const validateFile = useCallback((file) => {
    if (file.size > maxSize) {
      throw new Error(`文件大小不能超过 ${Math.round(maxSize / 1024 / 1024)}MB`);
    }
    
    if (accept !== '*/*') {
      const acceptTypes = accept.split(',').map(type => type.trim());
      const fileType = file.type;
      const fileName = file.name;
      
      const isValidType = acceptTypes.some(type => {
        if (type.startsWith('.')) {
          return fileName.toLowerCase().endsWith(type.toLowerCase());
        }
        return fileType.match(type.replace('*', '.*'));
      });
      
      if (!isValidType) {
        throw new Error(`不支持的文件类型，仅支持: ${accept}`);
      }
    }
  }, [accept, maxSize]);
  
  const upload = useCallback(async (files, metadata = {}) => {
    try {
      setUploading(true);
      setProgress(0);
      setError(null);
      setResult(null);
      
      const fileList = Array.isArray(files) ? files : [files];
      
      if (!multiple && fileList.length > 1) {
        throw new Error('不支持多文件上传');
      }
      
      // 验证文件
      fileList.forEach(validateFile);
      
      const uploadPromises = fileList.map(file => {
        return uploadFn(file, metadata, (progressEvent) => {
          setProgress(progressEvent.percentage);
          if (onProgress) {
            onProgress(progressEvent, file);
          }
        });
      });
      
      const results = await Promise.all(uploadPromises);
      const successResults = results.filter(r => r.success);
      
      if (successResults.length === results.length) {
        const uploadResult = multiple ? successResults : successResults[0];
        setResult(uploadResult);
        if (onSuccess) {
          onSuccess(uploadResult);
        }
        return uploadResult;
      } else {
        throw new Error('部分文件上传失败');
      }
    } catch (err) {
      setError(err);
      if (onError) {
        onError(err);
      }
      throw err;
    } finally {
      setUploading(false);
    }
  }, [uploadFn, multiple, validateFile, onSuccess, onError, onProgress]);
  
  const reset = useCallback(() => {
    setUploading(false);
    setProgress(0);
    setError(null);
    setResult(null);
  }, []);
  
  return {
    uploading,
    progress,
    error,
    result,
    upload,
    reset
  };
};

// ============= 业务相关Hooks =============

/**
 * 用户管理Hook
 */
export const useUsers = (initialParams = {}) => {
  const {
    data: users,
    pagination,
    loading,
    error,
    updateParams,
    refresh
  } = usePaginatedApi(
    (params) => apiManager.users.getUsers(params),
    initialParams
  );
  
  const createUser = useCallback(async (userData) => {
    const result = await apiManager.users.createUser(userData);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  }, [refresh]);
  
  const updateUser = useCallback(async (userId, userData) => {
    const result = await apiManager.users.updateUser(userId, userData);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  }, [refresh]);
  
  const deleteUser = useCallback(async (userId) => {
    const result = await apiManager.users.deleteUser(userId);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  }, [refresh]);
  
  return {
    users,
    pagination,
    loading,
    error,
    updateParams,
    refresh,
    createUser,
    updateUser,
    deleteUser
  };
};

/**
 * 音频管理Hook
 */
export const useAudios = (initialParams = {}) => {
  const {
    data: audios,
    pagination,
    loading,
    error,
    updateParams,
    refresh
  } = usePaginatedApi(
    (params) => apiManager.audios.getAudios(params),
    initialParams
  );
  
  const {
    uploading,
    progress,
    error: uploadError,
    upload,
    reset: resetUpload
  } = useFileUpload(
    (file, metadata, onProgress) => apiManager.audios.uploadAudio(file, metadata, onProgress),
    {
      accept: '.mp3,.wav,.flac,.m4a',
      maxSize: 100 * 1024 * 1024, // 100MB
      onSuccess: () => {
        refresh(); // 上传成功后刷新列表
      }
    }
  );
  
  const deleteAudio = useCallback(async (audioId) => {
    const result = await apiManager.audios.deleteAudio(audioId);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  }, [refresh]);
  
  const updateAudio = useCallback(async (audioId, audioData) => {
    const result = await apiManager.audios.updateAudio(audioId, audioData);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  }, [refresh]);
  
  return {
    audios,
    pagination,
    loading,
    error,
    updateParams,
    refresh,
    // 上传相关
    uploading,
    progress,
    uploadError,
    upload,
    resetUpload,
    // 操作相关
    deleteAudio,
    updateAudio
  };
};

/**
 * 搜索Hook
 */
export const useSearch = (searchFn, options = {}) => {
  const {
    debounceMs = 300,
    minLength = 2,
    immediate = false
  } = options;
  
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const debounceTimerRef = useRef(null);
  const isMountedRef = useRef(true);
  
  const search = useCallback(async (searchQuery = query) => {
    if (searchQuery.length < minLength) {
      setResults([]);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      const result = await searchFn(searchQuery);
      
      if (!isMountedRef.current) return;
      
      if (result.success) {
        setResults(result.data);
      } else {
        throw new Error(result.error?.message || '搜索失败');
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err);
        setResults([]);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [searchFn, query, minLength]);
  
  const debouncedSearch = useCallback((searchQuery) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    
    debounceTimerRef.current = setTimeout(() => {
      search(searchQuery);
    }, debounceMs);
  }, [search, debounceMs]);
  
  const clear = useCallback(() => {
    setQuery('');
    setResults([]);
    setError(null);
  }, []);
  
  // 监听查询变化
  useEffect(() => {
    if (query.length >= minLength) {
      debouncedSearch(query);
    } else {
      setResults([]);
    }
  }, [query, minLength, debouncedSearch]);
  
  // 立即搜索
  useEffect(() => {
    if (immediate && query) {
      search();
    }
  }, [immediate, query, search]);
  
  // 清理函数
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);
  
  return {
    query,
    setQuery,
    results,
    loading,
    error,
    search,
    clear
  };
};

/**
 * 表单Hook
 */
export const useForm = (initialValues = {}, validationRules = {}, submitFn = null) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [submitting, setSubmitting] = useState(false);
  
  const validate = useCallback((field = null) => {
    const fieldsToValidate = field ? [field] : Object.keys(validationRules);
    const newErrors = { ...errors };
    let isValid = true;
    
    fieldsToValidate.forEach(fieldName => {
      const rules = validationRules[fieldName];
      if (!rules) return;
      
      const value = values[fieldName];
      let fieldError = null;
      
      for (const rule of rules) {
        if (typeof rule === 'function') {
          const result = rule(value, values);
          if (result !== true) {
            fieldError = result;
            break;
          }
        } else if (rule.validator) {
          const result = rule.validator(value, values);
          if (result !== true) {
            fieldError = rule.message || result;
            break;
          }
        }
      }
      
      if (fieldError) {
        newErrors[fieldName] = fieldError;
        isValid = false;
      } else {
        delete newErrors[fieldName];
      }
    });
    
    setErrors(newErrors);
    return isValid;
  }, [errors, values, validationRules]);
  
  const setFieldValue = useCallback((field, value) => {
    setValues(prev => ({ ...prev, [field]: value }));
    setTouched(prev => ({ ...prev, [field]: true }));
    
    // 延迟验证，避免在用户输入时立即显示错误
    setTimeout(() => validate(field), 0);
  }, [validate]);
  
  const setFieldError = useCallback((field, error) => {
    setErrors(prev => ({ ...prev, [field]: error }));
  }, []);
  
  const clearErrors = useCallback(() => {
    setErrors({});
  }, []);
  
  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);
  
  const submit = useCallback(async () => {
    if (!submitFn) {
      throw new Error('未提供提交函数');
    }
    
    // 标记所有字段为已触摸
    const allTouched = {};
    Object.keys(validationRules).forEach(field => {
      allTouched[field] = true;
    });
    setTouched(allTouched);
    
    const isValid = validate();
    if (!isValid) {
      throw new Error('表单验证失败');
    }
    
    try {
      setSubmitting(true);
      const result = await submitFn(values);
      return result;
    } finally {
      setSubmitting(false);
    }
  }, [submitFn, values, validationRules, validate]);
  
  const isValid = Object.keys(errors).length === 0;
  
  return {
    values,
    errors,
    touched,
    submitting,
    isValid,
    validate,
    setFieldValue,
    setFieldError,
    clearErrors,
    reset,
    submit
  };
};

/**
 * 权限检查Hook
 */
export const usePermissions = () => {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const loadPermissions = useCallback(async () => {
    try {
      setLoading(true);
      const result = await apiManager.users.getCurrentUserPermissions();
      if (result.success) {
        setPermissions(result.data);
      }
    } catch (error) {
      console.error('获取权限失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);
  
  const hasPermission = useCallback((permission) => {
    return permissions.includes(permission);
  }, [permissions]);
  
  const hasAnyPermission = useCallback((permissionList) => {
    return permissionList.some(permission => hasPermission(permission));
  }, [hasPermission]);
  
  const hasAllPermissions = useCallback((permissionList) => {
    return permissionList.every(permission => hasPermission(permission));
  }, [hasPermission]);
  
  useEffect(() => {
    loadPermissions();
  }, [loadPermissions]);
  
  return {
    permissions,
    loading,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    loadPermissions
  };
};

/**
 * 通知Hook
 */
export const useNotifications = () => {
  const [notifications, setNotifications] = useState([]);
  
  const addNotification = useCallback((notification) => {
    const id = Date.now().toString();
    const newNotification = {
      id,
      type: 'info',
      duration: 5000,
      ...notification
    };
    
    setNotifications(prev => [...prev, newNotification]);
    
    // 自动移除
    if (newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, newNotification.duration);
    }
    
    return id;
  }, []);
  
  const removeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);
  
  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);
  
  const success = useCallback((message, options = {}) => {
    return addNotification({
      type: 'success',
      title: '成功',
      message,
      ...options
    });
  }, [addNotification]);
  
  const error = useCallback((message, options = {}) => {
    return addNotification({
      type: 'error',
      title: '错误',
      message,
      duration: 0, // 错误消息不自动消失
      ...options
    });
  }, [addNotification]);
  
  const warning = useCallback((message, options = {}) => {
    return addNotification({
      type: 'warning',
      title: '警告',
      message,
      ...options
    });
  }, [addNotification]);
  
  const info = useCallback((message, options = {}) => {
    return addNotification({
      type: 'info',
      title: '信息',
      message,
      ...options
    });
  }, [addNotification]);
  
  return {
    notifications,
    addNotification,
    removeNotification,
    clearAll,
    success,
    error,
    warning,
    info
  };
};

// ============= 导出所有Hooks =============

export {
  // 认证相关
  AuthProvider,
  useAuth,
  
  // 基础API
  useApi,
  usePaginatedApi,
  useFileUpload,
  
  // 业务相关
  useUsers,
  useAudios,
  useSearch,
  
  // 表单处理
  useForm,
  
  // 权限检查
  usePermissions,
  
  // 通知系统
  useNotifications
};

// ============= 使用示例 =============

/*
// App.js - 根组件
import React from 'react';
import { AuthProvider } from './react-api-hooks.js';
import UserList from './UserList.js';

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <UserList />
      </div>
    </AuthProvider>
  );
}

export default App;

// UserList.js - 用户列表组件
import React, { useState } from 'react';
import { useUsers, useAuth, useNotifications } from './react-api-hooks.js';

function UserList() {
  const { user, logout } = useAuth();
  const { success, error } = useNotifications();
  const {
    users,
    pagination,
    loading,
    error: usersError,
    updateParams,
    createUser,
    deleteUser
  } = useUsers();
  
  const [searchKeyword, setSearchKeyword] = useState('');
  
  const handleSearch = (e) => {
    const keyword = e.target.value;
    setSearchKeyword(keyword);
    updateParams({ keyword, page: 1 });
  };
  
  const handleCreateUser = async () => {
    try {
      const result = await createUser({
        username: 'newuser',
        email: 'newuser@example.com',
        password: 'password123',
        full_name: '新用户'
      });
      
      if (result.success) {
        success('用户创建成功');
      }
    } catch (err) {
      error('创建用户失败: ' + err.message);
    }
  };
  
  const handleDeleteUser = async (userId) => {
    if (window.confirm('确定要删除这个用户吗？')) {
      try {
        const result = await deleteUser(userId);
        if (result.success) {
          success('用户删除成功');
        }
      } catch (err) {
        error('删除用户失败: ' + err.message);
      }
    }
  };
  
  const handlePageChange = (page) => {
    updateParams({ page });
  };
  
  if (loading) {
    return <div>加载中...</div>;
  }
  
  if (usersError) {
    return <div>错误: {usersError.message}</div>;
  }
  
  return (
    <div>
      <div>
        <h2>用户列表</h2>
        <p>当前用户: {user?.full_name}</p>
        <button onClick={logout}>登出</button>
      </div>
      
      <div>
        <input
          type="text"
          placeholder="搜索用户..."
          value={searchKeyword}
          onChange={handleSearch}
        />
        <button onClick={handleCreateUser}>创建用户</button>
      </div>
      
      <div>
        {users.map(user => (
          <div key={user.id} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
            <h3>{user.full_name}</h3>
            <p>用户名: {user.username}</p>
            <p>邮箱: {user.email}</p>
            <p>状态: {user.is_active ? '激活' : '禁用'}</p>
            <button onClick={() => handleDeleteUser(user.id)}>删除</button>
          </div>
        ))}
      </div>
      
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
}

export default UserList;

// FileUpload.js - 文件上传组件
import React, { useState } from 'react';
import { useFileUpload, useNotifications } from './react-api-hooks.js';
import { apiManager } from './api-client-example.js';

function FileUpload() {
  const [selectedFile, setSelectedFile] = useState(null);
  const { success, error } = useNotifications();
  
  const {
    uploading,
    progress,
    upload,
    reset
  } = useFileUpload(
    (file, metadata, onProgress) => apiManager.audios.uploadAudio(file, metadata, onProgress),
    {
      accept: '.mp3,.wav,.flac,.m4a',
      maxSize: 100 * 1024 * 1024,
      onSuccess: () => {
        success('文件上传成功');
        setSelectedFile(null);
      },
      onError: (err) => {
        error('文件上传失败: ' + err.message);
      }
    }
  );
  
  const handleFileSelect = (e) => {
    setSelectedFile(e.target.files[0]);
    reset();
  };
  
  const handleUpload = async () => {
    if (selectedFile) {
      try {
        await upload(selectedFile, {
          script_id: 1,
          role_name: '主角',
          notes: '第一次录制'
        });
      } catch (err) {
        // 错误已在onError中处理
      }
    }
  };
  
  return (
    <div>
      <h3>音频文件上传</h3>
      
      <input
        type="file"
        accept=".mp3,.wav,.flac,.m4a"
        onChange={handleFileSelect}
        disabled={uploading}
      />
      
      {selectedFile && (
        <div>
          <p>选中文件: {selectedFile.name}</p>
          <p>文件大小: {Math.round(selectedFile.size / 1024)} KB</p>
        </div>
      )}
      
      <button
        onClick={handleUpload}
        disabled={!selectedFile || uploading}
      >
        {uploading ? '上传中...' : '上传'}
      </button>
      
      {uploading && (
        <div>
          <div>上传进度: {progress}%</div>
          <div style={{ width: '100%', backgroundColor: '#f0f0f0' }}>
            <div
              style={{
                width: `${progress}%`,
                height: '20px',
                backgroundColor: '#4caf50'
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default FileUpload;
*/