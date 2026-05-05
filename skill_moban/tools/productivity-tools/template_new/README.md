# Productivity-Tools Template

这是面向 `productivity-tools` 类 skill 的模板。它综合参考 SkillsMP `productivity-tools` 类热门 skill 的共性能力：围绕公开信息源、固定输入目录和明确交付合同，完成可复跑的整理、筛选、归并与结构化输出。

## 第一部分：任务设计参考

* **Skill 价值定位**：`productivity-tools` 类热门 skill 常见价值在于把日常信息处理工作流变成稳定可执行路径，例如来源扫描、材料整理、状态跟踪、结构化汇总和最终交付。对于 `blogwatcher` 这一类 skill，核心价值集中在多 feed 扫描、更新发现和文章级管理入口。
* **Task 目标形态**：这类任务适合设计成公开数据驱动的交付型流程，例如 feed digest、晨报归并、文章筛选、变更列表整理或状态清单更新。题面应优先写清输入边界、输出合同和禁止事项，把来源扫描方式、归并路径和细化操作留给 solver 自行识别。
* **Verifier 设计重点**：Verifier 应重点检查 solver 是否完成了全量来源扫描、是否正确处理重复引用与时间边界、是否把不在范围内的内容排除在正式结果外，以及最终产物是否与输入镜像保持一致。防作弊测试需要覆盖输入完整性、skill 完整性、输出白名单和重复项处理。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`productivity_tools__developer_feed_digest`
- 类别：`productivity-tools`
- 难度：`hard`
- 绑定 Skill：`blogwatcher`
- 输入数据参考来源：
  - `environment/data/mirror/site/feeds/github-changelog.xml`：任务内 GitHub Changelog RSS 镜像；直接整理自 GitHub Changelog 官方 feed  
    【https://github.blog/changelog/feed/】
  - `environment/data/mirror/site/feeds/github-changelog-team.atom`：任务内第二观察别名使用的 Atom 镜像；直接整理自 GitHub Changelog 官方 feed  
    【https://github.blog/changelog/feed/】
  - `environment/data/mirror/site/feeds/github-blog.xml`：任务内 GitHub Blog RSS 镜像；直接整理自 GitHub Blog 官方 feed  
    【https://github.blog/feed/】
  - `environment/data/mirror/site/feeds/python-blog.atom`：任务内 Python Insider Atom 镜像；直接整理自 Python 官方博客 feed  
    【https://blog.python.org/feeds/posts/default】
  - `environment/data/mirror/site/feeds/node-blog.xml`：任务内 Node.js Blog RSS 镜像；直接整理自 Node.js 官方博客 feed  
    【https://nodejs.org/en/feed/blog.xml】
  - `environment/data/mirror/site/feeds/docker-blog.xml`：任务内 Docker Blog RSS 镜像；直接整理自 Docker 官方博客 feed  
    【https://www.docker.com/blog/feed/】
  - `environment/data/mirror/site/articles/*.html`：任务内文章页面镜像；内容直接整理自下列公开文章页面  
    【https://github.blog/changelog/2026-05-01-upcoming-deprecation-of-gpt-5-2-and-gpt-5-2-codex/】  
    【https://github.blog/changelog/2026-04-27-github-copilot-code-review-will-start-consuming-github-actions-minutes-on-june-1-2026/】  
    【https://github.blog/changelog/2026-04-27-copilot-student-gpt-5-3-codex-removal-from-model-picker/】  
    【https://github.blog/security/securing-the-git-push-pipeline-responding-to-a-critical-remote-code-execution-vulnerability/】  
    【https://blog.python.org/2026/05/python-3145rc1/】  
    【https://blog.python.org/2026/04/python-3150a8-3144-31313/】  
    【https://nodejs.org/en/blog/release/v24.15.0】  
    【https://nodejs.org/en/blog/announcements/discontinuing-security-bug-bounties】  
    【https://www.docker.com/blog/trivy-kics-and-the-shape-of-supply-chain-attacks-so-far-in-2026/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：oracle 会独立解析本地镜像 feed 与文章页面，重新计算时间边界、重复引用、范围判断和优先级，再对照 solver 的 JSON 与 Markdown 交付。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 多 feed 扫描 | RSS 与 Atom 来源都被纳入扫描 | 识别并处理多种 feed 入口 |
| 时间边界 | 仅保留 checkpoint 之后的新文章 | 更新发现与状态边界判断 |
| 重复归并 | 同一 canonical URL 的多来源引用被合并，同时保留 duplicate skip 记录 | 文章级归并与来源追踪 |
| 范围筛选 | 教程、活动、营销、状态回顾不进入正式 digest | 扫描后筛选与整理 |
| 双产物一致性 | JSON 和 Markdown 中的正式条目保持一致 | 结构化交付与摘要输出 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入完整性 | `/app/data` 的内容哈希保持一致 |
| Skill 完整性 | skill 存在时，`environment/skills/blogwatcher/SKILL.md` 内容哈希保持一致 |
| 输出白名单 | `/app/output` 顶层仅保留合同要求的两个文件 |
| 重复保护 | 正式条目中不允许留下重复 canonical URL |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是提供一条稳定的 feed 扫描入口，把多来源更新发现这一步从零散解析工作中抽离出来，然后把精力集中到文章级归并和业务筛选。没有这条入口时，solver 更容易在 Atom/RSS 差异、重复引用处理和范围筛选上留下动作级遗漏。

基于最近 **3 次** 有效对比实验：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `33%` | `100%` | 近 3 次有效对照里，without Skill 有 2 次在 duplicate 归并或 skipped item 完整性上留下动作级遗漏；with Skill 3 次都稳定通过 |
| Agent 执行耗时 | `284.4s` | `279.4s` | With Skill 的扫描与归并路径更稳，平均 Agent 耗时降低约 `1.8%` |
| Tokens | `534.3k` | `504.5k` | 按轨迹总 token 口径统计，Without Skill 的上下文与试错开销约为 With Skill 的 `1.06x` |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── bin/
│   ├── data/
│   └── skills/
├── tests/
└── solution/
```
