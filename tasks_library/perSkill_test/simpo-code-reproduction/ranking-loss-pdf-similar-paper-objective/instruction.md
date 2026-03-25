你在维护一个轻量偏好排序原型仓库 `/root/rankbench`。

仓库里缺了一个核心目标函数：`/root/rankbench/rankbench/objective.py` 中的 `length_normalized_bt_loss`。请阅读 `/root/rankbench/docs/` 目录中的论文原文，找到关于长度归一化奖励和带目标边际的 Bradley-Terry 目标的定义，然后按论文实现这个函数。

完成实现后：

1. 不要修改 `/root/rankbench/data/fixed_batch.npz` 和 `/root/rankbench/scripts/run_fixed_case.py`。
2. 运行 `python3 /root/rankbench/scripts/run_fixed_case.py`。
3. 生成 `/root/ranking_losses.npz`，其中必须包含 key `losses`，值为固定 batch 的逐样本损失向量。

评测会重新运行 runner，确认输出数值与论文一致，并检查 runner 确实调用了你补全的函数。
