# Publish Requirements

正式交付由两部分组成：

1. `/app/output/warehouse.duckdb`
2. live publish bundle 与 receipt

## Live manifest

提交 publish bundle 前，必须先调用：

- `GET http://127.0.0.1:8331/manifest`

manifest 会返回当前发布批次要求的：

- `snapshot_id`
- `contract_version`
- `warehouse_path`
- `required_tables`

## Publish bundle

`/app/output/publish_bundle.json` 必须来自最终 warehouse，而不是猜测或手写常量。至少需要包含：

- `snapshot_id`
- `contract_version`
- `warehouse_path`
- `tables`

其中 `tables` 中每个元素至少包含：

- `name`
- `row_count`
- `sha256`

## Receipt

`/app/output/publish_receipt.json` 必须来自 live `POST /publish` 的真实响应。

## 禁止事项

- 手写 receipt
- 复制静态 bundle 充当 live 结果
- 绕过 manifest 直接猜当前发布批次
- 把 publish 降级成只检查文件是否存在
