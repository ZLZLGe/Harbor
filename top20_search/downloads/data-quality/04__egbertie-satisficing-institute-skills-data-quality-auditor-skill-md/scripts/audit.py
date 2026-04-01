#!/usr/bin/env python3
"""
audit.py - 数据质量审计命令行工具
S1-S7 全标准支持

Usage:
    python3 audit.py --source data.csv --format csv
    python3 audit.py --source "postgresql://localhost/db" --table users --config config.yaml
    python3 audit.py --adversarial-test  # 运行对抗测试
"""

import argparse
import sys
import json
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from data_quality_auditor import QualityAuditor, run_adversarial_test


def main():
    parser = argparse.ArgumentParser(
        description="数据质量审计器 V2.0.0 - 5标准/7标准项",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 审计CSV文件
  python3 audit.py --source data/users.csv
  
  # 使用自定义配置
  python3 audit.py --source data.csv --config config/quality_requirements.yaml
  
  # 运行对抗测试 (S7)
  python3 audit.py --adversarial-test
  
  # 生成HTML报告
  python3 audit.py --source data.csv --output-format html --output report.html
        """
    )
    
    parser.add_argument('--source', '-s', type=str,
                        help='数据源路径或连接字符串')
    parser.add_argument('--format', '-f', type=str, default='auto',
                        choices=['auto', 'csv', 'json', 'parquet', 'sqlite'],
                        help='数据源格式 (默认: auto)')
    parser.add_argument('--table', '-t', type=str,
                        help='数据库表名')
    parser.add_argument('--config', '-c', type=str,
                        default='config/quality_requirements.yaml',
                        help='配置文件路径')
    parser.add_argument('--output', '-o', type=str,
                        default='reports/quality_report',
                        help='输出文件路径 (不含扩展名)')
    parser.add_argument('--output-format', type=str, default='json',
                        choices=['json', 'html', 'both'],
                        help='输出格式')
    parser.add_argument('--adversarial-test', action='store_true',
                        help='运行对抗测试 (S7)')
    parser.add_argument('--dataset-name', '-n', type=str,
                        help='数据集名称')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出')
    
    args = parser.parse_args()
    
    # 初始化审计器
    auditor = QualityAuditor(args.config)
    
    if args.adversarial_test:
        # S7: 运行对抗测试
        results = run_adversarial_test(auditor)
        
        # 保存报告
        output_base = args.output
        auditor.save_report(results['report'], f"{output_base}_adversarial.json", 'json')
        auditor.save_report(results['report'], f"{output_base}_adversarial.html", 'html')
        
        print(f"\n📄 报告已保存:")
        print(f"   JSON: {output_base}_adversarial.json")
        print(f"   HTML: {output_base}_adversarial.html")
        
        # 返回检测率作为退出码
        sys.exit(0 if results['detection_rate'] >= 80 else 1)
    
    elif args.source:
        # 执行正常审计
        print(f"🔍 开始审计: {args.source}")
        
        dataset_name = args.dataset_name or Path(args.source).stem
        report = auditor.audit(args.source, args.format, dataset_name)
        
        # 输出摘要
        print("\n" + "="*60)
        print("📊 审计结果摘要")
        print("="*60)
        print(f"数据集: {report.dataset_name}")
        print(f"记录数: {report.record_count}")
        print(f"综合评分: {report.overall_score} 分")
        print(f"质量等级: {report.grade}")
        print("\n维度评分:")
        for name, dim in report.dimensions.items():
            print(f"  {name:15s}: {dim.score:6.2f} 分 (权重: {dim.weight})")
        
        # 输出问题
        total_issues = sum(len(dim.issues) for dim in report.dimensions.values())
        if total_issues > 0:
            print(f"\n⚠️  发现 {total_issues} 个问题:")
            for name, dim in report.dimensions.items():
                for issue in dim.issues:
                    icon = "🔴" if issue.severity == 'critical' else "🟡"
                    print(f"   {icon} [{name}] {issue.field}: {issue.description}")
        else:
            print("\n✅ 未发现质量问题")
        
        # 输出改进建议
        if report.recommendations:
            print(f"\n💡 改进建议 (前3条):")
            for rec in report.recommendations[:3]:
                icon = "🔴" if rec['priority'] == 'high' else "🟡"
                print(f"   {icon} {rec['suggestion']}")
        
        # 保存报告
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        
        if args.output_format in ['json', 'both']:
            json_path = f"{args.output}.json"
            auditor.save_report(report, json_path, 'json')
            print(f"\n📄 JSON报告: {json_path}")
        
        if args.output_format in ['html', 'both']:
            html_path = f"{args.output}.html"
            auditor.save_report(report, html_path, 'html')
            print(f"📄 HTML报告: {html_path}")
        
        # 质量门禁检查
        alert_threshold = auditor.config.get('requirements', {}).get('integration', {}).get('alert_threshold', 80)
        if report.overall_score < alert_threshold:
            print(f"\n⚠️ 警告: 质量评分 {report.overall_score} 低于阈值 {alert_threshold}")
            sys.exit(2)
        
        print("\n✅ 审计完成")
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
