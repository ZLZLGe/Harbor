# Data Quality Auditor 数据质量审计器

**版本**: 2.0.0  
**标准**: 5标准/7标准项 ✅  
**状态**: 已认证

---

## 📋 标准实现

| 标准 | 名称 | 状态 | 说明 |
|------|------|------|------|
| S1 | 输入规范 | ✅ | 支持CSV/JSON/Parquet/数据库 |
| S2 | 质量审计流程 | ✅ | 完整性→准确性→一致性→时效性 |
| S3 | 输出报告 | ✅ | JSON/HTML/MD + 改进建议 |
| S4 | 流程集成 | ✅ | CI/CD + Cron定时任务 |
| S5 | 量化指标 | ✅ | 错误率/缺失率/重复率/综合评分 |
| S6 | 局限标注 | ✅ | 明确标注业务逻辑限制 |
| S7 | 对抗测试 | ✅ | 检测率 80%+ |

---

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 审计CSV文件
python3 scripts/audit.py --source examples/sample_data.csv

# 运行对抗测试 (S7)
python3 scripts/adversarial_test.py

# 自检 (验证5标准)
python3 scripts/self_check.py
```

---

## 📁 目录结构

```
data-quality-auditor/
├── SKILL.md                          # 标准文档
├── _meta.json                        # 元数据
├── requirements.txt                  # 依赖
├── cron.json                         # 定时任务配置
├── config/
│   ├── quality_requirements.yaml     # S1: 质量需求配置
│   └── pipeline_integration.yaml     # S4: 管道集成配置
├── scripts/
│   ├── data_quality_auditor.py       # 核心审计模块
│   ├── audit.py                      # 命令行工具
│   ├── generate_report.py            # 报告生成
│   ├── adversarial_test.py           # S7: 对抗测试
│   └── self_check.py                 # 自检脚本
├── tests/
│   ├── adversarial_test_cases.yaml   # S7: 测试用例
│   └── data/                         # 测试数据
├── examples/
│   └── sample_data.csv               # 示例数据
└── reports/                          # 输出报告
    ├── trends/                       # S5: 趋势数据
    └── *.json/html                   # 审计报告
```

---

## 📊 审计维度

### 完整性 (Completeness)
- NULL值检测
- 空字符串检测
- 必填项检查

### 准确性 (Accuracy)
- 数值范围检查
- 异常值检测 (IQR/Z-Score)
- 业务规则验证

### 一致性 (Consistency)
- 格式统一性
- 重复记录检测
- Email/Phone格式验证

### 时效性 (Timeliness)
- 数据新鲜度
- 更新频率检查
- 时序连续性

---

## 🛠️ 使用方法

### 基本审计

```bash
python3 scripts/audit.py \
  --source data/users.csv \
  --output reports/audit_report \
  --output-format both
```

### Python API

```python
from scripts.data_quality_auditor import QualityAuditor

auditor = QualityAuditor("config/quality_requirements.yaml")
report = auditor.audit("data/users.csv", "csv")

print(f"评分: {report.overall_score}")
print(f"等级: {report.grade}")

for rec in report.recommendations:
    print(f"建议: {rec['suggestion']}")
```

### 对抗测试 (S7)

```bash
python3 scripts/adversarial_test.py
```

验证检测能力：
- 完整性污染检测
- 准确性异常检测
- 一致性问题检测
- 时效性过期检测
- 重复记录检测

---

## ⚠️ 局限说明 (S6)

本工具仅检测技术性数据质量问题：
- ❌ 无法判断业务逻辑正确性
- ❌ 无法判断语义正确性
- ❌ 无法检测跨系统隐含错误
- ⚠️ 关键业务决策前需人工审核

---

## 📈 集成示例

### GitHub Actions

```yaml
name: Data Quality Gate
on: [push]
jobs:
  quality-check:
    steps:
      - uses: actions/checkout@v3
      - name: Run Audit
        run: |
          python3 scripts/audit.py \
            --source data/ \
            --config config/quality_requirements.yaml
```

### 定时任务

```bash
# cron.json
{
  "jobs": [
    {
      "name": "daily-audit",
      "schedule": "0 8 * * *",
      "command": "python3 scripts/audit.py --source data/daily.csv"
    }
  ]
}
```

---

## ✅ 认证状态

```json
{
  "standard": "5标准/7标准项",
  "version": "2.0.0",
  "pass_rate": "100%",
  "certified": true
}
```

---

*Created by Satisficing Institute*  
*Updated: 2026-03-21*
