# SEO Launch Readiness Remediation Template

这是面向 `sales-marketing` 类 SEO skill 的模板。它综合参考 SkillsMP 销售营销类热门 SEO 能力的共性：本地营销站审计、收录准备度诊断、页面规范化修复、站内发现路径修复、sitemap 治理、结构化数据校验和 source-backed 发布说明。

## 第一部分：任务设计参考

* **Skill 价值定位**：SEO 类 skill 的共同价值，不是生成一份泛泛的优化建议，而是把“用 live crawl / audit 找根因、修真实页面、重建站点、再复验”的流程标准化。高质量 skill 应帮助 agent 优先区分历史 snapshot 和当前事实源，并把页面修复与站点级发布门槛联动起来。
* **Task 目标形态**：任务应提供真实风格的营销站源码、本地审计服务、关键词映射、旧 crawl snapshot、内容 brief 和参考资料包。目标不应只是写审计报告，而应要求 agent 完成页面修复、遗留 URL 规范化、发现路径改造、sitemap 修复和机器可读交付。
* **Verifier 设计重点**：Verifier 应同时验证目标页面最终状态、站点级发现路径、旧 URL 归并、输出合同和防作弊边界。重点包括 live audit 是否通过、target page 是否全部过 gate、关键词覆盖和输出是否一致、输入和隐藏服务是否未被修改，以及 solver 是否真的用了本地 live audit 链路。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`sales-marketing__seo_launch_readiness_remediation`
- 类别：`sales-marketing`
- 难度：`hard`
- 绑定 Skill：`seo`
- 输入数据参考来源：
  - `environment/data/reference_pages/posthog-product-analytics.json`：任务内产品分析页参考形态；来源于  
    [https://posthog.com/product-analytics](https://posthog.com/product-analytics)
  - `environment/data/reference_pages/posthog-pricing.json`：任务内定价页参考形态；来源于  
    [https://posthog.com/pricing](https://posthog.com/pricing)
  - `environment/data/reference_pages/sentry-error-monitoring.json`：任务内错误监控页参考形态；来源于  
    [https://sentry.io/for/performance/](https://sentry.io/for/performance/)
  - `environment/data/reference_pages/posthog-docs.json`：任务内 docs hub 发现路径参考形态；来源于  
    [https://posthog.com/docs](https://posthog.com/docs)

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法通过本地 `seo-audit` 服务读取 live release gate、逐页修复源码、重新 build 站点，并在最终 live audit 全绿后生成 `seo_fixes_report.json`、`keyword_coverage.csv` 和 `growth_summary.md`。Oracle 关注是否真的修复了站点和发现路径，而不是只生成一份静态 SEO 报告。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出文件存在且可解析 | 3 个要求文件存在并能正确解析 | 结构化交付 |
| target page 全量覆盖 | 报告和覆盖表完整覆盖 manifest 里的目标页 | 面向发布门槛的全量审查 |
| live release gate 通过 | 所有目标页在当前 `seo-audit` 下无 blocker | 基于真实 crawl / audit 的修复闭环 |
| 页面状态与 live audit 一致 | canonical、title、meta、H1、结构化数据、内部发现路径结果一致 | 技术 SEO 修复与复验 |
| 旧 URL 归并 | legacy URL 正常规范化且不再污染 sitemap | canonical / redirect 治理 |
| 关键词覆盖 | `keyword_coverage.csv` 与 live audit、keyword map 一致 | 关键词映射与页面信号校验 |
| 摘要文件业务可读 | 增长摘要包含修复概况、风险、发现路径和发布建议 | 面向业务方的 SEO 说明 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| live audit 访问痕迹 | solver 在 verifier 前确实调用了 release gate、逐页 audit 和 link graph 等 live 审计链路 |
| 输入不可变 | `seo_inputs/` 未被修改 |
| 隐藏服务不可变 | 本地 `seo-audit` 服务未被篡改 |
| skill 不可变 | skill 存在时，bundled skill 内容未被修改 |
| 输出无占位符 | 没有 placeholder、todo、verifier hack 痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把“先查 live gate、再逐页复验、再修发现路径和旧 URL、最后重跑 build 和 audit”的工作流标准化，从而明显降低遗漏收录阻塞和误用旧 snapshot 的概率。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | `without_skill` 三次都至少保留 1 项 verifier 失败；代表性失败是没走 live release gate，导致 live blockers 仍存在，属于行动级失败。 |
| Agent 执行耗时 | `356.9s` | `371.5s` | 这组任务的主要分离信号不是更短耗时，而是 `with_skill` 更稳定走完整 live SEO workflow；`without_skill` 往往更早停在不完整修复。 |
| Tokens | `0.50M` | `0.98M` | `without_skill` 通常 token 更少，因为它经常少做 live 诊断和复验动作；这里更关键的是完成率和工作流遵循度，而不是省 token。 |

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
│   ├── hidden-service-src/
│   └── skills/
├── tests/
│   ├── conftest.py
│   ├── test.sh
│   ├── test_outputs.py
│   └── test_guardrails.py
└── solution/
    ├── solve.py
    └── solve.sh
```
