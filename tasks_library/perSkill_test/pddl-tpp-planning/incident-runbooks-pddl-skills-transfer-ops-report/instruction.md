你需要为一组运维事故处置场景生成汇总报告。

输入清单位于 `/app/runbooks/incidents.json`，结构如下：

```json
{
  "domain": "runbooks/domain.pddl",
  "incidents": [
    {
      "incident_id": "checkout-api-memory-leak",
      "title": "Checkout API memory leak",
      "problem": "runbooks/problems/checkout-api-memory-leak.pddl",
      "plan_output": "results/plans/checkout-api-memory-leak.txt"
    }
  ]
}
```

要求如下：

1. 读取清单中的共享 domain 和 5 个 incident 对应的 problem 文件。
2. 对每个 incident 判断是否能找到一个合法的顺序计划：
   - 如果可解，`status` 写为 `solved`，并把完整计划文本保存到该 incident 指定的 `plan_output`。
   - 如果不可解，`status` 写为 `unsolved`，并且不要创建该 incident 的计划文件。
3. 生成主输出文件 `results/incident-runbooks.json`。它必须是一个 JSON 对象，并且包含键 `incidents`。
4. `incidents` 必须是长度为 5 的数组；每个元素至少包含以下字段：
   - `incident_id`: incident 标识符
   - `status`: `solved` 或 `unsolved`
   - `actions`: 动作序列。可解时按执行顺序列出动作字符串；不可解时必须是空数组
   - `action_count`: 动作数。可解时等于动作序列长度；不可解时必须为 `0`
   - `plan_file`: 可解时必须等于清单中的 `plan_output`；不可解时必须为 `null`
5. 对于可解 incident：
   - 计划文件必须是纯文本
   - 每行恰好一个动作，格式类似 `acknowledge(checkout-api-memory-leak)`
   - `actions` 的内容必须与计划文件逐行一致
6. 所有输出都写到工作目录下的 `results/` 中，不要修改输入资产。

评测会检查：

- `results/incident-runbooks.json` 的结构和字段值
- 5 个 incident 的 `status` 是否与实际可解性一致
- 可解 incident 的计划文件是否存在且语义有效
- 不可解 incident 是否没有额外计划文件
