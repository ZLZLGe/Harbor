# top20_search

`top20_search` 用于按 bucket 执行技能筛选流水线：

`搜索 -> 下载 -> 评审 -> 入选 -> 写入 results/<bucket>/selected_manifest.yaml`

默认目标是每个 bucket 最终保留 `20` 个通过筛选的 skill。若候选池提前耗尽，则返回不足 `20` 的结果。

## 项目结构

- `configs/domains_and_buckets.yaml`
  定义 bucket、搜索词、排除词和目标数量。
- `configs/bucket_review_rules.yaml`
  定义所有 bucket 共用的 Harbor 评审规则。
- `src/run_bucket_search.py`
  主入口，负责串起完整流程。
- `src/evaluate_harbor_fit.py`
  负责调用模型评审，并用代码做最终硬门槛收口。
- `downloads/<bucket>/`
  候选 skill 的下载缓存目录。
- `results/<bucket>/selected_manifest.yaml`
  最终入选结果清单。

## 评审规则

所有 bucket 共用 `bucket_review_rules._shared` 中的一套规则，不再为不同主题维护单独的评审配置。

这套规则的目标是筛出更适合重构成 Harbor 任务的 skill，重点关注：

- 环境复现成本是否低
- 输入输出契约是否清晰
- 验收是否可以稳定、程序化验证
- 是否依赖私有 SaaS、实时外部系统或组织内部环境
- 是否只是参考材料、平台路由或过于宽泛的工作流

模型先给出结构化评审结果，代码再做硬门槛检查：

- 必需 keep rule 没命中：强制 `drop`
- 任一 drop rule 命中：强制 `drop`

因此，最终结果不是单纯依赖模型口头判断。

## 当前 bucket

当前仓库已配置这些 bucket：

- `data-quality`
- `xlsx`
- `portfolio-management`
- `debugging`
- `bioinformatics`

这些 bucket 共享同一套评审规则，差异只体现在搜索配置上。

## 运行前准备

至少需要两类凭据：

- SkillsMP token：用于搜索和下载 skill
- OpenAI 兼容接口配置：用于评审 skill

Python 环境建议使用 `python3`，并安装项目依赖，例如 `requests`、`PyYAML`。

## 配置方式

### SkillsMP token

以下环境变量任选其一：

```bash
export SKILLSMP_API_KEY='<your-skillsmp-token>'
# 或
export SKILLSMP_TOKEN='<your-skillsmp-token>'
# 或
export SKILLSMP_AUTH_TOKEN='<your-skillsmp-token>'
```

### OpenAI 兼容接口

程序会优先读取本机 Codex 配置：

- `~/.codex/config.toml`
- `~/.codex/auth.json`

也可以直接用环境变量覆盖：

```bash
export OPENAI_API_KEY='<your-openai-api-key>'
export OPENAI_BASE_URL='https://api.ikuncode.cc/v1'
```

`OPENAI_BASE_URL` 建议写到 `/v1`，不要写到 `/v1/chat/completions`。

## 运行方式

在 Harbor 仓库根目录执行：

```bash
python3 top20_search/src/run_bucket_search.py --bucket-slug data-quality
```

也可以运行其他 bucket：

```bash
python3 top20_search/src/run_bucket_search.py --bucket-slug xlsx
python3 top20_search/src/run_bucket_search.py --bucket-slug debugging
```

## 运行行为

- 会持续处理候选，直到达到 `selected_target`
- 若候选提前耗尽，会返回部分结果
- 每次运行前会清空并重建 `downloads/<bucket>/`
- 物化结果时会清空并重建 `results/<bucket>/`
- 单个候选下载、解析或评审失败时，会打印 `skip candidate <id>: <reason>`，然后继续处理后续候选

当前共享评审规则默认使用：

- `preferred_model: gpt-5.4`
- `max_markdown_files: 1`
- `max_total_characters: 2000`

这是稳定性优先的保守配置。

## 新增或修改 bucket

新增 bucket 只需要改 `configs/domains_and_buckets.yaml`。

示例：

```yaml
search_buckets:
  - slug: your-bucket
    name: Your Bucket
    domain: data-ml-engineering
    description: 用一句话说明这个 bucket 想搜什么。
    seed_queries:
      - core query
      - another query
    expand_queries:
      - related query
    exclude_terms:
      - install skill
      - registry
    candidate_limit: 100
    selected_target: 20
    target_limit: 20
```

只要共享规则 `_shared.enabled: true`，新增 bucket 就可以直接运行，不需要在 `bucket_review_rules.yaml` 里额外添加同名条目。

## 常见问题

- 搜索词过泛：会召回大量 meta skill、参考型 skill 或平台型 skill，评审会大量 `drop`
- provider 能列模型但不能实际调用：通常表现为 `/v1/models` 可用，但实际请求时报 `model_not_found`
- `base_url` 写错：应配置到 `/v1`，不要直接写 completions 路径

## 测试

运行全部测试：

```bash
python3 -m unittest discover -s top20_search/tests -p 'test_*.py' -v
```

只跑评审和主流程相关测试：

```bash
python3 -m unittest top20_search.tests.test_evaluate_harbor_fit top20_search.tests.test_run_bucket_search -v
```
