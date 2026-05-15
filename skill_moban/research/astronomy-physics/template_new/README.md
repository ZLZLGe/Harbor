# Astronomy & Physics Template

这是面向 astronomy-physics 类 skill 的模板。它综合参考 SkillsMP 这一类热门 skill 的共性能力：围绕 FITS、WCS、天球坐标、时间系统、星表匹配、物理量换算和距离模型，完成一条可审计、可复现的科学分析交付链路。模板任务强调多源输入、数值一致性、中间表可追溯，以及从 detector-space 到 review packet 的完整闭环。

## 第一部分：任务设计参考

* **Skill 价值定位**：这一类 skill 的核心价值，是把科学数据处理拆成稳定的对象级工作流，例如 WCS 坐标重建、时间归一化、目录交叉匹配、表格写出、距离模型计算和单位一致性检查。任务设计应让 solver 必须走完整分析链路，而不是只拼一个末端报表。
* **Verifier 设计重点**：Verifier 既要核对最终数值，也要保护分析过程本身。除最终输出比对外，还应覆盖输入数据不被改写、输入变动会带来结果联动、重复运行可复现这几类保护，避免 solver 通过写死答案、跳过计算或只修表面字段蒙混过关。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`astronomy-physics__ngc4993-followup-packet`
- 类别：`astronomy-physics`
- 绑定 Skill：`astropy`
- 输入数据参考来源：
  - `environment/data/fits/ngc4993_g.fits`：NGC 4993 视场 g 波段 FITS cutout；设计形态参考 Legacy Survey DR10 cutout  
    [https://www.legacysurvey.org/viewer/fits-cutout?ra=197.448711&dec=-23.383976&layer=ls-dr10&pixscale=0.262&bands=g&size=256](https://www.legacysurvey.org/viewer/fits-cutout?ra=197.448711&dec=-23.383976&layer=ls-dr10&pixscale=0.262&bands=g&size=256)
  - `environment/data/fits/ngc4993_r.fits`：NGC 4993 视场 r 波段 FITS cutout；设计形态参考 Legacy Survey DR10 cutout  
    [https://www.legacysurvey.org/viewer/fits-cutout?ra=197.448711&dec=-23.383976&layer=ls-dr10&pixscale=0.262&bands=r&size=256](https://www.legacysurvey.org/viewer/fits-cutout?ra=197.448711&dec=-23.383976&layer=ls-dr10&pixscale=0.262&bands=r&size=256)
  - `environment/data/fits/ngc4993_z.fits`：NGC 4993 视场 z 波段 FITS cutout；设计形态参考 Legacy Survey DR10 cutout  
    [https://www.legacysurvey.org/viewer/fits-cutout?ra=197.448711&dec=-23.383976&layer=ls-dr10&pixscale=0.262&bands=z&size=256](https://www.legacysurvey.org/viewer/fits-cutout?ra=197.448711&dec=-23.383976&layer=ls-dr10&pixscale=0.262&bands=z&size=256)
  - `environment/data/catalogs/gaia_foreground_slice.ecsv`：NGC 4993 同视场 Gaia DR3 cone-search 目录切片；设计形态参考 Gaia cone-search 工作流  
    [https://gaia.aip.de/cms/services/cone-search/](https://gaia.aip.de/cms/services/cone-search/)
  - `environment/data/catalogs/host_galaxies.tsv`：宿主星系 review slice；主宿主条目形态参考 SIMBAD，邻近星系检索形态参考 NED  
    [https://simbad.cds.unistra.fr/simbad/sim-id?Ident=NGC+4993](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=NGC+4993)  
    [https://ned.ipac.caltech.edu/Documents/Guides/Searches](https://ned.ipac.caltech.edu/Documents/Guides/Searches)

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出合同 | 检查 5 个交付文件是否齐全、可解析，字段是否完整且顺序正确 | 结构化交付与表格写出 |
| 坐标与时间 | 核对 detector-space 到 sky-coordinate 的重建结果，以及 ISO / MJD 时间归一化是否正确 | WCS、SkyCoord、Time |
| 目录匹配 | 核对 Gaia 最近邻、宿主最近邻、角距离和匹配状态是否一致 | 星表读取、坐标匹配、角距离计算 |
| 光度与距离 | 核对校准星等、误差、宿主红移距离、投影 offset 是否一致 | 单位处理、距离模型、物理量推导 |
| 报表闭环 | 核对 briefing、support tables、diagnostics 之间是否互相对齐 | 多表一致性与审阅收口 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入数据保护 | 检查 solver 是否改写了原始输入数据文件 |
| 位置扰动联动 | 改动候选体像素位置后，重建坐标和下游结果必须同步变化 |
| 阈值规则联动 | 改动 review 规则阈值后，分类标签必须随之变化 |
| 宿主红移联动 | 改动宿主红移后，距离与投影 offset 必须同步变化 |
| 观测元数据联动 | 改动观测起始时间、曝光时间后，时间和光度结果必须同步变化 |
| 重复运行一致性 | 同一输入重复运行两次，输出文件内容必须一致 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务把 `astropy` 常见工作流压缩在同一条交付链里，solver 需要稳定处理 FITS/WCS、坐标匹配、时间系统、表格写出和距离模型。skill 的核心价值，在于把这些分析步骤连成一套更稳的实现路径，减少在坐标原点、距离口径、表间一致性上的试错。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败与构建失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `TBD` | `TBD` | `TBD` |
| Agent 执行耗时 | `TBD` | `TBD` | `TBD` |
| Tokens | `TBD` | `TBD` | `TBD` |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
