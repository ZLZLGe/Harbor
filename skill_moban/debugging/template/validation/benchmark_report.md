# 基准报告

## 任务元数据
- 任务名称：`nextjs-analytics-dashboard-runtime-regression-debugging`
- 类别：`debugging`
- 难度：`hard`
- 标签：`debugging`、`react`、`nextjs`、`browser-testing`、`hydration`、`cls`、`lazy-loading`、`interaction-latency`、`dashboard`
- 描述：修复一个 Next.js analytics dashboard 的运行时回归，目标覆盖 deeplink 稳定性、advanced insights 按需加载、重复交互下的性能退化。
- required skill：`browser-testing`

## 新鲜验证（2026-04-09）
- baseline（buggy）：
  - 运行方式：`ndar-debugging-source-20260409` 镜像 + `bash /tests/test.sh`
  - 结果：`6/9`
  - 奖励：`0`
  - 证据文件：
    - [2026-04-09_fresh_baseline_verifier.txt](./2026-04-09_fresh_baseline_verifier.txt)
    - [fresh-baseline-2026-04-09/verifier/reward.txt](./fresh-baseline-2026-04-09/verifier/reward.txt)
- oracle（reference fix）：
  - 运行方式：`ndar-debugging-source-20260409` 镜像 + `bash /solution/solve.sh && bash /tests/test.sh`
  - 结果：`9/9`
  - 奖励：`1`
  - 证据文件：
    - [2026-04-09_fresh_oracle_verifier.txt](./2026-04-09_fresh_oracle_verifier.txt)
    - [fresh-oracle-2026-04-09/verifier/reward.txt](./fresh-oracle-2026-04-09/verifier/reward.txt)

## Harbor Formal 结果（skill 依赖性）
- `without-skill`（有效新 key 轮次）：
  - run 路径：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-without-skills-formal-20260409-r12-tablet-cls-final2-newkey1`
  - trial 路径：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-without-skills-formal-20260409-r12-tablet-cls-final2-newkey1/task_without_skills__ASKcCsL`
  - verifier：`8/9`，`reward=0.0`
  - 唯一失败项：`alert deeplink stays stable across profiles`
  - 失败信息：`CLS regression exceeded the threshold on alert deeplink`
  - 证据文件：
    - `/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-without-skills-formal-20260409-r12-tablet-cls-final2-newkey1/task_without_skills__ASKcCsL/verifier/pytest-output.txt`
    - `/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-without-skills-formal-20260409-r12-tablet-cls-final2-newkey1/task_without_skills__ASKcCsL/verifier/reward.txt`
- `with-skill`（对照）：
  - run 路径：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260409-r4`
  - trial 路径：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260409-r4/task_with_skills__CYfzCdE`
  - verifier：`9/9`，`reward=1.0`
  - 证据文件：
    - `/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260409-r4/task_with_skills__CYfzCdE/verifier/pytest-output.txt`
    - `/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260409-r4/task_with_skills__CYfzCdE/verifier/reward.txt`

## 运行时间与 Token 对比
同模型 `gpt-5.4`、同 `reasoning_effort=high`。

| run | trial path | reward | total_s | agent_s | verifier_s | input_tokens | cache_tokens | output_tokens | input+output |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| without-skill (current) | `.../codex-without-skills-formal-20260409-r12-tablet-cls-final2-newkey1/task_without_skills__ASKcCsL` | 0.0 | 1909.2 | 1835.0 | 47.7 | 3,045,527 | 2,545,920 | 19,000 | 3,064,527 |
| with-skill (r4) | `.../codex-with-skills-formal-20260409-r4/task_with_skills__CYfzCdE` | 1.0 | 572.8 | 474.5 | 51.6 | 1,605,940 | 1,518,208 | 14,319 | 1,620,259 |
| with-skill (dashboard run) | `.../codex-with-skills-formal-20260409-dashboard/task_with_skills__QRXo2Zd` | 1.0 | 569.0 | 383.5 | 43.5 | 1,003,877 | 967,680 | 10,596 | 1,014,473 |

## 结果解读
- 当前 redesign 已满足目标约束：`without-skill` 不是“环境不可用导致失败”，而是在真实修复后仍遗漏跨 profile deeplink CLS，最终 `8/9`。
- `with-skill` 对照轮次稳定 `9/9`，并显著降低运行时间和 token 消耗，说明 skill 在“正确复现路径（尤其双 profile）”上提供了实质帮助。
- verifier 区分度稳定：同一天 fresh baseline/oracle 为 `6/9` vs `9/9`，formal without/with 为 `8/9` vs `9/9`。

## 维护建议
- 状态：`APPROVE`
- 理由：任务真实性与可解性已被 fresh baseline/oracle 验证。
- 理由：skill 相关性由有效 formal 证据支撑，且失败点精准落在 redesign 的 hidden tablet CLS 场景。
