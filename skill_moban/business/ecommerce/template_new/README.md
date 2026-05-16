# Ecommerce Template

这是面向 `ecommerce` 类 skill 的模板。它综合参考 SkillsMP `ecommerce` 类热门 skill 的共性能力：围绕商品目录、集合展示、搜索入口、店铺前台规则和结构化交付，把公开来源形态的电商输入快照落到可复跑的页面渲染和报告产物。

## 第一部分：任务设计参考

* **Skill 价值定位**：`ecommerce` 类热门 skill 的共同价值，是把目录数据、页面结构、搜索分组、前台展示规则和交付产物串成一条可执行工作流。对这类模板来说，skill 的作用应聚焦在帮助 solver 更快识别 Shopify 主题工作区、Liquid 渲染路径、主题检查和收口动作，同时把题面的业务判断保持在必要披露范围内。
* **Verifier 设计重点**：Verifier 应优先检查 solver 是否完成了关键电商动作和页面闭环，不要只卡表面格式。重点应覆盖商品卡顺序、徽章与库存提示、过滤与排序、搜索分组、报告字段、重建能力，以及输入变更后页面和报告能否一起刷新。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ecommerce__shopify_capsule_collection_preview`
- 类别：`ecommerce`
- 绑定 Skill：`shopify-expert`
- 输入数据参考来源：
  - `environment/data/catalog_products.json`：任务内商品目录与变体快照；设计形态参考 Shopify 商品 CSV 示例与 Dawn 商品卡片  
    https://raw.githubusercontent.com/shopifypartners/shopify-product-csvs-and-images/master/csv-files/apparel.csv  
    https://github.com/Shopify/dawn/blob/main/snippets/card-product.liquid
  - `environment/data/collection_context.json`：任务内集合顺序、精选位、过滤项和排序项；设计形态参考 Dawn 集合页与 Shopify 商品分类参考  
    https://github.com/Shopify/dawn/blob/main/sections/main-collection-product-grid.liquid  
    https://shopify.github.io/product-taxonomy/
  - `environment/data/predictive_search_snapshot.json`：任务内搜索建议、集合和商品分组输入；设计形态参考 Dawn predictive search  
    https://github.com/Shopify/dawn/blob/main/sections/predictive-search.liquid
  - `environment/data/theme_section_blueprint.json`：任务内 section、block 和 settings 蓝图；设计形态参考 Dawn 集合页与搜索 section 结构  
    https://github.com/Shopify/dawn/blob/main/sections/main-collection-product-grid.liquid  
    https://github.com/Shopify/dawn/blob/main/sections/predictive-search.liquid
  - `environment/data/theme_quality_rules.json`：任务内页面与报告检查项；设计形态参考 Dawn 商品卡片和集合页的结构约束  
    https://github.com/Shopify/dawn/blob/main/snippets/card-product.liquid  
    https://github.com/Shopify/dawn/blob/main/sections/main-collection-product-grid.liquid

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 集合页渲染 | 检查标题、工具栏、商品卡数量、商品句柄、价格、库存提示、徽章和图片属性是否与输入一致 | 沿着 Shopify 主题结构把目录数据落到集合页 |
| 过滤与排序 | 检查过滤组、选项计数和排序项是否跟随当前集合上下文刷新 | 保持集合控制项由输入驱动，不写死前台结果 |
| 搜索面板与报告 | 检查 queries / collections / products 三组搜索结果，以及报告字段与统计是否完整 | 让搜索面板和结构化交付一起收口 |
| 本地主题检查 | 检查 `shopify theme check` 是否通过 | 在交付前完成主题检查和最后一轮修正 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入数据保护 | 原始输入文件不能被改写 |
| 变更传播 | 调整精选位、查询词和库存后，集合页、搜索面板和报告都要同步刷新 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 Shopify 主题工作区阅读、Liquid section / snippet 定位、主题检查与数据驱动渲染整合成一条更稳定的执行路径，从而减少在徽章逻辑、页面重建和交付收口上的反复试错。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败、BuildException、build cancelled 一类 trial，并按当前 final verifier 口径统一复核）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0 / 3` | `2 / 3` | 近 3 次有效对照里，without Skill 主要停在 sale badge 残留和最后一轮主题检查收口；with Skill 仍有 1 次漏掉 report availability 的同步。 |
| Agent 执行耗时 | `385.5s` | `350.7s` | With Skill 的定位与收口更快，平均 Agent 耗时下降约 `9.0%`。 |
| Tokens | `768,173` | `643,226` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.19x`。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（业务目标、输入、输出合同、禁止事项）
├── task.toml               # 任务元数据（技能要求、超时、环境资源）
├── PLAN.json               # 任务构建元信息（设计理由、环境取舍、verifier 重点、实验口径）
├── README.md               # 模板说明、实验结果与目录结构
├── environment/            # 单容器运行环境
│   ├── Dockerfile          # 环境镜像定义
│   ├── data/               # 输入数据
│   ├── workspace/          # 待完成的 Shopify 主题工作区
│   └── skills/             # 仅 with_skill 环境保留的绑定 skill
├── tests/                  # Verifier 主测试与防作弊测试
└── solution/               # 官方参考解与 solve.sh
```
