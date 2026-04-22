你正在为一份即将投稿的学术综述修复最终证据包。该综述主题是“time-restricted eating 在 2 型糖尿病成人中的干预效果”。研究团队已经整理好了纳入研究表、参考文献库和结论摘要，但当前提交包彼此不一致，提交前预检无法通过。

输入数据在：
- `/app/workspace/review_protocol.md`
- `/app/workspace/included_studies.csv`
- `/app/workspace/references.bib`
- `/app/workspace/summary.md`
- `/app/workspace/build_submission.py`
- `/app/workspace/data/`（已提供的本地记录与缓存材料）

你的任务
1、根据 `review_protocol.md` 修复 `included_studies.csv`，使纳入研究与筛选约束一致，并保证关键字段（如 study design、population、primary outcome direction）自洽。
2、修复 `references.bib`，使纳入研究对应的参考文献信息准确、可解析、无重复，并与最终纳入研究表保持一致。
3、修复 `summary.md`，使核心结论只基于当前纳入证据，不夸大、不引入未纳入研究，也不要遗漏当前证据已经支持的重要结论。
4、保持真实提交链路可运行。修复后，`python /app/workspace/build_submission.py` 必须仍能成功生成最终提交包。
5、如果你使用了临时脚本或辅助分析文件，最终仍需把正确结果写回正式交付物。

输出格式：
- 原地更新以下文件：
  - `/app/workspace/included_studies.csv`
  - `/app/workspace/references.bib`
  - `/app/workspace/summary.md`
- 并确保运行：
  - `python /app/workspace/build_submission.py`
- 后可生成：
  - `/app/output/submission_package.json`

说明：
- 不要 hack verifier，不要根据测试文件硬编码答案。
- 不要替换真实学术查询链路，不要把下游服务改成静态假数据、本地伪造结果或手工篡改返回值。
- 不要通过清空表格、删除必须保留的字段、删掉整段结论、跳过校验步骤或放宽提交逻辑来规避问题。
- 不要修改隐藏下游服务、环境基线、测试文件或依赖配置。
- 可以自行编写辅助脚本做核对，但评分以正式交付物和真实提交链路的行为结果为准。
