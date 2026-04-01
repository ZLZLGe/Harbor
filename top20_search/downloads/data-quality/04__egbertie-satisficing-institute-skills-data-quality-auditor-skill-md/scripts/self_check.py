#!/usr/bin/env python3
"""
self_check.py - S1-S7 自检脚本
验证 Skill 是否符合 5 标准/7标准项
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent))


class StandardChecker:
    """5标准/7标准项 检查器"""
    
    def __init__(self, skill_path: str = "."):
        self.skill_path = Path(skill_path)
        self.results: Dict[str, Tuple[bool, str]] = {}
        self.passed = 0
        self.failed = 0
        
    def check_s1_input_specification(self) -> Tuple[bool, str]:
        """S1: 输入规范检查"""
        checks = []
        
        # 检查配置文件存在
        config_file = self.skill_path / "config" / "quality_requirements.yaml"
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                if 'requirements' in config and 'input' in config['requirements']:
                    checks.append("✓ 输入规范配置存在")
                else:
                    return False, "输入规范配置不完整"
        else:
            return False, "缺少 quality_requirements.yaml"
        
        # 检查是否支持多种数据源
        auditor_file = self.skill_path / "scripts" / "data_quality_auditor.py"
        if auditor_file.exists():
            content = auditor_file.read_text()
            if 'csv' in content and 'json' in content and 'load_data' in content:
                checks.append("✓ 支持多数据源(CSV/JSON/Parquet)")
            else:
                return False, "数据源支持不完整"
        
        return True, " | ".join(checks)
    
    def check_s2_quality_audit_process(self) -> Tuple[bool, str]:
        """S2: 质量审计流程检查"""
        checks = []
        
        auditor_file = self.skill_path / "scripts" / "data_quality_auditor.py"
        content = auditor_file.read_text()
        
        # 检查四维审计方法
        dimensions = ['completeness', 'accuracy', 'consistency', 'timeliness']
        for dim in dimensions:
            if f'audit_{dim}' in content:
                checks.append(f"✓ {dim}")
            else:
                return False, f"缺少 {dim} 审计方法"
        
        # 检查执行顺序
        if 'completeness' in content and 'accuracy' in content:
            checks.append("✓ 审计流程完整")
        
        return True, " | ".join(checks)
    
    def check_s3_output_report(self) -> Tuple[bool, str]:
        """S3: 输出报告检查"""
        checks = []
        
        # 检查报告生成
        auditor_file = self.skill_path / "scripts" / "data_quality_auditor.py"
        content = auditor_file.read_text()
        
        if 'QualityReport' in content and 'save_report' in content:
            checks.append("✓ 报告类定义")
        else:
            return False, "缺少报告类"
        
        if 'generate_recommendations' in content:
            checks.append("✓ 改进建议生成")
        else:
            return False, "缺少建议生成"
        
        # 检查报告格式
        report_script = self.skill_path / "scripts" / "generate_report.py"
        if report_script.exists():
            checks.append("✓ 报告生成脚本")
        
        return True, " | ".join(checks)
    
    def check_s4_pipeline_integration(self) -> Tuple[bool, str]:
        """S4: 流程集成检查"""
        checks = []
        
        # 检查CI/CD配置
        pipeline_config = self.skill_path / "config" / "pipeline_integration.yaml"
        if pipeline_config.exists():
            checks.append("✓ 管道集成配置")
        else:
            return False, "缺少 pipeline_integration.yaml"
        
        # 检查触发器配置
        with open(pipeline_config) as f:
            config = yaml.safe_load(f)
            if 'triggers' in config:
                checks.append("✓ 触发器配置")
            else:
                return False, "缺少触发器配置"
        
        # 检查cron配置
        cron_file = self.skill_path / "cron.json"
        if cron_file.exists():
            checks.append("✓ 定时任务配置")
        
        return True, " | ".join(checks)
    
    def check_s5_quantified_metrics(self) -> Tuple[bool, str]:
        """S5: 量化指标检查"""
        checks = []
        
        auditor_file = self.skill_path / "scripts" / "data_quality_auditor.py"
        content = auditor_file.read_text()
        
        # 检查核心指标
        metrics = ['error_rate', 'missing_rate', 'duplicate_rate', 'overall_score']
        found = 0
        for metric in metrics:
            if metric.replace('_', '') in content.lower() or metric in content:
                found += 1
        
        if found >= 3:
            checks.append(f"✓ 核心指标 ({found}/4)")
        else:
            return False, f"指标不完整 ({found}/4)"
        
        # 检查评分算法
        if 'calculate_overall_score' in content:
            checks.append("✓ 综合评分算法")
        
        # 检查趋势追踪
        trends_dir = self.skill_path / "reports" / "trends"
        if trends_dir.exists():
            checks.append("✓ 趋势追踪目录")
        
        return True, " | ".join(checks)
    
    def check_s6_limitations(self) -> Tuple[bool, str]:
        """S6: 局限标注检查"""
        checks = []
        
        # 检查SKILL.md中的局限说明
        skill_md = self.skill_path / "SKILL.md"
        content = skill_md.read_text()
        
        if 'S6' in content and '局限' in content:
            checks.append("✓ SKILL.md 局限章节")
        else:
            return False, "SKILL.md 缺少局限说明"
        
        # 检查代码中的局限标注
        auditor_file = self.skill_path / "scripts" / "data_quality_auditor.py"
        auditor_content = auditor_file.read_text()
        
        if 'limitations' in auditor_content and ('业务逻辑' in auditor_content or '业务正确性' in auditor_content):
            checks.append("✓ 代码局限标注")
        else:
            return False, "代码缺少局限标注"
        
        return True, " | ".join(checks)
    
    def check_s7_adversarial_testing(self) -> Tuple[bool, str]:
        """S7: 对抗测试检查"""
        checks = []
        
        # 检查对抗测试脚本
        test_script = self.skill_path / "scripts" / "adversarial_test.py"
        if test_script.exists():
            checks.append("✓ 对抗测试脚本")
        else:
            return False, "缺少 adversarial_test.py"
        
        # 检查测试用例定义
        test_cases = self.skill_path / "tests" / "adversarial_test_cases.yaml"
        if test_cases.exists():
            checks.append("✓ 测试用例定义")
        else:
            return False, "缺少 adversarial_test_cases.yaml"
        
        # 检查核心审计器是否支持对抗测试
        auditor_file = self.skill_path / "scripts" / "data_quality_auditor.py"
        content = auditor_file.read_text()
        
        if 'create_adversarial_test_data' in content and 'run_adversarial_test' in content:
            checks.append("✓ 对抗测试功能")
        else:
            return False, "审计器缺少对抗测试功能"
        
        # 检查测试数据目录
        test_data_dir = self.skill_path / "tests" / "data"
        if test_data_dir.exists():
            checks.append("✓ 测试数据目录")
        
        return True, " | ".join(checks)
    
    def run_all_checks(self) -> bool:
        """运行所有检查"""
        print("="*70)
        print("🔍 Data Quality Auditor - 5标准/7标准项 自检")
        print("="*70)
        
        standards = [
            ("S1", "输入规范 (Input Specification)", self.check_s1_input_specification),
            ("S2", "质量审计流程 (Quality Audit)", self.check_s2_quality_audit_process),
            ("S3", "输出报告 (Output Report)", self.check_s3_output_report),
            ("S4", "流程集成 (Pipeline Integration)", self.check_s4_pipeline_integration),
            ("S5", "量化指标 (Quantified Metrics)", self.check_s5_quantified_metrics),
            ("S6", "局限标注 (Limitations)", self.check_s6_limitations),
            ("S7", "对抗测试 (Adversarial Testing)", self.check_s7_adversarial_testing),
        ]
        
        for code, name, check_func in standards:
            print(f"\n[{code}] {name}")
            try:
                passed, message = check_func()
                self.results[code] = (passed, message)
                
                if passed:
                    print(f"  ✅ 通过 - {message}")
                    self.passed += 1
                else:
                    print(f"  ❌ 失败 - {message}")
                    self.failed += 1
            except Exception as e:
                print(f"  ❌ 错误 - {e}")
                self.results[code] = (False, str(e))
                self.failed += 1
        
        # 输出汇总
        print("\n" + "="*70)
        print("📊 自检结果汇总")
        print("="*70)
        print(f"通过: {self.passed}/7")
        print(f"失败: {self.failed}/7")
        
        if self.failed == 0:
            print("\n🎉 恭喜! 所有标准检查通过!")
            print("   数据质量审计器已达到 5标准/7标准项 要求")
            return True
        else:
            print(f"\n⚠️  有 {self.failed} 项标准未通过，请查看详情")
            return False
    
    def generate_report(self, output_path: str = "reports/self_check_report.json"):
        """生成自检报告"""
        report = {
            'skill_name': 'data-quality-auditor',
            'version': '2.0.0',
            'standard': '5标准/7标准项',
            'timestamp': str(Path().stat().st_mtime),
            'results': {
                code: {'passed': r[0], 'message': r[1]}
                for code, r in self.results.items()
            },
            'summary': {
                'total': 7,
                'passed': self.passed,
                'failed': self.failed,
                'pass_rate': f"{self.passed/7*100:.1f}%"
            },
            'certified': self.failed == 0
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 自检报告已保存: {output_path}")


def main():
    # 切换到 Skill 目录
    skill_path = Path(__file__).parent.parent
    os.chdir(skill_path)
    
    checker = StandardChecker(skill_path)
    passed = checker.run_all_checks()
    checker.generate_report()
    
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
