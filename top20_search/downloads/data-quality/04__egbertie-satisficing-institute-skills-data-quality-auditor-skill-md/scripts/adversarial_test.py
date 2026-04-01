#!/usr/bin/env python3
"""
adversarial_test.py - S7: 对抗测试专用脚本
用于验证数据质量审计器的检测能力
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data_quality_auditor import QualityAuditor, run_adversarial_test
import json


def main():
    print("="*70)
    print("🧪 数据质量审计器 - S7: 对抗测试")
    print("="*70)
    print("\n本测试通过故意污染数据来验证检测能力:\n")
    
    # 初始化审计器
    config_path = "config/quality_requirements.yaml"
    auditor = QualityAuditor(config_path)
    
    # 运行对抗测试
    results = run_adversarial_test(auditor)
    
    # 保存详细报告
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    
    # JSON报告
    report_dict = {
        'test_name': 'S7_Adversarial_Test',
        'execution_time': results['report'].generated_at,
        'detection_summary': results['tests'],
        'detection_rate': results['detection_rate'],
        'passed': results['detection_rate'] >= 80,
        'dataset_stats': {
            'total_records': results['report'].record_count,
            'overall_score': results['report'].overall_score,
            'grade': results['report'].grade
        }
    }
    
    json_path = output_dir / "s7_adversarial_test_results.json"
    with open(json_path, 'w') as f:
        json.dump(report_dict, f, indent=2)
    
    # HTML报告
    html_path = output_dir / "s7_adversarial_test_report.html"
    auditor.save_report(results['report'], str(html_path), 'html')
    
    print("\n" + "="*70)
    print("📄 测试报告已保存:")
    print(f"   JSON: {json_path}")
    print(f"   HTML: {html_path}")
    print("="*70)
    
    # 返回结果
    if results['detection_rate'] >= 80:
        print("\n✅ S7 对抗测试通过! 检测率 ≥ 80%")
        return 0
    else:
        print(f"\n❌ S7 对抗测试未通过. 检测率 {results['detection_rate']:.0f}% < 80%")
        return 1


if __name__ == "__main__":
    sys.exit(main())
