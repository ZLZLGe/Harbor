# Transfer: 预订定价策略翻译

`/root/BookingPolicies.py` 是一个 Python 预订定价策略模块。请把它翻译为 Scala 2.13，并将结果保存到 `/root/BookingPolicies.scala`。

要求：

- Scala 文件必须使用 `package booking`。
- 需要保留并实现这些核心类型：`RoomType`、`BookingOrder`、`ChargeSummary`、`DiscountPolicy`、`StandardPolicy`、`MemberPolicy`、`CorporatePolicy`、`LongStayPolicy`、`FamilyPolicy`、`PolicyRegistry`、`PricingLedger`。
- 需要保留并实现这些核心接口或方法：`fromCode`、`fromPayload`、`renderLine`、`quote`、`quoteAll`、`register`、`buildDefaults`、`supportedCodes`、`fromPayloads`、`totalDue`、`totalDiscount`、`renderReport`。
- 语义应与 Python 版本一致：房型目录、订单类方法构造器、折扣策略模板方法、策略注册表、费用拆分、积分计算和批量汇总逻辑都要保持一致。
- 只依赖 Scala 2.13 标准库，不要引入第三方库。
- 代码应符合 Scala 风格，不要做逐行机械翻译。
