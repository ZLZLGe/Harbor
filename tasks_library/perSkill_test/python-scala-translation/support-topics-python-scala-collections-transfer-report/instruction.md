# Support Topic Report Transfer

请把 `/root/support_topic_report.py` 翻译为 Scala 2.13，并把最终代码写到 `/root/SupportTopicReport.scala`。

实现要求：

- 不要写 `package` 声明。
- 只使用 Scala 2.13 标准库，不要引入第三方依赖。
- 输出文件必须定义公开对象 `SupportTopicReport`。
- `SupportTopicReport` 必须提供可运行的 `main(args: Array[String]): Unit`，并按下面的命令行契约工作：
  - `args(0)` 是输入工单 TSV 路径
  - `args(1)` 是停用词文件路径
  - `args(2)` 是输出报表路径
  - 参数数量不为 3 时，应输出用法信息并以非 0 状态退出

输入资产：

- `/root/tickets.tsv`
- `/root/stopwords.txt`
- `/root/support_topic_report.py`

工单与分词规则：

- TSV 按表头读取，至少包含这些列：
  - `ticket_id`
  - `queue`
  - `agent`
  - `status`
  - `subject`
  - `body`
- 每个字段都需要 `trim` 后再使用。
- 停用词文件是一行一个词；空行忽略；匹配时不区分大小写。
- 主题词来自 `subject` 和 `body` 拼接后的文本。
- 分词规则使用正则 `[A-Za-z]+`，统一转成小写。
- 长度小于 4 的词要忽略。
- 停用词要忽略。
- 同一张工单里的重复词只计一次；后续所有词频统计都基于“某个词是否出现在该工单中”。

报表语义契约：

- 状态值按小写判断，只有 `open` 和 `pending` 计入 active；其他状态都视为 inactive。
- 需要生成 UTF-8 文本报表，并写到 `args(2)` 指定路径。
- 报表必须严格由这 3 个 section 组成，section 之间用一个空行分隔：

1. `QUEUE SUMMARY`
2. `AGENT SUMMARY`
3. `QUEUE OVERLAPS`

- `QUEUE SUMMARY` 中每一行格式必须是 `QUEUE\t<queue>\t<ticket_count>\t<active_count>\t<agent_count>\t<topic1,topic2,...>`。
- 队列排序规则：
  - `active_count` 降序
  - `ticket_count` 降序
  - `queue` 升序
- 其中 `topic1,topic2,...` 是该队列前 5 个主题词：
  - 词频按覆盖工单数统计
  - 先按词频降序，再按词字典序升序
  - 不足 5 个就全部输出
  - 如果为空，输出 `-`

- `AGENT SUMMARY` 中每一行格式必须是 `AGENT\t<agent>\t<ticket_count>\t<queue1,queue2,...>\t<topic1,topic2,...>`。
- 坐席排序规则：
  - 不同队列数降序
  - `ticket_count` 降序
  - `agent` 升序
- `queue1,queue2,...` 是该坐席处理过的队列名去重后按字典序拼接。
- 主题词取该坐席前 3 个主题词，排序和空值规则与队列 section 相同。

- `QUEUE OVERLAPS` 中每一行格式必须是 `OVERLAP\t<queue_a>\t<queue_b>\t<shared1,shared2,...>`。
- 先对每个队列取它在 `QUEUE SUMMARY` 中的前 5 个主题词集合，再对所有不同队列两两求交集。
- 只输出交集非空的队列对。
- overlap 行排序规则：
  - 交集词数降序
  - `queue_a` 升序
  - `queue_b` 升序
- `shared1,shared2,...` 需要按字典序升序拼接。

验证方式：

- 测试会直接编译 `/root/SupportTopicReport.scala`。
- 测试会按命令行方式运行 `SupportTopicReport`，检查生成的报表内容。
- 测试不仅会使用题目提供的 `/root/tickets.tsv` 和 `/root/stopwords.txt`，也可能额外构造新的 TSV/停用词文件再次运行。
- 只要命令行行为、输出文件格式和报表语义一致，内部实现细节不限。
