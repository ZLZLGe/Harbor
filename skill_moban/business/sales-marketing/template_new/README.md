# Sales-Marketing Template

这是面向 `sales-marketing` 类 skill 的模板。它综合参考 SkillsMP `sales-marketing` 类热门 skill 的共性能力：围绕业务目标收集结构化输入、做出带约束的判断、把分析结果落到可执行交付物，并在预算、优先级、例外项和风险之间完成收口。

## 第一部分：任务设计参考

* **Skill 价值定位**：`sales-marketing` 类热门 skill 常见价值，是把业务分析、优先级判断、约束识别和结果落地串成一条可执行路径。对这类模板来说，skill 不应直接把答案写在题面里，而应帮助 solver 更快识别输入信号、选择方法、完成取舍，并把结论整理成团队可用的输出。
* **Verifier 设计重点**：这类任务的 verifier 应优先检查 solver 是否完成了关键业务动作和结果闭环，不要只卡表面格式。它应核对输入是否被完整使用、确认 promo / launch / budget tradeoff 是否体现在行动里、检查约束是否被遵守，并拦住硬编码、忽略状态阻断、把 review set 塞满低优先级行或只做表层汇总的捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`sales-marketing__retail-replenishment-planning`
- 类别：`sales-marketing`
- 难度：`hard`
- 绑定 Skill：`inventory-demand-planning`
- 输入数据参考来源：
  - `environment/data/historical_demand_weekly.csv`：任务内周级销量历史；设计形态参考 UCI `Sales Transactions Weekly`，并扩展为门店维度规划场景  
    https://archive.ics.uci.edu/dataset/396/sales+transactions+dataset+weekly
  - `environment/data/planning_manifest.json`：任务内规划窗口和范围声明，来自模板内部配置
  - `environment/data/sku_store_setup.csv`：任务内门店与 SKU 配置，来自模板内部配置
  - `environment/data/inventory_snapshot.csv`：任务内库存与占用快照，来自模板内部配置
  - `environment/data/open_purchase_orders.csv`：任务内在途到货数据，来自模板内部配置
  - `environment/data/promotion_schedule.csv`：任务内促销排期，来自模板内部配置
  - `environment/data/vendor_constraints.csv`：任务内供应约束与成本数据，来自模板内部配置
  - `environment/data/planning_policy.yaml`：任务内规划规则与预算阈值，来自模板内部配置
  - `environment/data/new_sku_analogs.csv`：任务内短历史商品类比映射，来自模板内部配置

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应 Skill 考察点 |
| :--- | :--- | :--- |
| 格式要求 | 检查最终输出（CSV / JSON / Markdown）是否齐全、可读且字段完整 | 明确交付标准后，再组织内容 |
| 预测覆盖与准确度 | 确认预测涵盖所有门店和 SKU，并核对各种商品状态（平稳/趋势/新品）的预测特征是否合理 | 结合实际需求规律选择预测方法，并考虑促销与库存缓冲 |
| 核心补货订单 | 确认当期补货计划中，是否在有限的处理额度内优先保障了促销和新品需求 | 将预测结果转化为区分优先级的执行动作 |
| 结果闭环 | 检查汇总指标（总额、预算校验、风险项、例外情况）是否与明细数据一致 | 确保明细报表与汇总结论完全对齐 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入数据保护 | 原始数据文件（`/app/data`）不允许被修改 |
| 业务规则校验 | 已阻断或停用状态的商品不能出现在补货计划中 |
| 新品逻辑透明度 | 总结报告中必须体现出新品的参考指标与预算预留 |
| 优先级过滤 | 当期执行计划不能被低优先级的补货任务注水占满 |
| 促销反馈 | 预测数据必须明显反映出促销活动带来的销量波峰与波谷 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的主要价值是帮助 solver 更快锁定 demand-profile 对应方法、short-history analog 处理、promo / launch 优先级，以及 review-cap 内的 current-cycle action 取舍。按当前 final verifier 口径统一复核最近 3 次有效对照后，with_skill 全部可通过；without_skill 都保留了至少一项动作级失败，主要集中在预算利用、launch 保护和例外项闭环。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial，并按当前 final verifier 口径统一复核）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | 近 3 次有效对照里，without Skill 都留下了至少一项动作级失败；with Skill 在当前 final verifier 口径下可稳定通过。 |
| Agent 执行耗时 | `658.4s` | `695.9s` | 这 3 轮里 With Skill 的主要收益体现在通过率，不体现在平均耗时。 |
| Tokens | `0.91M` | `1.28M` | 这 3 轮里 With Skill 的平均 tokens 更高，优势主要来自方法收敛质量而不是更低上下文开销。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（症状、业务约束、输出合同、禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、超时、环境资源）
├── PLAN.json               # 任务构建元信息（设计理由、环境取舍、verifier 重点、实验口径）
├── README.md               # 模板说明、实验结果与目录结构
├── environment/            # 单容器运行环境
│   ├── Dockerfile          # 环境镜像定义
│   ├── data/               # 固定输入数据
│   └── skills/             # 仅 with_skill 环境保留的绑定 skill
├── tests/                  # Verifier 主测试与防作弊测试
└── solution/               # 官方参考解与 solve.sh
```
