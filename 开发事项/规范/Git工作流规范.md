# Git 工作流规范

## 1. 分支管理策略

### 1.1 分支类型

我们采用 Git Flow 工作流模式，包含以下分支类型：

#### 主要分支

- **main/master**: 主分支，始终保持可发布状态
- **develop**: 开发分支，集成最新的开发功能

#### 辅助分支

- **feature/***: 功能分支，用于开发新功能
- **release/***: 发布分支，用于准备新版本发布
- **hotfix/***: 热修复分支，用于紧急修复生产环境问题
- **bugfix/***: 缺陷修复分支，用于修复开发环境中的问题

### 1.2 分支命名规范

```bash
# ✅ 正确的分支命名
feature/user-management
feature/audio-player
feature/HSHS-123-user-authentication

release/v1.2.0
release/v2.0.0-beta

hotfix/critical-security-fix
hotfix/HSHS-456-login-error

bugfix/form-validation-error
bugfix/HSHS-789-audio-playback-issue

# ❌ 错误的分支命名
feature/UserManagement  # 使用了大写字母
my-feature             # 没有分支类型前缀
fix                    # 命名过于简单
feature/修复用户登录     # 使用了中文
```

### 1.3 分支工作流程

#### 功能开发流程

```bash
# 1. 从 develop 分支创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/user-management

# 2. 开发功能并提交
git add .
git commit -m "feat: add user list component"
git commit -m "feat: implement user creation form"
git commit -m "feat: add user deletion functionality"

# 3. 推送分支到远程
git push origin feature/user-management

# 4. 创建 Pull Request 到 develop 分支
# 在 GitHub/GitLab 上创建 PR

# 5. 代码审查通过后合并
# 使用 Squash and Merge 或 Merge Commit

# 6. 删除功能分支
git checkout develop
git pull origin develop
git branch -d feature/user-management
git push origin --delete feature/user-management
```

#### 发布流程

```bash
# 1. 从 develop 创建发布分支
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# 2. 更新版本号和发布说明
# 修改 package.json, version.py 等文件
git add .
git commit -m "chore: bump version to 1.2.0"

# 3. 测试和修复（如有必要）
git commit -m "fix: resolve issue in user export"

# 4. 合并到 main 分支
git checkout main
git pull origin main
git merge --no-ff release/v1.2.0
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin main --tags

# 5. 合并回 develop 分支
git checkout develop
git merge --no-ff release/v1.2.0
git push origin develop

# 6. 删除发布分支
git branch -d release/v1.2.0
git push origin --delete release/v1.2.0
```

#### 热修复流程

```bash
# 1. 从 main 分支创建热修复分支
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# 2. 修复问题
git add .
git commit -m "fix: resolve critical security vulnerability"

# 3. 更新版本号
git commit -m "chore: bump version to 1.2.1"

# 4. 合并到 main 分支
git checkout main
git merge --no-ff hotfix/critical-security-fix
git tag -a v1.2.1 -m "Hotfix version 1.2.1"
git push origin main --tags

# 5. 合并到 develop 分支
git checkout develop
git merge --no-ff hotfix/critical-security-fix
git push origin develop

# 6. 删除热修复分支
git branch -d hotfix/critical-security-fix
git push origin --delete hotfix/critical-security-fix
```

## 2. 提交信息规范

### 2.1 提交信息格式

我们采用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```base
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### 2.2 提交类型 (type)

| 类型 | 描述 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: add user authentication` |
| `fix` | 缺陷修复 | `fix: resolve login validation error` |
| `docs` | 文档更新 | `docs: update API documentation` |
| `style` | 代码格式化（不影响功能） | `style: format code with prettier` |
| `refactor` | 代码重构（不是新功能也不是修复） | `refactor: extract user service logic` |
| `perf` | 性能优化 | `perf: improve query performance` |
| `test` | 测试相关 | `test: add unit tests for user service` |
| `chore` | 构建过程或辅助工具的变动 | `chore: update dependencies` |
| `ci` | CI/CD 相关 | `ci: add GitHub Actions workflow` |
| `build` | 构建系统或外部依赖变动 | `build: update webpack configuration` |
| `revert` | 回滚之前的提交 | `revert: revert "feat: add user auth"` |

### 2.3 作用域 (scope)

作用域用于说明提交影响的范围，可选但推荐使用：

```bash
# 前端作用域
feat(components): add UserCard component
fix(store): resolve user state mutation issue
style(pages): update login page layout

# 后端作用域
feat(api): add user management endpoints
fix(auth): resolve JWT token validation
perf(db): optimize user query performance

# 通用作用域
docs(readme): update installation guide
chore(deps): update package dependencies
ci(github): add automated testing workflow
```

### 2.4 提交信息示例

#### 简单提交

```bash
# ✅ 正确示例
feat: add user registration functionality
fix: resolve audio playback issue on Safari
docs: update API documentation for user endpoints
style: format code according to ESLint rules
refactor: extract common validation logic
test: add integration tests for auth flow
chore: update Node.js to version 18

# ❌ 错误示例
add user feature          # 缺少类型前缀
Fix bug                   # 首字母大写
feat: Add user feature.   # 首字母大写且有句号
update                    # 描述过于简单
修复用户登录问题           # 使用中文
```

#### 详细提交

```bash
feat(auth): implement JWT-based authentication

- Add JWT token generation and validation
- Implement login and logout endpoints
- Add middleware for protected routes
- Update user model to include token fields

Closes #123
```

```bash
fix(audio): resolve playback issues on mobile devices

The audio player was not working correctly on iOS Safari due to
autoplay restrictions. This commit:

- Adds user gesture detection before playback
- Implements fallback for unsupported audio formats
- Updates audio controls for better mobile UX

Fixes #456
Tested on: iOS Safari 15+, Android Chrome 90+
```

```bash
breaking: update user API response format

CHANGE: User API now returns standardized response format

Before:
{
  "user": { ... },
  "roles": [ ... ]
}

After:
{
  "code": 0,
  "message": "success",
  "data": {
    "user": { ... },
    "roles": [ ... ]
  }
}

BREAKING CHANGE: All user-related API endpoints now use the new response format.
Clients need to update their response handling logic.

Migration guide: https://docs.example.com/migration/v2
```

### 2.5 提交信息验证

#### 使用 commitlint 进行验证

```javascript
// commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'docs',
        'style',
        'refactor',
        'perf',
        'test',
        'chore',
        'ci',
        'build',
        'revert'
      ]
    ],
    'type-case': [2, 'always', 'lower-case'],
    'type-empty': [2, 'never'],
    'scope-case': [2, 'always', 'lower-case'],
    'subject-case': [2, 'always', 'lower-case'],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 72],
    'body-leading-blank': [1, 'always'],
    'body-max-line-length': [2, 'always', 100],
    'footer-leading-blank': [1, 'always'],
    'footer-max-line-length': [2, 'always', 100]
  }
};
```

#### Git Hooks 配置

```bash
# .husky/commit-msg
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npx --no-install commitlint --edit "$1"
```

## 3. Pull Request 规范

### 3.1 PR 标题规范

PR 标题应该遵循与提交信息相同的格式：

```bash
# ✅ 正确示例
feat: implement user management system
fix: resolve audio playback issues
docs: update installation guide
refactor: optimize database queries

# ❌ 错误示例
User management feature
Bug fixes
Updates
```

### 3.2 PR 描述模板

```markdown
## 📝 变更描述

简要描述本次 PR 的主要变更内容。

## 🎯 变更类型

- [ ] 新功能 (feat)
- [ ] 缺陷修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 性能优化 (perf)
- [ ] 测试相关 (test)
- [ ] 构建/工具相关 (chore)

## 🔗 相关 Issue

- Closes #123
- Fixes #456
- Related to #789

## 📋 变更清单

- [ ] 添加用户列表组件
- [ ] 实现用户创建功能
- [ ] 添加用户删除确认对话框
- [ ] 更新用户管理 API 文档

## 🧪 测试说明

### 测试环境
- [ ] 本地开发环境
- [ ] 测试环境
- [ ] 预发布环境

### 测试用例
1. 验证用户列表正确显示
2. 测试用户创建流程
3. 确认用户删除功能
4. 检查权限控制

## 📸 截图/录屏

如果涉及 UI 变更，请提供相关截图或录屏。

## ⚠️ 注意事项

- [ ] 需要数据库迁移
- [ ] 需要更新环境变量
- [ ] 需要更新部署配置
- [ ] 包含破坏性变更

## 📚 文档更新

- [ ] API 文档已更新
- [ ] 用户手册已更新
- [ ] 开发文档已更新
- [ ] 无需文档更新

## ✅ 检查清单

- [ ] 代码已通过 ESLint/Flake8 检查
- [ ] 已添加必要的单元测试
- [ ] 测试覆盖率满足要求
- [ ] 已更新相关文档
- [ ] 已测试向后兼容性
- [ ] 已考虑性能影响
```

### 3.3 PR 审查规范

#### 审查者职责

1. **代码质量审查**
   - 检查代码是否符合项目规范
   - 验证逻辑正确性和性能
   - 确保安全性和可维护性

2. **功能验证**
   - 验证功能是否按需求实现
   - 测试边界条件和异常情况
   - 确认用户体验

3. **文档检查**
   - 确保代码注释充分
   - 验证 API 文档更新
   - 检查变更日志

#### 审查标准

```markdown
## 代码审查检查清单

### 🔍 代码质量
- [ ] 代码风格符合项目规范
- [ ] 变量和函数命名清晰
- [ ] 代码逻辑清晰易懂
- [ ] 没有重复代码
- [ ] 错误处理完善

### 🛡️ 安全性
- [ ] 输入验证充分
- [ ] 没有 SQL 注入风险
- [ ] 没有 XSS 漏洞
- [ ] 权限控制正确
- [ ] 敏感信息已保护

### ⚡ 性能
- [ ] 数据库查询优化
- [ ] 没有 N+1 查询问题
- [ ] 缓存策略合理
- [ ] 资源使用效率高

### 🧪 测试
- [ ] 单元测试覆盖充分
- [ ] 集成测试通过
- [ ] 边界条件已测试
- [ ] 异常情况已处理

### 📚 文档
- [ ] 代码注释充分
- [ ] API 文档已更新
- [ ] README 已更新
- [ ] 变更日志已记录
```

## 4. 版本管理

### 4.1 版本号规范

我们采用 [语义化版本控制](https://semver.org/lang/zh-CN/) (SemVer)：

```base
主版本号.次版本号.修订号 (MAJOR.MINOR.PATCH)
```

- **主版本号 (MAJOR)**：不兼容的 API 修改
- **次版本号 (MINOR)**：向下兼容的功能性新增
- **修订号 (PATCH)**：向下兼容的问题修正

#### 版本号示例

```bash
# 正式版本
v1.0.0    # 首个正式版本
v1.1.0    # 新增功能
v1.1.1    # 修复缺陷
v2.0.0    # 重大更新，不向下兼容

# 预发布版本
v1.2.0-alpha.1    # Alpha 版本
v1.2.0-beta.1     # Beta 版本
v1.2.0-rc.1       # Release Candidate

# 开发版本
v1.2.0-dev.20231201    # 开发版本
```

### 4.2 标签管理

```bash
# 创建带注释的标签
git tag -a v1.2.0 -m "Release version 1.2.0

New features:
- User management system
- Audio player improvements
- Performance optimizations

Bug fixes:
- Fixed login validation issue
- Resolved audio playback problems

Breaking changes:
- Updated API response format"

# 推送标签到远程
git push origin v1.2.0

# 推送所有标签
git push origin --tags

# 删除本地标签
git tag -d v1.2.0

# 删除远程标签
git push origin --delete v1.2.0
```

### 4.3 变更日志 (CHANGELOG)

```markdown
# 变更日志

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本控制遵循 [语义化版本控制](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 用户头像上传功能
- 音频文件批量导入

### 变更
- 优化用户列表加载性能
- 更新 UI 组件库到最新版本

### 修复
- 修复音频播放器在 Safari 上的兼容性问题

## [1.2.0] - 2023-12-01

### 新增
- 用户管理系统
  - 用户列表、创建、编辑、删除功能
  - 角色权限管理
  - 用户状态管理
- 音频播放器改进
  - 支持更多音频格式
  - 添加播放列表功能
  - 改进移动端体验

### 变更
- 更新 API 响应格式为统一结构
- 优化数据库查询性能
- 改进错误处理和用户反馈

### 修复
- 修复登录验证错误
- 解决音频播放问题
- 修复表单验证 bug

### 安全
- 加强输入验证
- 更新依赖包以修复安全漏洞

## [1.1.1] - 2023-11-15

### 修复
- 修复用户登录时的验证错误
- 解决音频文件上传失败问题

## [1.1.0] - 2023-11-01

### 新增
- 音频文件管理功能
- 用户个人资料页面

### 变更
- 改进响应式设计
- 优化加载性能

## [1.0.0] - 2023-10-01

### 新增
- 初始版本发布
- 基础用户认证功能
- 音频播放基础功能
- 管理后台界面
```

## 5. Git 配置和工具

### 5.1 Git 配置

```bash
# 全局配置
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase false
git config --global core.autocrlf input
git config --global core.editor "code --wait"

# 项目特定配置
git config user.name "Project Name"
git config user.email "project@example.com"

# 设置别名
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual '!gitk'
```

### 5.2 .gitignore 配置

```gitignore
# 依赖目录
node_modules/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/

# 环境配置
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
.venv
venv/
ENV/
env/

# IDE 配置
.vscode/
.idea/
*.swp
*.swo
*~

# 日志文件
*.log
logs/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# 运行时文件
*.pid
*.seed
*.pid.lock

# 缓存文件
.cache/
.parcel-cache/
.next/
out/
.nuxt/
dist/
.tmp/
.temp/

# 测试覆盖率
coverage/
.nyc_output/

# 数据库文件
*.db
*.sqlite
*.sqlite3

# 上传文件
uploads/
static/uploads/
media/

# 操作系统文件
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# 备份文件
*.bak
*.backup
*.old
*.orig
*.tmp
```

### 5.3 Git Hooks

#### pre-commit Hook

```bash
#!/bin/sh
# .husky/pre-commit

# 运行代码格式化
npm run format

# 运行代码检查
npm run lint

# 运行类型检查
npm run type-check

# 运行测试
npm run test:unit

# 检查是否有未提交的变更
if ! git diff --cached --quiet; then
  echo "✅ Pre-commit checks passed"
else
  echo "❌ No staged changes found"
  exit 1
fi
```

#### commit-msg Hook

```bash
#!/bin/sh
# .husky/commit-msg

# 验证提交信息格式
npx --no-install commitlint --edit "$1"
```

#### pre-push Hook

```bash
#!/bin/sh
# .husky/pre-push

# 运行完整测试套件
npm run test

# 构建检查
npm run build

echo "✅ Pre-push checks passed"
```

## 6. 最佳实践

### 6.1 提交频率

- **小而频繁的提交**：每个提交应该代表一个逻辑上的变更单元
- **原子性提交**：每个提交应该是完整的，不应该破坏构建
- **及时提交**：不要积累太多变更才提交

### 6.2 分支管理

- **保持分支简洁**：及时删除已合并的分支
- **定期同步**：经常从主分支拉取最新变更
- **避免长期分支**：功能分支不应该存在太长时间

### 6.3 代码审查

- **及时审查**：尽快响应 PR 审查请求
- **建设性反馈**：提供具体、有帮助的建议
- **学习机会**：将代码审查视为学习和分享知识的机会

### 6.4 冲突解决

```bash
# 解决合并冲突的步骤

# 1. 拉取最新的目标分支
git checkout develop
git pull origin develop

# 2. 切换到功能分支并合并
git checkout feature/user-management
git merge develop

# 3. 解决冲突
# 编辑冲突文件，解决冲突标记

# 4. 标记冲突已解决
git add .
git commit -m "resolve merge conflicts with develop"

# 5. 推送更新
git push origin feature/user-management
```

## 7. 总结

### 7.1 核心原则

1. **一致性**：团队成员遵循统一的工作流程
2. **可追溯性**：清晰的提交历史和变更记录
3. **协作性**：有效的代码审查和知识分享
4. **质量保证**：通过自动化检查确保代码质量
5. **持续改进**：根据团队反馈优化工作流程

### 7.2 关键要点

- 使用规范的分支命名和提交信息格式
- 保持小而频繁的提交
- 进行充分的代码审查
- 维护清晰的版本历史
- 及时更新文档和变更日志

通过遵循这些 Git 工作流规范，团队可以更高效地协作，减少冲突，提高代码质量，并确保项目的可维护性。
