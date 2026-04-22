# Multi-channel Launch Content Pack

基于冻结的 launch brief、fact sheet、voice guide、channel requirements 和 keyword plan，生成 `blog_post.md`、`linkedin_post.md`、`newsletter.json`、`seo_meta.json`，并通过 `build_bundle.py` 产出最终的 `publish_bundle.json`。任务形态对齐 `content-creation` 里更接近真实内容运营流程的 skills，而不是“修 app / 调隐藏服务”。

## 📌 任务元数据

- 任务 ID：`multi-channel-launch-content-pack`
- 类别：`content-creation`
- 难度：`hard`
- 绑定 Skill：`content-bundle-audit`
- 交付物：`blog_post.md`、`linkedin_post.md`、`newsletter.json`、`seo_meta.json`、`publish_bundle.json`
- 环境形态：单容器；`environment/workspace/` 提供冻结资料，`environment/skills/` 提供内容审计 Skill

这个任务对齐 SkillsMP 中 `content-engine`、`brand-voice`、`content-writer`、`newsletter-generation` 一类高频 workflow：先吃 brief，再做事实约束和渠道适配，最后交付 publish-ready 内容包，而不是只输出一段泛化文案。

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`8/8` 通过
- 有效样本：`content-template-final-oracle-b / template_new__vtRTFZ9`
- 时间：开始 `2026-04-21T08:55:36Z`，结束 `2026-04-21T08:56:24Z`

Verifier 策略：

- 主测：检查 `blog_post.md`、`linkedin_post.md`、`newsletter.json`、`seo_meta.json`、`publish_bundle.json` 是否齐全、可解析、可打包。
- 主测：检查博客长度、H1/H2 结构、首段事实覆盖、CTA、一致的 launch facts、SEO 关键词契约和 bundle 元数据。
- 主测：检查 LinkedIn、newsletter 和 SEO metadata 各自满足独立渠道约束，而不是博客的机械缩写。
- 主测：检查跨渠道事实一致性、差异化程度和禁用 claims。
- 防作弊：冻结 `launch_brief.md`、`fact_sheet.json`、`keyword_plan.json`、`source_notes.md`、`build_bundle.py` 等输入与打包逻辑，禁止直接篡改。
- 防作弊：禁止删功能规避问题、伪造 bundle、漏交渠道产物、或通过替换真实链路来绕过 verifier。

数据质量：

- 输入资料是冻结的产品发布资料包，不依赖评测时联网抓取，因此稳定、可复验。
- 资料同时包含结构化 JSON 与长文本约束，具备真实内容工作流需要的结构复杂度。
- verifier 关注 publish-ready 行为结果，不绑定某个唯一措辞。

数据来源：

- 数据为任务内置的冻结 launch asset pack，模拟真实 SaaS 新版本发布材料组合：brief、fact sheet、voice guide、channel requirements、keyword plan、source notes。
- 不在评测时访问外部网站；真实性来自工作流形态和资料组织方式，而不是在线抓取。

多模态：

- 不适用（纯文本 / JSON 内容包任务）。

## ⚡ Skill 相关性评估

结论：强相关。

这个任务里，Skill 的核心价值不是直接替 solver 生成四份最终文案，而是把最容易耗掉时间的约束整理和终检流程标准化：

- 用 `fact_matrix.py` 把 confirmed facts、forbidden claims 和 roadmap notes 拉平。
- 用 `channel_stats.py` 快速检查 subject / preview / hook / SEO 长度边界。
- 用 `audit_bundle.py` 做跨渠道事实审计、禁用 claim 检查和最终收口。
- 在结束前强制跑 `build_bundle.py`，保证最后交付物不是半成品。

最近 **3 次有效 with-skill** 与 **3 次有效 without-skill** 对照实验如下。统计只纳入 task-level `result.json` 中 `exception_info == null` 且 reward 存在的有效 trial；已排除 `BuildException`、`ConnectError` 等基础设施失败样本。

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | With Skill 从 `0/3` 提升到 `3/3` |
| 总耗时 | `211.9s` | `232.4s` | With Skill 略高约 `9.7%`，主要受 E2B 构建/排队噪声影响 |
| Agent 执行耗时 | `126.5s` | `101.4s` | With Skill 更快，平均 Agent 耗时降低约 `19.8%` |
| Input Tokens | `164.7k` | `163.7k` | With Skill 略低约 `0.6%` |

有效样本：

- With Skill：
  - `content-template-final-with-i / task_with_skills_e2b__TuWEf5u`
  - `content-template-final-with-j / task_with_skills_e2b__xSdZSRZ`
  - `content-template-final-with-k / task_with_skills_e2b__V7XekRK`
- Without Skill：
  - `content-template-without-skills-r4 / task_without_skills_e2b__b3UrwKX`
  - `content-template-final-without-c / task_without_skills_e2b__Mw9JS8A`
  - `content-template-final-without-e / task_without_skills_e2b__hkXJMfV`

失败轨迹摘要：

- `without_skill` 的典型问题不是起不来，而是最终交付物仍然会留下一项 verifier 失败，最常见是 SEO description / newsletter preview 这类渠道收尾约束没完全收住。
- `with_skill` 在最终有效样本里会主动读取 skill、运行审计脚本，并出现 `ALL_CHECKS_PASS` 后再打包；这明显降低了最后一公里的收敛成本。
- 早期诊断阶段曾发现 skill `SKILL.md` 缺少 YAML frontmatter，导致技能未真正加载；修复后重新跑的最终版 with-skill 样本全部通过。该问题定位过程不计入上表统计。

## 📁 标准目录结构说明

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
