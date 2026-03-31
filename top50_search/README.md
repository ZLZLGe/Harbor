# top50_search

## 用法

在 Harbor 根目录下运行。

### 1. 运行测试

```bash
python3 -m unittest discover -s top50_search/tests -p 'test_*.py' -v
```

### 2. 配置 SkillsMP 认证

脚本会按下面顺序读取 token，三选一即可：

```bash
export SKILLSMP_API_KEY='<your-token>'
```

或：

```bash
export SKILLSMP_TOKEN='<your-token>'
```

或：

```bash
export SKILLSMP_AUTH_TOKEN='<your-token>'
```

### 3. 运行单个 bucket

```bash
python3 top50_search/src/run_bucket_search.py --bucket-slug data-quality
```

可选参数：

```bash
python3 top50_search/src/run_bucket_search.py \
  --config-path top50_search/configs/domains_and_buckets.yaml \
  --bucket-slug data-quality \
  --results-root top50_search/results
```

### 4. 运行后的产物查看

查看本轮下载到的候选 skill 目录数：

```bash
find top50_search/downloads/data-quality -mindepth 1 -maxdepth 1 -type d | wc -l
```

查看本轮入选结果：

```bash
sed -n '1,120p' top50_search/results/data-quality/selected_manifest.yaml
```

## 搜别的类别怎么改 `configs`

要新增类别，主要改两个文件：

- `top50_search/configs/domains_and_buckets.yaml`
- `top50_search/configs/harbor_fit_rules.yaml`

先改前者让脚本“搜到”，后改后者让脚本“筛得准”。

### 1. 改 `domains_and_buckets.yaml`

规则很简单：

- `domains` 放上层领域，比如 `software-engineering`、`scientific-computing`
- `search_buckets` 放实际执行搜索的最终类别
- 每个最末级类别都建一个独立 bucket

示例：

```yaml
domains:
  - slug: software-engineering
    name: Software Engineering
    description: Engineering workflows such as debugging, security, and performance.

search_buckets:
  - slug: debugging
    name: Debugging
    domain: software-engineering
    description: Skills focused on bug isolation, reproduction, and root-cause analysis.
    seed_queries:
      - debugging
      - bug reproduction
      - root cause analysis
    expand_queries:
      - stack trace analysis
      - crash investigation
      - regression diagnosis
    exclude_terms:
      - install skill
      - publish skill
      - registry
      - marketplace
    candidate_limit: 100
    target_limit: 50
```

关键字段：

- `slug`：唯一标识，运行时用 `--bucket-slug`
- `domain`：必须引用已存在的 domain slug
- `seed_queries`：核心搜索词
- `expand_queries`：补充搜索词
- `exclude_terms`：排除元信息类结果
- `candidate_limit`：每个 query 拉多少候选
- `target_limit`：当前 bucket 的目标数量

运行示例：

```bash
python3 top50_search/src/run_bucket_search.py --bucket-slug debugging
```

### 2. 改 `harbor_fit_rules.yaml`

只改搜索 bucket 不够。  
当前评估逻辑是按 `data-quality` 主题设计的，直接拿去筛 `debugging`、`xlsx`、`legal-research`、`bioinformatics` 这类类别，误筛会很多。

所以新增类别后，还需要同步补这个类别对应的评估规则；否则会出现：

- 能搜到候选，但大量候选被误判淘汰
- 搜索词是对的，但最终结果不准

### 3. 推荐组织方式

- 一个上层领域对应一个 `domain`
- 一个最末级类别对应一个 `search_bucket`
- `target_limit` 如果目标仍然是 Top 50，就统一写 `50`

例如：

- `Finance & Economics` -> `portfolio-management`、`financial-modeling`、`risk-analysis`
- `Software Engineering` -> `debugging`、`version-control`、`security-engineering`
- `Scientific Computing` -> `bioinformatics`、`cheminformatics`、`physics-simulation`

## 目录与文件含义

### `configs/`

- `domains_and_buckets.yaml`
  - 搜索配置入口。
  - 定义 domain、bucket、查询词、排除词、candidate_limit、target_limit。
  - 想搜索新的类别时，优先改这个文件：先补 `domains`，再为目标类别新增 `search_buckets`。
- `harbor_fit_rules.yaml`
  - Harbor 适配规则。
  - 定义 `capability_boundary`、`environment_reproducibility`、`verifier_stability` 三个轴的正负信号。
  - 如果新类别与 data-quality 差异很大，除了改 bucket 搜索词，还需要同步调整这里的评估规则。

### `src/`

- `search_skillsmp.py`
  - 负责调用 SkillsMP 搜索接口并把返回结果归一化成统一 candidate 结构。
- `fetch_skill_bundle.py`
  - 负责根据 GitHub tree URL 拉取 skill 目录内容并写入本地。
- `evaluate_harbor_fit.py`
  - 负责读取下载下来的 skill 文档并按 Harbor 规则打分。
- `run_bucket_search.py`
  - 总入口。
  - 负责把搜索、下载、评估、筛选、结果落盘串起来。

### `tests/`

- 存放 `top50_search` 的单元测试和 fixture。
- 用来验证搜索归一化、skill 下载、Harbor 评估、bucket runner 行为。

### `downloads/`

- 本轮 bucket run 的候选下载缓存。
- 路径格式：

```text
top50_search/downloads/<bucket-slug>/<rank>__<skill-id>/
```

- 每次运行同一个 bucket 前，脚本会先清空对应的 `downloads/<bucket-slug>/`，所以这里的内容只代表本轮运行。
- 这里放的是“成功下载到本地的候选 skill 目录内容”，不等于最终入选。

### `results/`

- 本轮 bucket run 的最终筛选结果。
- 路径格式：

```text
top50_search/results/<bucket-slug>/
```

- 这里只保留当前这轮 run 最终通过 Harbor 评估的 skill。

### `results/<bucket>/selected_manifest.yaml`

- 最终入选清单。
- 每一项表示一个通过筛选的 skill bundle。
- 字段含义：
  - `rank`：该 skill 在本轮候选列表中的排序位置。
  - `id`：skill 的唯一标识。
  - `name`：skill 名称。
  - `author`：skill 作者。
  - `skillsmp_url`：SkillsMP 页面地址。
  - `github_url`：GitHub skill 目录地址。
  - `selected_dir`：该 skill 在 `results/<bucket>/` 里的本地目录名。

## 运行语义

- `downloads/` 表示“本轮成功下载下来的候选”。
- `results/` 表示“本轮最终入选的候选”。
- 如果某个 candidate 下载失败，它不会进入 `downloads/` 的本轮产物，也不会进入 `results/`。
- 如果某个 candidate 下载成功但 Harbor 评估不通过，它会留在 `downloads/`，但不会出现在 `results/`。
