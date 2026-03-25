# 任务说明

`/app/input/photos/` 下有 3 张便利店货架图片。每张图片里都能看到若干正面朝向镜头的商品包装；每个包装正面都有一个两字母的 `package_code`，同一商品每出现一个独立正面，就算 1 个可见陈列面。

请结合下面两个输入文件，完成补货审核：

- `/app/input/audit_targets.csv`
  - 给出需要审核的 `photo_id`、`product_name`、`package_code` 和目标陈列面数 `target_facings`
- `/app/input/product_reference.json`
  - 给出每个 `package_code` 对应的商品名称和包装颜色说明，方便你核对图片里的商品

你的任务是对 `audit_targets.csv` 中的每一行，统计该商品在对应图片中的 `visible_facings`，并根据下面规则生成审核状态：

- `out_of_stock`: `visible_facings == 0`
- `understocked`: `0 < visible_facings < target_facings`
- `ok`: `visible_facings >= target_facings`

把结果写入 `/app/output/shelf_audit.csv`，并严格满足以下要求：

- CSV 表头必须且只能是：`photo_id,product_name,target_facings,visible_facings,audit_status`
- 每一行都必须对应 `audit_targets.csv` 中的一行，且输出顺序必须与 `audit_targets.csv` 完全一致
- `photo_id` 和 `product_name` 必须直接沿用 `audit_targets.csv` 的值
- `target_facings` 和 `visible_facings` 必须是十进制整数
- `audit_status` 只能是 `ok`、`understocked`、`out_of_stock` 之一
- 不要输出额外列、额外行，也不要用其他文件替代这个 CSV
