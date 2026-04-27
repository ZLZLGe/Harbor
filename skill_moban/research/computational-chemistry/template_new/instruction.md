你正在协助一个药物发现团队完成一批小分子候选物的离线 lead triage。团队已经从公开数据库风格的数据源中整理出候选分子、靶点活性记录、同系物注释和药品安全信号摘要；这些数据存在重复盐型、无效 SMILES、单位不一致、活性方向混杂和结构告警，需要你整理、计算并给出可复核的候选优先级。

输入数据在 `/root/workspace/data/`：

- `candidates.csv`：候选分子清单，包含 `candidate_id`、`compound_name`、`smiles`、`series`、`source_note`
- `target_profile.json`：项目约束，包含目标靶点、活性阈值、理化性质范围、必须排除的安全风险类别
- `activity_records.jsonl`：公开数据库风格的体外活性记录，包含不同单位的 IC50/Ki/Kd/EC50 数据、实验关系符号和 assay 置信度
- `safety_reports.jsonl`：OpenFDA 风格的药品安全和相互作用摘要，包含同名药物、近似名称和 MedDRA 反应术语
- `assay_notes.md`：项目科学家对筛选策略、单位解释和特殊边界条件的说明

你的任务：

1. 在 `/root/workspace/solution.py` 中实现函数：

```python
def build_lead_triage_report(
    data_dir: str = "/root/workspace/data",
    output_dir: str = "/root/workspace/output"
) -> dict:
    ...
```

2. 对候选分子进行标准化处理。你需要解析 SMILES，去除无法解析的候选，合并同一母体结构的重复记录，并保留能追溯到原始 `candidate_id` 的映射。

3. 基于分子结构计算药物发现筛选所需的性质，包括但不限于：
   - exact 或近似分子量
   - LogP
   - HBD
   - HBA
   - TPSA
   - 可旋转键数
   - 芳香环或环系统相关指标
   - QED 或等价的综合 drug-likeness 指标

4. 统一 `activity_records.jsonl` 中的活性数据。你需要将 nM、uM、mM 等单位统一到 nM，并在可计算时转换为 pActivity。对于带有 `>`、`<`、`>=`、`<=` 的记录，应保留方向信息，不得把 censored value 当作精确值直接平均。

5. 按 `target_profile.json` 和 `assay_notes.md` 的约束对候选物进行筛选和排序。排序应综合考虑：
   - 靶点活性强弱和 assay 置信度
   - Lipinski / Veber 风格口服可及性约束
   - PAINS、反应性基团或结构告警
   - 安全事件和药物相互作用风险
   - 同一化学 series 内的多样性，避免 shortlist 被单一骨架完全占据

6. 在 `/root/workspace/output/` 下生成以下文件：

   - `lead_triage.csv`
   - `lead_triage.json`
   - `excluded_candidates.csv`
   - `method_notes.md`

7. `lead_triage.csv` 必须包含以下列，列名需完全一致：

```text
rank,candidate_id,compound_name,canonical_smiles,series,activity_nM,pActivity,mw,logp,hbd,hba,tpsa,rotatable_bonds,qed,rule_flags,safety_flags,triage_score,recommendation,rationale
```

8. `lead_triage.json` 必须包含以下顶层字段：

```json
{
  "target": "...",
  "selected_candidates": [],
  "excluded_candidates": [],
  "summary": {},
  "method": {}
}
```

9. `excluded_candidates.csv` 必须说明每个被排除候选的原因。原因可以包括无效结构、重复母体、活性不足、理化性质越界、结构告警、安全风险或证据不足。

10. `method_notes.md` 需要用简短文字说明你的计算口径，包括单位转换、活性聚合、结构标准化、排序策略和安全信号处理方式。不要写成泛泛的项目介绍，重点说明本次数据如何被处理。

输出格式要求：

- `lead_triage.csv` 必须按 `rank` 从小到大排序。
- `rank` 从 `1` 开始连续编号。
- `triage_score` 必须是数值，范围为 `0` 到 `100`。
- `recommendation` 只能使用以下值之一：
  - `advance`
  - `backup`
  - `deprioritize`
  - `exclude`
- `rule_flags` 和 `safety_flags` 可以为空字符串；如果有多个标记，请用分号分隔。
- 所有 JSON 输出必须是合法 UTF-8 JSON。
- 所有 CSV 输出必须包含表头。

说明：

- 你可以使用 RDKit、datamol、medchem、pandas、numpy 或其他合理的开源 Python 包。
- 你可以新增辅助脚本，但主入口必须是 `/root/workspace/solution.py` 中的 `build_lead_triage_report`。
- 你不需要联网完成任务；应优先使用 `/root/workspace/data/` 中给定的数据。
- 不要求得到唯一实现，但输出必须能体现真实的分子标准化、活性归一化、药物相似性评估和风险筛选逻辑。
- 不要硬编码 verifier 结果、候选排名或只针对固定文件名拼接答案。
- 不要修改、删除或替换输入数据。
- 不要绕过真实计算链路，例如直接复制预期输出、伪造性质值、跳过 SMILES 解析、跳过活性单位转换，或用固定名单代替筛选逻辑。
- 不要修改测试、verifier、运行入口或环境中的 skill。
