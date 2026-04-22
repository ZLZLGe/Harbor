你是一名计算化学研究员。你需要从一个冻结的小分子候选库中，筛选出一组可复核的 lead-like 候选化合物，并给出每个候选的标准化分子表示、关键理化性质、结构警报结果、与参考活性分子的相似性以及最终排序。

输入数据在：
- `/root/data/library/`（候选分子库，包含 `.sdf`、`.smi` 和供应商元数据）
- `/root/data/reference/actives.csv`（参考活性分子）
- `/root/data/reference/rules.json`（lead-like 约束与结构警报规则）
- `/root/data/reference/scoring.json`（候选排序规则与字段定义）

你的任务
1、编写 Python 脚本，对候选分子进行读取、标准化、去重、性质计算、结构警报检测和相似性计算。
2、同一真实化合物如果只是在盐型、质子化状态或书写形式上不同，应该被合并为同一个标准化候选；但立体化学不同的化合物不能被错误合并。
3、对每个标准化候选，至少计算以下字段：
- `canonical_smiles`
- `inchikey`
- `molecular_weight`
- `logp`
- `tpsa`
- `hbd`
- `hba`
- `rotatable_bonds`
- `qed`
4、使用给定参考活性分子，基于 Morgan fingerprint 与 Tanimoto similarity 计算每个候选到参考集合的最高相似度。Morgan fingerprint 需要使用 `radius = 2`、`nBits = 2048`，并保留立体化学信息。
5、根据 `rules.json` 判断每个候选是否满足 lead-like 约束，是否命中结构警报，并给出最终的 `keep` / `reject` 结论。
6、根据 `scoring.json` 的规则对所有 `keep` 候选进行稳定排序，生成最终 shortlist。
7、你必须真正从输入分子文件中完成标准化、去重、性质计算、结构警报检测和排序；不能手写答案，也不能人工维护化合物到结果的映射表。

输出格式：
你需要把解答写到 `/root/workspace/solution.py`。

脚本中必须提供以下入口函数：
```python
def build_leadlike_shortlist(
    library_dir: str,
    actives_csv: str,
    rules_json: str,
    scoring_json: str,
    top_k: int = 20,
) -> dict:
```

返回结果必须是一个 `dict`，并且至少包含以下顶层键：
```python
{
    "summary": {
        "n_input_records": int,
        "n_standardized_candidates": int,
        "n_keep": int,
        "n_reject": int
    },
    "shortlist": [
        {
            "rank": int,
            "compound_id": str,
            "canonical_smiles": str,
            "inchikey": str,
            "molecular_weight": float,
            "logp": float,
            "tpsa": float,
            "hbd": int,
            "hba": int,
            "rotatable_bonds": int,
            "qed": float,
            "max_similarity_to_actives": float,
            "alerts": list[str],
            "decision": "keep"
        }
    ],
    "rejected_compounds": [
        {
            "compound_id": str,
            "canonical_smiles": str,
            "alerts": list[str],
            "reasons": list[str],
            "decision": "reject"
        }
    ]
}
```

其中：
- `shortlist` 只包含最终保留并进入排序的候选，按最终排序从高到低排列。
- `rejected_compounds` 需要包含被剔除的标准化候选及其剔除原因。
- 如果排序分数相同，必须使用 `compound_id` 的字母序升序打破平局，以保证结果稳定。
- 所有浮点数保留到小数点后 4 位。

说明：
- 你可以使用 RDKit 或其他合适的化学信息学库。
- 你必须从提供的分子文件中解析结构，不能只依赖文件名、记录顺序或隐藏规律。
- 不要根据测试文件、预期结果或样例输出硬编码 shortlist、结构警报结果、相似度、分子性质或排序。
- 不要跳过标准化、去重、结构警报检测或相似性计算后直接构造结果。
- 不要把所有候选都标记为 `keep`，也不要通过放宽规则来规避筛选逻辑。
- 不要 hack verifier，不要修改输入数据、测试文件或依赖配置。
- 输出应当对同一输入数据稳定可复现。
