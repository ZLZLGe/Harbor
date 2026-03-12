# Skill 内化：从任意 Skill 反推 Task 的通用框架

## 1. 什么是 skill 内化

在这套方法里，`skill 内化` 不是让模型背下 `SKILL.md` 的文字，也不是让模型学会某个固定脚本路径。

它指的是：模型在**没有外部 skill 文件、没有显式工具提示**的情况下，仍然能够：

- 识别什么时候应该启用某类能力
- 用对这类问题的标准拆解方式
- 执行关键领域操作
- 遵守关键约束并输出正确结果

更短地说：

- **外化 skill**：模型通过读取 `SKILL.md`、脚本、参考材料来完成任务
- **内化 skill**：模型把这套“触发条件 + 解题程序 + 约束意识”学进参数里

## 2. 要内化什么

建议把每个 skill 拆成 6 个层次，重点蒸馏其中稳定、可复用的部分。

### 2.1 触发条件

模型在看到什么输入、文件、描述时，应该想到这类能力。

### 2.2 问题分解方式

这类问题通常该先做什么、再做什么。

### 2.3 领域对象与表示

这个领域中最关键的对象、变量和结构是什么。

### 2.4 关键操作模式

该 skill 最擅长的动作，例如解析、比对、查表、变换、聚类、过滤、校验。

### 2.5 约束与校验习惯

要特别小心的单位、容差、字段完整性、主对象选择规则等。

### 2.6 输出契约

什么结果才算完成，输出文件、字段、格式、精度要求是什么。

不建议优先内化的内容：

- 单个任务里偶然出现的路径
- skill 文档的措辞风格
- 特定脚本调用姿势
- 与单个 benchmark 强绑定的表面模板

## 3. 从任意 skill 反推 task 的通用框架

## 3.1 先拆 skill，再写 task

先读 `SKILL.md` 与 `scripts/`，输出一张统一能力卡片：

- `skill_name`
- `activation_signals`
- `core_capability`
- `decomposition`
- `critical_constraints`
- `expected_output_contract`
- `common_failures`

目标是先回答一句话：

> 这个 skill 最适合承担任务中的哪一步“主难点”？

## 3.2 把 skill 语言翻译成业务语言

不要直接把 skill 名词塞进任务说明。应该把技能能力改写成现实世界动作。

例如：

- `mesh-analysis` → “从带噪声的扫描件中找出主零件并计算几何量”
- `pdf` → “从报告里提取结构化表格信息”
- `pcap-analysis` → “从流量数据中识别可疑行为”

任务说明应该看起来像人在工作中交代任务，而不是工具教程。

## 3.3 设计一个薄业务壳

推荐结构：

`任务 = skill 核心能力 + 薄业务逻辑 + 固定输出契约`

其中“薄业务逻辑”通常是：

- 查表
- 规则映射
- 阈值判断
- 汇总排序
- 固定格式报告

这样 skill 的价值清晰，task 也不会退化成“API demo”。

## 3.4 用 5 个问题筛 task

每个候选 task 都问：

- 真实吗？
- 难点落在这个 skill 的强项上吗？
- 能否 deterministic 测试？
- with-skill 和 without-skill 差距明显吗？
- instruction 能否不提 skill 名仍然讲清楚？

如果这 5 个问题中有明显不满足的项，这个 task 就不适合做内化训练样本。

## 3.5 把 task 拆成 5 层

一个稳定的重构 task，最好显式拆成这 5 层：

- `场景层`：为什么要做这件事
- `输入层`：给 agent 什么文件
- `能力层`：skill 覆盖哪些关键步骤
- `业务层`：skill 之外还要加什么规则
- `输出层`：交付什么 deterministic 结果

## 3.6 instruction 的写法

instruction 只写：

- 业务目标
- 输入文件路径
- 输出文件路径
- 约束条件
- 验收格式

instruction 不写：

- skill 名
- 工具名
- 类名
- 脚本路径
- 完整算法

## 3.7 Oracle 的角色

Oracle 的职责是证明：这个 task 在当前环境下可以稳定完成。

因此 Oracle 可以直接调用 skill，但最好只让它负责：

- 读取输入
- 调用 skill 完成主难点
- 补一层薄业务逻辑
- 写出结果

如果 Oracle 重写了 skill 的核心逻辑，往往说明 skill 与 task 的分层不清楚。

## 3.8 tests 的角色

tests 不应直接 import skill，而应独立计算 ground truth。

优先验证：

- 输出文件是否存在
- 输出结构是否正确
- 关键字段是否正确
- 数值是否在容差内
- 主能力是否真的被完成

## 3.9 with-skill / no-skill 对照

最干净的做法是：

- `instruction.md` 相同
- 输入数据相同
- tests 相同
- 差异只在 skill 是否暴露给 agent

这样评测结果才能干净地归因到 skill。

## 4. 标准工作流

### Step 1：为 skill 建能力卡片

固定输出：

- `skill_name`
- `activation_signals`
- `core_capability`
- `decomposition`
- `critical_constraints`
- `expected_output_contract`
- `common_failures`

### Step 2：为每个 skill 提 3 个候选 task

每个候选 task 最少写清：

- 场景
- 主难点
- skill 覆盖部分
- 薄业务逻辑
- 输出文件
- 可验证方式

### Step 3：选最佳 task

优先级建议：

- 真实度高
- 测试最稳
- with / without skill 差距大
- instruction 最自然

### Step 4：构造训练样本

每个训练样本最好保留三层 supervision：

- 最终输出
- 高层 plan
- 关键结构化中间状态

### Step 5：保留 benchmark 原题做盲测

训练集与最终测试集必须分离。仓库作者原生 task 更适合作为 held-out evaluation，而不是训练集。

## 5. 提示词模板

## 5.1 分析 skill 并反推 task

```text
你现在是 SkillsBench 任务设计者。请基于一个已有 skill，反向设计 benchmark task。

我会提供：
1. SKILL.md
2. scripts/ 或工具接口
3. 任务仓库约束：
   - instruction.md 必须像真人给 agent 下任务
   - 不能在 instruction.md 中提 skill 名、工具名、API 名
   - task 必须 realistic、verifiable、with-skill 明显更容易
   - tests 必须独立于 skill 计算 ground truth
   - 最终可以做 with-skills / without-skills 对照

请按下面步骤输出，不要写代码：
1. 提取这个 skill 的核心能力边界：
   - 它能稳定解决什么问题
   - 它不解决什么问题
   - 它最适合承担任务中的哪一步难点
2. 设计 3 个候选 task 场景，每个都要包含：
   - 真实工作场景
   - skill 覆盖的关键难点
   - task 额外的一层薄业务逻辑
   - 可验证输出
   - with-skill / without-skill 的差异来源
3. 对每个候选 task 分析：
   - realism
   - verifiability
   - skill leverage
   - instruction naturalness
   - implementation risk
4. 选出最佳 task，并说明理由。
5. 给出该 task 的结构设计：
   - instruction.md 应写什么
   - environment/ 放什么数据
   - solve.sh 怎样利用 skill
   - tests 如何独立计算 ground truth
   - no-skill 对照版如何构造

要求：
- 不要把 task 设计成 skill API 的直接演示
- 不要把完整解法写进 instruction
- 不要依赖 LLM judge
```

## 5.2 写 instruction.md

```text
请根据以下 task 设计信息，写一个 SkillsBench 风格的 instruction.md。

要求：
- 必须像真人在工作中交代任务
- 只写业务目标、输入、输出、约束、交付物
- 不要提 skill 名、工具名、脚本名、类名、库名
- 不要泄露完整解法
- 不要写成教程或标准答案
- 让 agent 可以自己发现并使用环境中的 skill

task 信息：
- 业务场景：<填写>
- 输入文件：<填写>
- 要完成的目标：<填写>
- 输出文件：<填写>
- 格式要求：<填写>
- 精度/约束：<填写>

请输出：
1. instruction.md 正文
2. 再补一句简短说明：为什么这个 instruction 不会直接提示 skill
```

## 5.3 检查 task 是否像 benchmark 而不是 demo

```text
请审查下面这个 task 设计，判断它是不是一个高质量的 skill-based benchmark task。

请从以下维度逐项打分并解释：
1. 真实性
2. 可验证性
3. skill 的必要性
4. with-skill / without-skill 差距
5. instruction 是否自然
6. tests 是否独立
7. skill 是否过拟合单任务
8. 是否像“调用工具 demo”

最后输出：
- 最大问题
- 最值得保留的设计点
- 如何把它改造成更好的 benchmark task
```

## 6. `mesh-analysis` 重构示例摘要

以 `mesh-analysis` 为例，适合的重构路线是：

- skill 负责：Binary STL 解析、连通分量分析、主组件选择、体积计算、属性提取
- task 负责：查表、规则映射、结果输出

推荐把 benchmark 原题保留为测试集，再另外设计一个不同业务壳的训练任务，例如：

- 噪声扫描件主零件的材料成本估算
- 扫描件主零件的涂层用量估算
- 扫描件主零件的材料风险分级

这些任务共用同一核心能力，但表面任务壳不同，更适合拿来做 skill 内化训练。
