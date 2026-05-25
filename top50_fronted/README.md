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
- 小类技能列表使用 `GET /api/skills?page=1&limit=50&sortBy=stars&category=<subcategory_slug>`
- 本地会按 `stars desc -> forks desc -> name asc -> id asc` 再排一次，避免服务端排序波动

## 运行方式

```bash
PYTHONPATH=vendor python3 src/skillsmp_snapshot.py
```

## 输出文件

```text
./subcategory_hot_skills_snapshot.yaml
./subcategory_top50/<category_slug>/<subcategory_slug>.yaml
```

其中：

- `subcategory_hot_skills_snapshot.yaml`
  保存完整分类树和全部小类 top50 快照，适合全局分析
- `subcategory_top50/<category_slug>/<subcategory_slug>.yaml`
  每个小类单独一份 top50 快照，适合后续按小类建模模板

例如：

- `subcategory_top50/data-and-ai/llm-ai.yaml`
- `subcategory_top50/development/frontend.yaml`

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

## 测试

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```
