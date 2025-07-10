# 数据库设计方案

## 概述

本文档描述了绘声绘社管理系统的数据库设计方案，包括用户管理、角色权限、剧本管理、音频管理、部门管理等核心模块的表结构设计。

## 设计原则

1. **规范化设计**：遵循数据库范式，减少数据冗余
2. **性能优化**：合理设计索引，优化查询性能
3. **扩展性**：预留扩展字段，支持业务发展
4. **数据完整性**：通过约束保证数据一致性
5. **安全性**：敏感数据加密存储

## 表结构设计

### 1. 用户管理模块

#### 1.1 用户表 (users)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    real_name VARCHAR(50) COMMENT '真实姓名',
    display_name VARCHAR(50) COMMENT '显示名称',
    phone VARCHAR(20) COMMENT '手机号',
    avatar_url VARCHAR(500) COMMENT '头像URL',
    bio TEXT COMMENT '个人简介',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '状态：1-正常，2-禁用，3-待激活',
    last_login_at TIMESTAMP WITH TIME ZONE COMMENT '最后登录时间',
    email_verified_at TIMESTAMP WITH TIME ZONE COMMENT '邮箱验证时间',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_users_status CHECK (status IN (1, 2, 3))
);
```

#### 1.2 用户配置表 (user_profiles)

```sql
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai' COMMENT '时区',
    language VARCHAR(10) DEFAULT 'zh-CN' COMMENT '语言',
    theme VARCHAR(20) DEFAULT 'light' COMMENT '主题',
    notification_settings JSONB COMMENT '通知设置',
    privacy_settings JSONB COMMENT '隐私设置',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

### 2. 角色权限模块

#### 2.1 角色表 (roles)

```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL COMMENT '角色名称',
    display_name VARCHAR(100) NOT NULL COMMENT '显示名称',
    description TEXT COMMENT '角色描述',
    is_system BOOLEAN DEFAULT FALSE COMMENT '是否为系统角色',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '状态：1-正常，2-禁用',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_roles_status CHECK (status IN (1, 2))
);
```

#### 2.2 权限表 (permissions)

```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL COMMENT '权限名称',
    display_name VARCHAR(100) NOT NULL COMMENT '显示名称',
    description TEXT COMMENT '权限描述',
    resource VARCHAR(50) NOT NULL COMMENT '资源',
    action VARCHAR(50) NOT NULL COMMENT '操作',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

#### 2.3 用户角色关联表 (user_roles)

```sql
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE COMMENT '过期时间',
    
    UNIQUE(user_id, role_id)
);
```

#### 2.4 角色权限关联表 (role_permissions)

```sql
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    
    UNIQUE(role_id, permission_id)
);
```

### 3. 部门管理模块

#### 3.1 部门表 (departments)

```sql
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '部门名称',
    parent_id INTEGER REFERENCES departments(id) ON DELETE SET NULL COMMENT '上级部门ID',
    manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL COMMENT '部门负责人ID',
    manager_phone VARCHAR(20) COMMENT '负责人手机号',
    manager_email VARCHAR(100) COMMENT '负责人邮箱',
    description TEXT COMMENT '部门描述',
    sort_order INTEGER DEFAULT 0 NOT NULL COMMENT '排序',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '部门状态：1-正常，2-停用',
    level INTEGER DEFAULT 1 NOT NULL COMMENT '部门层级',
    path VARCHAR(500) COMMENT '部门路径',
    remarks TEXT COMMENT '备注',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL COMMENT '创建人ID',
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL COMMENT '更新人ID',
    
    CONSTRAINT ck_departments_status CHECK (status IN (1, 2)),
    CONSTRAINT ck_departments_level CHECK (level >= 1 AND level <= 10),
    CONSTRAINT ck_departments_sort_order CHECK (sort_order >= 0),
    CONSTRAINT ck_departments_no_self_reference CHECK (id != parent_id),
    UNIQUE(name, parent_id)
);
```

#### 3.2 部门成员表 (department_members)

```sql
CREATE TABLE department_members (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE COMMENT '部门ID',
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE COMMENT '用户ID',
    position VARCHAR(100) COMMENT '职位',
    is_manager BOOLEAN DEFAULT FALSE NOT NULL COMMENT '是否为负责人',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '成员状态：1-正常，2-离职',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL COMMENT '加入时间',
    left_at TIMESTAMP WITH TIME ZONE COMMENT '离职时间',
    remarks TEXT COMMENT '备注',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_department_members_status CHECK (status IN (1, 2)),
    UNIQUE(department_id, user_id)
);
```

### 4. 剧社管理模块

#### 4.1 剧社表 (drama_societies)

```sql
CREATE TABLE drama_societies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL COMMENT '剧社名称',
    description TEXT COMMENT '剧社描述',
    logo_url VARCHAR(500) COMMENT 'Logo URL',
    founder_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT COMMENT '创始人ID',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '状态：1-正常，2-停用',
    member_count INTEGER DEFAULT 0 COMMENT '成员数量',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_drama_societies_status CHECK (status IN (1, 2)),
    CONSTRAINT ck_drama_societies_member_count CHECK (member_count >= 0)
);
```

#### 4.2 剧本表 (scripts)

```sql
CREATE TABLE scripts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL COMMENT '剧本标题',
    description TEXT COMMENT '剧本描述',
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT COMMENT '作者ID',
    drama_society_id INTEGER REFERENCES drama_societies(id) ON DELETE SET NULL COMMENT '所属剧社ID',
    genre VARCHAR(50) COMMENT '类型',
    tags JSONB COMMENT '标签',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '状态：1-草稿，2-审核中，3-已发布，4-已完结',
    word_count INTEGER DEFAULT 0 COMMENT '字数',
    chapter_count INTEGER DEFAULT 0 COMMENT '章节数',
    cover_url VARCHAR(500) COMMENT '封面URL',
    published_at TIMESTAMP WITH TIME ZONE COMMENT '发布时间',
    completed_at TIMESTAMP WITH TIME ZONE COMMENT '完结时间',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_scripts_status CHECK (status IN (1, 2, 3, 4)),
    CONSTRAINT ck_scripts_word_count CHECK (word_count >= 0),
    CONSTRAINT ck_scripts_chapter_count CHECK (chapter_count >= 0)
);
```

#### 4.3 剧本章节表 (script_chapters)

```sql
CREATE TABLE script_chapters (
    id SERIAL PRIMARY KEY,
    script_id INTEGER NOT NULL REFERENCES scripts(id) ON DELETE CASCADE COMMENT '剧本ID',
    title VARCHAR(200) NOT NULL COMMENT '章节标题',
    content TEXT COMMENT '章节内容',
    chapter_number INTEGER NOT NULL COMMENT '章节序号',
    word_count INTEGER DEFAULT 0 COMMENT '字数',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '状态：1-草稿，2-已发布',
    published_at TIMESTAMP WITH TIME ZONE COMMENT '发布时间',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_script_chapters_status CHECK (status IN (1, 2)),
    CONSTRAINT ck_script_chapters_word_count CHECK (word_count >= 0),
    CONSTRAINT ck_script_chapters_chapter_number CHECK (chapter_number > 0),
    UNIQUE(script_id, chapter_number)
);
```

#### 4.4 剧本分配表 (script_assignments)

```sql
CREATE TABLE script_assignments (
    id SERIAL PRIMARY KEY,
    script_id INTEGER NOT NULL REFERENCES scripts(id) ON DELETE CASCADE COMMENT '剧本ID',
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE COMMENT '用户ID',
    role VARCHAR(50) NOT NULL COMMENT '角色：author-作者，editor-编辑，reviewer-审核员',
    assigned_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT COMMENT '分配人ID',
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL COMMENT '分配时间',
    
    CONSTRAINT ck_script_assignments_role CHECK (role IN ('author', 'editor', 'reviewer')),
    UNIQUE(script_id, user_id, role)
);
```

### 5. 音频管理模块

#### 5.1 配音录制表 (cv_recordings)

```sql
CREATE TABLE cv_recordings (
    id SERIAL PRIMARY KEY,
    script_id INTEGER NOT NULL REFERENCES scripts(id) ON DELETE CASCADE COMMENT '剧本ID',
    chapter_id INTEGER REFERENCES script_chapters(id) ON DELETE CASCADE COMMENT '章节ID',
    cv_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE COMMENT '配音员ID',
    character_name VARCHAR(100) COMMENT '角色名称',
    audio_url VARCHAR(500) NOT NULL COMMENT '音频文件URL',
    duration INTEGER COMMENT '时长（秒）',
    file_size BIGINT COMMENT '文件大小（字节）',
    format VARCHAR(20) COMMENT '音频格式',
    quality VARCHAR(20) COMMENT '音质',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '状态：1-录制中，2-待审核，3-已通过，4-需重录',
    submitted_at TIMESTAMP WITH TIME ZONE COMMENT '提交时间',
    reviewed_at TIMESTAMP WITH TIME ZONE COMMENT '审核时间',
    reviewer_id INTEGER REFERENCES users(id) ON DELETE SET NULL COMMENT '审核员ID',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_cv_recordings_status CHECK (status IN (1, 2, 3, 4)),
    CONSTRAINT ck_cv_recordings_duration CHECK (duration >= 0),
    CONSTRAINT ck_cv_recordings_file_size CHECK (file_size >= 0)
);
```

#### 5.2 审核记录表 (review_records)

```sql
CREATE TABLE review_records (
    id SERIAL PRIMARY KEY,
    recording_id INTEGER NOT NULL REFERENCES cv_recordings(id) ON DELETE CASCADE COMMENT '录音ID',
    reviewer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE COMMENT '审核员ID',
    status INTEGER NOT NULL COMMENT '审核结果：3-通过，4-需重录',
    feedback TEXT COMMENT '审核意见',
    score INTEGER COMMENT '评分（1-10）',
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL COMMENT '审核时间',
    
    CONSTRAINT ck_review_records_status CHECK (status IN (3, 4)),
    CONSTRAINT ck_review_records_score CHECK (score >= 1 AND score <= 10)
);
```

#### 5.3 反馈记录表 (feedback_records)

```sql
CREATE TABLE feedback_records (
    id SERIAL PRIMARY KEY,
    recording_id INTEGER NOT NULL REFERENCES cv_recordings(id) ON DELETE CASCADE COMMENT '录音ID',
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE COMMENT '反馈用户ID',
    type VARCHAR(20) NOT NULL COMMENT '反馈类型：suggestion-建议，issue-问题，praise-表扬',
    content TEXT NOT NULL COMMENT '反馈内容',
    status INTEGER DEFAULT 1 NOT NULL COMMENT '状态：1-待处理，2-已处理，3-已忽略',
    processed_by INTEGER REFERENCES users(id) ON DELETE SET NULL COMMENT '处理人ID',
    processed_at TIMESTAMP WITH TIME ZONE COMMENT '处理时间',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_feedback_records_type CHECK (type IN ('suggestion', 'issue', 'praise')),
    CONSTRAINT ck_feedback_records_status CHECK (status IN (1, 2, 3))
);
```

#### 5.4 音频模板表 (audio_templates)

```sql
CREATE TABLE audio_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    format VARCHAR(20) NOT NULL COMMENT '音频格式',
    sample_rate INTEGER NOT NULL COMMENT '采样率',
    bit_rate INTEGER NOT NULL COMMENT '比特率',
    channels INTEGER NOT NULL COMMENT '声道数',
    quality_level VARCHAR(20) NOT NULL COMMENT '质量等级',
    max_duration INTEGER COMMENT '最大时长（秒）',
    max_file_size BIGINT COMMENT '最大文件大小（字节）',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否为默认模板',
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT COMMENT '创建人ID',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT ck_audio_templates_sample_rate CHECK (sample_rate > 0),
    CONSTRAINT ck_audio_templates_bit_rate CHECK (bit_rate > 0),
    CONSTRAINT ck_audio_templates_channels CHECK (channels > 0),
    CONSTRAINT ck_audio_templates_max_duration CHECK (max_duration > 0),
    CONSTRAINT ck_audio_templates_max_file_size CHECK (max_file_size > 0)
);
```

## 索引设计

### 基础索引

```sql
-- 用户表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at);

-- 角色表索引
CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_roles_status ON roles(status);

-- 权限表索引
CREATE INDEX idx_permissions_resource_action ON permissions(resource, action);

-- 部门表索引
CREATE INDEX idx_departments_parent_id ON departments(parent_id);
CREATE INDEX idx_departments_manager_id ON departments(manager_id);
CREATE INDEX idx_departments_status ON departments(status);
CREATE INDEX idx_departments_level ON departments(level);
CREATE INDEX idx_departments_sort_order ON departments(sort_order);
CREATE INDEX idx_departments_name ON departments(name);
CREATE INDEX idx_departments_path ON departments(path);
CREATE INDEX idx_departments_created_at ON departments(created_at);

-- 部门成员表索引
CREATE INDEX idx_department_members_dept_id ON department_members(department_id);
CREATE INDEX idx_department_members_user_id ON department_members(user_id);
CREATE INDEX idx_department_members_status ON department_members(status);
CREATE INDEX idx_department_members_is_manager ON department_members(is_manager);
CREATE INDEX idx_department_members_joined_at ON department_members(joined_at);

-- 剧本表索引
CREATE INDEX idx_scripts_author_id ON scripts(author_id);
CREATE INDEX idx_scripts_drama_society_id ON scripts(drama_society_id);
CREATE INDEX idx_scripts_status ON scripts(status);
CREATE INDEX idx_scripts_published_at ON scripts(published_at);
CREATE INDEX idx_scripts_title ON scripts USING gin(to_tsvector('chinese', title));

-- 配音录制表索引
CREATE INDEX idx_cv_recordings_script_id ON cv_recordings(script_id);
CREATE INDEX idx_cv_recordings_cv_user_id ON cv_recordings(cv_user_id);
CREATE INDEX idx_cv_recordings_status ON cv_recordings(status);
CREATE INDEX idx_cv_recordings_submitted_at ON cv_recordings(submitted_at);
```

### 复合索引

```sql
-- 用户角色复合索引
CREATE INDEX idx_user_roles_user_role ON user_roles(user_id, role_id);

-- 部门复合索引
CREATE INDEX idx_departments_parent_status ON departments(parent_id, status);
CREATE INDEX idx_departments_level_sort ON departments(level, sort_order);
CREATE INDEX idx_department_members_dept_status ON department_members(department_id, status);
CREATE INDEX idx_department_members_user_status ON department_members(user_id, status);

-- 剧本复合索引
CREATE INDEX idx_scripts_society_status ON scripts(drama_society_id, status);
CREATE INDEX idx_script_chapters_script_number ON script_chapters(script_id, chapter_number);

-- 配音复合索引
CREATE INDEX idx_cv_recordings_script_status ON cv_recordings(script_id, status);
CREATE INDEX idx_cv_recordings_user_status ON cv_recordings(cv_user_id, status);
```

## 触发器设计

### 更新时间触发器

```sql
-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为各表创建更新时间触发器
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_departments_updated_at
    BEFORE UPDATE ON departments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_department_members_updated_at
    BEFORE UPDATE ON department_members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 其他表的触发器...
```

## 分区策略

### 操作日志表分区（按月）

```sql
-- 创建分区主表
CREATE TABLE operation_logs (
    id BIGSERIAL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 创建月度分区
CREATE TABLE operation_logs_2024_01 PARTITION OF operation_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE operation_logs_2024_02 PARTITION OF operation_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- 创建分区索引
CREATE INDEX idx_operation_logs_2024_01_user_id ON operation_logs_2024_01(user_id);
CREATE INDEX idx_operation_logs_2024_01_action ON operation_logs_2024_01(action);
```

## 数据完整性约束

### 检查约束

```sql
-- 用户状态约束
ALTER TABLE users ADD CONSTRAINT ck_users_status CHECK (status IN (1, 2, 3));

-- 部门层级约束
ALTER TABLE departments ADD CONSTRAINT ck_departments_level CHECK (level >= 1 AND level <= 10);

-- 评分约束
ALTER TABLE review_records ADD CONSTRAINT ck_review_records_score CHECK (score >= 1 AND score <= 10);
```

### 外键约束

```sql
-- 部门自引用约束
ALTER TABLE departments ADD CONSTRAINT fk_departments_parent 
    FOREIGN KEY (parent_id) REFERENCES departments(id) ON DELETE SET NULL;

-- 防止部门自引用
ALTER TABLE departments ADD CONSTRAINT ck_departments_no_self_reference 
    CHECK (id != parent_id);
```

## 性能优化建议

### 查询优化

1. **使用适当的索引**：为经常查询的字段创建索引
2. **避免全表扫描**：使用 WHERE 子句限制查询范围
3. **使用 LIMIT**：分页查询时使用 LIMIT 和 OFFSET
4. **优化 JOIN**：使用适当的 JOIN 类型，避免笛卡尔积
5. **使用 EXPLAIN ANALYZE**：分析查询执行计划

### 数据库配置优化

```sql
-- 调整工作内存
SET work_mem = '256MB';

-- 调整共享缓冲区
SET shared_buffers = '1GB';

-- 启用查询计划缓存
SET plan_cache_mode = 'auto';

-- 调整检查点设置
SET checkpoint_completion_target = 0.9;
```

### 监控指标

1. **连接数**：监控数据库连接数
2. **查询性能**：监控慢查询
3. **缓存命中率**：监控缓冲区命中率
4. **磁盘使用率**：监控磁盘空间使用
5. **锁等待**：监控锁等待情况

## 备份与恢复策略

### 备份策略

1. **全量备份**：每日凌晨进行全量备份
2. **增量备份**：每小时进行 WAL 归档
3. **异地备份**：将备份文件同步到异地存储
4. **备份验证**：定期验证备份文件完整性

### 恢复策略

1. **时间点恢复**：支持恢复到任意时间点
2. **表级恢复**：支持单表数据恢复
3. **灾难恢复**：制定完整的灾难恢复计划

## 数据迁移方案

### Alembic 配置

```python
# alembic.ini 配置
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://user:password@localhost/dbname

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME
```

### 数据初始化脚本

```sql
-- 初始化系统角色
INSERT INTO roles (name, display_name, description, is_system) VALUES
('admin', '系统管理员', '拥有所有权限的系统管理员', true),
('manager', '部门经理', '部门管理权限', false),
('member', '普通成员', '基础权限', false);

-- 初始化系统权限
INSERT INTO permissions (name, display_name, description, resource, action) VALUES
('user:create', '创建用户', '创建新用户的权限', 'user', 'create'),
('user:read', '查看用户', '查看用户信息的权限', 'user', 'read'),
('user:update', '更新用户', '更新用户信息的权限', 'user', 'update'),
('user:delete', '删除用户', '删除用户的权限', 'user', 'delete'),
('department:create', '创建部门', '创建新部门的权限', 'department', 'create'),
('department:read', '查看部门', '查看部门信息的权限', 'department', 'read'),
('department:update', '更新部门', '更新部门信息的权限', 'department', 'update'),
('department:delete', '删除部门', '删除部门的权限', 'department', 'delete');

-- 初始化根部门
INSERT INTO departments (name, description, level, path, created_by) VALUES
('绘声绘社', '绘声绘社根部门', 1, '/1/', 1);
```

## 总结

本数据库设计方案涵盖了绘声绘社管理系统的核心功能模块，包括：

1. **用户管理**：完整的用户信息和配置管理
2. **角色权限**：灵活的 RBAC 权限控制系统
3. **部门管理**：支持多级层级的部门组织架构
4. **剧本管理**：剧社、剧本、章节的完整管理
5. **音频管理**：配音录制、审核、反馈的全流程管理

设计遵循了数据库设计的最佳实践，确保了数据的完整性、一致性和性能，同时具备良好的扩展性以支持未来的业务发展。
