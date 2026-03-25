你需要基于 `/root/data/` 中提供的课程成绩模板工作簿生成课程期末报告工作簿，并将结果保存到同一目录下。

输入工作簿包含 4 个工作表：
- `Scores`：每名学生的平时与期末成绩
- `Weights`：4 个成绩组成项的权重。第 1 行是组成项名称，第 2 行是对应权重
- `GradeBands`：成绩等级表。数据区按 `MinScore` 从低到高排序
- `Report`：当前只有占位内容，等待你填写

请在 `Report` 中完成以下内容：

1. 在 `A1:J1` 写入以下表头，并从第 2 行开始按 `Scores` 中原有顺序逐行生成每名学生的报告，不要遗漏、重排或汇总：
   `StudentID`, `StudentName`, `Homework`, `Midterm`, `Project`, `FinalExam`, `WeightedTotal`, `MissingFlag`, `LetterGrade`, `PassStatus`
2. `StudentID` 到 `FinalExam` 这 6 列都必须使用电子表格公式引用 `Scores` 中对应行的数据，不能直接写死结果。
3. 如果某个成绩组成项在 `Scores` 中为空白，对应的 `Report` 单元格也必须保持为空白，而不是显示为 `0`。
4. `WeightedTotal` 必须使用电子表格公式，根据 `Weights` 中的 4 个权重计算加权总评，并保留 2 位小数。
   - 如果某个成绩组成项为空白，在计算 `WeightedTotal` 时该项按 `0` 参与计算
5. `MissingFlag` 必须使用电子表格公式：
   - 只要 `Homework`、`Midterm`、`Project`、`FinalExam` 这 4 个单元格里有任意空白，就返回 `MISSING`
   - 否则返回 `OK`
6. `LetterGrade` 必须使用电子表格公式，根据 `WeightedTotal` 在 `GradeBands` 中命中的分数档位返回对应的 `LetterGrade`。
7. `PassStatus` 必须使用电子表格公式，根据 `WeightedTotal` 在 `GradeBands` 中命中的分数档位返回对应的 `PassStatus` 文本。

输出要求：

- 最终文件名必须与任务要求的主输出文件名完全一致，并保存在 `/root/data/` 下
- `Report` 中从第 2 行开始的所有数据单元格都必须保留为电子表格公式
- 公式缓存结果必须可直接读取，不能依赖手动打开后再重新计算
- 如果修改 `Weights` 或 `GradeBands` 中的规则并重新计算工作簿，`Report` 中的总评、等级和通过状态也必须随之更新
