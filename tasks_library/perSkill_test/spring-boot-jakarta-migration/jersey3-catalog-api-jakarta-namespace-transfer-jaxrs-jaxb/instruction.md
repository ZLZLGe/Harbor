在 `/workspace` 下有一个已经升级到 Java 21 与 Jersey 3 的商品目录 API，但源码和测试里还残留旧命名空间，导致当前项目无法通过构建与测试。

请修复这次迁移，重点检查并更新这些位置：

- `src/main/java/com/example/catalog/api/CatalogApplication.java`
- `src/main/java/com/example/catalog/api/CatalogResource.java`
- `src/main/java/com/example/catalog/model/CatalogSnapshot.java`
- `src/main/java/com/example/catalog/model/CatalogPreviewRequest.java`
- `src/main/java/com/example/catalog/model/CatalogPreview.java`
- `src/main/java/com/example/catalog/model/CatalogItem.java`
- `src/test/java/com/example/catalog/api/CatalogResourceTest.java`
- `src/test/java/com/example/catalog/api/CatalogXmlCodecTest.java`

需要满足的结果：

1. 与本次任务相关的应用代码和测试代码中的 `javax.ws.rs`、`javax.xml.bind`、`javax.annotation` 引用都要迁移到 Jersey 3 可用的命名空间。
2. `GET /catalog/summary` 的接口语义必须保持不变：
   - 返回 `catalogName = seasonal-catalog`
   - 返回 `maintainer = ops-bot`
   - 返回 `itemCount = 2`
   - 返回的两个种子商品 SKU 仍然是 `SKU-100` 和 `SKU-200`
3. `POST /catalog/preview` 的接口语义必须保持不变：
   - `displayName` 需要去掉首尾空白
   - `warehouseZone` 为空白时回退为 `UNASSIGNED`，否则转成大写
   - 响应中的 `status` 必须保持为 `READY`
   - 响应中的 `generatedBy` 必须保持为 `catalog-preview`
   - 响应中的 `slug` 必须继续按 `sku` 与清洗后的 `displayName` 生成，例如 `sku-300` 加 `Insulated Mug` 应得到 `sku-300-insulated-mug`
4. 现有 XML 契约不能破坏：
   - `catalogSnapshot` 仍然是摘要响应的 XML 根元素
   - `catalogPreview` 仍然是预览响应的 XML 根元素
5. 最终 `mvn test` 必须通过。

不要改成别的技术栈，也不要绕开现有测试语义。
