-- =============================================================================
-- 有声剧本管理系统数据库初始化脚本
-- =============================================================================
-- 此脚本用于 Docker 环境下的数据库初始化
-- 在 PostgreSQL 容器启动时自动执行

-- 设置客户端编码
SET client_encoding = 'UTF8';

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- 创建自定义类型
DO $$ 
BEGIN
    -- 用户状态枚举
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status') THEN
        CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended', 'deleted');
    END IF;
    
    -- 剧本状态枚举
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'script_status') THEN
        CREATE TYPE script_status AS ENUM ('draft', 'in_progress', 'completed', 'published', 'archived');
    END IF;
    
    -- 音频状态枚举
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audio_status') THEN
        CREATE TYPE audio_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'approved', 'rejected');
    END IF;
    
    -- 审听状态枚举
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_status') THEN
        CREATE TYPE review_status AS ENUM ('pending', 'approved', 'rejected', 'needs_revision');
    END IF;
END $$;

-- 创建函数：更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 创建函数：生成唯一的文件名
CREATE OR REPLACE FUNCTION generate_unique_filename(original_name TEXT)
RETURNS TEXT AS $$
DECLARE
    file_extension TEXT;
    base_name TEXT;
    unique_name TEXT;
BEGIN
    -- 提取文件扩展名
    file_extension := CASE 
        WHEN original_name ~ '\.' THEN 
            '.' || split_part(original_name, '.', array_length(string_to_array(original_name, '.'), 1))
        ELSE ''
    END;
    
    -- 生成唯一文件名
    unique_name := extract(epoch from now())::bigint::text || '_' || 
                   substr(md5(random()::text), 1, 8) || 
                   file_extension;
    
    RETURN unique_name;
END;
$$ LANGUAGE plpgsql;

-- 创建函数：计算文件大小的人类可读格式
CREATE OR REPLACE FUNCTION format_file_size(size_bytes BIGINT)
RETURNS TEXT AS $$
DECLARE
    units TEXT[] := ARRAY['B', 'KB', 'MB', 'GB', 'TB'];
    unit_index INTEGER := 1;
    size_value NUMERIC := size_bytes;
BEGIN
    WHILE size_value >= 1024 AND unit_index < array_length(units, 1) LOOP
        size_value := size_value / 1024.0;
        unit_index := unit_index + 1;
    END LOOP;
    
    RETURN round(size_value, 2)::text || ' ' || units[unit_index];
END;
$$ LANGUAGE plpgsql;

-- 创建函数：格式化音频时长
CREATE OR REPLACE FUNCTION format_duration(duration_seconds INTEGER)
RETURNS TEXT AS $$
DECLARE
    hours INTEGER;
    minutes INTEGER;
    seconds INTEGER;
BEGIN
    IF duration_seconds IS NULL THEN
        RETURN NULL;
    END IF;
    
    hours := duration_seconds / 3600;
    minutes := (duration_seconds % 3600) / 60;
    seconds := duration_seconds % 60;
    
    IF hours > 0 THEN
        RETURN format('%s:%02s:%02s', hours, minutes, seconds);
    ELSE
        RETURN format('%s:%02s', minutes, seconds);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 创建索引函数：用于全文搜索
CREATE OR REPLACE FUNCTION create_search_vector(title TEXT, content TEXT, tags TEXT[])
RETURNS tsvector AS $$
BEGIN
    RETURN to_tsvector('simple', 
        COALESCE(title, '') || ' ' || 
        COALESCE(content, '') || ' ' || 
        COALESCE(array_to_string(tags, ' '), '')
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 创建序列：用于生成编号
CREATE SEQUENCE IF NOT EXISTS script_number_seq START 1000;
CREATE SEQUENCE IF NOT EXISTS audio_number_seq START 10000;

-- 创建视图：用户统计信息
CREATE OR REPLACE VIEW user_stats AS
SELECT 
    u.id,
    u.username,
    u.nickname,
    COUNT(DISTINCT s.id) as script_count,
    COUNT(DISTINCT a.id) as audio_count,
    COUNT(DISTINCT ar.id) as review_count,
    u.created_at,
    u.last_login_at
FROM users u
LEFT JOIN scripts s ON u.id = s.creator_id
LEFT JOIN cv_recordings a ON u.id = a.cv_user_id
LEFT JOIN audio_reviews ar ON u.id = ar.reviewer_id
WHERE u.status = 'active'
GROUP BY u.id, u.username, u.nickname, u.created_at, u.last_login_at;

-- 创建视图：剧本统计信息
CREATE OR REPLACE VIEW script_stats AS
SELECT 
    s.id,
    s.title,
    s.status,
    COUNT(DISTINCT c.id) as chapter_count,
    COUNT(DISTINCT a.id) as assignment_count,
    COUNT(DISTINCT cr.id) as recording_count,
    s.created_at,
    s.updated_at
FROM scripts s
LEFT JOIN script_chapters c ON s.id = c.script_id
LEFT JOIN script_assignments a ON s.id = a.script_id
LEFT JOIN cv_recordings cr ON s.id = cr.script_id
GROUP BY s.id, s.title, s.status, s.created_at, s.updated_at;

-- 插入初始数据

-- 插入默认角色
INSERT INTO roles (name, description, is_system, permissions) VALUES
('超级管理员', '系统超级管理员，拥有所有权限', true, '[
    "user:create", "user:read", "user:update", "user:delete",
    "role:create", "role:read", "role:update", "role:delete",
    "script:create", "script:read", "script:update", "script:delete",
    "audio:create", "audio:read", "audio:update", "audio:delete",
    "system:admin"
]'::jsonb),
('管理员', '系统管理员，拥有大部分管理权限', true, '[
    "user:read", "user:update",
    "role:read",
    "script:create", "script:read", "script:update", "script:delete",
    "audio:create", "audio:read", "audio:update", "audio:delete"
]'::jsonb),
('导演', '剧本导演，负责剧本管理和人员分配', true, '[
    "script:create", "script:read", "script:update",
    "audio:read", "audio:update",
    "assignment:create", "assignment:read", "assignment:update", "assignment:delete"
]'::jsonb),
('CV', '配音演员，负责录音和上传音频', true, '[
    "script:read",
    "audio:create", "audio:read", "audio:update",
    "recording:create", "recording:read", "recording:update"
]'::jsonb),
('审听员', '音频审听员，负责审听和反馈', true, '[
    "script:read",
    "audio:read",
    "review:create", "review:read", "review:update"
]'::jsonb),
('普通用户', '普通用户，基础权限', true, '[
    "script:read",
    "audio:read"
]'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- 插入默认权限
INSERT INTO permissions (name, description, resource, action) VALUES
('user:create', '创建用户', 'user', 'create'),
('user:read', '查看用户', 'user', 'read'),
('user:update', '更新用户', 'user', 'update'),
('user:delete', '删除用户', 'user', 'delete'),
('role:create', '创建角色', 'role', 'create'),
('role:read', '查看角色', 'role', 'read'),
('role:update', '更新角色', 'role', 'update'),
('role:delete', '删除角色', 'role', 'delete'),
('script:create', '创建剧本', 'script', 'create'),
('script:read', '查看剧本', 'script', 'read'),
('script:update', '更新剧本', 'script', 'update'),
('script:delete', '删除剧本', 'script', 'delete'),
('audio:create', '创建音频', 'audio', 'create'),
('audio:read', '查看音频', 'audio', 'read'),
('audio:update', '更新音频', 'audio', 'update'),
('audio:delete', '删除音频', 'audio', 'delete'),
('assignment:create', '创建分配', 'assignment', 'create'),
('assignment:read', '查看分配', 'assignment', 'read'),
('assignment:update', '更新分配', 'assignment', 'update'),
('assignment:delete', '删除分配', 'assignment', 'delete'),
('recording:create', '创建录音', 'recording', 'create'),
('recording:read', '查看录音', 'recording', 'read'),
('recording:update', '更新录音', 'recording', 'update'),
('review:create', '创建审听', 'review', 'create'),
('review:read', '查看审听', 'review', 'read'),
('review:update', '更新审听', 'review', 'update'),
('system:admin', '系统管理', 'system', 'admin')
ON CONFLICT (name) DO NOTHING;

-- 插入默认音频模板
INSERT INTO audio_templates (name, description, settings) VALUES
('标准录音模板', '标准的录音质量要求', '{
    "sample_rate": 44100,
    "bit_depth": 16,
    "channels": 1,
    "format": "wav",
    "max_duration": 600,
    "noise_threshold": -60
}'::jsonb),
('高质量录音模板', '高质量录音要求，适用于重要角色', '{
    "sample_rate": 48000,
    "bit_depth": 24,
    "channels": 1,
    "format": "wav",
    "max_duration": 1200,
    "noise_threshold": -65
}'::jsonb),
('快速录音模板', '快速录音模板，适用于背景音等', '{
    "sample_rate": 22050,
    "bit_depth": 16,
    "channels": 1,
    "format": "mp3",
    "max_duration": 300,
    "noise_threshold": -55
}'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- 创建默认管理员用户（密码：admin123，请在生产环境中修改）
-- 注意：这里的密码哈希是 bcrypt 加密的 "admin123"
INSERT INTO users (username, email, password_hash, nickname, is_superuser, status) VALUES
('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5e', '系统管理员', true, 'active')
ON CONFLICT (username) DO NOTHING;

-- 为默认管理员分配超级管理员角色
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u, roles r
WHERE u.username = 'admin' AND r.name = '超级管理员'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成！';
    RAISE NOTICE '默认管理员账号：admin';
    RAISE NOTICE '默认管理员密码：admin123';
    RAISE NOTICE '请在生产环境中修改默认密码！';
END $$;