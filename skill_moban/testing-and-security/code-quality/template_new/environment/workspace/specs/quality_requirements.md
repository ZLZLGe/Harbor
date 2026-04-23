# Quality Requirements

这个仓库的目标不是单纯“修一个函数”，而是把一条会持续演进的结算导出链路变成可交接、可诊断、可复核的质量体系。

最低质量标准：

- 功能测试至少覆盖 reference 和 dirty incident 两个场景
- 质量说明要能把 spec、incident 和 gateway 验收连起来
- code review 运行说明里要明确哪些行为属于高风险回归，以及每条 finding 至少要带什么 evidence
- integration test 运行说明里要说明如何清空旧产物再重跑
- spec audit 运行说明里要说明哪些字段契约不能被“看起来差不多”的替代实现吞掉
- 汇总产物里要明确两个正式场景的验收结果，方便复核 daily / monthly 是否都真正过了真实 gateway
