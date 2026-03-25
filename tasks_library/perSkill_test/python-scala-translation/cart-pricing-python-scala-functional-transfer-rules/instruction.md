# Transfer: Cart Pricing Rule Engine Translation

`/root/cart_pricing.py` 是一个 Python 购物车定价规则引擎。请把它翻译成一个可直接用 `scalac` 编译的 Scala 2.13 单文件实现，并将结果保存到 `/root/CartPricing.scala`。

输出文件必须满足这些约束：

1. 不要写 `package` 声明；验证脚本会把它当作单文件源码直接编译。
2. 只使用 Scala 2.13 标准库。
3. 需要保留并暴露这些 Scala API：
   - 类型：`CartLine`、`CustomerContext`、`Coupon`、`PricingBreakdown`、`PricingStep`、`CartPricingEngine`
   - 方法：`lineTotal`、`applyDiscount`、`withWarning`、`price`
   - `object CartPricing` 中的公开函数：`toMoney`、`normalizeCouponCode`、`computeSubtotal`、`makeBulkDiscount`、`makeTierDiscount`、`validateCoupon`、`couponStep`、`composeSteps`
4. `CustomerContext` 里可以缺失的信息要用自然表达缺失值的 Scala 方式，不要退回到 `null` 风格。
5. `validateCoupon` 必须用显式的成功/失败结果来表达普通校验失败；不要把“券无效”这类常规分支写成抛异常流程。测试会按 `Either[String, Coupon]` 这个公开返回契约调用它。
6. 金额请用 `BigDecimal` 表达，并统一保留到 2 位小数、`HALF_UP` 舍入。

行为契约如下，测试只会检查这些公开可观察行为：

1. `normalizeCouponCode` 需要对输入做 `trim` 和大写归一化；空白或缺失值返回空结果。
2. `computeSubtotal` 需要返回所有 `CartLine.lineTotal` 之和。
3. `makeBulkDiscount` 需要返回一个闭包式规则。这个规则会：
   - 只对 `quantity >= minQuantity` 的条目生效
   - 如果指定了 `category`，只对至少包含该分类的条目生效，分类比较忽略首尾空白并按小写处理
   - 折扣额按命中条目的行总价乘以百分比计算
   - 使用传入的 `label`；如果没有传入，就使用 `bulk:<minQuantity>`
4. `makeTierDiscount` 需要只在客户等级匹配时生效；等级比较要 `trim` 后转小写。
5. `validateCoupon` 需要返回这些失败原因之一：
   - `"coupon inactive"`
   - `"subtotal below minimum"`
   - `"coupon tier mismatch"`
   - `"coupon category mismatch"`
6. `couponStep` 需要：
   - 对空白券码追加 warning：`"coupon skipped: empty code"`
   - 对查不到的券码追加 warning：`"coupon skipped: <CODE> not found"`
   - 对校验失败的券追加 warning：`"coupon skipped: <reason>"`
   - 对合法券应用规则名 `coupon:<CODE>`
   - 如果券限制了分类，只对命中分类的商品金额打折
7. `composeSteps` 必须按传入顺序依次执行规则。
8. `PricingBreakdown.applyDiscount` 只在折扣额大于 0 时追加规则；`total` 不能变成负数。

重点是写出 idiomatic Scala：用不可变数据、`Option`、`Either`、高阶函数和清晰的数据建模表达原始 Python 逻辑，而不是逐行硬翻。
