# Content Creation 模板说明

## 第一部分：任务设计参考

- **Skill 价值定位**：技能收益必须体现在“把真实内容工作流里高成本、易遗漏、难收口的步骤标准化”，例如 source-derived voice 对齐、跨渠道改写、事实矩阵整理、SEO / newsletter / social 的格式检查、最终 bundle 审计。这一定位参考了 SkillsMP `content-creation` 类里更高频也更高信号的技能方向，例如 `article-writing`、`brand-voice`、`content-engine`、`newsletter-generation`、`content-writer`。严禁把 Skill 设计成隐藏答案、直接代写最终交付物、偷偷修改题面/测试/数据，或靠额外依赖与额外 prompt 差异制造收益。

- **任务目标形态**：任务应要求 Agent 基于冻结资料完成真实内容交付，而不是做开放式 brainstorming。更合适的目标形态是：读 brief、抽取 confirmed facts、按 channel requirements 生成多个渠道产物、保持 voice 与事实一致、再完成最终打包或发布前检查。不应把任务设计成“修 app / 找隐藏链接 / 调隐藏服务”，也不应退化成只写一段文案、只做机械改写、或只填一个固定模板。

- **验证设计重点**：Verifier 应检查内容是否完整、事实是否来自给定资料、不同渠道是否各自像样，并确认最终打包流程能跑通。Guardrail 只负责拦住明显取巧行为，例如改原始资料、编造产品能力、复制粘贴同一份内容或绕开交付流程。

## 第二部分：示例任务

### 任务概述

`multi-channel-launch-content-pack` 是一个直接面向内容运营交付的模板任务。Agent 需要基于冻结的 `launch_brief.md`、`fact_sheet.json`、`voice_guide.md`、`channel_requirements.md`、`keyword_plan.json` 和 `source_notes.md`，产出：

- `blog_post.md`
- `linkedin_post.md`
- `newsletter.json`
- `seo_meta.json`
- `publish_bundle.json`

任务目标不是“修系统”，而是把一套真实风格的产品发布资料转成可发布的多渠道内容包，并通过最终打包脚本验证交付物完整性。

### 📌 任务元数据

- 任务 ID：`multi-channel-launch-content-pack`
- 类别：`content-creation`
- 难度：`hard`
- 绑定 Skill：`content-bundle-audit`
- 交付物：博客、LinkedIn、newsletter、SEO metadata、最终 bundle
- 环境形态：单容器；`environment/workspace/` 提供冻结资料，`environment/skills/` 提供审计 Skill

这个示例任务对齐的是 SkillsMP 里最常见的那类 content workflow：先吃 brief，再做 brand voice / content engine / newsletter generation 的联合收口，最后交付 publish-ready bundle，而不是生成一段孤立文本。

### 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`8/8` 通过
- 有效样本：`content-template-final-oracle-b / template_new__vtRTFZ9`
- 时间：开始 `2026-04-21T08:55:36Z`，结束 `2026-04-21T08:56:24Z`

Verifier 策略：

- 主测：检查 `blog_post.md`、`linkedin_post.md`、`newsletter.json`、`seo_meta.json`、`publish_bundle.json` 是否齐全、可解析、可打包。
- 主测：检查博客长度、H1/H2 结构、首段事实覆盖、CTA、一致的 launch facts、SEO 关键词契约和 bundle 元数据。
- 主测：检查 LinkedIn、newsletter 和 SEO metadata 是否满足各自渠道约束，而不是博客的机械缩写。
- 主测：检查跨渠道事实一致性、差异化程度和禁用 claims。
- 防作弊：冻结 `launch_brief.md`、`fact_sheet.json`、`keyword_plan.json`、`source_notes.md`、`build_bundle.py` 等输入与打包逻辑。
- 防作弊：禁止改资料、伪造 bundle、漏交渠道产物、删功能规避问题，或通过替换真实链路绕过 verifier。


多模态：

- 不适用（纯文本 / JSON 内容包任务）。

### ⚡ Skill 相关性评估

结论：强相关。

这个任务里，Skill 的核心价值不是直接替 solver 写四份最终文案，而是把最容易耗掉时间的部分标准化：

- 用 `fact_matrix.py` 拉平 confirmed facts、forbidden claims 和 roadmap notes。
- 用 `channel_stats.py` 快速检查 subject / preview / hook / SEO 长度边界。
- 用 `audit_bundle.py` 做跨渠道事实审计、禁用 claim 检查和最终收口。
- 在结束前强制跑 `build_bundle.py`，保证最终交付物不是半成品。

最近 **3 次有效 with-skill** 与 **3 次有效 without-skill** 对照实验如下。统计只纳入 task-level `result.json` 中 `exception_info == null` 且 reward 存在的有效 trial；已排除 `BuildException`、`ConnectError` 等基础设施失败样本。

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | With Skill 从 `0/3` 提升到 `3/3` |
| 总耗时 | `211.9s` | `232.4s` | With Skill 略高约 `9.7%`，主要受 E2B 构建/排队噪声影响 |
| Agent 执行耗时 | `126.5s` | `101.4s` | With Skill 更快，平均 Agent 耗时降低约 `19.8%` |
| Input Tokens | `164.7k` | `163.7k` | With Skill 略低约 `0.6%` |

失败轨迹摘要：

- `without_skill` 的典型问题不是起不来，而是最终交付物仍然会留下一项 verifier 失败，最常见是 SEO description / newsletter preview 这类渠道收尾约束没完全收住。
- `with_skill` 在最终有效样本里会主动读取 skill、运行审计脚本，并出现 `ALL_CHECKS_PASS` 后再打包；这明显降低了最后一公里的收敛成本。
- 早期迭代里曾定位到 skill `SKILL.md` 缺少 YAML frontmatter，导致技能未真正加载；修复后重新跑的最终版 with-skill 样本全部通过。该问题定位过程不计入上表统计。

### 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
