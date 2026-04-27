你正在为一个多夜巡天观测项目整理瞬变候选体复核包。当前交付物中的候选体位置、观测时间、星表匹配和物理量摘要来自多个观测夜与不同 FITS 图像扩展，必须统一到可复核、可重复运行的正式结果中。

输入数据在：
- `/root/environment/data/fits/`：多夜观测的 FITS 图像文件，包含 WCS、观测时间、滤光片、曝光时间和图像扩展信息
- `/root/environment/data/detections/`：候选体像素坐标、孔径流量、流量误差、信噪比和质量标记
- `/root/environment/data/catalogs/`：参考星表、宿主星系表、已知移动天体表和交叉匹配辅助数据
- `/root/environment/data/calibration/`：滤光片零点、消光系数、观测站点信息和项目阈值配置
- `/root/environment/pipeline/`：当前分析入口和配套脚本
- `/services/field-context/server.py`：同容器内的本地下游 field context 服务启动入口，只允许调用，不允许修改
- 如果容器中存在 `/root/.codex/skills/astropy/probes/transient_triage_probe.py`，可以把它作为 Astropy 诊断探针使用，用于检查 WCS、时间、交叉匹配、测光和分类计算；最终交付物仍必须由正式入口 `/root/environment/pipeline/run_transient_triage.py` 重新生成

当前症状：
- 一部分候选体的像素位置被直接当作天球坐标使用，导致 RA/Dec、银道坐标和星表匹配结果不可信
- 不同观测夜的时间字段混用了 ISO、MJD 和曝光起始时间，导致同一候选体的观测时间排序和移动天体排除结果不一致
- 星表匹配半径在角秒和角度之间存在混用，部分 Gaia 近邻、宿主星系和移动天体污染源被错误保留或错误剔除
- 测光摘要没有稳定区分原始流量、校准 AB 星等、星等误差、宿主红移距离和绝对星等，最终报告中的候选体分级无法复核
- 下游 field context 摘要与正式候选体表中的坐标、候选体数量和分类结果对不上

你的任务
1、基于 FITS WCS、候选体像素坐标、观测元数据和校准表，重建每个候选体的 ICRS 天球坐标、银道坐标、观测时间和测光量。检测表中的像素坐标使用 FITS 1-based convention。
2、对所有候选体执行参考星表、宿主星系和已知移动天体的交叉匹配，匹配距离必须使用真实角距离并按配置阈值判断。
3、根据校准后的 AB 星等、星等误差、宿主红移、宇宙学距离和质量标记，生成可复核的候选体分类与是否可报告标记。
4、调用本地 field context 服务，为最终可报告候选体补充 field-level 上下文，并确保服务返回内容与正式结果表一致。
5、保留完整审计结果，使每个输入 detection 都能追溯到对应 FITS 文件、HDU、像素坐标、天球坐标、匹配证据、质量标记和最终分类。
6、修复或补全正式分析链路。完成后，`python /root/environment/pipeline/run_transient_triage.py --output /root/answer` 必须能成功运行并重新生成全部正式交付物。
7、如果你编写了临时脚本或辅助分析文件，最终仍需把正确结果写回正式交付物，并保证正式入口可重复运行。

输出格式：
- `/root/answer/astrometric_candidates.ecsv`
  - 必须覆盖所有输入 detection
  - 必须包含列：`field_id`, `candidate_id`, `fits_file`, `hdu_name`, `x_pixel`, `y_pixel`, `ra_icrs_deg`, `dec_icrs_deg`, `gal_l_deg`, `gal_b_deg`, `obstime_utc_iso`, `obstime_mjd`, `filter`, `snr`, `quality_flags`, `classification`, `reportable`
  - `classification` 只能使用这些标签：`extragalactic_transient`, `reject_stellar_counterpart`, `reject_moving_object`, `reject_low_snr`, `reject_quality_flag`, `review_faint_host_association`, `review_no_host`, `reject_uncertain_photometry`
  - `reportable` 只能为 true/false；只有 `classification == extragalactic_transient` 的候选体可标为 true
- `/root/answer/photometry_summary.tsv`
  - 必须覆盖所有输入 detection
  - 必须包含列：`candidate_id`, `flux_aperture`, `flux_err`, `zeropoint_ab`, `extinction_mag`, `calibrated_ab_mag`, `mag_unc`, `host_id`, `host_redshift`, `luminosity_distance_mpc`, `absolute_mag`
- `/root/answer/crossmatch_audit.tsv`
  - 必须覆盖所有输入 detection
  - 必须包含列：`candidate_id`, `nearest_gaia_source_id`, `gaia_sep_arcsec`, `nearest_host_id`, `host_sep_arcsec`, `nearest_moving_object_id`, `moving_object_sep_arcsec`, `match_decision`, `rejection_reason`
- `/root/answer/triage_diagnostics.tsv`
  - 必须覆盖所有输入 detection
  - 必须包含列：`candidate_id`, `wcs_roundtrip_x_pixel`, `wcs_roundtrip_y_pixel`, `gaia_reject_margin_arcsec`, `host_match_margin_arcsec`, `moving_object_reject_margin_arcsec`, `classification_priority`, `row_signature`
  - `wcs_roundtrip_x_pixel` 和 `wcs_roundtrip_y_pixel` 是最终 ICRS 坐标通过同一个 FITS WCS 反投影回检测表 1-based 像素 convention 后的位置
  - `gaia_reject_margin_arcsec = gaia_sep_arcsec - gaia_reject_arcsec`
  - `host_match_margin_arcsec = host_match_arcsec - host_sep_arcsec`
  - `moving_object_reject_margin_arcsec = moving_object_sep_arcsec - moving_object_reject_arcsec`；没有有效时间窗内移动天体时留空
  - `classification_priority` 对应下方分类优先级的序号
  - `row_signature` 是每行审计签名：如果存在 Astropy diagnostics kernel，请使用该 kernel 的签名域和签名约定生成；如果不存在，需要自行从公开输入重建同一类行级审计签名，签名必须稳定、逐行唯一，并对坐标、分类、可报告标记、测光和最近邻匹配对象敏感
- `/root/answer/report.json`
  - 顶层必须包含键：`n_input_detections`, `n_reportable_candidates`, `coordinate_frame`, `time_scale`, `cosmology`, `classification_summary`, `field_context_summary`, `reportable_candidates`, `notes`
  - `reportable_candidates` 中每个候选体必须包含：`candidate_id`, `ra_icrs_deg`, `dec_icrs_deg`, `obstime_utc_iso`, `calibrated_ab_mag`, `classification`, `primary_evidence`
  - `coordinate_frame` 必须明确说明最终天球坐标使用 ICRS
  - `time_scale` 必须明确说明最终报告时间使用 UTC，并说明 MJD 对应关系
  - `cosmology` 必须明确说明宿主距离计算使用 Astropy `Planck18`；为避免下游系统歧义，建议写成包含 `Planck18` 的字符串
  - `field_context_summary` 必须是本地 field context 服务返回的完整 JSON 对象，不要再包一层 `context`、`result` 或 `request_candidates`
- `/root/answer/field_context.json`
  - 必须包含本地 field context 服务对最终可报告候选体返回的完整 JSON 响应体
  - 文件内容必须与 `/root/answer/report.json` 中的 `field_context_summary` 完全一致
  - 候选体集合、坐标和 field_id 必须与 `astrometric_candidates.ecsv` 和 `report.json` 保持一致

说明：
- 使用容器内提供的 FITS、检测表、参考星表、校准表和本地下游服务完成分析，输出结果必须可复现。
- 观测时间以曝光中点为准：`DATE-OBS + EXPTIME / 2`，最终报告时间使用 UTC ISO 与对应 MJD。
- AB 星等按 `zeropoint_ab - 2.5 * log10(flux_aperture / exposure_seconds) - extinction_mag` 计算；星等误差按 `1.0857362047581294 * flux_err / flux_aperture` 传播。
- 宿主距离和绝对星等使用 Astropy `Planck18` 宇宙学模型计算。
- 候选体分类按以下优先级确定：
  1. `quality_flags` 不是 `none`：`reject_quality_flag`
  2. `snr` 小于配置中的 `min_snr`：`reject_low_snr`
  3. 最近 Gaia 源距离小于等于配置中的 `gaia_reject_arcsec`：`reject_stellar_counterpart`
  4. 有效时间窗内最近移动天体距离小于等于配置中的 `moving_object_reject_arcsec`：`reject_moving_object`
  5. 没有宿主星系落在配置中的 `host_match_arcsec` 内：`review_no_host`
  6. 星等误差无效或大于配置中的 `max_mag_unc`：`reject_uncertain_photometry`
  7. 绝对星等无效或大于配置中的 `reportable_absolute_mag_max`：`review_faint_host_association`
  8. 其余候选体：`extragalactic_transient`
- 不要硬编码坐标、匹配对象、候选体分类、可报告数量或摘要内容。
- 不要替换真实链路，不要把 WCS 转换、星表匹配、测光校准、宇宙学距离计算或 field context 调用改成静态假数据、手写结果、本地伪造响应或直接复制旧输出后微调。
- 不要通过删功能规避问题，例如跳过 FITS WCS、跳过时间标准化、跳过交叉匹配、跳过移动天体排除、跳过测光误差传播、跳过 field context 服务，或把所有候选体都标成可报告或不可报告。
- 不要修改输入数据、下游服务、依赖配置或环境基线。
- 不要假设像素坐标就是天球坐标；不要把角秒阈值当作角度阈值；不要忽略 FITS HDU、WCS frame、观测时间尺度、滤光片或曝光信息。
- 不要要求 solve 时访问互联网；正式结果应完全由容器内数据和本地服务生成。
- 可以自由增加日志、辅助脚本或局部重构；最终必须通过正式入口重新生成交付物。
