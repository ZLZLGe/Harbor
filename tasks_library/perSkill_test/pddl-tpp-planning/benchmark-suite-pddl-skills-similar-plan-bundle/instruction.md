你需要完成一个小型 classical planning 基准包。

输入文件位于 `/app/benchmark/manifest.json`。其结构如下：

```json
{
  "shared_domain": "benchmark/domain/shared-domain.pddl",
  "cases": [
    {
      "case_id": "west-link",
      "problem": "benchmark/problems/west-link.pddl",
      "plan_path": "results/plans/west-link.plan"
    }
  ]
}
```

要求如下：

1. 读取 manifest，使用其中给出的共享 domain 和每个 case 的 problem 文件，为全部 6 个 case 生成顺序计划。
2. 每个 case 的计划都要写到该 case 指定的 `plan_path`。
3. 计划文件必须是纯文本；每行恰好一个动作，格式类似 `drive(truck1, depot1, market1)`。
4. 你还需要生成主输出文件 `results/benchmark-plan-index.json`，它必须是一个 JSON 对象，并包含键 `cases`。`cases` 必须是长度为 6 的数组；数组中的每个元素至少包含以下字段：
   - `case_id`: case 的标识符
   - `plan_file`: 该 case 的计划文件路径
   - `step_count`: 计划中的动作步数
   - `validated`: 布尔值，表示你是否确认该计划可解该 case
5. `plan_file` 应与 manifest 中该 case 的 `plan_path` 一致。
6. `step_count` 必须与对应计划文件中的动作行数一致。
7. 所有输出都写到工作目录下的 `results/` 中，不要改写输入资产。

评测会检查：

- `results/benchmark-plan-index.json` 的结构和字段值是否符合约定
- 6 个计划文件是否全部存在
- 计划文本能否被解析成顺序计划并通过语义验证
- `validated` 是否为 `true`
