你要把一组真实风格的课程素材整理成一份可以直接用于新手培训的数据分析教学 notebook。

输入数据在：
- `/app/workspace/lesson_brief.md`：课程目标、受众、必须覆盖的知识点
- `/app/workspace/learner_events.csv`：学习行为事件数据
- `/app/workspace/quiz_attempts.csv`：练习与测验结果数据
- `/app/workspace/quiz_items.csv`：题目主题、错误分布与常见误区提示
- `/app/workspace/metric_definitions.yaml`：指标口径与字段解释
- `/app/workspace/reference_docs/`：参考资料与术语说明
- `/app/workspace/draft_notebook.ipynb`：当前的草稿 notebook，可以参考，也可以重做
- `/app/workspace/draft_instructor_guide.md`：当前的草稿讲师讲义
- `/app/workspace/build_lesson_package.py`：正式打包脚本；最终交付完成后需要运行它
- 如果运行环境中提供了 task-local `lesson-notebook-diagnostics`，优先先跑它给出的修复入口和检查脚本，再决定是否手工重写

你的任务
1、生成 `/app/output/student_lesson.ipynb`。这是一份面向初学者的数据分析教学 notebook，必须能按顺序执行，并且真正使用给定数据完成分析。
2、生成 `/app/output/instructor_guide.md`。这是一份和 notebook 对齐的讲师讲义，需要说明每一节想让学员学到什么、要提醒什么误区、以及可以怎么带练习。
3、生成 `/app/output/lesson_manifest.json`，格式如下：

```json
{
  "lesson_info": {
    "title": "New Analyst Workshop",
    "audience": "new data analysts"
  },
  "sections": [
    {
      "title": "What we're analyzing",
      "learning_goal": "Understand the business question",
      "uses_files": ["learner_events.csv"],
      "has_exercise": false
    }
  ],
  "key_metrics": [
    {
      "name": "completion_rate",
      "definition_source": "metric_definitions.yaml"
    }
  ]
}
```

4、生成 `/app/output/source_map.json`，用于标注每个章节的主要来源和关键结论。格式如下：

```json
{
  "sections": [
    {
      "title": "What we're analyzing",
      "sources": ["lesson_brief.md", "learner_events.csv"],
      "claims": [
        {
          "claim_id": "overview-1",
          "statement": "This lesson uses learner events and quiz outcomes from one workshop snapshot.",
          "source_files": ["lesson_brief.md", "learner_events.csv", "quiz_attempts.csv"]
        }
      ]
    }
  ]
}
```

5、notebook 和 instructor guide 都必须包含下面这些章节标题，且顺序必须一致：
- `What we're analyzing`
- `Understand the event data`
- `Build the session funnel`
- `Compare quiz outcomes`
- `Spot metric definition traps`
- `Practice`
- `Wrap up`
6、`lesson_manifest.json` 和 `source_map.json` 中的 `sections` 也必须使用同样的章节标题和顺序。
7、notebook 至少要：
- 读取并使用正式输入数据
- 产出至少 3 个基于数据计算的表格或图表
- 明确解释至少 2 个来自 `metric_definitions.yaml` 的指标或口径
- 明确使用 `quiz_items.csv` 讲清至少 1 个题目主题或常见误区
- `Practice` 章节不能只是泛泛提问；应至少给出 3 个基于可见输入的练习或反思提示，分别回扣事件漏斗、指标口径和题目误区分析，并在题干中点名相关输入文件
- 在文中标注至少 2 处来源，说明某个结论、字段解释或指标定义来自哪个输入文件
8、notebook、instructor guide、`lesson_manifest.json` 和 `source_map.json` 中的结论、术语、章节顺序和指标解释，必须彼此一致。
9、最终运行：

```bash
python /app/workspace/build_lesson_package.py
```

并生成：

- `/app/output/final_package.json`

10、如果你写了辅助脚本或中间文件，最终仍然需要把正确结果落实到正式输出文件里。

输出格式：
- 生成：
  - `/app/output/student_lesson.ipynb`
  - `/app/output/instructor_guide.md`
  - `/app/output/lesson_manifest.json`
  - `/app/output/source_map.json`
  - `/app/output/final_package.json`
- `student_lesson.ipynb` 必须是可正常打开和复核的 notebook
- `lesson_manifest.json` 必须是合法 JSON
- `source_map.json` 必须是合法 JSON
- `final_package.json` 必须来自正式打包脚本，而不是手写伪结果

说明：
- 不要 hack verifier，不要根据测试文件硬编码图表数值、指标结果、章节内容或 JSON 字段值。
- 不要把任务降级成只写一份静态总结、纯 Markdown 文档、图片截图或空壳 notebook。
- 不要伪造数据分析过程，不要把应当由代码计算得到的结果改成手写常量。
- 不要删除必需章节、练习、来源标注、题目误区分析、指标解释或讲师讲义来规避问题。
- 不要修改输入数据、测试文件、依赖配置或 skill 本体。
