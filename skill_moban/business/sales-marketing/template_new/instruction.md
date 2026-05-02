你需要为一个开发者工具 SaaS 团队修复其产品营销站在发布前的有机搜索发布阻塞。团队已经把站点源码、关键词规划、历史快照、参考资料和当前发布校验链路放进容器，但增长团队仍然无法批准这次上线。

输入数据位于容器内：

- `/root/workspace/site/`：营销站源码与构建脚本。
- `/root/workspace/seo_inputs/site_manifest.json`：站点入口、目标页面、正式构建命令和输出要求。
- `/root/workspace/seo_inputs/keyword_map.csv`：目标页面、主关键词、次关键词、搜索意图、页面类型和标题约束。
- `/root/workspace/seo_inputs/search_console_snapshot.json`：较早导出的索引覆盖、查询词和落地页表现快照，可能过期。
- `/root/workspace/seo_inputs/crawl_snapshot.ndjson`：较早抓取的页面与站内信号快照，可能只覆盖部分 URL，且不再代表当前真实站点。
- `/root/workspace/seo_inputs/content_briefs/`：按页面整理的产品定位、功能事实、受众、禁止 claims 和可引用证据。
- `/root/workspace/seo_inputs/reference_pages/`：从公开产品页、文档页和定价页归一化整理的参考资料包。
- 容器内还提供了当前发布校验所需的本地预览与校验工具。

## 你的任务

1. 审查目标页面、站点源码、历史快照和当前发布校验结果，定位导致目标页面无法满足上线门槛的根因。
2. 在不改变站点核心产品定位和页面用途的前提下，修复这些发布阻塞，使所有 target page 满足 `site_manifest.json` 和 `keyword_map.csv` 定义的要求。
3. 使用正式构建重新生成站点产物，并基于容器内当前校验链路确认目标页面已达到发布条件。
4. 产出一份机器可读的修复报告、一份关键词覆盖表和一份给增长负责人的简短摘要。

## 业务规则

1. `site_manifest.json` 中列出的每个 target page 都必须被检查，不能遗漏。
2. `search_console_snapshot.json` 和 `crawl_snapshot.ndjson` 只能作为历史上下文，不能代替当前构建后的实际校验结果。
3. 所有 target page 最终都必须满足发布门槛；不得通过删除页面、改成 noindex、加入 robots 屏蔽、替换为占位页或改动页面用途来规避问题。
4. `keyword_map.csv` 中定义的页面定位、关键词映射和标题约束必须被遵守，不能自行改写目标关键词或放宽门槛。
5. 如果某个历史 URL 已被新页面替代，必须按站点规则处理为规范跳转或规范化归并，不能保留相互竞争的重复正式页。
6. 页面事实必须来自现有源码、content brief 或 reference packet 中允许使用的证据。不得捏造产品能力、客户案例、性能数字、集成数量、安全合规承诺或市场排名。

## 输出格式

如 `/root/output/` 不存在，请先创建该目录。

写入 `/root/output/seo_fixes_report.json`，结构如下：

```json
{
  "site_id": "site-000",
  "target_pages": [
    {
      "page_id": "pricing",
      "url": "https://example.test/pricing",
      "primary_keyword": "string",
      "indexable": true,
      "canonical_url": "https://example.test/pricing",
      "title": "string",
      "meta_description": "string",
      "h1": "string",
      "incoming_internal_links": 2,
      "structured_data_types": ["SoftwareApplication"],
      "fixes_applied": ["string"],
      "evidence_refs": ["brief:pricing", "ref:posthog-pricing"]
    }
  ],
  "sitemap_summary": {
    "sitemap_path": "string",
    "expected_urls_present": true,
    "unexpected_urls": []
  },
  "redirects_or_canonicalizations": [
    {
      "source_url": "string",
      "target_url": "string",
      "reason": "string"
    }
  ],
  "remaining_risks": [
    {
      "page_id": "string",
      "risk": "string",
      "why_not_blocking": "string"
    }
  ],
  "validation": {
    "build_status": "pass",
    "seo_audit_status": "pass"
  }
}
```

要求：

- `target_pages` 必须覆盖 `site_manifest.json` 中的全部 target page，且每个 `page_id` 只能出现一次。
- `indexable` 必须使用 `true` 或 `false`。
- `canonical_url` 必须写最终正式 canonical URL。
- `incoming_internal_links` 必须是 JSON number。
- `structured_data_types` 必须写出该页最终被当前发布校验链路识别到的 schema type。
- `fixes_applied` 至少列出该页的关键修复动作。
- `evidence_refs` 至少包含 2 条引用，且至少 1 条来自 `content_briefs/`、至少 1 条来自 `reference_pages/`。
- `validation.build_status` 和 `validation.seo_audit_status` 必须都是 `pass`。

写入 `/root/output/keyword_coverage.csv`，列名必须严格如下：

```csv
page_id,url,primary_keyword,secondary_keywords,title_length,primary_keyword_in_title,primary_keyword_in_h1,meta_description_present,canonical_self_referencing,indexable,incoming_internal_links,structured_data_ok
```

要求：

- 必须覆盖全部 target page。
- `secondary_keywords` 使用 `|` 分隔。
- `title_length` 必须是数值。
- `primary_keyword_in_title`、`primary_keyword_in_h1`、`meta_description_present`、`canonical_self_referencing`、`indexable`、`structured_data_ok` 必须使用 `true` 或 `false`。

写入 `/root/output/growth_summary.md`，内容必须包含：

- 站点编号；
- 已修复的 target page 数量；
- 仍保留的非阻塞风险；
- sitemap 和规范化处理概况；
- 关键词覆盖概况；
- 最重要的站内发现路径改动；
- 最重要的结构化数据改动；
- 对增长负责人的简短发布建议。

## 说明

- 不要修改 `/root/workspace/seo_inputs/` 下的输入文件。
- 不要把历史 snapshot 当作唯一依据，也不要绕过当前容器内的实际校验链路。
- 不要用静态手写报告、伪造 crawl 结果、伪造结构化数据结果或缓存答案来替代真实站点修复链路。
- 不要删除 target page、关闭构建检查、关闭 sitemap 校验、删除发现路径要求，或通过减少功能来规避问题。
- 不要修改 verifier 文件、task metadata、environment 文件或任何 `skills` 目录内容。
- 可以在工作目录中编写辅助脚本，但最终只需要提交 `/root/output/` 下要求的 3 个文件，并保留站点修复结果。


