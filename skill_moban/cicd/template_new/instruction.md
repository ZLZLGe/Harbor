你是负责 release engineering 的值班工程师，需要修复当前这条 GitHub Actions 风格发布流水线的 dry-run 事故。

输入数据在：
- `/app/workspace/.github/workflows/release-dry-run.yml`：待修复的流水线定义
- `/app/workspace/scripts/`：待修复的发布脚本与辅助工具
- `/app/workspace/data/`：公开的发布说明、历史快照与对比样本
- `/services/release-broker/`：同容器内隐藏下游服务与冻结数据，只允许调用，不允许修改

你的任务
1、修复 `/app/workspace/.github/workflows/release-dry-run.yml` 和 `/app/workspace/scripts/`，让 release dry-run 能在现有多阶段流水线下稳定产出完整的发布 bundle。
2、修复后生成的发布结果必须继续通过真实本地 broker 链路获取 candidate、provenance 和 promotion plan，不能退回到公开的历史快照或静态 fallback。
3、保持当前 release 流程的阶段语义不变：仍需保留 inspect、package、attest、promote 这些阶段及其依赖关系，不能把整条流水线改写成绕过约束的一步脚本。
4、保持现有输出契约兼容。修复后必须继续生成：
   - `/app/workspace/out/release-bundle.json`
   - `/app/workspace/out/promotion-plan.json`
   - `/app/workspace/out/release-summary.md`
5、如果你编写了临时调试脚本或排障笔记，最终仍需把正确修复落实到正式流水线与正式脚本中。
6、如果环境中存在 `/opt/task-skills/github-actions-release-audit/` 诊断工具包，请优先用其中的 workflow graph、dry-run replay 和 contract check 探针复现问题，再修改正式文件。

输出格式：
- 原地更新 `/app/workspace/.github/workflows/release-dry-run.yml` 与 `/app/workspace/scripts/` 下的代码和必要配置。
- 保持 `/app/workspace/out/` 下的产物结构与字段语义兼容。

说明：
- 不要 hack verifier，不要根据测试文件硬编码 release id、artifact digest、promotion channel、candidate 数量或固定输出内容。
- 不要替换真实链路，不要绕过、短路或伪造本地 release broker；不要把需要通过 broker 获取的 candidate、provenance、promotion plan 改成读取静态 JSON、写死常量或只用 fallback 数据。
- 不要通过删功能规避问题，例如删除阶段依赖、取消 attestation、移除 promotion gate、跳过 bundle 校验，或把多阶段流水线折叠成单步 shell 脚本。
- 不要修改隐藏服务、测试文件、依赖配置或公开输出契约。
- 可以增加日志、增加局部校验或编写辅助分析脚本，但评分以正式流水线和正式脚本在真实链路下的行为结果为准。
