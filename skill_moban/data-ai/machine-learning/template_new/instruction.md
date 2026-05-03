你需要为一个房间占用相位识别项目交付一条正式训练链路。当前团队已经整理好了开发集序列索引、holdout 序列索引、相位标签映射和交付合同，但还没有一条可稳定复用的生产级运行入口。这里的相位标签描述的是最近一段传感器轨迹所处的变化阶段，而不是单个时间点的快照状态。你的任务是在保留现有数据链路和交付边界的前提下，生成一套可运行、可重复生成且可离线重放的训练流程，并产出正式交付物。

输入数据在：
- `/root/environment/project/`：项目骨架、配置占位和运行入口目录
- `/root/environment/data/phase_sequences/`：任务内的开发集序列索引、holdout 序列索引、逐样本序列文件、特征说明、相位标签映射和来源元信息
- `/root/environment/data/contracts/`：输出合同、开发集/验证集/holdout 的分区约束和模型包清单要求

业务约束：
- 最终链路必须从提供的序列索引和逐样本序列文件中完成训练、验证、holdout 评估和模型导出，不能改成手工整理结果或静态拼装答案。
- 训练集与验证集必须从开发集索引中按合同定义的源分区约束动态拆分；holdout 评估只能使用提供的 holdout 索引，不能把 holdout 并回拟合阶段，也不能无视合同固定使用某个写死切分。
- 每条序列样本都带有明确的 `sequence_length`，正式训练、评估和导出推理都必须遵守这个有效长度边界。
- 每个 `sequence_path` 都对应独立的逐样本 `.npy` 文件，磁盘上的存储行数不保证在所有文件间一致；不要把“当前文件长度刚好一样”当成正式前提，`sequence_length` 才是有效前缀的唯一权威边界。
- 不要先把整个 split 物化成固定时间维的单个 ndarray 再假定后续所有序列都会共用这个时间维；正式链路必须能处理逐样本文件在磁盘行数上的差异。
- 正式交付物必须可重复生成。不要把墙钟时间、临时路径、随机文件名或其他一次性字段写进最终交付物。
- 最终链路必须在 CPU-only 环境下稳定运行，并且导出后的离线重放结果要与正式评估口径保持一致。
- 模型包必须保留正式推理和后续续训所需的核心权重、关键元数据与必要配置。
- 用于恢复训练状态的快照应只保留恢复所需的关键状态；不要把与续训无关的额外数组对象直接塞进快照本体。

你的任务

1、在 `/root/environment/project/` 下生成正式训练与导出链路，使以下入口能够成功生成最终交付物：

```bash
python /root/environment/project/run_pipeline.py --output /root/answer
```

2、生成的链路必须覆盖序列读取、按合同拆分开发集、训练、验证、holdout 评估、预测导出和模型包导出，且继续以仓库中的现有目录作为唯一事实来源。

3、最终结果必须同时提供样本级预测、整体指标、逐类表现、逐 epoch 训练记录和可复现的模型包清单。

输出格式：

- `/root/answer/holdout_predictions.csv`
  - 必须覆盖全部 holdout 序列样本
  - 必须包含列：`sequence_id`, `source_file`, `anchor_timestamp`, `sequence_length`, `phase_id`, `phase_label`, `predicted_phase_id`, `predicted_phase_label`, `confidence`

- `/root/answer/holdout_metrics.json`
  - 顶层必须包含键：`dataset`, `split`, `training`, `holdout`, `per_class`, `notes`
  - `holdout` 中必须包含：`accuracy`, `macro_f1`, `weighted_f1`
  - `training` 中必须明确给出导出所对应的 `best_epoch` 和 `selected_val_macro_f1`
  - `split` 中必须明确说明训练、验证和 holdout 的样本数量、来源分区和验证合同取值
  - `split` 中至少要显式给出：`train_sequences`, `val_sequences`, `holdout_sequences`, `train_sources`, `val_sources`, `holdout_sources`, `validation_sources_from_contract`

- `/root/answer/confusion_matrix.csv`
  - 必须按标准相位标签输出混淆矩阵
  - 必须包含 `actual_phase_label` 列，并按预测标签列输出 `pred_STEADY_EMPTY`, `pred_RAMPING_UP`, `pred_RAMPING_DOWN`, `pred_STEADY_OCCUPIED`
  - 行列标签必须与 `holdout_predictions.csv` 和 `holdout_metrics.json` 中的类别语义一致

- `/root/answer/training_history.csv`
  - 必须是逐 epoch 的训练记录
  - 必须覆盖至少 10 个真实训练 epoch
  - 至少包含列：`epoch`, `train_loss`, `val_loss`, `val_macro_f1`, `selected_for_export`

- `/root/answer/model_bundle/manifest.json`
  - 必须包含导出模型包中各核心文件的路径说明
  - 必须覆盖正式权重文件、可恢复训练的快照、相位标签映射、预处理信息、运行配置、split 元数据和推理入口
  - manifest 必须在相同输入下保持稳定，不要写入会随每次运行变化的时间戳或一次性字段
  - 模型包中必须包含一个可直接运行的 `inference.py`、一份正式权重文件，以及一份能够恢复训练状态的快照，使导出物能够在不重新训练的前提下重放指定 split 的预测结果
  - 用于正式推理的权重文件和用于恢复训练的快照都应保持可移植、可在 CPU 环境中直接重放；快照本体只放恢复训练真正需要的状态
  - 用于恢复训练状态的快照顶层至少要显式包含：`epoch`, `model_state_dict`, `optimizer_state_dict`, `selected_val_macro_f1`

说明：

- 可以修改或新增 `/root/environment/project/` 下的代码、配置和辅助脚本，但不要修改 `/root/environment/data/` 下的输入数据。
- 可以使用环境中已安装的本地依赖，但不要引入需要外部账号、云权限或交互式登录的新服务。
- 不要通过硬编码预测结果、硬编码指标、删除训练流程、跳过真实评估、伪造标签映射、只对固定样本生效，或把 holdout 数据提前用于拟合来规避问题。
- 不要通过无视合同固定使用某个写死验证分区、把全部开发集直接并回拟合，或把 holdout 集参与参数更新来规避问题。
- 不要修改隐藏下游服务、测试文件、环境基线或依赖配置。
- 若编写临时文件，最终仍需由正式入口把正确交付物写入 `/root/answer/`。
