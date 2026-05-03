# Content-Creation Template

这是面向 `content-creation` 类 skill 的模板。它综合参考 SkillsMP content-creation 类热门 skill 的共性能力：多来源素材梳理、品牌语气对齐、跨渠道改写、来源登记、发布前缺口整理，以及把一份主材料扩展成可交付的内容包。

## 第一部分：任务设计参考

* **Skill 价值定位**：content-creation 类热门 skill 的核心价值，是把“读完素材后写几段文案”提升为“沿素材边界、渠道约束和品牌语气完成整套内容生产闭环”。模板任务应让 skill 承接素材筛选、语气抽取、渠道拆分、来源复核和交付前自查，而不直接把答案或隐藏流程写进题面。
* **Task 目标形态**：任务应落在内容团队常见的 campaign、newsletter、社媒线程、长短内容联动、内容运营收口等场景里。题面重点保留交付合同、受众、渠道限制和禁止事项，把内容方向收敛、素材优先级判断、语气迁移和复核路径留给 solver 与 skill 完成。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿素材与发布链路完成了整套动作，而不只看表面格式。重点应覆盖输入材料参与度、来源行号有效性、跨渠道差异、禁写项、发布缺口梳理，以及对跳过本地 review workflow、查看隐藏实现、硬编码答案和改输入的防护。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`content-creation__agent_first_campaign_pack`
- 类别：`content-creation`
- 难度：`hard`
- 绑定 Skill：`content-engine`
- 输入数据参考来源：
  - `environment/data/anchor_article.md`：任务内主文章工作稿；设计形态参考 PostHog Product for Engineers 文章  
    https://newsletter.posthog.com/p/what-we-wish-we-knew-before-building
  - `environment/data/supporting_context/agent_first_rules.md`：任务内补充原则稿；设计形态参考 PostHog Product for Engineers 文章  
    https://newsletter.posthog.com/p/the-golden-rules-of-agent-first-product
  - `environment/data/supporting_context/ai_features_lessons.md`：任务内上线后运营补充稿；设计形态参考 PostHog Product for Engineers 文章  
    https://newsletter.posthog.com/p/what-weve-learned-about-building
  - `environment/data/supporting_context/posthog_overview.md`：任务内产品背景材料；设计形态参考 PostHog 官网概览  
    https://posthog.com/
  - `environment/data/supporting_context/product_for_engineers_about.md`：任务内刊物语气说明；设计形态参考 Product for Engineers about 页面  
    https://newsletter.posthog.com/about
  - `environment/data/voice_samples/how_we_choose_technologies.md`：任务内品牌样例文稿；设计形态参考 Product for Engineers 文章  
    https://newsletter.posthog.com/p/how-we-choose-technologies
  - `environment/data/voice_samples/using_your_own_product_is_a_superpower.md`：任务内品牌样例文稿；设计形态参考 Product for Engineers 文章  
    https://newsletter.posthog.com/p/using-your-own-product-is-a-superpower
  - `environment/data/voice_samples/beyond_the_10x_engineer.md`：任务内品牌样例文稿；设计形态参考 Product for Engineers 文章  
    https://newsletter.posthog.com/p/beyond-the-10x-engineer
  - `environment/data/voice_samples/the_hidden_danger_of_shipping_fast.md`：任务内品牌样例文稿；设计形态参考 Product for Engineers 文章  
    https://newsletter.posthog.com/p/the-hidden-danger-of-shipping-fast
  - `environment/data/voice_samples/great_companies_are_built_in_hackathons.md`：任务内品牌样例文稿；设计形态参考 Product for Engineers 文章  
    https://newsletter.posthog.com/p/great-companies-are-built-in-hackathons

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 通过容器内 review service 读取素材索引、约束和逐文档行数，再沿官方解法生成 3 份渠道内容、来源映射和发布缺口输出。它证明任务可重跑、可核对，且不依赖隐藏答案文件。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出契约 | 校验 6 个输出文件存在、可解析，并满足 JSON / Markdown 结构要求 | 先理解正式交付合同，再组织最终产物 |
| 渠道约束与差异 | 校验 X / LinkedIn / newsletter 的字数、段落、标题、编号和跨渠道差异 | 多渠道改写与渠道特化意识 |
| 来源映射 | 校验 `source_map.json` 覆盖全部 deliverable，行号有效，且达到最小引用与文件覆盖要求 | 素材选用、行号登记和来源复核 |
| 发布缺口 | 校验 `publish_gaps.json` 覆盖约束里要求的 follow-up topic，且内容与当前素材边界一致 | 发布前缺口收口与团队协同意识 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 本地 review workflow | 要求 solver 在 verifier 前调用本地 review service，并覆盖索引、约束和文档检查链路 |
| 隐藏实现与环境完整性 | 禁止查看隐藏 service 实现、禁止修改输入数据与 `environment/skills`，并要求服务在 verifier 结束时仍健康 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把“主文章 + 补充材料 + 语气样例 + 发布约束 + 本地 review service”这条内容生产链路标准化，从而显著降低 solver 在素材边界、来源登记和跨渠道收口上的试错成本。without Skill 理论上可解，但更容易绕去查隐藏实现，或在 review workflow、来源覆盖和发布前复核动作上收不齐。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除平台 build 失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 每次都保留至少 1 项 verifier 失败；失败集中在查看隐藏 review-service 实现，另有 trial 暴露出来源覆盖不足或漏掉 review-service 文档检查。 |
| Agent 执行耗时 | `221.3s` | `175.5s` | With Skill 的素材分拣、渠道拆分和复核收敛更快，平均 Agent 执行耗时降低约 `20.7%`。 |
| Tokens | `344,639` | `223,731` | 按 `input + output` 汇总，With Skill 的平均 tokens 约为 Without Skill 的 `0.65x`，上下文和试错开销更低。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── hidden-service-src/
│   └── skills/
├── tests/
└── solution/
```
