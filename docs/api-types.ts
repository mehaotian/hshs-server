// API 接口类型定义文件
// 为前端项目提供完整的类型支持

// ============= 基础响应类型 =============

/**
 * 基础响应接口
 */
export interface BaseResponse {
  success: boolean;
  message: string;
  timestamp: string;
  request_id?: string;
}

/**
 * 成功响应接口
 */
export interface SuccessResponse<T = any> extends BaseResponse {
  success: true;
  data: T;
}

/**
 * 错误响应接口
 */
export interface ErrorResponse extends BaseResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
  };
  data?: null;
}

/**
 * 分页信息接口
 */
export interface Pagination {
  page: number;
  size: number;
  total: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

/**
 * 分页响应接口
 */
export interface PaginatedResponse<T = any> extends BaseResponse {
  success: true;
  data: T[];
  pagination: Pagination;
}

/**
 * API响应类型联合
 */
export type ApiResponse<T = any> = SuccessResponse<T> | ErrorResponse;
export type ApiPaginatedResponse<T = any> =
  | PaginatedResponse<T>
  | ErrorResponse;

// ============= 用户相关类型 =============

/**
 * 用户基础信息
 */
export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  avatar_url?: string;
  phone?: string;
  last_login?: string;
  login_count: number;
  failed_login_attempts: number;
  created_at: string;
  updated_at: string;
}

/**
 * 用户档案信息
 */
export interface UserProfile {
  id: number;
  user_id: number;
  bio?: string;
  voice_experience?: string;
  voice_characteristics?: string;
  specialties?: string[];
  preferred_roles?: string[];
  availability?: string;
  contact_preferences?: Record<string, any>;
  social_links?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

/**
 * 用户创建请求
 */
export interface UserCreateRequest {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
  full_name: string;
  phone?: string;
}

/**
 * 用户更新请求
 */
export interface UserUpdateRequest {
  email?: string;
  full_name?: string;
  phone?: string;
  is_active?: boolean;
}

/**
 * 用户统计信息
 */
export interface UserStatistics {
  total_users: number;
  active_users: number;
  new_users_today: number;
  new_users_this_week: number;
  new_users_this_month: number;
  user_growth_rate: number;
}

// ============= 认证相关类型 =============

/**
 * 登录请求
 */
export interface LoginRequest {
  username: string; // 可以是用户名或邮箱
  password: string;
}

/**
 * 注册请求
 */
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
  full_name: string;
}

/**
 * Token信息
 */
export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

/**
 * 刷新Token请求
 */
export interface RefreshTokenRequest {
  refresh_token: string;
}

/**
 * 密码修改请求
 */
export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

/**
 * 忘记密码请求
 */
export interface ForgotPasswordRequest {
  email: string;
}

/**
 * 重置密码请求
 */
export interface ResetPasswordRequest {
  token: string;
  new_password: string;
  confirm_password: string;
}

// ============= 角色权限相关类型 =============

/**
 * 权限信息
 */
export interface Permission {
  id: number;
  name: string;
  description?: string;
  resource: string;
  action: string;
  created_at: string;
  updated_at: string;
}

/**
 * 角色信息
 */
export interface Role {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
  permissions: Permission[];
  user_count: number;
  created_at: string;
  updated_at: string;
}

/**
 * 角色创建请求
 */
export interface RoleCreateRequest {
  name: string;
  description?: string;
  permission_ids: number[];
}

/**
 * 角色更新请求
 */
export interface RoleUpdateRequest {
  name?: string;
  description?: string;
  is_active?: boolean;
  permission_ids?: number[];
}

/**
 * 用户角色分配
 */
export interface UserRoleAssignment {
  user_id: number;
  role_ids: number[];
}

/**
 * 角色统计信息
 */
export interface RoleStatistics {
  total_roles: number;
  active_roles: number;
  total_permissions: number;
  most_used_roles: Array<{
    role_name: string;
    user_count: number;
  }>;
}

// ============= 剧本相关类型 =============

/**
 * 剧本信息
 */
export interface Script {
  id: number;
  title: string;
  description?: string;
  author: string;
  genre?: string;
  tags?: string[];
  status: "draft" | "published" | "archived";
  content?: string;
  file_path?: string;
  file_size?: number;
  word_count?: number;
  estimated_duration?: number;
  cover_image?: string;
  created_by: number;
  created_at: string;
  updated_at: string;
  creator: User;
  chapters: Chapter[];
  assignments: ScriptAssignment[];
}

/**
 * 章节信息
 */
export interface Chapter {
  id: number;
  script_id: number;
  title: string;
  content: string;
  order_index: number;
  estimated_duration?: number;
  word_count?: number;
  created_at: string;
  updated_at: string;
}

/**
 * 剧本分配
 */
export interface ScriptAssignment {
  id: number;
  script_id: number;
  user_id: number;
  role_name: string;
  character_description?: string;
  chapter_ids: number[];
  status: "assigned" | "in_progress" | "completed" | "reviewed";
  assigned_at: string;
  deadline?: string;
  completed_at?: string;
  notes?: string;
  user: User;
  script: Script;
}

/**
 * 剧本创建请求
 */
export interface ScriptCreateRequest {
  title: string;
  description?: string;
  author: string;
  genre?: string;
  tags?: string[];
  content?: string;
}

/**
 * 剧本更新请求
 */
export interface ScriptUpdateRequest {
  title?: string;
  description?: string;
  author?: string;
  genre?: string;
  tags?: string[];
  status?: "draft" | "published" | "archived";
  content?: string;
}

// ============= 音频相关类型 =============

/**
 * 音频文件信息
 */
export interface Audio {
  id: number;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size: number;
  duration?: number;
  format: string;
  sample_rate?: number;
  bit_rate?: number;
  channels?: number;
  script_id?: number;
  chapter_id?: number;
  user_id: number;
  role_name?: string;
  status: "uploaded" | "processing" | "processed" | "approved" | "rejected";
  upload_date: string;
  processed_date?: string;
  metadata?: Record<string, any>;
  tags?: string[];
  notes?: string;
  user: User;
  script?: Script;
  chapter?: Chapter;
  reviews: AudioReview[];
  feedback: AudioFeedback[];
}

/**
 * 音频审听记录
 */
export interface AudioReview {
  id: number;
  audio_id: number;
  reviewer_id: number;
  status: "pending" | "approved" | "rejected" | "needs_revision";
  score?: number;
  comments?: string;
  reviewed_at: string;
  reviewer: User;
}

/**
 * 音频反馈
 */
export interface AudioFeedback {
  id: number;
  audio_id: number;
  user_id: number;
  feedback_type: "quality" | "performance" | "technical" | "other";
  rating?: number;
  comments?: string;
  timestamp?: number; // 音频中的时间点
  created_at: string;
  user: User;
}

/**
 * 音频上传请求
 */
export interface AudioUploadRequest {
  file: File;
  script_id?: number;
  chapter_id?: number;
  role_name?: string;
  notes?: string;
  tags?: string[];
}

/**
 * 音频更新请求
 */
export interface AudioUpdateRequest {
  filename?: string;
  role_name?: string;
  status?: "uploaded" | "processing" | "processed" | "approved" | "rejected";
  notes?: string;
  tags?: string[];
}

// ============= 搜索和过滤类型 =============

/**
 * 基础搜索参数
 */
export interface BaseSearchParams {
  page?: number;
  size?: number;
  keyword?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

/**
 * 用户搜索参数
 */
export interface UserSearchParams extends BaseSearchParams {
  is_active?: boolean;
  is_verified?: boolean;
  role_id?: number;
  created_after?: string;
  created_before?: string;
}

/**
 * 剧本搜索参数
 */
export interface ScriptSearchParams extends BaseSearchParams {
  author?: string;
  genre?: string;
  status?: "draft" | "published" | "archived";
  tags?: string[];
  created_by?: number;
}

/**
 * 音频搜索参数
 */
export interface AudioSearchParams extends BaseSearchParams {
  script_id?: number;
  user_id?: number;
  status?: "uploaded" | "processing" | "processed" | "approved" | "rejected";
  format?: string;
  duration_min?: number;
  duration_max?: number;
  upload_after?: string;
  upload_before?: string;
}

/**
 * 角色搜索参数
 */
export interface RoleSearchParams extends BaseSearchParams {
  is_active?: boolean;
  has_permissions?: boolean;
}

// ============= API客户端接口 =============

/**
 * API客户端配置
 */
export interface ApiClientConfig {
  baseURL?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

/**
 * 请求配置
 */
export interface RequestConfig {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  headers?: Record<string, string>;
  params?: Record<string, any>;
  data?: any;
  timeout?: number;
}

// ============= Hook 相关类型 =============

/**
 * API Hook 返回值
 */
export interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * 分页 Hook 返回值
 */
export interface UsePaginatedApiResult<T> {
  data: T[];
  pagination: Pagination | null;
  loading: boolean;
  error: Error | null;
  params: BaseSearchParams;
  updateParams: (newParams: Partial<BaseSearchParams>) => void;
  refetch: () => Promise<void>;
}

/**
 * 认证 Hook 返回值
 */
export interface UseAuthResult {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<ApiResponse<Token>>;
  logout: () => Promise<void>;
  register: (userData: RegisterRequest) => Promise<ApiResponse<User>>;
  checkAuthStatus: () => Promise<void>;
}

// ============= 表单相关类型 =============

/**
 * 表单字段错误
 */
export interface FieldError {
  field: string;
  message: string;
}

/**
 * 表单验证结果
 */
export interface ValidationResult {
  isValid: boolean;
  errors: FieldError[];
}

/**
 * 表单状态
 */
export interface FormState<T> {
  values: T;
  errors: Record<keyof T, string>;
  touched: Record<keyof T, boolean>;
  isSubmitting: boolean;
  isValid: boolean;
}

// ============= 文件上传相关类型 =============

/**
 * 文件上传进度
 */
export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

/**
 * 文件上传状态
 */
export interface UploadStatus {
  status: "idle" | "uploading" | "success" | "error";
  progress?: UploadProgress;
  error?: string;
  result?: any;
}

// ============= 通知相关类型 =============

/**
 * 通知类型
 */
export type NotificationType = "success" | "error" | "warning" | "info";

/**
 * 通知消息
 */
export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  duration?: number;
  actions?: Array<{
    label: string;
    action: () => void;
  }>;
}

// ============= 导出所有类型 =============

export type {
  // 响应类型
  BaseResponse,
  SuccessResponse,
  ErrorResponse,
  Pagination,
  PaginatedResponse,
  ApiResponse,
  ApiPaginatedResponse,

  // 用户类型
  User,
  UserProfile,
  UserCreateRequest,
  UserUpdateRequest,
  UserStatistics,

  // 认证类型
  LoginRequest,
  RegisterRequest,
  Token,
  RefreshTokenRequest,
  PasswordChangeRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,

  // 角色权限类型
  Permission,
  Role,
  RoleCreateRequest,
  RoleUpdateRequest,
  UserRoleAssignment,
  RoleStatistics,

  // 剧本类型
  Script,
  Chapter,
  ScriptAssignment,
  ScriptCreateRequest,
  ScriptUpdateRequest,

  // 音频类型
  Audio,
  AudioReview,
  AudioFeedback,
  AudioUploadRequest,
  AudioUpdateRequest,

  // 搜索类型
  BaseSearchParams,
  UserSearchParams,
  ScriptSearchParams,
  AudioSearchParams,
  RoleSearchParams,

  // API客户端类型
  ApiClientConfig,
  RequestConfig,

  // Hook类型
  UseApiResult,
  UsePaginatedApiResult,
  UseAuthResult,

  // 表单类型
  FieldError,
  ValidationResult,
  FormState,

  // 文件上传类型
  UploadProgress,
  UploadStatus,

  // 通知类型
  NotificationType,
  Notification,
};

// ============= 常量定义 =============

/**
 * API 端点常量
 */
export const API_ENDPOINTS = {
  // 认证相关
  AUTH: {
    LOGIN: "/auth/login",
    REGISTER: "/auth/register",
    REFRESH: "/auth/refresh",
    LOGOUT: "/auth/logout",
    ME: "/auth/me",
    CHANGE_PASSWORD: "/auth/change-password",
    FORGOT_PASSWORD: "/auth/forgot-password",
    RESET_PASSWORD: "/auth/reset-password",
    VERIFY_TOKEN: "/auth/verify-token",
  },

  // 用户相关
  USERS: {
    LIST: "/users",
    CREATE: "/users",
    DETAIL: (id: number) => `/users/${id}`,
    UPDATE: (id: number) => `/users/${id}`,
    DELETE: (id: number) => `/users/${id}`,
    STATISTICS: "/users/statistics/overview",
    PERMISSIONS: "/users/me/permissions",
  },

  // 角色权限相关
  ROLES: {
    LIST: "/roles",
    CREATE: "/roles",
    DETAIL: (id: number) => `/roles/${id}`,
    UPDATE: (id: number) => `/roles/${id}`,
    DELETE: (id: number) => `/roles/${id}`,
    PERMISSIONS: "/roles/permissions",
    STATISTICS: "/roles/statistics",
  },

  // 剧本相关
  SCRIPTS: {
    LIST: "/scripts",
    CREATE: "/scripts",
    DETAIL: (id: number) => `/scripts/${id}`,
    UPDATE: (id: number) => `/scripts/${id}`,
    DELETE: (id: number) => `/scripts/${id}`,
    CHAPTERS: (id: number) => `/scripts/${id}/chapters`,
    ASSIGNMENTS: (id: number) => `/scripts/${id}/assignments`,
  },

  // 音频相关
  AUDIOS: {
    LIST: "/audios",
    UPLOAD: "/audios/upload",
    DETAIL: (id: number) => `/audios/${id}`,
    UPDATE: (id: number) => `/audios/${id}`,
    DELETE: (id: number) => `/audios/${id}`,
    SEARCH: "/audios/search",
    REVIEWS: "/audios/search/reviews",
    FEEDBACK: "/audios/search/feedback",
  },
} as const;

/**
 * HTTP 状态码常量
 */
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  VALIDATION_ERROR: 422,
  RATE_LIMIT: 429,
  INTERNAL_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
} as const;

/**
 * 错误码常量
 */
export const ERROR_CODES = {
  BAD_REQUEST: "BAD_REQUEST",
  UNAUTHORIZED: "UNAUTHORIZED",
  FORBIDDEN: "FORBIDDEN",
  NOT_FOUND: "NOT_FOUND",
  VALIDATION_ERROR: "VALIDATION_ERROR",
  RATE_LIMIT_EXCEEDED: "RATE_LIMIT_EXCEEDED",
  INTERNAL_ERROR: "INTERNAL_ERROR",
  TOKEN_EXPIRED: "TOKEN_EXPIRED",
  INVALID_CREDENTIALS: "INVALID_CREDENTIALS",
  USER_NOT_FOUND: "USER_NOT_FOUND",
  EMAIL_ALREADY_EXISTS: "EMAIL_ALREADY_EXISTS",
  USERNAME_ALREADY_EXISTS: "USERNAME_ALREADY_EXISTS",
} as const;

/**
 * 默认配置常量
 */
export const DEFAULT_CONFIG = {
  API_BASE_URL: "http://localhost:8000/api/v1",
  REQUEST_TIMEOUT: 30000,
  PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
  TOKEN_STORAGE_KEY: "access_token",
  REFRESH_TOKEN_STORAGE_KEY: "refresh_token",
} as const;
