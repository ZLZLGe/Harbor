# perSkill_test 缺口盘点报告

## 快照信息

- 生成时间: `2026-03-24T21:06:59+08:00`
- source root: `/home/levi/Harbor/tasks_library/skillsbench/tasks`
- target root: `/home/levi/Harbor/tasks_library/perSkill_test`
- 统计口径: 每个 shipped skill 目标 task 数固定为 `4`；`>= 4` 视为已跑满，`< 4` 视为缺口。

## 总览

- source task 总数: `87`
- perSkill_test 中已出现的 source task 数: `70`
- 顶层完全未出现的 source task 数: `17`
- 未跑满 4 个 task 的 skill 数: `141`
- 被忽略的异常目录数: `5`

## 完全未出现的 source task

| source_task_id | expected_skills | expected_task_count |
| --- | --- | --- |
| enterprise-information-search | enterprise-artifact-search | 4 |
| gh-repo-analytics | gh-cli | 4 |
| latex-formula-extraction | marker, pdf | 8 |
| lean4-proof | lean4-memories, lean4-theorem-proving | 8 |
| pg-essay-to-audiobook | audiobook, elevenlabs-tts, gtts, openai-tts | 16 |
| quantum-numerical-simulation | qutip | 4 |
| react-performance-debugging | browser-testing, react-best-practices | 8 |
| shock-analysis-demand | xlsx | 4 |
| simpo-code-reproduction | nlp-research-repo-package-installment, pdf | 8 |
| travel-planning | search-accommodations, search-attractions, search-cities, search-driving-distance, search-flights, search-restaurants | 24 |
| trend-anomaly-causal-inference | data_cleaning, did_causal_analysis, feature_engineering, time_series_anomaly_detection | 16 |
| video-filler-word-remover | ffmpeg-video-editing, filler-word-processing, whisper-transcription | 12 |
| video-silence-remover | audio-extractor, energy-calculator, pause-detector, report-generator, segment-combiner, silence-detector, video-processor | 28 |
| video-tutorial-indexer | speech-to-text | 4 |
| virtualhome-agent-planning | pddl-skills | 4 |
| weighted-gdp-calc | xlsx | 4 |
| xlsx-recover-data | data-reconciliation, xlsx | 8 |

## 未跑满 4 个 task 的 skill

| source_task_id | skill_dir | actual_task_count | missing_task_count | existing_task_ids |
| --- | --- | --- | --- | --- |
| dynamic-object-aware-egomotion | egomotion-estimation | 0 | 4 | - |
| earthquake-phase-association | licenses | 0 | 4 | - |
| earthquake-phase-association | seisbench-model-api | 0 | 4 | - |
| energy-market-pricing | power-flow-data | 0 | 4 | - |
| exoplanet-detection-period | lomb-scargle-periodogram | 0 | 4 | - |
| exoplanet-detection-period | transit-least-squares | 0 | 4 | - |
| fix-build-agentops | temporal-python-testing | 0 | 4 | - |
| fix-build-google-auto | maven-dependency-management | 0 | 4 | - |
| fix-erlang-ssh-cve | erlang-concurrency | 0 | 4 | - |
| fix-erlang-ssh-cve | erlang-distribution | 0 | 4 | - |
| fix-erlang-ssh-cve | senior-security | 0 | 4 | - |
| fix-visual-stability | browser-testing | 0 | 4 | - |
| lake-warming-attribution | contribution-analysis | 0 | 4 | - |
| mario-coin-counting | image_editing | 0 | 4 | - |
| mhc-layer-impl | modal-gpu | 0 | 4 | - |
| multilingual-video-dubbing | ffmpeg-audio-processing | 0 | 4 | - |
| multilingual-video-dubbing | text-to-speech | 0 | 4 | - |
| organize-messy-files | pdf | 0 | 4 | - |
| organize-messy-files | pptx | 0 | 4 | - |
| pedestrian-traffic-counting | gemini-count-in-video | 0 | 4 | - |
| python-scala-translation | python-scala-collections | 0 | 4 | - |
| python-scala-translation | python-scala-syntax-mapping | 0 | 4 | - |
| r2r-mpc-control | finite-horizon-lqr | 0 | 4 | - |
| r2r-mpc-control | integral-action-design | 0 | 4 | - |
| r2r-mpc-control | mpc-horizon-tuning | 0 | 4 | - |
| scheduling-email-assistant | gmail-skill | 0 | 4 | - |
| scheduling-email-assistant | google-calendar-skill | 0 | 4 | - |
| sec-financial-report | 13f-analyzer | 0 | 4 | - |
| seismic-phase-picking | licenses | 0 | 4 | - |
| seismic-phase-picking | obspy-datacenter-client | 0 | 4 | - |
| seismic-phase-picking | seisbench-model-api | 0 | 4 | - |
| setup-fuzzing-py | fuzzing-python | 0 | 4 | - |
| setup-fuzzing-py | setup-env | 0 | 4 | - |
| speaker-diarization-subtitles | automatic-speech-recognition | 0 | 4 | - |
| speaker-diarization-subtitles | multimodal-fusion | 0 | 4 | - |
| speaker-diarization-subtitles | voice-activity-detection | 0 | 4 | - |
| spring-boot-jakarta-migration | jakarta-namespace | 0 | 4 | - |
| syzkaller-ppdev-syzlang | syzlang-ioctl-basics | 0 | 4 | - |
| threejs-to-obj | threejs | 0 | 4 | - |
| data-to-d3 | d3-visualization | 1 | 3 | trail-analysis-d3-visualization-transfer-elevation-profile |
| dynamic-object-aware-egomotion | dyn-object-masks | 1 | 3 | microscope-stage-dyn-object-masks-transfer-motile-cells |
| earthquake-phase-association | gamma-phase-associator | 1 | 3 | volcano-swarm-gamma-phase-associator-transfer-geojson |
| energy-ac-optimal-power-flow | casadi-ipopt-nlp | 1 | 3 | battery-model-casadi-ipopt-nlp-transfer-parameter-fit |
| exceltable-in-ppt | xlsx | 1 | 3 | exchange-matrix-xlsx-similar-note-update |
| find-topk-similiar-chemicals | pubchem-database | 1 | 3 | vendor-analogs-pubchem-database-similar-catalog-ranking |
| fix-build-google-auto | maven-build-lifecycle | 1 | 3 | adapt-maven-build-lifecycle-transfer-profile-package-assets |
| fix-visual-stability | react-best-practices | 1 | 3 | smooth-precall-lobby-react-best-practices-transfer-session |
| fix-visual-stability | web-interface-guidelines | 1 | 3 | analytics-workspace-web-interface-guidelines-transfer-virtualized-panels |
| flood-risk-analysis | usgs-data-download | 1 | 3 | dam-ops-usgs-data-download-transfer-station-metadata-audit |
| glm-lake-mendota | glm-basics | 1 | 3 | temperate-reservoir-glm-basics-similar-profile-calibration |
| glm-lake-mendota | glm-calibration | 1 | 3 | temperate-dimictic-glm-calibration-similar-multi-year-profile-fit |
| glm-lake-mendota | glm-output | 1 | 3 | stratification-glm-output-transfer-thermocline-tracking |
| invoice-fraud-detection | xlsx | 1 | 3 | event-ops-xlsx-transfer-shift-assignment |
| jpg-ocr-stat | image-ocr | 1 | 3 | menu-board-image-ocr-transfer-ranking |
| mario-coin-counting | object_counter | 1 | 3 | form-stamp-check-object_counter-object-counter-transfer-paper-trail |
| mhc-layer-impl | mhc-algorithm | 1 | 3 | grid-forecast-mhc-algorithm-transfer-load-horizon |
| mhc-layer-impl | nanogpt-training | 1 | 3 | resume-nanogpt-training-transfer-checkpoint-parity |
| multilingual-video-dubbing | ffmpeg-video-editing | 1 | 3 | digital-signage-loop-ffmpeg-video-editing-transfer-storefront |
| organize-messy-files | docx | 1 | 3 | archive-briefs-docx-similar-subject-inventory |
| organize-messy-files | file-organizer | 1 | 3 | seminar-archive-file-organizer-similar-reading-room |
| paper-anonymizer | academic-pdf-redaction | 1 | 3 | literary-contest-academic-pdf-redaction-transfer-manuscript |
| paper-anonymizer | pdf | 1 | 3 | litigation-binder-pdf-transfer-exhibit-assembly |
| python-scala-translation | python-scala-libraries | 1 | 3 | audit-event-python-scala-libraries-similar-jsonl-normalizer |
| reserves-at-risk-calc | xlsx | 1 | 3 | scholarship-audit-xlsx-transfer-awards |
| spring-boot-jakarta-migration | spring-boot-migration | 1 | 3 | customer-profiles-spring-boot-migration-similar-java21-upgrade |
| suricata-custom-exfil | pcap-triage-tshark | 1 | 3 | dns-pcap-triage-tshark-transfer-beacon-clusters |
| suricata-custom-exfil | suricata-offline-evejson | 1 | 3 | harbor-suricata-offline-evejson-transfer-smtp-finance-dropbox |
| suricata-custom-exfil | suricata-rules-basics | 1 | 3 | tcp-suricata-rules-basics-transfer-backup-sync |
| syzkaller-ppdev-syzlang | syz-extract-constants | 1 | 3 | uinput-syz-extract-constants-similar-ioctl-matrix |
| syzkaller-ppdev-syzlang | syzkaller-build-loop | 1 | 3 | watchdog-syzkaller-build-loop-similar-char-device-coverage |
| civ6-adjacency-optimizer | hex-grid-spatial | 2 | 2 | plague-cordon-hex-grid-spatial-transfer-containment-ring, wildfire-relay-hex-grid-spatial-transfer-coverage-network |
| dapt-intrusion-detection | threat-detection | 2 | 2 | campus-soc-threat-detection-similar-threat-verdict, kubernetes-egress-threat-detection-transfer-pod-triage |
| energy-market-pricing | economic-dispatch | 2 | 2 | grid-reserve-economic-dispatch-similar-fuel-bid-shock, mine-site-economic-dispatch-transfer-load-breakpoints |
| exoplanet-detection-period | box-least-squares | 2 | 2 | cheops-transit-box-least-squares-similar-period, eclipsing-binary-box-least-squares-transfer-orbit |
| fix-build-agentops | testing-python | 2 | 2 | csv-metrics-testing-python-transfer-parameterized-validation, repair-normalizer-testing-python-similar-pytest-regression |
| fix-build-google-auto | maven-plugin-configuration | 2 | 2 | auto-compiler-maven-plugin-configuration-similar-annotation-processors, release-docs-maven-plugin-configuration-transfer-javadoc-gating |
| fix-druid-loophole-cve | jackson-security | 2 | 2 | ingestion-preview-jackson-security-similar-empty-key-guard, plugin-manifest-jackson-security-transfer-polymorphic-type-lockdown |
| fix-druid-loophole-cve | senior-java | 2 | 2 | order-analytics-senior-java-transfer-query-collapse, report-preview-senior-java-similar-expression-bypass |
| fix-erlang-ssh-cve | erlang-otp-behaviors | 2 | 2 | lease-broker-erlang-otp-behaviors-transfer-expiry-ack, pipeline-supervisor-erlang-otp-behaviors-transfer-restart-cascade |
| flink-query | pdf | 2 | 2 | cluster-schema-pdf-similar-eventspec, submission-packet-pdf-transfer-assembly |
| gravitational-wave-detection | matched-filtering | 2 | 2 | bns-alert-matched-filtering-transfer-early-warning, compact-binary-matched-filtering-similar-template-bank-scan |
| grid-dispatch-operator | dc-power-flow | 2 | 2 | offshore-export-dc-power-flow-transfer-curtailment-balance, regional-redispatch-dc-power-flow-similar-maintenance-window |
| invoice-fraud-detection | pdf | 2 | 2 | board-book-pdf-transfer-assembly, enrollment-form-pdf-transfer-completion-packet |
| jpg-ocr-stat | openai-vision | 2 | 2 | construction-site-openai-vision-transfer-safety-delta, greenhouse-frames-openai-vision-transfer-growth-timeline |
| manufacturing-equipment-maintenance | reflow_machine_maintenance_guidance | 2 | 2 | maintenance-backlog-reflow_machine_maintenance_guidance-reflow-machine-maintenance-guidance-transfer-priority, quality-escape-reflow_machine_maintenance_guidance-reflow-machine-maintenance-guidance-transfer-containment |
| parallel-tfidf-search | python-parallelization | 2 | 2 | endpoint-probe-python-parallelization-transfer-async-audit, photo-dedupe-python-parallelization-transfer-phash-clusters |
| pdf-excel-diff | xlsx | 2 | 2 | clinic-ops-xlsx-transfer-shift-conflict-audit, employee-records-xlsx-similar-change-audit |
| pedestrian-traffic-counting | gemini-video-understanding | 2 | 2 | docksafe-gemini-video-understanding-transfer-near-miss-timeline, lecture-gemini-video-understanding-transfer-structured-chapters |
| pedestrian-traffic-counting | gpt-multimodal | 2 | 2 | rainy-sidewalk-gpt-multimodal-similar-umbrella-walkers, seedling-trays-gpt-multimodal-transfer-germination-map |
| powerlifting-coef-calc | xlsx | 2 | 2 | course-grades-xlsx-transfer-weighted-report, regatta-points-xlsx-similar-team-leaderboard |
| protein-expression-analysis | xlsx | 2 | 2 | campus-energy-xlsx-transfer-tariff-variance, metabolite-panel-xlsx-similar-treatment-shifts |
| python-scala-translation | python-scala-idioms | 2 | 2 | alert-routing-python-scala-idioms-transfer-escalation-policy, message-canonicalizer-python-scala-idioms-similar-pipeline |
| sales-pivot-analysis | xlsx | 2 | 2 | retail-margin-xlsx-similar-pivot-report, warehouse-aging-xlsx-transfer-restock-priorities |
| seismic-phase-picking | seismic-picker-selection | 2 | 2 | quarry-repeaters-seismic-picker-selection-transfer-template-refinement, regional-aftershock-seismic-picker-selection-similar-mixed-network |
| setup-fuzzing-py | discover-important-function | 2 | 2 | archive-parser-discover-important-function-similar-fuzz-notes, packaging-backend-discover-important-function-transfer-build-boundaries |
| spring-boot-jakarta-migration | spring-security-6 | 2 | 2 | approval-workflow-spring-security-6-transfer-method-security, member-directory-spring-security-6-similar-access-rules |
| threejs-structure-parser | obj-exporter | 2 | 2 | desk-lamp-obj-exporter-similar-segment-bundles, solar-array-obj-exporter-transfer-variant-pack |
| threejs-to-obj | obj-exporter | 2 | 2 | desk-lamp-obj-exporter-similar-blender-handoff, molecular-lattice-obj-exporter-transfer-science-mesh |
| adaptive-cruise-control | pid-controller | 3 | 1 | drone-altitude-hold-pid-controller-transfer-hover-window, greenhouse-climate-pid-controller-transfer-temperature-zone, water-tank-level-pid-controller-transfer-pump-balance |
| dynamic-object-aware-egomotion | output-validation | 3 | 1 | cell-migration-output-validation-transfer-confluence-watch, harbor-radar-output-validation-transfer-vessel-sweeps, wildfire-timelapse-output-validation-transfer-front-progression |
| dynamic-object-aware-egomotion | sampling-and-indexing | 3 | 1 | assembly-line-sampling-and-indexing-transfer-state-spans, atrium-egomotion-sampling-and-indexing-similar-crowd-mask-alignment, intersection-queue-sampling-and-indexing-transfer-vehicle-counts |
| earthquake-phase-association | obspy-data-api | 3 | 1 | aftershock-bulletin-obspy-data-api-similar-quakeml-packet, harbor-hydrophone-obspy-data-api-transfer-deployment-inventory, volcano-waveform-qc-obspy-data-api-transfer-gap-report |
| earthquake-phase-association | seismic-picker-selection | 3 | 1 | glacier-icequake-seismic-picker-selection-transfer-mixed-sensor-catalog, repeater-search-seismic-picker-selection-transfer-template-correlation, strong-motion-seismic-picker-selection-transfer-rapid-alert-windows |
| econ-detrending-correlation | timeseries-detrending | 3 | 1 | demography-timeseries-detrending-transfer-fertility-trough, energy-demand-timeseries-detrending-transfer-power-output-volatility, labor-rates-timeseries-detrending-transfer-beveridge-cycle |
| energy-market-pricing | locational-marginal-prices | 3 | 1 | data-center-siting-locational-marginal-prices-transfer-interconnection-choice, heatwave-derating-locational-marginal-prices-transfer-price-islands, reserve-stress-locational-marginal-prices-transfer-scarcity-pricing |
| exceltable-in-ppt | pptx | 3 | 1 | deckops-pptx-similar-embedded-forecast-refresh, deckops-pptx-transfer-executive-subset-rebuild, deckops-pptx-transfer-review-comments-injection |
| exoplanet-detection-period | exoplanet-workflows | 3 | 1 | alias-check-exoplanet-workflows-transfer-true-period, ground-campaign-exoplanet-workflows-transfer-ephemeris, multi-planet-exoplanet-workflows-transfer-outer-planet |
| exoplanet-detection-period | light-curve-preprocessing | 3 | 1 | asteroid-nightly-drift-light-curve-preprocessing-transfer-cleaned-series, quasar-season-offset-light-curve-preprocessing-transfer-rms, tess-known-transit-light-curve-preprocessing-similar-depth |
| find-topk-similiar-chemicals | pdf | 3 | 1 | compound-property-neighbors-pdf-similar-ranking, equipment-checkout-pdf-transfer-form, invoice-reconciliation-pdf-transfer-ledger |
| fix-erlang-ssh-cve | find-bugs | 3 | 1 | go-gateway-find-bugs-transfer-rate-limit-race, otp-ssh-find-bugs-similar-channel-state-audit, python-backup-find-bugs-transfer-tar-symlink |
| fix-erlang-ssh-cve | ssh-penetration-testing | 3 | 1 | bastion-ssh-penetration-testing-transfer-remote-forward-acl, policy-ssh-penetration-testing-transfer-weak-algorithm-audit, sprayguard-ssh-penetration-testing-transfer-password-spray-throttle |
| flink-query | senior-data-engineer | 3 | 1 | campaign-attribution-senior-data-engineer-transfer-lag-audit, cdc-quality-senior-data-engineer-transfer-disorder-report, pipeline-closeout-senior-data-engineer-transfer-sla-rollup |
| gravitational-wave-detection | conditioning | 3 | 1 | commissioning-baseline-conditioning-transfer-quiet-segment, hydrophone-transient-conditioning-transfer-window-qc, observatory-strain-conditioning-similar-candidate-prep |
| grid-dispatch-operator | economic-dispatch | 3 | 1 | balancing-market-economic-dispatch-similar-reserve-clearing, campus-cooling-economic-dispatch-transfer-chiller-plant, district-heating-economic-dispatch-transfer-steam-reserve |
| hvac-control | excitation-signal-design | 3 | 1 | conveyor-motor-excitation-signal-design-transfer-speed-fit, incubator-heater-excitation-signal-design-similar-characterization, reservoir-valve-excitation-signal-design-transfer-level-fit |
| hvac-control | imc-tuning-rules | 3 | 1 | brine-mixer-imc-tuning-rules-transfer-concentration, incubator-imc-tuning-rules-similar-recovery, tank-level-imc-tuning-rules-transfer-balance |
| jpg-ocr-stat | pdf | 3 | 1 | audit-pdf-transfer-packet-rebuild, intake-pdf-transfer-form-packet, statement-pdf-transfer-metrics-rollup |
| jpg-ocr-stat | video-frame-extraction | 3 | 1 | assembly-line-video-frame-extraction-transfer-cap-audit, lecture-screen-video-frame-extraction-transfer-slide-index, traffic-signal-video-frame-extraction-transfer-phase-counts |
| jpg-ocr-stat | xlsx | 3 | 1 | receipt-text-xlsx-similar-rollup, volunteer-roster-xlsx-transfer-planning, warehouse-kpi-xlsx-transfer-dashboard |
| lab-unit-harmonization | lab-unit-harmonization | 3 | 1 | icu-lab-unit-harmonization-transfer-blood-gas-stream, nephrology-lab-unit-harmonization-similar-dialysis-followup, screening-lab-unit-harmonization-transfer-wellness-batch |
| manufacturing-equipment-maintenance | reflow-profile-compliance-toolkit | 3 | 1 | cure-oven-reflow-profile-compliance-toolkit-transfer-epoxy-batch-disposition, npi-reflow-profile-compliance-toolkit-similar-first-article-release, wave-solder-reflow-profile-compliance-toolkit-transfer-through-hole-audit |
| mario-coin-counting | ffmpeg | 3 | 1 | archive-ffmpeg-transfer-frame-hash-index, demo-ffmpeg-similar-storyboard-manifest, lecture-ffmpeg-transfer-slide-gallery |
| mars-clouds-clustering | parallel-processing | 3 | 1 | exoplanet-transit-search-parallel-processing-transfer-gridscan, lunar-boulder-consensus-parallel-processing-similar-sweep, port-inventory-simulator-parallel-processing-transfer-montecarlo |
| multilingual-video-dubbing | ffmpeg-format-conversion | 3 | 1 | ivr-prompt-ffmpeg-format-conversion-transfer-telephony, localized-lesson-ffmpeg-format-conversion-similar-delivery, podcast-preview-ffmpeg-format-conversion-transfer-opus-release |
| multilingual-video-dubbing | ffmpeg-media-info | 3 | 1 | bodycam-evidence-ffmpeg-media-info-transfer-clip-triage, broadcast-ad-ffmpeg-media-info-transfer-ingest-gate, dub-delivery-ffmpeg-media-info-similar-qc-report |
| multilingual-video-dubbing | ffmpeg-video-filters | 3 | 1 | coaching-ffmpeg-video-filters-transfer-slow-motion-replay, localization-ffmpeg-video-filters-similar-dubbed-visual-cleanup, security-ffmpeg-video-filters-transfer-privacy-redaction |
| offer-letter-generator | docx | 3 | 1 | festival-program-docx-transfer-run-of-show, patient-discharge-docx-transfer-home-care-packet, site-audit-docx-transfer-corrective-report |
| parallel-tfidf-search | memory-optimization | 3 | 1 | catalog-ndjson-memory-optimization-transfer-deduper, streaming-tfidf-memory-optimization-similar-index-builder, telemetry-csv-memory-optimization-transfer-window-stats |
| parallel-tfidf-search | workload-balancing | 3 | 1 | archive-checksum-workload-balancing-transfer-manifest, mandelbrot-tiles-workload-balancing-transfer-renderer, skewed-ngram-search-workload-balancing-similar-pipeline |
| pddl-tpp-planning | pddl-skills | 3 | 1 | datacenter-failover-pddl-skills-transfer-service-recovery, observatory-ops-pddl-skills-transfer-night-schedule, wetlab-assay-pddl-skills-transfer-assay-pipeline |
| pedestrian-traffic-counting | video-frame-extraction | 3 | 1 | gauge-inspection-video-frame-extraction-transfer-peak-readings, lecture-slides-video-frame-extraction-transfer-deck-keyframes, sidewalk-peak-video-frame-extraction-similar-crowd-hotspots |
| powerlifting-coef-calc | senior-data-scientist | 3 | 1 | grocery-forecasting-senior-data-scientist-transfer-seasonal-reorder, hospital-triage-senior-data-scientist-transfer-readmission-risk, retail-abtest-senior-data-scientist-transfer-campaign-lift |
| pptx-reference-formatting | pptx | 3 | 1 | conference-session-pptx-similar-index, design-review-pptx-transfer-notes-comments, onboarding-template-pptx-transfer-brand-remix |
| python-scala-translation | python-scala-functional | 3 | 1 | record-canonicalizer-python-scala-functional-similar-mixed-input-pipeline, shift-windows-python-scala-functional-transfer-recurring-scheduler, survey-branching-python-scala-functional-transfer-decision-graph |
| python-scala-translation | python-scala-oop | 3 | 1 | booking-policies-python-scala-oop-transfer-pricing, combat-engine-python-scala-oop-transfer-arena, rubric-scorer-python-scala-oop-transfer-evaluation |
| sales-pivot-analysis | pdf | 3 | 1 | expense-audit-pdf-transfer-policy-exceptions, maintenance-schedule-pdf-transfer-downtime-calendar, regional-sales-pdf-similar-quarterly-rollup |
| sec-financial-report | fuzzy-name-search | 3 | 1 | hospital-claims-fuzzy-name-search-transfer-provider-reconciliation, media-rights-fuzzy-name-search-transfer-title-royalty-recon, procurement-audit-fuzzy-name-search-transfer-vendor-concentration |
| seismic-phase-picking | obspy-data-api | 3 | 1 | aftershock-obspy-data-api-similar-arrival-windows, quarry-obspy-data-api-transfer-blast-manifest, volcano-obspy-data-api-transfer-tremor-coverage |
| shock-analysis-supply | xlsx | 3 | 1 | reservoir-planning-xlsx-transfer-drought-resilience, tourism-demand-xlsx-similar-capacity-shock, warehouse-service-xlsx-transfer-buffer-stock |
| spring-boot-jakarta-migration | hibernate-upgrade | 3 | 1 | reconciliation-batch-hibernate-upgrade-transfer-criteria-search, sample-archive-hibernate-upgrade-transfer-sequence-enum-mapping, shipment-events-hibernate-upgrade-transfer-json-mapping |
| threejs-structure-parser | threejs | 3 | 1 | exhibition-hall-threejs-transfer-zone-bounds, stadium-lighting-threejs-transfer-instanced-inventory, wind-turbine-threejs-similar-part-export |

## 忽略的异常目录

异常目录数量: `5`

| source_task_id | child_dir | reason |
| --- | --- | --- |
| dapt-intrusion-detection | cloud-edge-threat-detection-tran__CYbrwys | missing task.toml |
| dapt-intrusion-detection | iot-fleet-threat-detection-trans__f7oCGFk | missing task.toml |
| dapt-intrusion-detection | isp-abuse-threat-detection-trans__Q4VC8iP | missing task.toml |
| dapt-intrusion-detection | traffic-windows-threat-detection__grHPLju | missing task.toml |
| dapt-intrusion-detection | vpn-gateway-threat-detection-tra__HXHnxga | missing task.toml |

## 统计说明

- 本报告按 source task 的 shipped skills 统计。
- 每个 shipped skill 的目标数量固定按 `4` 计算。
- `actual_task_count > 4` 不算缺口，不会在本报告中单列问题。
- `perSkill_test` 顶层的 `jobs` 目录已忽略。
- 异常目录不会计入任何 skill 的有效 task 数。

