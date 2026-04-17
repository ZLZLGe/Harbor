你是一名测试架构工程师。请读取 `/app/workspace/input/modules.csv`，并生成 `/app/workspace/output/polyglot_test_blueprint.csv`。

输入 CSV 至少包含这些字段：
- `module_id`
- `language`
- `module_kind`
- `needs_io_mock`
- `needs_property_tests`
- `needs_benchmarks`
- `needs_async`

输出 CSV 必须且只能包含以下列，顺序固定：
- `module_id`
- `runner`
- `core_pattern`
- `mock_style`
- `advanced_track`
- `coverage_tool`
- `verification_command`

规则要求：
- 离线、确定性，不要依赖网络。
- 按 `module_id` 升序排序。
- 不要输出额外列。
- 不要输出 `null`、`None`、`N/A`、`nil` 等空值样式字符串。
- 语言映射必须符合各自测试生态：
  - C++ 使用 GoogleTest / CTest。
  - Go 使用 table-driven tests / subtests / fuzz。
  - Kotlin 使用 Kotest / MockK。
  - Perl 使用 Test2::V0 / Test::More / prove。
  - Python 使用 pytest fixtures / parametrize。
  - Rust 使用 cargo test / rstest / proptest / mockall。

`advanced_track` 需要在请求相关能力时写出合适的高级方向，例如 property/fuzz、benchmark、async；未请求时保留为空字符串。

你可以参考 `/app/environment/skills/` 中的技能目录来保持语言模式一致。
