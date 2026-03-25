# 任务说明

仓库位于 `/workspace/shift-digest`。这里有一个已经能运行的 CSV 报表 CLI，但回归测试和案例矩阵还没有补齐。

请只补测试与产物，完成以下内容：

1. 在仓库内新增 `tests/test_cli_golden.py`。
2. 在仓库内生成 `artifacts/cli_case_matrix.json`。

`tests/test_cli_golden.py` 必须满足：

- 使用 pytest。
- 至少包含 2 个 `pytest.mark.parametrize` 参数化测试。
- 成功案例要真正调用 CLI，并用 `tmp_path` 生成输出文件路径。
- 成功案例要校验退出码为 `0`，并逐行比对输出文件内容。
- 失败案例要校验退出码为 `1`、输出文件没有生成，并且 `stderr` 包含约定错误消息。

`artifacts/cli_case_matrix.json` 必须是 UTF-8 JSON 对象，并满足：

- 顶层包含 `"tool": "shift_digest.cli"`。
- 顶层包含 `"cases"`，长度固定为 5。
- 每个 case 都要包含 `case_id`、`kind`、`input`、`args`、`expected_exit_code`。
- `kind = "success"` 的 case 还要包含 `expected_output_lines`。
- `kind = "error"` 的 case 还要包含 `expected_stderr`。
- `input` 要写成相对于仓库根目录的路径。
- `args` 不要重复写 `--input` 或 `--output`；测试里自己补上这两个参数。

请覆盖下面 5 个案例：

1. `weekday-team-min20`
   - `kind`: `success`
   - `input`: `sample_data/weekday.csv`
   - `args`: `["--group-by", "team", "--min-minutes", "20"]`
   - `expected_exit_code`: `0`
   - `expected_output_lines`:
     - `Shift Digest`
     - `group_by=team`
     - `rows=3`
     - `groups=2`
     - `1. api | tickets=2 | total_minutes=55`
     - `2. ops | tickets=1 | total_minutes=22`

2. `weekend-owner-min30-include-cancelled`
   - `kind`: `success`
   - `input`: `sample_data/weekend.csv`
   - `args`: `["--group-by", "owner", "--min-minutes", "30", "--include-cancelled"]`
   - `expected_exit_code`: `0`
   - `expected_output_lines`:
     - `Shift Digest`
     - `group_by=owner`
     - `rows=3`
     - `groups=3`
     - `1. Eli | tickets=1 | total_minutes=120`
     - `2. Ada | tickets=1 | total_minutes=40`
     - `3. Dia | tickets=1 | total_minutes=40`

3. `weekday-status-min10`
   - `kind`: `success`
   - `input`: `sample_data/weekday.csv`
   - `args`: `["--group-by", "status", "--min-minutes", "10"]`
   - `expected_exit_code`: `0`
   - `expected_output_lines`:
     - `Shift Digest`
     - `group_by=status`
     - `rows=4`
     - `groups=2`
     - `1. closed | tickets=2 | total_minutes=52`
     - `2. open | tickets=2 | total_minutes=35`

4. `missing-duration-column`
   - `kind`: `error`
   - `input`: `sample_data/missing_duration.csv`
   - `args`: `["--group-by", "team"]`
   - `expected_exit_code`: `1`
   - `expected_stderr`: `Missing required columns: duration_minutes`

5. `weekend-no-matches`
   - `kind`: `error`
   - `input`: `sample_data/weekend.csv`
   - `args`: `["--group-by", "team", "--min-minutes", "200"]`
   - `expected_exit_code`: `1`
   - `expected_stderr`: `No records matched the provided filters.`

完成后，下面命令应能通过：

```bash
cd /workspace/shift-digest
pytest -q tests/test_cli_golden.py
```
