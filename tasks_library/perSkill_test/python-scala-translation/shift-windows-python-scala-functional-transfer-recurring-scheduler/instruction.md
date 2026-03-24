# Transfer: Python 排班窗口规划器转 Scala

`/root/ShiftWindowPlanner.py` 是一个面向值班与轮班窗口规划的 Python 模块，`/root/planner_cases.json` 提供了几组可用于自查的样例场景。请将该模块翻译成 **Scala 2.13**，并把结果保存到 `/root/ShiftWindowPlanner.scala`。

这个模块原本依赖递归生成器、可选配置、时间区间比较和后处理合并来组织排班逻辑。你的 Scala 版本需要保留等价语义，但实现风格应明显偏向 Scala 的函数式写法，而不是逐行直译。重点包括：

- 用清晰的 ADT 表达时间区间、排班模板、阻塞窗口、计划结果和配置。
- 把 Python 的递归 `yield from` 式展开改写成 `LazyList` 或 `Iterator` 驱动的惰性实现。
- 用 `Option` 处理可选配置、默认值回退和可选截止条件。
- 用模式匹配或组合函数组织标签命名、冲突过滤与时间区间合并。
- 正确处理重复展开、冲突剔除、按标签筛选、相邻窗口合并和结果截断。

为避免测试时接口不匹配，Scala 代码至少需要暴露这些公共类型与成员：

- `TimeRange`
- `ShiftTemplate`
- `BlockedWindow`
- `PlannerConfig`
- `PlannedShift`
- `ShiftWindowPlanner`
- `TimeRange.overlaps(...)`
- `TimeRange.merge(...)`
- `PlannerConfig.normalized(...)`
- `ShiftWindowPlanner.weekly(...)`
- `ShiftWindowPlanner.withFallbackConfig(...)`
- `ShiftWindowPlanner.expandRecurring(...)`
- `ShiftWindowPlanner.filterConflicts(...)`
- `ShiftWindowPlanner.mergeRanges(...)`
- `ShiftWindowPlanner.plan(...)`

实现要求：

- 代码必须能被 Scala 2.13 编译。
- 输出文件只能是 `/root/ShiftWindowPlanner.scala`。
- 不要额外添加和题目无关的大量兜底逻辑。
- 不要加入额外的 `package` 声明，保持文件可以被直接编译。
- 可以在不改变核心语义的前提下调整内部结构和局部命名，使实现更符合 Scala 风格。
