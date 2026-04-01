# top20_search

`top20_search` 用来按 bucket 持续执行这一条流水线：

`搜索 -> 下载 -> 规则评审 -> 入选 -> 写入 results/<bucket>/selected_manifest.yaml`

默认目标是让每个 bucket 最终保留 `20` 个通过筛选的 skill；如果候选池提前耗尽，就返回不足 `20` 的结果。

## 这次改了什么

当前版本已经改成“所有 bucket 完全共用一套评审规则”。

现在 `bucket_review_rules.yaml` 里只保留：

- `bucket_review_rules._shared`
  共享的 Harbor 筛选规则、模型和上下文限制。

也就是说：

- bucket 的“任务可复现性”和“可验证性”规则全局统一。
- bucket 之间不再维护任何评审层面的主题差异配置。
- bucket 的区别只体现在搜索配置里，例如 `seed_queries`、`expand_queries`、`exclude_terms`。

## 共享筛选规则的设计目标

这套规则是为了让筛选后的 skill 更适合重构成 Harbor 任务。核心目标有两条：

1. 环境复现成本低
2. verifier 易于做稳定、无歧义、程序化验证

具体会优先保留这类 skill：

- 能清楚映射到目标 bucket，任务边界明确，不是泛化工作流或市场/路由类技能
- 自带可落地的资产，例如 schema、配置、脚本、样例、参考表、模板、检查清单
- 关键信息可以在 `instruction.md` 和输入资产中自包含，不依赖隐含前提
- 不强依赖私有 SaaS、在线变动接口、人工审批、昂贵基础设施
- 输出格式、路径、字段、容忍误差、边界条件足够明确，适合拆成 pytest 风格的小验证单元

会优先剔除这类 skill：

- 主要讲安装、发布、marketplace、session 管理、agent dispatcher
- 依赖私有账号、实时外部系统、不可控外部状态
- 验收标准主观、模糊、不可程序化
- 能力边界过宽，难以收敛成一个有稳定 verifier 的 Harbor 任务
- 缺少明确输入输出契约，没法写出稳定断言

## 评审是怎么执行的

评审入口在：

- `top20_search/src/evaluate_harbor_fit.py`

运行时会做两层判断：

### 第一层：LLM 逐个 skill 评审

模型会根据：

- `_shared` 里的共享规则
- 当前 bucket slug
- 当前 bundle 中截取的 markdown 内容

返回结构化结果：

- `selected`
- `decision`
- `summary`
- `matched_keep_rules`
- `matched_drop_rules`
- `confidence`

### 第二层：代码做硬门槛收口

即使模型返回了 `selected=true`，代码仍会再次检查：

- 所有 `required: true` 的 keep rule 是否都被命中
- 是否命中了任意 drop rule

只要：

- 缺少任何一个必需 keep rule
- 或命中了任意 drop rule

就会被代码强制改成 `drop`。

这一步是为了避免“模型口头说能保留，但实际上不满足 Harbor 任务重构前提”的情况。

## 当前支持状态

当前仓库里已经配置了这些 bucket：

- `data-quality`
- `xlsx`
- `portfolio-management`
- `debugging`
- `bioinformatics`

说明：

- `data-quality` 已经走通过实际运行链路，是当前主验证 bucket。
- 其它 bucket 现在也使用同一套共享评审规则，可以直接跑。
- 但除了 `data-quality` 之外，其它 bucket 目前仍主要是搜索配置级别的 scaffold，搜索词还可以继续细化。

## 目录结构

- 配置目录：`top20_search/configs/`
- 下载缓存：`top20_search/downloads/<bucket-slug>/`
- 最终结果：`top20_search/results/<bucket-slug>/selected_manifest.yaml`
- 主入口：`top20_search/src/run_bucket_search.py`

核心配置文件：

- `top20_search/configs/domains_and_buckets.yaml`
  作用：定义 bucket 的搜索词、排除词、目标数量等搜索参数。
- `top20_search/configs/bucket_review_rules.yaml`
  作用：定义所有 bucket 共用的 Harbor 筛选规则。

## 先决条件

运行前至少需要两类凭据：

- SkillsMP token：用于搜索和下载候选 skill
- OpenAI 兼容接口配置：用于让模型按规则评审 skill

Python 运行环境：

- 建议使用 `python3`
- 需要安装当前项目依赖，例如 `requests`、`PyYAML`

## Codex 配置怎么写

`top20_search` 默认优先读取本机 Codex 配置，而不是强制要求每次都传环境变量。

默认读取位置：

- `~/.codex/config.toml`
- `~/.codex/auth.json`

### `~/.codex/config.toml`

这个文件决定：

- 当前使用哪个 provider
- provider 的 `base_url`
- 默认模型

示例：

```toml
model_provider = "ikuncode"
model = "gpt-5.4"
model_reasoning_effort = "high"
network_access = "enabled"

[model_providers.ikuncode]
name = "ikuncode"
base_url = "https://api.ikuncode.cc/v1"
wire_api = "responses"
requires_openai_auth = true
```

说明：

- `base_url` 建议写到 `/v1`，不要直接写到 `/v1/chat/completions`
- 当前 `top20_search` 会自动拼接 `/v1/responses`
- 当前共享评审规则默认模型是 `gpt-5.4`

### `~/.codex/auth.json`

这个文件用于保存 OpenAI 兼容接口的 API key。

示例：

```json
{
  "OPENAI_API_KEY": "sk-xxxx"
}
```

## 环境变量怎么传

### SkillsMP token

三选一即可，代码按以下优先级读取：

```bash
export SKILLSMP_API_KEY='<your-skillsmp-token>'
# 或
export SKILLSMP_TOKEN='<your-skillsmp-token>'
# 或
export SKILLSMP_AUTH_TOKEN='<your-skillsmp-token>'
```

### OpenAI 兼容接口

如果 `~/.codex/config.toml` 和 `~/.codex/auth.json` 已经配置好了，通常不需要再额外传。

如果要临时覆盖本机配置：

```bash
export OPENAI_API_KEY='<your-openai-api-key>'
export OPENAI_BASE_URL='https://api.ikuncode.cc/v1'
```

## 最简单的运行方式

在 Harbor 仓库根目录执行：

```bash
python3 top20_search/src/run_bucket_search.py --bucket-slug data-quality
```

也可以运行别的 bucket：

```bash
python3 top20_search/src/run_bucket_search.py --bucket-slug xlsx
python3 top20_search/src/run_bucket_search.py --bucket-slug debugging
```

## 运行语义

- runner 会持续处理候选，直到 `selected_target` 达到为止
- 若候选提前耗尽，会返回不足 `selected_target` 的结果
- 每次运行前会清空并重建下载目录：
  `top20_search/downloads/<bucket-slug>/`
- 最终物化结果时会清空并重建结果目录：
  `top20_search/results/<bucket-slug>/`
- 单个候选下载、解析、评审失败时，会打印：
  `skip candidate <id>: <reason>`
  然后继续处理后面的候选

为了兼容当前代理链路，共享评审规则目前统一采用：

- `max_markdown_files: 1`
- `max_total_characters: 2000`

这个限制是稳定性优先的保守配置，`data-quality` 的已验证路径也沿用它。

## 如何新增或修改 bucket

现在新增 bucket 只需要改一个地方：搜索配置。

### 第一步：修改 `domains_and_buckets.yaml`

文件：

- `top20_search/configs/domains_and_buckets.yaml`

你需要新增一个 bucket 条目，例如：

```yaml
search_buckets:
  - slug: your-bucket
    name: Your Bucket
    domain: data-ml-engineering
    description: 用一句话说明这个 bucket 想搜什么。
    seed_queries:
      - your bucket
      - core query
    expand_queries:
      - related query
      - another query
    exclude_terms:
      - install skill
      - registry
    candidate_limit: 100
    selected_target: 20
    target_limit: 20
```

### 第二步：确认共享规则处于启用状态

文件：

- `top20_search/configs/bucket_review_rules.yaml`

这里不再按 bucket 写差异配置，只需要保证 `_shared.enabled: true`。

说明：

- 所有 bucket 统一复用 `_shared` 规则
- 只要 `domains_and_buckets.yaml` 里新增了 bucket
- 且 `_shared` 规则是启用状态

这个 bucket 就可以直接运行，不需要在 `bucket_review_rules.yaml` 里再补同名条目。

## 常见坑

- `base_url` 写成 `https://api.xxx.com/v1/chat/completions`
  通常不对。应写到 `/v1`
- 搜索词过泛
  会导致抓到大量“meta skill”或 marketplace 型 skill，评审会频繁 drop
- provider 能列模型，但具体模型不可调用
  典型现象是 `/v1/models` 成功，但实际请求时报 `model_not_found`

## 推荐排查顺序

1. 先验证 key 是否能列模型
2. 再验证目标模型是否真的可调用
3. 再跑 `run_bucket_search.py`
4. 最后检查 `top20_search/results/<bucket>/selected_manifest.yaml`

## 测试

运行全量测试：

```bash
python3 -m unittest discover -s top20_search/tests -p 'test_*.py' -v
```

只跑评审和主流程测试：

```bash
python3 -m unittest top20_search.tests.test_evaluate_harbor_fit top20_search.tests.test_run_bucket_search -v
```
