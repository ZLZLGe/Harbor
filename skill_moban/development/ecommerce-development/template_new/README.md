# Ecommerce Development Template

这是面向 `ecommerce-development` 类 skill 的模板。它综合参考 SkillsMP 这一类热门 skill 的共性能力：商店初始化、商品结构配置、配送规则、支付规则、公开接口定制，以及把多来源商品素材整理成可运营的 WooCommerce 工作区。

## 第一部分：任务设计参考

* **Skill 价值定位**：ecommerce-development 类热门 skill 的价值，通常落在把平台配置、目录结构、支付与配送规则、定制代码和交付验证串成一条完整交付链路。它应该帮助 solver 更快识别平台内的关键动作和检查路径，并把结果沉淀成可运行的商店能力。
* **Task 目标形态**：任务宜放在店铺搭建、商品导入、类目组织、配送配置、支付范围控制、营销 feed 或轻量 storefront 接口等场景中。题面应重点保留业务目标、输入数据、交付合同和禁止事项，把平台内实现顺序留给 solver 与 skill 自行判断。
* **Verifier 设计重点**：Verifier 应优先验证平台动作是否落地，例如目录是否按数据生成、变体是否可用、配送和支付规则是否生效、接口是否按输入数据返回结果。它还需要防止硬编码、跳过平台配置、篡改输入数据或只做表层接口伪装。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ecommerce_development__museum_printshop_launch`
- 类别：`ecommerce-development`
- 难度：`hard`
- 绑定 Skill：`wordpress-woocommerce-development`
- 输入数据参考来源：
  - `environment/data/met_print_seed.csv`：任务内商品种子行；字段组织参考 The Met Open Access 对象快照与馆藏上新清单  
    https://github.com/metmuseum/openaccess
  - `environment/data/met_object_details.ndjson`：任务内作品明细快照；对象字段直接来源于 The Met Collection API  
    https://metmuseum.github.io/  
    https://collectionapi.metmuseum.org/public/collection/v1/objects/436532
  - `environment/data/met_departments.json`：任务内部门清单快照；字段直接来源于 The Met Collection API departments 接口  
    https://collectionapi.metmuseum.org/public/collection/v1/departments
  - `environment/data/collection_plan.json`：任务内系列与上架计划文件；结构设计参考 WooCommerce 商品分类与系列组织  
    https://woocommerce.com/document/managing-product-taxonomies/
  - `environment/data/shipping_rules.json`：任务内配送规则文件；结构设计参考 WooCommerce shipping zones / shipping classes  
    https://woocommerce.com/document/setting-up-shipping-zones/
  - `environment/data/checkout_policy.md`：任务内支付约束文件；约束形态参考 WooCommerce payment gateway 配置  
    https://woocommerce.com/document/payment-gateway-api/

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：oracle 在同一容器内启动 WordPress、WooCommerce 和数据库，执行参考 reseed 逻辑后，通过站点接口和 WooCommerce 内部状态重算目录、配送、支付与 feed 结果，证明任务可运行、可解。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 数据重建入口 | 校验 `scripts/reseed.php` 能基于当前输入生成 `seed-summary.json` | 通过平台内脚本完成导入与配置，而不是手填答案 |
| 商品与变体 | 校验商品、系列、部门、属性、变体、SKU 与库存映射是否符合输入数据 | WooCommerce 商品结构与变体建模 |
| 配送配置 | 校验 shipping classes、shipping zones、费率与地域范围是否生效 | 配送配置与平台规则落地 |
| 支付范围控制 | 校验代表性购物车上的网关可见性是否符合 checkout policy | 支付规则配置与条件限制 |
| Launch Feed | 校验 `/wp-json/harbor-printshop/v1/launch-feed` 的字段、排序与过滤结果 | WooCommerce 定制接口与上架结果收口 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入驱动 | 修改输入数据后重新 reseed，输出和 feed 必须跟着变化 |
| 数据完整性 | `/app/data/` 输入哈希保持不变，站点与 WooCommerce 在 verifier 结束时仍可用 |

### ⚡ Skill 相关性评估

结论：待实验补齐。这个任务的核心价值在于把 WooCommerce 的目录搭建、配送规则、支付范围控制和定制 feed 串成一条完整交付链路；题面只保留交付合同与业务约束，能否快速识别并完成平台内关键动作，将直接影响收敛速度与通过率。

基于最近 **n** 次有效对比实验（待补齐）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `待补齐` | `待补齐` | `待补齐` |
| Agent 执行耗时 | `待补齐` | `待补齐` | `待补齐` |
| Tokens | `待补齐` | `待补齐` | `待补齐` |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
