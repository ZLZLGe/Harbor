你需要基于本地提供的模板工作簿和四份输入表，完成一个债券组合压力测试工作簿，并将结果保存为 `bond-stress-book` 加 Excel 工作簿默认扩展名的文件。

可用输入文件：
- 模板工作簿文件名为 `bond-stress-template` 加 Excel 工作簿默认扩展名：包含目标工作表结构、估值日和情景参数。
- `portfolio_holdings.csv`：债券持仓清单。
- `coupon_calendar.csv`：每只债券的逐期付息/到期日期。
- `risk_free_curve.csv`：基准收益率曲线。
- `recovery_assumptions.csv`：不同评级桶的回收率假设。

模板中包含 8 个工作表：
- `Control`：估值日与压力情景参数，已预填。
- `Holdings`：导入持仓清单。
- `Coupon_Calendar`：导入逐期付息日历。
- `Curves`：导入基准收益率曲线。
- `Recovery_Assumptions`：导入回收率假设。
- `Cashflow_Model`：需要补齐逐期现金流、贴现和情景估值。
- `Scenario_Valuation`：需要按债券汇总基准估值、久期/凸性和情景损益。
- `Portfolio_Summary`：需要汇总组合层面的估值与压力测试结果。

请在模板基础上完成以下内容，且需要保留公式，不要把应由公式计算的结果改成手填常数：

1. 先把四个 CSV 的内容完整导入对应输入工作表，并保留原表头。

2. 在 `Cashflow_Model` 中，按 `Coupon_Calendar` 的每一行建立一条现金流记录，补齐 A:X 列，列含义如下：
- A:D 直接链接 `Bond_ID`、`Payment_Date`、`Is_Maturity`、`Recovery_Anchor`。
- E:J 从 `Holdings` 取回 `Position_Face`、`Coupon_Rate`、`Coupon_Frequency`、`Rating_Bucket`、`Curve_Tenor_Years`、`Spread_Bps`。
- K 列从 `Curves` 按 tenor 匹配基准收益率。
- L 列计算 `Base_Yield = Base_Curve + Spread_Bps / 10000`。
- M 列计算 `Year_Fraction = MAX((Payment_Date - Valuation_Date) / 365, 0)`。
- N 列计算票息现金流：若付款日在估值日之后，则为 `Position_Face * Coupon_Rate / Coupon_Frequency`，否则为 0。
- O 列计算本金现金流：若付款日在估值日之后且 `Is_Maturity = 1`，则为 `Position_Face`，否则为 0。
- P 列计算 `Total_Contractual_CF = Coupon_CF + Principal_CF`。
- Q 列计算基准贴现现值。
- R 列计算 `Base_PV * Year_Fraction`。
- S 列计算 `Base_PV * Year_Fraction^2`。
- T 列计算 `Parallel_Up_75` 情景下的逐期现值。
- U 列计算 `Parallel_Down_50` 情景下的逐期现值。
- V 列计算 `Credit_Stress` 情景下的逐期现值：
  - 如果该债券在 `Holdings` 中的 `Stress_Default_Flag = 1`，则忽略合同现金流，只在 `Recovery_Anchor = 1` 的那一行确认一次回收现金流，金额为 `Position_Face * 匹配到的 Recovery_Rate * Recovery_Multiplier`，再按 `Credit_Stress` 的贴现率折现。
  - 如果 `Stress_Default_Flag = 0`，则仍按合同现金流折现，只是贴现率改为 `Base_Yield + Curve_Shift + Spread_Shift`。
- W 列匹配评级桶对应的 `Recovery_Rate`。
- X 列取回 `Stress_Default_Flag`。

3. 在 `Scenario_Valuation` 中，按每只债券汇总结果，补齐 A:N 列：
- A:C 链接债券编号、发行人和评级桶。
- D 列填 `Base_Yield`。
- E 列汇总 `Base_Price`。
- F 列计算 `Macaulay_Duration = SUM(Base_PV * Year_Fraction) / Base_Price`。
- G 列计算 `Modified_Duration = Macaulay_Duration / (1 + Base_Yield)`。
- H 列计算 `Convexity = SUM(Base_PV * Year_Fraction^2) / Base_Price`。
- I/J 列分别给出 `Parallel_Up_75` 的价格与相对基准价格的损益。
- K/L 列分别给出 `Parallel_Down_50` 的价格与损益。
- M/N 列分别给出 `Credit_Stress` 的价格与损益。

4. 在 `Portfolio_Summary` 中补齐以下汇总：
- B2：组合 `Total Base Value`。
- B3：按基准市值加权的 `Modified Duration`。
- B4：按基准市值加权的 `Convexity`。
- B7:C9：分别汇总 `Parallel_Up_75`、`Parallel_Down_50`、`Credit_Stress` 三个情景下的组合总价值和组合损益。

输出要求：
- 最终文件名必须是 `bond-stress-book` 加 Excel 工作簿默认扩展名。
- 工作簿中应保留可见公式，跨表引用不能断。
- 请直接在当前工作目录生成输出文件，不要额外输出其他答案文件。
