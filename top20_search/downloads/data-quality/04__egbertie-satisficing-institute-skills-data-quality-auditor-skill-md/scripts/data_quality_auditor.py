#!/usr/bin/env python3
"""
data_quality_auditor.py - 数据质量审计核心模块
S1-S7 全标准实现

Author: Satisficing Institute
Version: 2.0.0
"""

import os
import re
import json
import yaml
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np


@dataclass
class QualityIssue:
    """质量问题记录"""
    dimension: str           # 维度: completeness, accuracy, consistency, timeliness
    severity: str            # 级别: critical, warning, info
    field: str               # 字段名
    issue_type: str          # 问题类型
    description: str         # 描述
    affected_count: int      # 影响记录数
    sample_values: List[Any] # 示例值
    suggestion: str          # 改进建议


@dataclass
class DimensionScore:
    """维度评分"""
    dimension: str
    score: float
    weight: float
    issues: List[QualityIssue]
    metrics: Dict[str, Any]


@dataclass
class QualityReport:
    """质量报告"""
    report_id: str
    generated_at: str
    dataset_name: str
    record_count: int
    overall_score: float
    grade: str
    dimensions: Dict[str, DimensionScore]
    recommendations: List[Dict[str, Any]]
    limitations: List[str]
    adversarial_test_results: Optional[Dict[str, Any]] = None


class QualityAuditor:
    """
    数据质量审计器
    
    S1: 输入规范处理
    S2: 四维质量审计
    S3: 报告生成
    S4: 可集成
    S5: 量化指标
    S6: 局限标注
    S7: 对抗测试支持
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.issues: List[QualityIssue] = []
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger('QualityAuditor')
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置"""
        default_config = {
            'requirements': {
                'completeness': {'min_threshold': 0.95},
                'accuracy': {'outlier_method': 'iqr', 'outlier_threshold': 1.5},
                'consistency': {'date_format': '%Y-%m-%d'},
                'timeliness': {'max_data_age_hours': 24},
                'scoring': {
                    'weights': {
                        'completeness': 0.30,
                        'accuracy': 0.30,
                        'consistency': 0.20,
                        'timeliness': 0.20
                    }
                }
            }
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    default_config.update(user_config)
                    
        return default_config
    
    # ========== S1: 输入处理 ==========
    
    def load_data(self, source: str, source_type: str = 'auto') -> pd.DataFrame:
        """
        S1: 加载数据
        
        Args:
            source: 数据源路径或连接字符串
            source_type: 数据源类型 (csv, json, parquet, sqlite, postgresql)
        """
        self.logger.info(f"Loading data from {source} (type: {source_type})")
        
        if source_type == 'auto':
            # 自动检测类型
            if source.endswith('.csv'):
                source_type = 'csv'
            elif source.endswith('.json'):
                source_type = 'json'
            elif source.endswith('.parquet'):
                source_type = 'parquet'
            elif '.db' in source or '.sqlite' in source:
                source_type = 'sqlite'
        
        try:
            if source_type == 'csv':
                df = pd.read_csv(source, encoding='utf-8')
            elif source_type == 'json':
                df = pd.read_json(source)
            elif source_type == 'parquet':
                df = pd.read_parquet(source)
            elif source_type == 'sqlite':
                import sqlite3
                conn = sqlite3.connect(source)
                df = pd.read_sql("SELECT * FROM data", conn)
                conn.close()
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
                
            self.logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            raise
    
    # ========== S2: 质量审计 ==========
    
    def audit_completeness(self, df: pd.DataFrame) -> DimensionScore:
        """
        S2.1: 完整性审计
        
        检查项:
        - NULL值检测
        - 空字符串检测
        - 必填项检查
        """
        self.logger.info("Auditing completeness...")
        issues = []
        total_cells = len(df) * len(df.columns)
        null_count = 0
        
        req = self.config.get('requirements', {}).get('completeness', {})
        min_threshold = req.get('min_threshold', 0.95)
        critical_fields = req.get('critical_fields', [])
        
        for col in df.columns:
            col_null = df[col].isna().sum()
            col_empty = 0
            
            # 检查空字符串
            if df[col].dtype == 'object':
                col_empty = (df[col].astype(str).str.strip() == '').sum()
            
            total_missing = col_null + col_empty
            missing_rate = total_missing / len(df)
            null_count += total_missing
            
            if missing_rate > 0:
                severity = 'critical' if col in critical_fields else 'warning'
                if missing_rate > (1 - min_threshold):
                    severity = 'critical'
                    
                issues.append(QualityIssue(
                    dimension='completeness',
                    severity=severity,
                    field=col,
                    issue_type='missing_values',
                    description=f"缺失率 {missing_rate*100:.2f}%",
                    affected_count=int(total_missing),
                    sample_values=df[df[col].isna() | (df[col].astype(str).str.strip() == '')][col].head(5).tolist(),
                    suggestion=f"检查数据源，考虑设置默认值或完善采集流程"
                ))
        
        # 计算得分
        completeness_rate = 1 - (null_count / total_cells)
        score = completeness_rate * 100
        
        return DimensionScore(
            dimension='completeness',
            score=score,
            weight=self.config['requirements']['scoring']['weights']['completeness'],
            issues=issues,
            metrics={'null_count': null_count, 'completeness_rate': completeness_rate}
        )
    
    def audit_accuracy(self, df: pd.DataFrame) -> DimensionScore:
        """
        S2.2: 准确性审计
        
        检查项:
        - 数值范围检查
        - 异常值检测 (IQR/Z-Score)
        - 业务规则检查
        """
        self.logger.info("Auditing accuracy...")
        issues = []
        
        req = self.config.get('requirements', {}).get('accuracy', {})
        outlier_method = req.get('outlier_method', 'iqr')
        numeric_ranges = req.get('numeric_ranges', {})
        
        # 检查数值范围
        for col in df.select_dtypes(include=[np.number]).columns:
            if col in numeric_ranges:
                ranges = numeric_ranges[col]
                min_val, max_val = ranges.get('min'), ranges.get('max')
                
                out_of_range = df[(df[col] < min_val) | (df[col] > max_val)]
                if len(out_of_range) > 0:
                    issues.append(QualityIssue(
                        dimension='accuracy',
                        severity='critical',
                        field=col,
                        issue_type='out_of_range',
                        description=f"数值超出范围 [{min_val}, {max_val}]",
                        affected_count=len(out_of_range),
                        sample_values=out_of_range[col].head(5).tolist(),
                        suggestion=f"检查数据采集逻辑，验证{col}的合理范围"
                    ))
            
            # 异常值检测
            if outlier_method == 'iqr':
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                threshold = req.get('outlier_threshold', 1.5)
                outliers = df[(df[col] < Q1 - threshold * IQR) | (df[col] > Q3 + threshold * IQR)]
                
                if len(outliers) > 0 and len(outliers) / len(df) > 0.02:  # 超过2%才告警
                    issues.append(QualityIssue(
                        dimension='accuracy',
                        severity='warning',
                        field=col,
                        issue_type='outliers',
                        description=f"检测到 {len(outliers)} 个异常值 (IQR方法)",
                        affected_count=len(outliers),
                        sample_values=outliers[col].head(5).tolist(),
                        suggestion=f"审查异常值是否为真实数据或采集错误"
                    ))
        
        # 计算得分
        score = max(0, 100 - len([i for i in issues if i.severity == 'critical']) * 10 
                    - len([i for i in issues if i.severity == 'warning']) * 5)
        
        return DimensionScore(
            dimension='accuracy',
            score=score,
            weight=self.config['requirements']['scoring']['weights']['accuracy'],
            issues=issues,
            metrics={'outlier_method': outlier_method}
        )
    
    def audit_consistency(self, df: pd.DataFrame) -> DimensionScore:
        """
        S2.3: 一致性审计
        
        检查项:
        - 格式统一性
        - 重复记录检测
        - 类型一致性
        """
        self.logger.info("Auditing consistency...")
        issues = []
        
        req = self.config.get('requirements', {}).get('consistency', {})
        email_pattern = req.get('email_pattern')
        
        # 检测重复记录
        duplicates = df[df.duplicated(keep=False)]
        if len(duplicates) > 0:
            duplicate_rate = len(duplicates) / len(df)
            severity = 'critical' if duplicate_rate > 0.01 else 'warning'
            issues.append(QualityIssue(
                dimension='consistency',
                severity=severity,
                field='*',
                issue_type='duplicates',
                description=f"发现 {len(duplicates)} 条重复记录 (重复率: {duplicate_rate*100:.2f}%)",
                affected_count=len(duplicates),
                sample_values=[],
                suggestion="添加主键约束或去重逻辑"
            ))
        
        # 检查email格式
        if email_pattern and 'email' in df.columns:
            pattern = re.compile(email_pattern)
            def is_valid_email(x):
                if pd.isna(x):
                    return True  # NULL值由完整性检查处理
                return bool(pattern.match(str(x)))
            
            invalid_emails = df[~df['email'].apply(is_valid_email)]
            if len(invalid_emails) > 0:
                issues.append(QualityIssue(
                    dimension='consistency',
                    severity='warning',
                    field='email',
                    issue_type='invalid_format',
                    description=f"发现 {len(invalid_emails)} 条无效email格式",
                    affected_count=len(invalid_emails),
                    sample_values=invalid_emails['email'].head(5).tolist(),
                    suggestion="添加前端email格式验证"
                ))
        
        # 计算得分
        score = max(0, 100 - len([i for i in issues if i.severity == 'critical']) * 15
                    - len([i for i in issues if i.severity == 'warning']) * 8)
        
        return DimensionScore(
            dimension='consistency',
            score=score,
            weight=self.config['requirements']['scoring']['weights']['consistency'],
            issues=issues,
            metrics={'duplicate_count': len(duplicates) if len(duplicates) > 0 else 0}
        )
    
    def audit_timeliness(self, df: pd.DataFrame) -> DimensionScore:
        """
        S2.4: 时效性审计
        
        检查项:
        - 数据新鲜度
        - 更新频率
        - 时序连续性
        """
        self.logger.info("Auditing timeliness...")
        issues = []
        
        req = self.config.get('requirements', {}).get('timeliness', {})
        max_age_hours = req.get('max_data_age_hours', 24)
        timestamp_col = req.get('timestamp_column', 'updated_at')
        
        # 检查时间戳列
        time_cols = [col for col in df.columns if 'time' in col.lower() 
                     or 'date' in col.lower() or col == timestamp_col]
        
        for col in time_cols:
            try:
                # 尝试转换为日期时间
                dt_series = pd.to_datetime(df[col], errors='coerce')
                if dt_series.notna().sum() == 0:
                    continue
                    
                latest = dt_series.max()
                now = pd.Timestamp.now()
                age_hours = (now - latest).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    issues.append(QualityIssue(
                        dimension='timeliness',
                        severity='warning',
                        field=col,
                        issue_type='stale_data',
                        description=f"数据已过时 {age_hours:.1f} 小时",
                        affected_count=len(df),
                        sample_values=[str(latest)],
                        suggestion=f"检查数据更新流程，确保数据在{max_age_hours}小时内更新"
                    ))
                    
            except Exception as e:
                self.logger.warning(f"Could not parse datetime for {col}: {e}")
        
        # 计算得分
        score = max(0, 100 - len([i for i in issues if i.severity == 'critical']) * 10
                    - len([i for i in issues if i.severity == 'warning']) * 5)
        
        return DimensionScore(
            dimension='timeliness',
            score=score,
            weight=self.config['requirements']['scoring']['weights']['timeliness'],
            issues=issues,
            metrics={'max_age_hours': max_age_hours}
        )
    
    # ========== S3: 报告生成 ==========
    
    def calculate_overall_score(self, dimensions: Dict[str, DimensionScore]) -> Tuple[float, str]:
        """
        S5: 计算综合评分
        
        总分 = Σ(维度得分 × 权重)
        """
        total_score = 0
        for dim in dimensions.values():
            total_score += dim.score * dim.weight
            
        # 评级
        grade_thresholds = self.config.get('requirements', {}).get('scoring', {}).get('grade_thresholds', {})
        if total_score >= grade_thresholds.get('A', 90):
            grade = 'A'
        elif total_score >= grade_thresholds.get('B', 80):
            grade = 'B'
        elif total_score >= grade_thresholds.get('C', 70):
            grade = 'C'
        elif total_score >= grade_thresholds.get('D', 60):
            grade = 'D'
        else:
            grade = 'F'
            
        return total_score, grade
    
    def generate_recommendations(self, dimensions: Dict[str, DimensionScore]) -> List[Dict[str, Any]]:
        """
        S3: 生成改进建议
        """
        recommendations = []
        
        for dim_name, dim_score in dimensions.items():
            for issue in dim_score.issues:
                if issue.severity in ['critical', 'warning']:
                    recommendations.append({
                        'priority': 'high' if issue.severity == 'critical' else 'medium',
                        'dimension': dim_name,
                        'field': issue.field,
                        'issue': issue.description,
                        'suggestion': issue.suggestion,
                        'affected_count': issue.affected_count
                    })
        
        # 按优先级排序
        recommendations.sort(key=lambda x: (0 if x['priority'] == 'high' else 1, -x['affected_count']))
        return recommendations
    
    def audit(self, source: str, source_type: str = 'auto', 
              dataset_name: Optional[str] = None) -> QualityReport:
        """
        执行完整审计
        
        Args:
            source: 数据源
            source_type: 数据源类型
            dataset_name: 数据集名称
        """
        self.logger.info(f"Starting audit for {source}")
        
        # S1: 加载数据
        df = self.load_data(source, source_type)
        
        if dataset_name is None:
            dataset_name = Path(source).stem if os.path.exists(source) else "dataset"
        
        # S2: 四维审计
        dimensions = {
            'completeness': self.audit_completeness(df),
            'accuracy': self.audit_accuracy(df),
            'consistency': self.audit_consistency(df),
            'timeliness': self.audit_timeliness(df)
        }
        
        # S5: 计算总分
        overall_score, grade = self.calculate_overall_score(dimensions)
        
        # S3: 生成建议
        recommendations = self.generate_recommendations(dimensions)
        
        # S6: 局限标注
        limitations = [
            "本工具仅检测技术性数据质量问题，不保证数据的业务正确性",
            "无法判断文本内容的语义正确性",
            "无法检测跨系统的隐含逻辑错误",
            "关键业务决策前请进行人工审核"
        ]
        
        # S6 局限说明: 仅检测技术性问题，不判断业务逻辑正确性
        
        # 生成报告
        report = QualityReport(
            report_id=f"dq-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            generated_at=datetime.now().isoformat(),
            dataset_name=dataset_name,
            record_count=len(df),
            overall_score=round(overall_score, 2),
            grade=grade,
            dimensions=dimensions,
            recommendations=recommendations,
            limitations=limitations
        )
        
        self.logger.info(f"Audit complete. Overall score: {overall_score:.2f}, Grade: {grade}")
        return report
    
    def save_report(self, report: QualityReport, output_path: str, format: str = 'json'):
        """保存报告"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            # 转换为字典
            report_dict = asdict(report)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False, default=str)
        elif format == 'html':
            self._generate_html_report(report, output_path)
            
        self.logger.info(f"Report saved to {output_path}")
    
    def _generate_html_report(self, report: QualityReport, output_path: str):
        """生成HTML报告"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>数据质量报告 - {{ dataset_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .score { font-size: 48px; font-weight: bold; text-align: center; margin: 20px 0; }
        .grade-A { color: #4CAF50; }
        .grade-B { color: #8BC34A; }
        .grade-C { color: #FFC107; }
        .grade-D { color: #FF9800; }
        .grade-F { color: #F44336; }
        .dimension { margin: 20px 0; padding: 15px; border-left: 4px solid #4CAF50; background: #f9f9f9; }
        .issue { margin: 10px 0; padding: 10px; background: #fff3cd; border-radius: 4px; }
        .issue.critical { background: #f8d7da; }
        .recommendation { margin: 10px 0; padding: 15px; background: #e3f2fd; border-radius: 4px; }
        .limitations { margin-top: 30px; padding: 20px; background: #fff8e1; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 数据质量报告</h1>
        <p><strong>数据集:</strong> {{ dataset_name }} | <strong>记录数:</strong> {{ record_count }}</p>
        <p><strong>生成时间:</strong> {{ generated_at }}</p>
        
        <div class="score grade-{{ grade }}">{{ overall_score }}分 ({{ grade }}级)</div>
        
        <h2>📈 维度评分</h2>
        <table>
            <tr><th>维度</th><th>得分</th><th>权重</th><th>问题数</th></tr>
            {% for name, dim in dimensions.items() %}
            <tr>
                <td>{{ name }}</td>
                <td>{{ dim.score }}</td>
                <td>{{ dim.weight }}</td>
                <td>{{ dim.issues|length }}</td>
            </tr>
            {% endfor %}
        </table>
        
        <h2>⚠️ 发现的问题</h2>
        {% for name, dim in dimensions.items() %}
            {% for issue in dim.issues %}
            <div class="issue {{ issue.severity }}">
                <strong>[{{ issue.severity.upper() }}]</strong> {{ issue.field }}: {{ issue.description }}
                <br><small>建议: {{ issue.suggestion }}</small>
            </div>
            {% endfor %}
        {% endfor %}
        
        <h2>💡 改进建议</h2>
        {% for rec in recommendations %}
        <div class="recommendation">
            <strong>[{{ rec.priority.upper() }}]</strong> {{ rec.issue }}
            <br>→ {{ rec.suggestion }}
        </div>
        {% endfor %}
        
        <div class="limitations">
            <h3>⚠️ 局限说明 (S6)</h3>
            <ul>
            {% for limit in limitations %}
                <li>{{ limit }}</li>
            {% endfor %}
            </ul>
        </div>
    </div>
</body>
</html>
        """
        
        from jinja2 import Template
        template = Template(html_template)
        html = template.render(**asdict(report))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)


# ========== S7: 对抗测试支持 ==========

def create_adversarial_test_data() -> pd.DataFrame:
    """
    S7: 创建对抗测试数据
    生成故意污染的数据集来测试检测能力
    """
    np.random.seed(42)
    n = 1000
    
    # 正常数据
    df = pd.DataFrame({
        'id': range(1, n + 1),
        'name': [f"User_{i}" for i in range(1, n + 1)],
        'email': [f"user{i}@example.com" for i in range(1, n + 1)],
        'age': np.random.randint(18, 80, n),
        'score': np.random.randint(0, 100, n),
        'created_at': pd.date_range(start='2024-01-01', periods=n, freq='h'),
        'updated_at': pd.date_range(start='2024-01-01', periods=n, freq='h')
    })
    
    # 污染1: 完整性攻击 - 10%的email为NULL
    null_indices = np.random.choice(df.index, size=int(n * 0.1), replace=False)
    df.loc[null_indices, 'email'] = None
    
    # 污染2: 准确性攻击 - 插入异常值
    outlier_indices = np.random.choice(df.index, size=int(n * 0.02), replace=False)
    df.loc[outlier_indices, 'age'] = np.random.choice([999, -10, 1500], size=len(outlier_indices))
    
    # 污染3: 一致性攻击 - 混合email格式
    invalid_email_indices = np.random.choice(df.index, size=int(n * 0.05), replace=False)
    df.loc[invalid_email_indices, 'email'] = 'invalid-email-format'
    
    # 污染4: 重复攻击 - 复制5%记录
    duplicate_indices = np.random.choice(df.index, size=int(n * 0.05), replace=False)
    duplicates = df.loc[duplicate_indices].copy()
    df = pd.concat([df, duplicates], ignore_index=True)
    
    # 污染5: 时效性攻击 - 部分记录时间戳过时
    stale_indices = np.random.choice(df.index, size=int(n * 0.08), replace=False)
    df.loc[stale_indices, 'updated_at'] = pd.Timestamp.now() - pd.Timedelta(days=7)
    
    return df


def run_adversarial_test(auditor: QualityAuditor) -> Dict[str, Any]:
    """
    S7: 运行对抗测试
    验证检测能力
    """
    print("\n" + "="*60)
    print("🧪 S7: 对抗测试 - 验证检测能力")
    print("="*60)
    
    # 创建污染数据
    test_df = create_adversarial_test_data()
    test_file = "tests/data/adversarial_test.csv"
    Path(test_file).parent.mkdir(parents=True, exist_ok=True)
    test_df.to_csv(test_file, index=False)
    
    print(f"✅ 创建测试数据: {len(test_df)} 条记录")
    print("   - 10% email为NULL (完整性攻击)")
    print("   - 2% age异常值 (准确性攻击)")
    print("   - 5% 无效email格式 (一致性攻击)")
    print("   - 5% 重复记录 (重复攻击)")
    print("   - 8% 过时数据 (时效性攻击)")
    
    # 执行审计
    report = auditor.audit(test_file, 'csv', dataset_name='adversarial_test')
    
    # 验证检测结果
    results = {
        'completeness_detected': False,
        'accuracy_detected': False,
        'consistency_detected': False,
        'timeliness_detected': False,
        'duplicates_detected': False
    }
    
    for dim_name, dim in report.dimensions.items():
        for issue in dim.issues:
            desc = issue.description.lower()
            if 'missing' in desc or '缺失' in desc:
                results['completeness_detected'] = True
            if 'outlier' in desc or 'out of range' in desc or '异常' in desc:
                results['accuracy_detected'] = True
            if 'duplicat' in desc or '重复' in desc:
                results['duplicates_detected'] = True
            if 'invalid' in desc or '格式' in desc:
                results['consistency_detected'] = True
            if 'stale' in desc or '过时' in desc:
                results['timeliness_detected'] = True
    
    # 计算检测率
    detection_count = sum(results.values())
    detection_rate = detection_count / len(results) * 100
    
    print("\n📊 检测结果:")
    for test, passed in results.items():
        status = "✅ 通过" if passed else "❌ 未通过"
        print(f"   {test}: {status}")
    
    print(f"\n🎯 综合检测率: {detection_rate:.0f}% ({detection_count}/{len(results)})")
    
    if detection_rate >= 80:
        print("✅ S7: 对抗测试通过!")
    else:
        print("⚠️ S7: 对抗测试部分通过，需优化检测规则")
    
    return {
        'tests': results,
        'detection_rate': detection_rate,
        'report': report
    }


if __name__ == "__main__":
    # 示例用法
    auditor = QualityAuditor("config/quality_requirements.yaml")
    
    # 运行对抗测试
    adversarial_results = run_adversarial_test(auditor)
    
    # 保存报告
    auditor.save_report(adversarial_results['report'], "reports/adversarial_test_report.json")
    auditor.save_report(adversarial_results['report'], "reports/adversarial_test_report.html", format='html')
    
    print("\n✅ 数据质量审计器 V2.0.0 运行完成")
    print("   报告已保存至 reports/ 目录")
