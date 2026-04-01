#!/usr/bin/env python3
"""
generate_report.py - 报告生成工具
从审计结果生成各种格式的报告
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data_quality_auditor import QualityAuditor, QualityReport, DimensionScore, QualityIssue


def load_report(report_path: str) -> dict:
    """加载审计报告"""
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_markdown_report(report_data: dict, output_path: str):
    """生成Markdown报告"""
    md_content = f"""# 数据质量审计报告

## 基本信息

| 项目 | 值 |
|------|-----|
| 报告ID | {report_data['report_id']} |
| 生成时间 | {report_data['generated_at']} |
| 数据集 | {report_data['dataset_name']} |
| 记录数 | {report_data['record_count']} |

## 综合评分

**{report_data['overall_score']} 分** | 等级: **{report_data['grade']}**

## 维度评分

| 维度 | 得分 | 权重 | 问题数 |
|------|------|------|--------|
"""
    
    for name, dim in report_data['dimensions'].items():
        md_content += f"| {name} | {dim['score']:.2f} | {dim['weight']} | {len(dim['issues'])} |\n"
    
    md_content += "\n## 详细问题\n\n"
    
    for name, dim in report_data['dimensions'].items():
        if dim['issues']:
            md_content += f"### {name}\n\n"
            for issue in dim['issues']:
                severity_icon = "🔴" if issue['severity'] == 'critical' else "🟡"
                md_content += f"- {severity_icon} **{issue['field']}**: {issue['description']}\n"
                md_content += f"  - 影响记录: {issue['affected_count']}\n"
                md_content += f"  - 建议: {issue['suggestion']}\n\n"
    
    md_content += "\n## 改进建议\n\n"
    
    for i, rec in enumerate(report_data['recommendations'][:10], 1):
        priority_icon = "🔴" if rec['priority'] == 'high' else "🟡"
        md_content += f"{i}. {priority_icon} **{rec['field']}**: {rec['suggestion']}\n"
    
    md_content += "\n## 局限说明 (S6)\n\n"
    for limit in report_data['limitations']:
        md_content += f"- ⚠️ {limit}\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✅ Markdown报告已生成: {output_path}")


def generate_csv_metrics(report_data: dict, output_path: str):
    """生成CSV格式的指标文件"""
    import csv
    
    # 计算各维度指标
    rows = []
    total_issues = sum(len(dim['issues']) for dim in report_data['dimensions'].values())
    
    for name, dim in report_data['dimensions'].items():
        critical_count = sum(1 for i in dim['issues'] if i['severity'] == 'critical')
        warning_count = sum(1 for i in dim['issues'] if i['severity'] == 'warning')
        
        rows.append({
            'dimension': name,
            'score': dim['score'],
            'weight': dim['weight'],
            'total_issues': len(dim['issues']),
            'critical_issues': critical_count,
            'warning_issues': warning_count,
            'grade': report_data['grade']
        })
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ CSV指标已生成: {output_path}")


def generate_trend_data(report_data: dict, trends_dir: str = "reports/trends"):
    """生成趋势数据文件"""
    from datetime import datetime
    import csv
    import os
    
    Path(trends_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d')
    
    # 更新总体趋势
    trend_file = Path(trends_dir) / "overall_score_trend.csv"
    
    # 读取现有数据或创建新文件
    existing_data = []
    if trend_file.exists():
        with open(trend_file, 'r') as f:
            reader = csv.DictReader(f)
            existing_data = list(reader)
    
    # 添加新记录
    existing_data.append({
        'date': timestamp,
        'dataset': report_data['dataset_name'],
        'overall_score': report_data['overall_score'],
        'grade': report_data['grade'],
        'record_count': report_data['record_count']
    })
    
    # 保留最近30天
    existing_data = existing_data[-30:]
    
    with open(trend_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'dataset', 'overall_score', 'grade', 'record_count'])
        writer.writeheader()
        writer.writerows(existing_data)
    
    print(f"✅ 趋势数据已更新: {trend_file}")


def main():
    parser = argparse.ArgumentParser(description="生成数据质量报告")
    parser.add_argument('--input', '-i', required=True, help='输入的JSON报告文件')
    parser.add_argument('--format', '-f', default='markdown',
                        choices=['markdown', 'html', 'csv', 'all'],
                        help='输出格式')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--update-trends', action='store_true',
                        help='更新趋势数据')
    
    args = parser.parse_args()
    
    # 加载报告
    report_data = load_report(args.input)
    
    # 确定输出路径
    base_path = args.output or f"reports/{report_data['dataset_name']}_report"
    
    # 生成各种格式的报告
    if args.format in ['markdown', 'all']:
        generate_markdown_report(report_data, f"{base_path}.md")
    
    if args.format in ['csv', 'all']:
        generate_csv_metrics(report_data, f"{base_path}_metrics.csv")
    
    if args.format in ['html', 'all']:
        # 使用auditor生成HTML
        auditor = QualityAuditor()
        from data_quality_auditor import QualityReport, DimensionScore, QualityIssue
        
        # 重建报告对象
        report = QualityReport(
            report_id=report_data['report_id'],
            generated_at=report_data['generated_at'],
            dataset_name=report_data['dataset_name'],
            record_count=report_data['record_count'],
            overall_score=report_data['overall_score'],
            grade=report_data['grade'],
            dimensions={},
            recommendations=report_data['recommendations'],
            limitations=report_data['limitations']
        )
        auditor._generate_html_report(report, f"{base_path}.html")
        print(f"✅ HTML报告已生成: {base_path}.html")
    
    # 更新趋势
    if args.update_trends:
        generate_trend_data(report_data)
    
    print("\n✅ 报告生成完成")


if __name__ == "__main__":
    main()
