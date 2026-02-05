# 贡献指南 (Contributing Guide)

感谢你对 Heavenly Mechanic Pavilion (天机阁) 项目的关注！我们欢迎各种形式的贡献。

## 开发环境准备

项目使用 [moonrepo](https://moonrepo.dev/) 管理多包仓库（Monorepo）。

### 依赖工具
- **Node.js**: v20+
- **pnpm**: v10+
- **Python**: v3.10+
- **uv**: 最新版 (用于 Python 依赖管理)
- **moon**: 最新版 (任务编排)

### 初始化项目
```bash
# 安装所有依赖
moon run :install
```

## 常用命令

我们通过 `moon` 统一管理所有任务：

- **代码检查**: `moon run :lint`
- **类型检查**: `moon run :typecheck`
- **运行测试**: `moon run :test`
- **代码格式化**: `moon run :format`
- **启动后端开发服务器**: `moon run server:dev`
- **启动前端开发服务器**: `moon run client:dev`

## 开发流程

1. **Fork** 本仓库并克隆到本地。
2. **创建特性分支**: `git checkout -b feat/your-feature-name`。
3. **编写代码**: 请确保遵循项目的代码风格规范。
4. **本地校验**: 在提交前运行 `moon run :lint` 和 `moon run :typecheck`。
5. **提交代码**: 遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范。
6. **发起 Pull Request**: 描述你的修改内容及目的。

## 代码风格

- **前端**: 使用 ESLint + Prettier。
- **后端**: 使用 Ruff + MyPy。

## CI/CD

项目配置了 GitHub Actions，每次推送或 PR 都会运行 `moon ci` 进行全量校验。请确保你的代码通过了所有 CI 检查。
