# Astronomy & Physics Template

这是面向 astronomy-physics 类 skill 的模板。它综合参考 SkillsMP 这一类热门 skill 的共性能力：把公开科学数据整理为可复现的分析流程，围绕坐标、时间、表格、FITS、交叉匹配和宇宙学量计算形成可验证交付物。模板任务强调多源输入、确定性输出和可审计中间量，尤其强调 detector-space 到 sky-coordinate 的重建和 nearest-host 距离上下文。

## 第一部分：任务设计参考

* **Skill 价值定位**：这一类 skill 的核心价值是把科学数据处理拆成稳定的对象级工作流，例如 WCS 坐标重建、时间系统归一化、目录交叉匹配、单位与宇宙学量计算。任务设计应把重点放在“从原始科学输入到审阅结论”的完整链路，避免退化成单点脚本拼接。
* **Verifier 设计重点**：Verifier 需要同时检查数值正确性、表间一致性和流程依赖性。除了比对最终输出，还应加入输入变异测试，确认 solver 确实读取了 WCS、阈值配置、host slice 和目录数据，避免写死答案。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`astronomy-physics__m101-candidate-review`
- 类别：`astronomy-physics`
- 绑定 Skill：`astropy`
- 输入数据参考来源：
  - `environment/data/fits/m101_field_g.fits`：M101 视场 g 波段 FITS cutout；设计直接取自 Legacy Survey DR10 cutout 接口  
    [https://www.legacysurvey.org/viewer/fits-cutout?ra=210.8023&dec=54.349&layer=ls-dr10&pixscale=0.262&bands=g&size=512](https://www.legacysurvey.org/viewer/fits-cutout?ra=210.8023&dec=54.349&layer=ls-dr10&pixscale=0.262&bands=g&size=512)
  - `environment/data/fits/m101_field_r.fits`：M101 视场 r 波段 FITS cutout；设计直接取自 Legacy Survey DR10 cutout 接口  
    [https://www.legacysurvey.org/viewer/fits-cutout?ra=210.8023&dec=54.349&layer=ls-dr10&pixscale=0.262&bands=r&size=512](https://www.legacysurvey.org/viewer/fits-cutout?ra=210.8023&dec=54.349&layer=ls-dr10&pixscale=0.262&bands=r&size=512)
  - `environment/data/fits/m101_field_z.fits`：M101 视场 z 波段 FITS cutout；设计直接取自 Legacy Survey DR10 cutout 接口  
    [https://www.legacysurvey.org/viewer/fits-cutout?ra=210.8023&dec=54.349&layer=ls-dr10&pixscale=0.262&bands=z&size=512](https://www.legacysurvey.org/viewer/fits-cutout?ra=210.8023&dec=54.349&layer=ls-dr10&pixscale=0.262&bands=z&size=512)
  - `environment/data/catalogs/gaia_m101_cone.ecsv`：M101 同视场 Gaia DR3 cone-search 目录切片；设计直接参考 Gaia Archive 目录查询  
    [https://gea.esac.esa.int/archive/](https://gea.esac.esa.int/archive/)
  - `environment/data/catalogs/host_galaxies.tsv`：M101 主宿主加 nearby-galaxy review slice；主宿主条目形态参考 SIMBAD 的 M101 条目，邻近宿主切片形态参考 NED 的公开 extragalactic search workflow  
    [https://simbad.cds.unistra.fr/simbad/sim-id?Ident=M+101](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=M+101)  
    [https://ned.ipac.caltech.edu/Documents/Guides/Searches](https://ned.ipac.caltech.edu/Documents/Guides/Searches)

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 格式要求 | 检查最终生成的所有文件是否齐全、可解析，且字段合规 | 掌握结构化文件的生成与规范交付 |
| 坐标与时间换算 | 确认图像像素坐标到天球坐标的转换、以及时间格式的统一是否准确 | 掌握天文坐标系与时间系统的标准转换 |
| 星表交叉匹配 | 验证附近恒星匹配、与宿主星系的间隔角度等计算结果是否无误 | 熟练进行空间角距离计算与目标检索 |
| 物理量与距离 | 核对亮度星等、误差计算、目标距离及绝对星等的计算链路是否严谨 | 掌握单位换算、宇宙学参数应用与物理公式推导 |
| 结果闭环 | 检查总结报告、待复核列表及各个明细表的数据是否完全吻合对齐 | 跨报表的数据核查与总体结论收口 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 防坐标写死 | 修改原始图片像素坐标后，程序输出的天球坐标结果必须随之变化 |
| 防规则绕过 | 修改判定规则参数后，最终自动输出的分类结果必须予以更新 |
| 防距离结论写死 | 更改目标星系的红移（距离）参数后，受此影响的评估结论必须相应改变 |
| 防假计算流程 | 代码必须真实读取图像、星表与规则文件进行处理，并调用标准的天文计算库，严禁硬编码（写死）结果 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务把 `astropy` 的 WCS、SkyCoord、Time、Table 和 cosmology 工作流组合成同一条业务链路，with_skill 更容易把 FITS 1-based 像素原点、Gaia/host 最近邻匹配和距离驱动分类一起做对；without_skill 即使修到接近可用，也更容易在 sky-coordinate 重建上留下系统性偏差。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除 build cancelled 与 setup 失败的 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | 最近 3 次有效对照里，without Skill 都保留 verifier 失败；主要失分点是 FITS 1-based WCS 重建误差连带影响 Gaia 分离角和 reportable 坐标。 |
| Agent 执行耗时 | `287.2s` | `319.6s` | With Skill 会额外核对 WCS、crossmatch 和 cosmology 约定，平均耗时略高，但通过率明显更好。 |
| Tokens | `0.87M` | `0.86M` | 这里按输入、缓存和输出合计 tokens 统计；两边成本接近，With Skill 略低，主要收益体现在成功率提升，成本变化很小。 |

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
