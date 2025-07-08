/**
 * Vue 3 Composition API 示例
 * 提供完整的Vue组合式API封装，用于调用后端API
 */

import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue';
import { apiManager } from './api-client-example.js';

// ============= 基础组合式API =============

/**
 * 通用API请求Hook
 * @param {Function} apiCall - API调用函数
 * @param {Array} dependencies - 依赖数组，变化时重新请求
 * @param {Object} options - 配置选项
 */
export function useApi(apiCall, dependencies = [], options = {}) {
  const {
    immediate = true,
    onSuccess = null,
    onError = null,
    transform = null
  } = options;
  
  const data = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const lastFetch = ref(null);
  
  const execute = async (...args) => {
    try {
      loading.value = true;
      error.value = null;
      
      const result = await apiCall(...args);
      
      if (result.success) {
        const transformedData = transform ? transform(result.data) : result.data;
        data.value = transformedData;
        lastFetch.value = new Date();
        
        if (onSuccess) {
          onSuccess(transformedData, result);
        }
      } else {
        throw new Error(result.error?.message || '请求失败');
      }
      
      return result;
    } catch (err) {
      error.value = err;
      if (onError) {
        onError(err);
      }
      throw err;
    } finally {
      loading.value = false;
    }
  };
  
  const refresh = () => execute();
  
  // 监听依赖变化
  if (dependencies.length > 0) {
    watch(dependencies, () => {
      if (immediate) {
        execute();
      }
    }, { immediate });
  } else if (immediate) {
    onMounted(() => execute());
  }
  
  return {
    data: readonly(data),
    loading: readonly(loading),
    error: readonly(error),
    lastFetch: readonly(lastFetch),
    execute,
    refresh
  };
}

/**
 * 分页API请求Hook
 * @param {Function} apiCall - API调用函数
 * @param {Object} initialParams - 初始参数
 * @param {Object} options - 配置选项
 */
export function usePaginatedApi(apiCall, initialParams = {}, options = {}) {
  const {
    immediate = true,
    onSuccess = null,
    onError = null
  } = options;
  
  const data = ref([]);
  const pagination = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const params = reactive({
    page: 1,
    size: 20,
    ...initialParams
  });
  
  const execute = async (newParams = {}) => {
    try {
      loading.value = true;
      error.value = null;
      
      const requestParams = { ...params, ...newParams };
      const result = await apiCall(requestParams);
      
      if (result.success) {
        data.value = result.data;
        pagination.value = result.pagination;
        
        if (onSuccess) {
          onSuccess(result.data, result.pagination);
        }
      } else {
        throw new Error(result.error?.message || '请求失败');
      }
      
      return result;
    } catch (err) {
      error.value = err;
      if (onError) {
        onError(err);
      }
      throw err;
    } finally {
      loading.value = false;
    }
  };
  
  const updateParams = (newParams) => {
    Object.assign(params, newParams);
    execute();
  };
  
  const nextPage = () => {
    if (pagination.value?.has_next) {
      updateParams({ page: params.page + 1 });
    }
  };
  
  const prevPage = () => {
    if (pagination.value?.has_prev) {
      updateParams({ page: params.page - 1 });
    }
  };
  
  const goToPage = (page) => {
    updateParams({ page });
  };
  
  const refresh = () => execute();
  
  // 监听参数变化
  watch(() => ({ ...params }), () => {
    if (immediate) {
      execute();
    }
  }, { immediate, deep: true });
  
  return {
    data: readonly(data),
    pagination: readonly(pagination),
    loading: readonly(loading),
    error: readonly(error),
    params: readonly(params),
    execute,
    updateParams,
    nextPage,
    prevPage,
    goToPage,
    refresh
  };
}

/**
 * 文件上传Hook
 * @param {Function} uploadFn - 上传函数
 * @param {Object} options - 配置选项
 */
export function useFileUpload(uploadFn, options = {}) {
  const {
    onSuccess = null,
    onError = null,
    onProgress = null,
    multiple = false,
    accept = '*/*',
    maxSize = 100 * 1024 * 1024 // 100MB
  } = options;
  
  const uploading = ref(false);
  const progress = ref(0);
  const error = ref(null);
  const result = ref(null);
  
  const validateFile = (file) => {
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
  };
  
  const upload = async (files, metadata = {}) => {
    try {
      uploading.value = true;
      progress.value = 0;
      error.value = null;
      result.value = null;
      
      const fileList = Array.isArray(files) ? files : [files];
      
      if (!multiple && fileList.length > 1) {
        throw new Error('不支持多文件上传');
      }
      
      // 验证文件
      fileList.forEach(validateFile);
      
      const uploadPromises = fileList.map(file => {
        return uploadFn(file, metadata, (progressEvent) => {
          progress.value = progressEvent.percentage;
          if (onProgress) {
            onProgress(progressEvent, file);
          }
        });
      });
      
      const results = await Promise.all(uploadPromises);
      const successResults = results.filter(r => r.success);
      
      if (successResults.length === results.length) {
        result.value = multiple ? successResults : successResults[0];
        if (onSuccess) {
          onSuccess(result.value);
        }
      } else {
        throw new Error('部分文件上传失败');
      }
      
      return result.value;
    } catch (err) {
      error.value = err;
      if (onError) {
        onError(err);
      }
      throw err;
    } finally {
      uploading.value = false;
    }
  };
  
  const reset = () => {
    uploading.value = false;
    progress.value = 0;
    error.value = null;
    result.value = null;
  };
  
  return {
    uploading: readonly(uploading),
    progress: readonly(progress),
    error: readonly(error),
    result: readonly(result),
    upload,
    reset
  };
}

// ============= 认证相关组合式API =============

/**
 * 认证状态管理
 */
export function useAuth() {
  const user = ref(null);
  const loading = ref(true);
  const isAuthenticated = computed(() => !!user.value);
  
  const checkAuthStatus = async () => {
    try {
      loading.value = true;
      const token = apiManager.client.getAccessToken();
      
      if (!token) {
        user.value = null;
        return;
      }
      
      const result = await apiManager.auth.getCurrentUser();
      if (result.success) {
        user.value = result.data;
      } else {
        user.value = null;
        apiManager.client.clearTokens();
      }
    } catch (error) {
      console.error('检查认证状态失败:', error);
      user.value = null;
      apiManager.client.clearTokens();
    } finally {
      loading.value = false;
    }
  };
  
  const login = async (credentials) => {
    try {
      const result = await apiManager.auth.login(credentials);
      if (result.success) {
        user.value = result.data.user;
      }
      return result;
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  };
  
  const logout = async () => {
    try {
      await apiManager.auth.logout();
    } catch (error) {
      console.error('登出失败:', error);
    } finally {
      user.value = null;
    }
  };
  
  const register = async (userData) => {
    try {
      const result = await apiManager.auth.register(userData);
      return result;
    } catch (error) {
      console.error('注册失败:', error);
      throw error;
    }
  };
  
  // 监听认证状态变化
  const handleAuthLogout = () => {
    user.value = null;
  };
  
  onMounted(() => {
    checkAuthStatus();
    window.addEventListener('auth:logout', handleAuthLogout);
  });
  
  onUnmounted(() => {
    window.removeEventListener('auth:logout', handleAuthLogout);
  });
  
  return {
    user: readonly(user),
    loading: readonly(loading),
    isAuthenticated,
    login,
    logout,
    register,
    checkAuthStatus
  };
}

/**
 * 用户权限检查
 */
export function usePermissions() {
  const permissions = ref([]);
  const loading = ref(false);
  
  const loadPermissions = async () => {
    try {
      loading.value = true;
      const result = await apiManager.users.getCurrentUserPermissions();
      if (result.success) {
        permissions.value = result.data;
      }
    } catch (error) {
      console.error('获取权限失败:', error);
    } finally {
      loading.value = false;
    }
  };
  
  const hasPermission = (permission) => {
    return permissions.value.includes(permission);
  };
  
  const hasAnyPermission = (permissionList) => {
    return permissionList.some(permission => hasPermission(permission));
  };
  
  const hasAllPermissions = (permissionList) => {
    return permissionList.every(permission => hasPermission(permission));
  };
  
  onMounted(() => {
    loadPermissions();
  });
  
  return {
    permissions: readonly(permissions),
    loading: readonly(loading),
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    loadPermissions
  };
}

// ============= 业务相关组合式API =============

/**
 * 用户管理
 */
export function useUsers(initialParams = {}) {
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
  
  const createUser = async (userData) => {
    const result = await apiManager.users.createUser(userData);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  };
  
  const updateUser = async (userId, userData) => {
    const result = await apiManager.users.updateUser(userId, userData);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  };
  
  const deleteUser = async (userId) => {
    const result = await apiManager.users.deleteUser(userId);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  };
  
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
}

/**
 * 音频管理
 */
export function useAudios(initialParams = {}) {
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
  
  const deleteAudio = async (audioId) => {
    const result = await apiManager.audios.deleteAudio(audioId);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  };
  
  const updateAudio = async (audioId, audioData) => {
    const result = await apiManager.audios.updateAudio(audioId, audioData);
    if (result.success) {
      refresh(); // 刷新列表
    }
    return result;
  };
  
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
}

/**
 * 搜索功能
 */
export function useSearch(searchFn, options = {}) {
  const {
    debounceMs = 300,
    minLength = 2,
    immediate = false
  } = options;
  
  const query = ref('');
  const results = ref([]);
  const loading = ref(false);
  const error = ref(null);
  
  let debounceTimer = null;
  
  const search = async (searchQuery = query.value) => {
    if (searchQuery.length < minLength) {
      results.value = [];
      return;
    }
    
    try {
      loading.value = true;
      error.value = null;
      
      const result = await searchFn(searchQuery);
      if (result.success) {
        results.value = result.data;
      } else {
        throw new Error(result.error?.message || '搜索失败');
      }
    } catch (err) {
      error.value = err;
      results.value = [];
    } finally {
      loading.value = false;
    }
  };
  
  const debouncedSearch = (searchQuery) => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    
    debounceTimer = setTimeout(() => {
      search(searchQuery);
    }, debounceMs);
  };
  
  const clear = () => {
    query.value = '';
    results.value = [];
    error.value = null;
  };
  
  // 监听查询变化
  watch(query, (newQuery) => {
    if (newQuery.length >= minLength) {
      debouncedSearch(newQuery);
    } else {
      results.value = [];
    }
  });
  
  if (immediate && query.value) {
    search();
  }
  
  onUnmounted(() => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
  });
  
  return {
    query,
    results: readonly(results),
    loading: readonly(loading),
    error: readonly(error),
    search,
    clear
  };
}

// ============= 表单处理组合式API =============

/**
 * 表单验证和提交
 */
export function useForm(initialValues = {}, validationRules = {}, submitFn = null) {
  const values = reactive({ ...initialValues });
  const errors = reactive({});
  const touched = reactive({});
  const submitting = ref(false);
  
  const validate = (field = null) => {
    const fieldsToValidate = field ? [field] : Object.keys(validationRules);
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
        errors[fieldName] = fieldError;
        isValid = false;
      } else {
        delete errors[fieldName];
      }
    });
    
    return isValid;
  };
  
  const setFieldValue = (field, value) => {
    values[field] = value;
    touched[field] = true;
    validate(field);
  };
  
  const setFieldError = (field, error) => {
    errors[field] = error;
  };
  
  const clearErrors = () => {
    Object.keys(errors).forEach(key => {
      delete errors[key];
    });
  };
  
  const reset = () => {
    Object.assign(values, initialValues);
    clearErrors();
    Object.keys(touched).forEach(key => {
      touched[key] = false;
    });
  };
  
  const submit = async () => {
    if (!submitFn) {
      throw new Error('未提供提交函数');
    }
    
    // 标记所有字段为已触摸
    Object.keys(validationRules).forEach(field => {
      touched[field] = true;
    });
    
    const isValid = validate();
    if (!isValid) {
      throw new Error('表单验证失败');
    }
    
    try {
      submitting.value = true;
      const result = await submitFn(values);
      return result;
    } finally {
      submitting.value = false;
    }
  };
  
  const isValid = computed(() => Object.keys(errors).length === 0);
  
  return {
    values,
    errors: readonly(errors),
    touched: readonly(touched),
    submitting: readonly(submitting),
    isValid,
    validate,
    setFieldValue,
    setFieldError,
    clearErrors,
    reset,
    submit
  };
}

// ============= 通知系统组合式API =============

/**
 * 通知管理
 */
export function useNotifications() {
  const notifications = ref([]);
  
  const addNotification = (notification) => {
    const id = Date.now().toString();
    const newNotification = {
      id,
      type: 'info',
      duration: 5000,
      ...notification
    };
    
    notifications.value.push(newNotification);
    
    // 自动移除
    if (newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, newNotification.duration);
    }
    
    return id;
  };
  
  const removeNotification = (id) => {
    const index = notifications.value.findIndex(n => n.id === id);
    if (index > -1) {
      notifications.value.splice(index, 1);
    }
  };
  
  const clearAll = () => {
    notifications.value = [];
  };
  
  const success = (message, options = {}) => {
    return addNotification({
      type: 'success',
      title: '成功',
      message,
      ...options
    });
  };
  
  const error = (message, options = {}) => {
    return addNotification({
      type: 'error',
      title: '错误',
      message,
      duration: 0, // 错误消息不自动消失
      ...options
    });
  };
  
  const warning = (message, options = {}) => {
    return addNotification({
      type: 'warning',
      title: '警告',
      message,
      ...options
    });
  };
  
  const info = (message, options = {}) => {
    return addNotification({
      type: 'info',
      title: '信息',
      message,
      ...options
    });
  };
  
  return {
    notifications: readonly(notifications),
    addNotification,
    removeNotification,
    clearAll,
    success,
    error,
    warning,
    info
  };
}

// ============= 导出所有组合式API =============

export {
  // 基础API
  useApi,
  usePaginatedApi,
  useFileUpload,
  
  // 认证相关
  useAuth,
  usePermissions,
  
  // 业务相关
  useUsers,
  useAudios,
  useSearch,
  
  // 表单处理
  useForm,
  
  // 通知系统
  useNotifications
};

// ============= 使用示例 =============

/*
// 在Vue组件中使用

<template>
  <div>
    <!-- 用户列表 -->
    <div v-if="loading">加载中...</div>
    <div v-else-if="error">错误: {{ error.message }}</div>
    <div v-else>
      <div v-for="user in users" :key="user.id">
        {{ user.full_name }} - {{ user.email }}
      </div>
      
      <!-- 分页 -->
      <div v-if="pagination">
        <button @click="prevPage" :disabled="!pagination.has_prev">上一页</button>
        <span>第 {{ pagination.page }} 页，共 {{ pagination.pages }} 页</span>
        <button @click="nextPage" :disabled="!pagination.has_next">下一页</button>
      </div>
    </div>
    
    <!-- 文件上传 -->
    <div>
      <input type="file" @change="handleFileSelect" accept=".mp3,.wav" />
      <button @click="handleUpload" :disabled="uploading">上传</button>
      <div v-if="uploading">上传进度: {{ progress }}%</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useUsers, useFileUpload } from './vue-api-composables.js';
import { apiManager } from './api-client-example.js';

// 用户列表
const {
  users,
  pagination,
  loading,
  error,
  updateParams,
  nextPage,
  prevPage
} = useUsers();

// 文件上传
const selectedFile = ref(null);
const {
  uploading,
  progress,
  upload
} = useFileUpload(
  (file, metadata, onProgress) => apiManager.audios.uploadAudio(file, metadata, onProgress)
);

const handleFileSelect = (event) => {
  selectedFile.value = event.target.files[0];
};

const handleUpload = async () => {
  if (selectedFile.value) {
    try {
      await upload(selectedFile.value, {
        script_id: 1,
        role_name: '主角'
      });
      alert('上传成功!');
    } catch (error) {
      alert('上传失败: ' + error.message);
    }
  }
};

// 搜索用户
const handleSearch = (keyword) => {
  updateParams({ keyword, page: 1 });
};
</script>
*/