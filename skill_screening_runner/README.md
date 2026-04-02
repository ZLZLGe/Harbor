# skill_screening_runner

独立的本地 skill Harbor 适配筛选工具。

这个模块只负责一件事：

- 对本地 skill 目录做 Harbor 适配筛选
- 既支持单个小类筛选，也支持自动发现多个小类后批量筛选

它不会修改：

- `/home/levi/Harbor/top50_fronted`
- `/home/levi/Harbor/codex_task_builder_v3`
- `/mnt/e/skill_all`

## 功能范围

- 输入一个小类目录，例如 `/mnt/e/skill_all/development/backend`
- 或输入一个大类目录，例如 `/mnt/e/skill_all/development`
- 或输入总根目录，例如 `/mnt/e/skill_all`
- 逐个 skill 调用 Codex 做结构化评审
- 为每个 skill 落 1 份 JSON 结果
- 为每个小类生成独立的 summary / keep_index / drop_index / failures
- 为单小类模式额外导出一个 `retained_skills/` 目录，收集所有 `keep` 的原始 skill
- 在批量模式下额外生成批量根目录级的总 summary / index / failures / manifest
- 在批量模式下额外生成批量根目录级 `retained_skills/`，统一收集所有 `keep` 的原始 skill

## 依赖

这个模块使用：

- `@openai/codex-sdk`
- `zod`
- `tsx`
- `typescript`

当前仓库里已有 `/home/levi/Harbor/codex_task_builder_v3/node_modules`，本地开发时可以直接复用。

运行前还需要可用的 Codex 认证，常见方式是：

- 已配置 `~/.codex/auth.json`
- 或环境里已有兼容的 OpenAI / Codex 认证

## 运行

单小类模式：

```bash
cd /home/levi/Harbor/skill_screening_runner
npm run screen -- \
  --subcategory-dir /mnt/e/skill_all/development/backend \
  --output-dir /mnt/e/skill_screening_runs/development__backend \
  --jobs 4 \
  --overwrite \
  --limit 10
```

批量模式，跑一个大类下全部小类：

```bash
cd /home/levi/Harbor/skill_screening_runner
npm run screen -- \
  --input-dir /mnt/e/skill_all/testing-and-security \
  --output-dir /mnt/e/skill_screening_runs/testing-and-security \
  --jobs 12 \
  --resume 
```
"E:\skill_all\testing-and-security"
批量模式，跑总根目录下全部小类：

```bash
cd /home/levi/Harbor/skill_screening_runner
npm run screen -- \
  --input-dir /mnt/e/skill_all \
  --output-dir /mnt/e/skill_screening_runs/all \
  --jobs 20 \
  --resume
```

完整用法：

```bash
cd /home/levi/Harbor/skill_screening_runner
npm run screen -- \
  [--input-dir /mnt/e/skill_all] \
  --subcategory-dir /mnt/e/skill_all/development/backend \
  --output-dir /mnt/e/skill_screening_runs/output \
  [--model gpt-5.4] \
  [--jobs 4] \
  [--limit 10] \
  [--resume] \
  [--overwrite] \
  [--prompt-path /home/levi/Harbor/skill_screening_runner/assets/single-skill-screening-prompt.md] \
  [--schema-path /home/levi/Harbor/skill_screening_runner/assets/output-schema.json]
```

参数说明：

- `--input-dir`
  - 可选，批量模式输入目录
  - 只能传总根目录或单个大类目录
  - 例子：
    - `/mnt/e/skill_all`
    - `/mnt/e/skill_all/development`
  - 不能直接传小类目录；如果要只跑一个小类，请改用 `--subcategory-dir`
- `--subcategory-dir`
  - 可选，单小类模式输入目录
  - 和 `--input-dir` 二选一
  - 例子：`/mnt/e/skill_all/development/backend`
- `--output-dir`
  - 必填，结果输出目录
  - 单小类模式下：就是该小类的结果目录
  - 批量模式下：是批量结果根目录
  - 例子：
    - 单小类：`/mnt/e/skill_screening_runs/development__backend`
    - 批量：`/mnt/e/skill_screening_runs/development`
- `--model`
  - 可选，覆盖默认模型
  - 如果不传，则使用 `SKILL_SCREENING_MODEL` 或 Codex 默认模型
- `--jobs`
  - 可选，并发数
  - 默认值：`4`
  - 要求：正整数
- `--limit`
  - 可选，只处理前 `N` 个 skill
  - 常用于小规模试跑
  - 单小类模式下：只跑该小类前 `N` 个 skill
  - 批量模式下：每个小类各自只跑前 `N` 个 skill
  - 要求：正整数
- `--resume`
  - 可选，跳过已经存在 `skills/*.json` 结果的 skill
  - 适合中断后续跑
- `--overwrite`
  - 可选，开始前先清空整个 `--output-dir`
  - 风险：会删除该输出目录下已有结果
  - 批量模式下会删除整个批量输出根目录
  - 不能和 `--resume` 同时使用
- `--prompt-path`
  - 可选，覆盖默认 prompt 模板路径
  - 默认值：`/home/levi/Harbor/skill_screening_runner/assets/single-skill-screening-prompt.md`
- `--schema-path`
  - 可选，覆盖默认输出 schema 路径
  - 默认值：`/home/levi/Harbor/skill_screening_runner/assets/output-schema.json`
- `--help`
  - 可选，打印帮助信息并退出

补充说明：

- `--resume` 的判断依据是目标输出目录下对应的 `skills/<skill-dir>.json` 是否已经存在
- 批量模式下会分别检查每个小类输出目录里的 `skills/<skill-dir>.json`
- `--overwrite` 会在运行前删除整个输出目录，因此只适合用于新一轮重跑
- 不传 `--limit` 时，会处理发现到的全部 skill
- 不传 `--jobs` 时，默认并发 4 个单 skill 任务
- 批量模式下，小类之间按顺序执行；`--jobs` 只控制单个小类内部的 skill 并发
- `--resume` 和 `--overwrite` 是互斥参数，不能同时传
- `--help` 只打印 CLI 用法，不会执行筛选

运行时默认策略：

- `sandboxMode = danger-full-access`
- `approvalPolicy = never`
- `networkAccessEnabled = true`
- `modelReasoningEffort = xhigh`

当前 runner 不会先替模型做目录快照或文件摘录，而是直接让 Codex 自己递归探索本地 skill 目录。

当前默认输出语言约定：

- JSON 字段名保持英文
- 结构化枚举值保持英文合法值
- 解释性正文默认要求为简体中文
- `capability_archetype` 保持稳定英文 slug

## 输出目录

单小类模式：

```text
<output-dir>/
  run_manifest.json
  summary.json
  keep_index.json
  drop_index.json
  failures.json
  retained_skills/
    <skill-dir>/
      ...
  skills/
    <skill-dir>.json
  logs/
    <skill-dir>.prompt.md
    <skill-dir>.raw.txt
    <skill-dir>.error.txt
```

批量模式：

```text
<output-dir>/
  batch_manifest.json
  batch_summary.json
  batch_keep_index.json
  batch_drop_index.json
  batch_failures.json
  retained_skills/
    <category>__<subcategory>__<skill-dir>/
      ...
  <category>__<subcategory>/
    run_manifest.json
    summary.json
    keep_index.json
    drop_index.json
    failures.json
    skills/
      <skill-dir>.json
    logs/
      <skill-dir>.prompt.md
      <skill-dir>.raw.txt
      <skill-dir>.error.txt
```

补充说明：

- `keep_index.json` / `batch_keep_index.json` 只是保留 skill 的结构化索引，不包含原始 skill 文件本体
- `retained_skills/` 才是复制出来的原始 skill 目录集合，适合后续直接浏览、人工复核或喂给后续流程
- 批量模式下使用 `<category>__<subcategory>__<skill-dir>` 命名，避免不同小类里的同名 skill 目录冲突

单个 skill 结果字段说明见：

- `docs/screening_result_fields_zh.md`

## 环境变量

- `SKILL_SCREENING_MODEL`
  - 可选，默认模型
- `SKILL_SCREENING_NETWORK_ACCESS`
  - 可选，设为 `0` 时禁用联网；默认允许联网
- `SKILL_SCREENING_REASONING_EFFORT`
  - 可选，当前默认 `xhigh`；只有显式设成 `low` 时才降级
- `CODEX_PATH`
  - 可选，覆盖 Codex 可执行路径

## 本地校验

```bash
cd /home/levi/Harbor/skill_screening_runner
npm run check
npm run test
```
