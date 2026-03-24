你接手的是一个本地多变量电网负荷预测基线，代码在 `/root/src`，输入资产在 `/root/data/grid_dispatch_panel.csv`。

目标是把当前单路时间序列回归脚手架扩展成“两条训练流程 + 一个统一报告”：

1. 保留现有 baseline 预测流程。
2. 把每个时间混合残差块中的时间混合支路和前馈支路改造成带双随机约束的多残差流混合。
3. 在同一脚本中训练 baseline 与约束版本，比较 24 步长预测窗口上的稳定性，并输出 `/root/grid_forecast_summary.json`。

约束与要求：

- 不要下载外部数据，直接使用 `/root/data/grid_dispatch_panel.csv`。
- 这是一个多变量序列回归任务，目标是预测未来 24 个小时的 `load_mw`。
- 评测重点是长预测窗口稳定性，因此输出中除了整体 `mae` / `rmse` 外，还需要给出最后 8 个预测步的 `tail_mae` / `tail_rmse`。
- 训练与评测都必须能在 CPU 环境完成，不要把任务改成依赖 GPU。
- `src/train.py` 当前只补好了 baseline 路径；你可以修改它，也可以新增模块，但最终需要直接生成目标 JSON。
- 输出 JSON 至少要包含下面这个结构：

```json
{
  "dataset": {
    "train_windows": 0,
    "val_windows": 0,
    "lookback": 72,
    "horizon": 24,
    "num_features": 0,
    "target": "load_mw",
    "feature_names": ["load_mw"]
  },
  "baseline": {
    "mae": 0.0,
    "rmse": 0.0,
    "tail_mae": 0.0,
    "tail_rmse": 0.0,
    "grad_norm_mean": 0.0,
    "grad_norm_std": 0.0,
    "grad_norm_cv": 0.0,
    "max_grad_norm": 0.0,
    "steps": 0
  },
  "mhc": {
    "mae": 0.0,
    "rmse": 0.0,
    "tail_mae": 0.0,
    "tail_rmse": 0.0,
    "grad_norm_mean": 0.0,
    "grad_norm_std": 0.0,
    "grad_norm_cv": 0.0,
    "max_grad_norm": 0.0,
    "steps": 0
  },
  "flow_diagnostics": {
    "num_streams": 4,
    "labels": ["block0.time"],
    "h_res_matrices": [[[0.0]]],
    "mean_row_abs_error": 0.0,
    "mean_col_abs_error": 0.0,
    "mean_offdiag_share": 0.0
  }
}
```

- `flow_diagnostics.labels` 与 `flow_diagnostics.h_res_matrices` 需要一一对应，覆盖所有被约束混合包裹的时间混合支路与前馈支路。
- 这些矩阵需要是非负的近似双随机矩阵，而不是直接把原始 logits 输出出来。
- 报告中要能够体现：约束版本在长预测窗口上保持可用精度，同时训练梯度离散度更平稳。

可直接复用的现有脚手架：

- `/root/src/data.py`：读取本地 CSV、构造 lookback/horizon 窗口与数据摘要。
- `/root/src/model.py`：baseline 时间混合块与回归头。
- `/root/src/train.py`：baseline 训练骨架与报告入口。

完成后，确保 `grid_forecast_summary.json` 存在且内容满足上面的结构与语义要求。
