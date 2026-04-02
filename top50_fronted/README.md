# top50_fronted

`skillsmp` 小类快照与模板资产目录。

当前目录主要包含两类产物：

- 阶段 1 快照资产：抓取 `skillsmp` 分类树与每个小类的 top50 skills
- 模板资产：为后续 `skill + 模板 -> task family` 生成准备可复用模板

## 目录目标

- 抓取 `skillsmp` 分类树（大类/小类）
- 按每个小类的 `top50` 技能生成快照
- 输出总快照和按小类拆分的快照文件
- 为后续小类级任务模板提供设计输入

## 当前实现约束

- 默认使用 `cloudscraper` 访问 `skillsmp`，绕过公开页面和旧接口的 Cloudflare challenge
- 小类技能列表使用 `GET /api/skills?page=<n>&limit=<page_size>&sortBy=stars&category=<subcategory_slug>`
- 当前旧接口单页实际上最多返回 `100` 条；当 `--limit > 100` 时，脚本会自动翻页并聚合
- 本地会按 `stars desc -> forks desc -> name asc -> id asc` 再排一次，避免服务端排序波动

## 运行方式

```bash
PYTHONPATH=vendor python3 src/skillsmp_snapshot.py
```

抓每个小类前 `200` 条时，建议单独写到新的输出文件和目录：

```bash
PYTHONPATH=vendor python3 src/skillsmp_snapshot.py \
  --limit 200 \
  --output subcategory_hot_skills_snapshot_top200.yaml \
  --per-subcategory-dir subcategory_top200
```

## 输出文件

```text
./subcategory_hot_skills_snapshot.yaml
./subcategory_top50/<category_slug>/<subcategory_slug>.yaml
./downloads_until_development/<category_slug>/<subcategory_slug>/<rank>__<skill_name>/
./downloads_until_development/download_manifest.yaml
```

其中：

- `subcategory_hot_skills_snapshot.yaml`
  保存完整分类树和全部小类 top50 快照，适合全局分析
- `subcategory_top50/<category_slug>/<subcategory_slug>.yaml`
  每个小类单独一份 top50 快照，适合后续按小类建模模板
- 当你用 `--limit 200 --per-subcategory-dir subcategory_top200` 时，会生成对应的 top200 快照目录

例如：

- `subcategory_top50/data-and-ai/llm-ai.yaml`
- `subcategory_top50/development/frontend.yaml`

## 批量下载 skill

当前还新增了一个批量下载脚本，用于把 `subcategory_top50` 中按一级目录名排序从开头到 `development` 为止的小类快照里的 skill 拉到本地。

如果你已经先生成了 `subcategory_top200`，也可以把下载脚本的 `--input-dir` 切到这个目录。

运行方式：

```bash
python3 src/download_subcategory_skills.py
```

可选参数：

```bash
python3 src/download_subcategory_skills.py \
  --input-dir subcategory_top50 \
  --end-category development \
  --output-dir downloads_until_development \
  --jobs 8
```

默认行为：

- 包含 `development`
- 按完全相同的 `github_url` 去重下载
- 默认按唯一 `github_url` 最多并行处理 `8` 个下载任务；可用 `--jobs` 调整
- 仍会按 `category/subcategory/rank__skill_name` 分别物化；如果 `skill_name` 不适合作为目录名，则退回成纯 `rank`
- tree 型 GitHub URL 先走 GitHub Contents API，失败后回退到 `git sparse-checkout`
- 对 GitHub 仓库根 URL 会先解析默认分支，再把仓库根目录当作 skill 根目录下载
- 如果根目录没有 `SKILL.md` 或 `skill.md`，该条会记为 `skipped`

如果你已经设置了 `GITHUB_TOKEN` 或 `GH_TOKEN`，GitHub API 下载通常会更稳。

运行结果会写到：

- `downloads_until_development/<category_slug>/<subcategory_slug>/<rank>__<skill_name>/`
- `downloads_until_development/download_manifest.yaml`

## 模板资产

当前已经补了一个面向 `llm-ai` 小类中 `agent-workflow` 型 skill 的模板目录：

- [agent_workflow_template/agent-workflow-template.yaml](/home/lenovo/skill/Harbor/top50_fronted/agent_workflow_template/agent-workflow-template.yaml)
- [agent_workflow_template/README.md](/home/lenovo/skill/Harbor/top50_fronted/agent_workflow_template/README.md)

这个模板的用途不是复刻某个已有任务内容，而是学习 `jpg-ocr-stat/image-ocr` 这种 `1 similar + 3 transfer` family 的组织方式，
再把它抽象成适合 `agent-workflow` 类 skill 的任务模板。

### 模板怎么用

后续使用时，最小输入是：

1. 一个目标 skill
2. 一个模板 YAML

对于当前已提供的 `agent_workflow_template`，推荐和下面这类小类快照一起使用：

- [llm-ai.yaml](/home/lenovo/skill/Harbor/top50_fronted/subcategory_top50/data-and-ai/llm-ai.yaml)

使用顺序：

1. 先从对应小类的 top50 快照里选定一个 skill
2. 再读取模板 YAML，确认这个模板定义的 `family_spec`
3. 根据模板里的 `instruction_scaffold_zh` 生成 4 个任务的 instruction 骨架
4. 根据模板里的 `task_package_contract` 把任务真正落成 Harbor task 包
5. 根据模板里的 `io_contract` 选择输入资产和输出形态

## 筛选 Prompt 资产

当前还补了一个面向“单个本地 skill 目录”的 Harbor 适配筛选 prompt 目录：

- [skill_screening_prompt/README.md](/home/levi/Harbor/top50_fronted/skill_screening_prompt/README.md)
- [skill_screening_prompt/single-skill-harbor-screening-prompt.md](/home/levi/Harbor/top50_fronted/skill_screening_prompt/single-skill-harbor-screening-prompt.md)
- [skill_screening_prompt/output-schema.json](/home/levi/Harbor/top50_fronted/skill_screening_prompt/output-schema.json)

这个 prompt 的定位是：

1. 你已经把某个目标 skill 下载到本地
2. 让 `Codex` 先递归探索这个 skill 目录
3. 再结合 Harbor skill 与 Harbor task builder 约束，判断这个 skill 是否值得保留

筛选时看的是两件事：

- 这个 skill 是否适合被转化为可验证、可复现的 Harbor 任务
- 在该任务里，`agent` 使用这个 skill 是否会明显优于不用 skill

这里不要求 skill 必须自带完整现成输入资产。只要它提供了足够清晰的方法、结构、规则或检查框架，使 `Codex` 能合理造输入、写题面和 verifier，就仍然可能被保留。

## 测试

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```
