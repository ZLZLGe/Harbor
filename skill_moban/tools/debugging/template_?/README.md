# 🛠️ Debugging 模板任务指南

欢迎来到 debugging 类模板任务的专属目录！这里是我们承接、管理和扩展各类调试（Debugging）任务的“大本营”。

为了让任务结构更加清晰，当前版本将模板按照环境骨架划分为三大基础类别。

## 💡 我们是如何分类的？

当你需要接入一个新的 Debugging skill 时，不需要从头开始。你只需要评估新skill产生task时的 Docker 基座、核心工具链与以下哪一类最相似，直接“对号入座”即可：

### 1. 🌐 浏览器应用环境 (browser-app-env)

适用场景： 浏览器应用类 Debugging 任务。

开箱即用： 复用了前端应用环境、浏览器自动化工具。

当前状态： 🌟 已有完整样例。`browser-app-env/` 目录已合并 `nextjs-commerce-runtime-regression-debugging` 这份完整任务骨架，涵盖 instruction、environment、tests、solution、validation 等本体，可以直接复用。

### 2. ⚙️ 仓库运行时环境 (repo-runtime-env)

适用场景： 仓库运行时类 Debugging 任务。

开箱即用： 复用了代码仓库、语言运行时、包管理器、build/test 命令、配置文件、环境变量和 flag 状态这一整套 repo 执行骨架。


当前状态： 🚧 当前提供合并后的模板规范 README，具体样例任务努力扩充中。

### 3. 📝 日志排障环境 (log-debug-env)

适用场景： 日志分析与排障类任务。

开箱即用： 整合了代码仓库、真实日志样本、事故样本以及常用的日志分析工具。

当前状态： 🚧 仅提供模板规范 README，具体样例任务努力扩充中。

## 📁 目录结构概览

```text
├── browser-app-env/     # 🌟 完整样例目录（已合并 nextjs-commerce-runtime-regression-debugging）
├── repo-runtime-env/    # 规范说明目录（覆盖构建/测试/配置/开关类任务）
└── log-debug-env/       # 规范说明目录（目前为 README）
```

## 📌 维护者寄语

状态：APPROVE ✅
