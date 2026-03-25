`/workspace` 下是一个已经切到 Spring Boot 3 的库存服务，但仓储层还残留了 Hibernate 5 时代的写法，导致项目在当前依赖下无法通过测试。

请修复这些兼容性问题，并确保 `mvn test` 通过。主要改动应落在 `/workspace/src/main/java/com/example/inventory/repository/StockItemRepository.java`。

需要满足的行为契约：

1. `searchActiveItems(String warehouseCode, String term, Integer minimumQuantity)` 只能返回指定仓库中 `active = true` 的库存项。
2. 当 `term` 非空白时，筛选条件需要大小写不敏感地匹配 `name` 或 `category`。
3. 当 `minimumQuantity` 非空时，只保留 `quantity >= minimumQuantity` 的库存项。
4. 查询结果必须按 `quantity` 升序，再按 `sku` 升序返回。
5. `deactivateLowStockItems(String warehouseCode, int cutoffQuantity)` 只停用指定仓库内、当前仍为激活状态、且 `quantity <= cutoffQuantity` 的库存项，并返回实际更新行数。
6. 把遗留的 `javax.persistence` 导入替换为与当前栈兼容的命名空间，并移除 Hibernate 5 专属的旧式 Criteria API 用法。

完成后请自行运行：

```bash
mvn test
```
