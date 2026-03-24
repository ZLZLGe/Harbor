当前工作目录下有一个本地 Python 仓库 `/app/packaging_backend_repo`。它实现了一个简化的打包后端，负责读取 `pyproject.toml`、处理 backend 配置项，并根据构建参数生成 wheel 或 metadata 计划。仓库同时带有一组现有单元测试。

你的任务是阅读这个仓库的源码和 `tests/`，找出最可能因为畸形 `pyproject.toml`、backend 配置项或构建参数而出错的关键边界函数，并把分析结果写到 `/app/build_boundary_report.json`。

输出文件必须是合法 JSON，对象中至少包含这些顶层字段：

- `repo_focus`
- `important_files`
- `boundary_candidates`
- `existing_tests`
- `top_priorities`

具体要求：

1. `important_files`
   - 至少列出 3 个源码文件。
   - 每项都要写出 `path`、`priority`、`reason`。
2. `boundary_candidates`
   - 至少列出 4 个具体函数或方法。
   - 每项都要写出：
     - `qualname`
     - `file`
     - `priority`
     - `build_stage`
     - `inputs`
     - `failure_modes`
     - `existing_test_refs`
     - `why_it_matters`
     - `suggested_probes`
   - 排名应体现优先级，重点放在配置解析、元数据规范化和构建参数收敛的边界。
3. `existing_tests`
   - 总结现有测试已经覆盖的路径。
   - 明确指出仍缺少的边界条件、异常路径或参数组合。
4. `top_priorities`
   - 只保留 3 个最高优先级目标。
   - 每项都要写清楚为什么优先、当前测试缺口，以及适合后续验证的输入方向。

额外要求：

- 不要修改 `/app/packaging_backend_repo` 里的源码或测试。
- 分析必须结合现有测试，而不是只看源码。
- 最终优先级结论必须明确到具体函数或方法，不能只写模块名。
