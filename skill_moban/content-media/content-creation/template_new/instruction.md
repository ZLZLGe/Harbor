你在为一支面向工程师的内容团队准备一套围绕 AI agent 主题的多平台内容包。团队已经把主文章、补充材料、品牌样例和发布约束整理到工作区；他们要求所有成稿都基于现有材料完成，并满足各自渠道的发布用途。

输入数据在 `/root/workspace/source_bundle/`：

- `source_index.json`：输入文件索引、来源编号、素材类型和建议用途。
- `anchor_article.md`：本次内容包的主文章。
- `supporting_context/`：产品介绍、补充文章、术语说明和可引用背景材料。
- `voice_samples/`：既有品牌/作者样例文稿。
- `campaign_constraints.json`：受众、渠道目标、字数范围、CTA 约束和禁写事项。
- `style_red_flags.txt`：内容负责人明确拒收的表达方式。

容器内还提供了本地 review service，用于交叉核对素材清单、行号引用和发布约束。

你的任务

1. 阅读全部输入材料，整理出本轮内容发布的统一方向，并完成 3 份对外交付件。
2. 基于现有材料完成一条 X thread、一篇 LinkedIn post 和一篇 newsletter draft，使其适合各自渠道阅读。
3. 为每份交付件补齐来源登记，标明关键表述依托的输入材料。
4. 列出发布前仍需内容团队确认、补充或审批的事项。

输出

如 `/root/output/` 不存在，请先创建该目录。所有交付件都写入 `/root/output/`，且仅创建以下文件：

- `campaign_summary.md`
- `x_thread.md`
- `linkedin_post.md`
- `newsletter_draft.md`
- `source_map.json`
- `publish_gaps.json`

`campaign_summary.md` 要求：

- 第一行写 1 句本轮 campaign summary。
- 之后写 3 行渠道说明，分别对应 X、LinkedIn、newsletter。
- 每行以 `- ` 开头，包含渠道名和该渠道的内容重点。

`x_thread.md` 要求：

- 使用英文写作。
- 5 到 7 条，按 `1/`、`2/` 递增编号。
- thread 首条直接进入观点、证据或张力。

`linkedin_post.md` 要求：

- 使用英文写作。
- 180 到 320 词。
- 最多 6 个自然段。
- 允许 1 组简短列表，列表项不超过 3 条。

`newsletter_draft.md` 要求：

- 使用英文写作。
- 文件前两行必须分别以 `Subject:` 和 `Preview:` 开头。
- 正文 350 到 550 词。
- 正文至少包含 3 个 `##` 二级标题。
- 首段直接进入主题。

`source_map.json` 必须满足以下结构：

```json
{
  "anchor_asset": "anchor_article.md",
  "deliverables": [
    {
      "file": "x_thread.md",
      "audience": "string",
      "content_focus": "string",
      "source_refs": ["relative/path.md#L10-L20"]
    }
  ],
  "shared_limits": ["string"]
}
```

要求：

- `deliverables` 必须覆盖 `x_thread.md`、`linkedin_post.md`、`newsletter_draft.md`。
- 每个 deliverable 至少提供 2 条 `source_refs`。
- `source_refs` 只能引用 `/root/workspace/source_bundle/` 内的文件。

`publish_gaps.json` 必须满足以下结构：

```json
{
  "gaps": [
    {
      "topic": "string",
      "why_it_matters": "string",
      "needed_from_team": "string"
    }
  ]
}
```

说明

- 只可使用 `/root/workspace/source_bundle/` 内的材料写作和取证。
- 不要补写输入中未出现的客户名称、数字、发布日期、功能能力、案例或引语。
- 不要把同一段文案直接复制到多个渠道文件中。
- 不要修改输入目录、测试、环境文件或任何 `skills` 目录内容。
- 可以编写辅助脚本；最终只提交 `/root/output/` 下要求的文件。
