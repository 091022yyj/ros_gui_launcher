#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志分析模块
- 自动分析日志中的错误和警告
- 提取关键信息
- 生成分析报告
"""
import os
import re
from collections import defaultdict, Counter
from datetime import datetime


class LogAnalyzer:
    """日志分析器"""

    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir

    def analyze_log_file(self, file_path, max_lines=10000):
        """分析单个日志文件"""
        if not os.path.exists(file_path):
            return {"error": "文件不存在"}

        analysis = {
            "file": file_path,
            "total_lines": 0,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
            "error_types": Counter(),
            "warning_types": Counter(),
            "time_range": None,
            "keywords": Counter(),
        }

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-max_lines:]

            analysis["total_lines"] = len(lines)

            first_time = None
            last_time = None

            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # 提取时间戳
                time_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', line)
                if time_match:
                    current_time = time_match.group(1)
                    if not first_time:
                        first_time = current_time
                    last_time = current_time

                # 检测错误
                if re.search(r'\[ERROR\]|error|failed|exception|fatal|critical', line, re.IGNORECASE):
                    analysis["error_count"] += 1
                    error_type = self._extract_error_type(line)
                    analysis["error_types"][error_type] += 1
                    if len(analysis["errors"]) < 100:  # 最多保存100条
                        analysis["errors"].append({
                            "line": i,
                            "content": line[:200]  # 限制长度
                        })

                # 检测警告
                elif re.search(r'\[WARN\]|warning', line, re.IGNORECASE):
                    analysis["warning_count"] += 1
                    warning_type = self._extract_warning_type(line)
                    analysis["warning_types"][warning_type] += 1
                    if len(analysis["warnings"]) < 100:  # 最多保存100条
                        analysis["warnings"].append({
                            "line": i,
                            "content": line[:200]  # 限制长度
                        })

                # 提取关键词
                keywords = re.findall(r'\b(?:node|topic|service|param|launch|package)\b', line, re.IGNORECASE)
                for kw in keywords:
                    analysis["keywords"][kw.lower()] += 1

            if first_time and last_time:
                analysis["time_range"] = {"start": first_time, "end": last_time}

        except Exception as e:
            analysis["error"] = str(e)

        return analysis

    def _extract_error_type(self, line):
        """提取错误类型"""
        # 常见错误模式
        patterns = [
            (r'connection refused', '连接被拒绝'),
            (r'timed out', '超时'),
            (r'not found', '未找到'),
            (r'permission denied', '权限拒绝'),
            (r'no such file', '文件不存在'),
            (r'segfault', '段错误'),
            (r'out of memory', '内存不足'),
            (r'undefined symbol', '未定义符号'),
            (r'import error', '导入错误'),
            (r'syntax error', '语法错误'),
        ]

        for pattern, error_type in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return error_type

        return '其他错误'

    def _extract_warning_type(self, line):
        """提取警告类型"""
        patterns = [
            (r'deprecated', '弃用警告'),
            (r'timeout', '超时警告'),
            (r'retry', '重试警告'),
            (r'not found', '未找到警告'),
            (r'invalid', '无效警告'),
        ]

        for pattern, warning_type in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return warning_type

        return '其他警告'

    def analyze_all_logs(self, max_lines_per_file=5000):
        """分析所有日志文件"""
        if not os.path.exists(self.log_dir):
            return {"error": "日志目录不存在"}

        analyses = []
        total_errors = 0
        total_warnings = 0

        for f in sorted(os.listdir(self.log_dir)):
            if not f.endswith(".log"):
                continue

            file_path = os.path.join(self.log_dir, f)
            analysis = self.analyze_log_file(file_path, max_lines_per_file)
            analyses.append(analysis)

            total_errors += analysis.get("error_count", 0)
            total_warnings += analysis.get("warning_count", 0)

        # 汇总错误类型
        all_error_types = Counter()
        all_warning_types = Counter()
        for a in analyses:
            all_error_types.update(a.get("error_types", {}))
            all_warning_types.update(a.get("warning_types", {}))

        return {
            "files": analyses,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "error_types": all_error_types.most_common(10),
            "warning_types": all_warning_types.most_common(10),
        }

    def generate_report(self, analysis, output_file=None):
        """生成分析报告"""
        report = []
        report.append("=" * 60)
        report.append("日志分析报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        if "files" in analysis:
            # 汇总分析
            report.append(f"分析文件数: {len(analysis['files'])}")
            report.append(f"总错误数: {analysis['total_errors']}")
            report.append(f"总警告数: {analysis['total_warnings']}")
            report.append("")

            # 错误类型统计
            if analysis["error_types"]:
                report.append("错误类型统计:")
                for error_type, count in analysis["error_types"]:
                    report.append(f"  - {error_type}: {count}次")
                report.append("")

            # 警告类型统计
            if analysis["warning_types"]:
                report.append("警告类型统计:")
                for warning_type, count in analysis["warning_types"]:
                    report.append(f"  - {warning_type}: {count}次")
                report.append("")

            # 详细文件分析
            for file_analysis in analysis["files"]:
                if file_analysis.get("error_count", 0) > 0 or file_analysis.get("warning_count", 0) > 0:
                    report.append(f"文件: {file_analysis.get('file', '未知')}")
                    report.append(f"  错误: {file_analysis.get('error_count', 0)}条")
                    report.append(f"  警告: {file_analysis.get('warning_count', 0)}条")
                    if file_analysis.get("errors"):
                        report.append("  最近错误:")
                        for err in file_analysis["errors"][:5]:
                            report.append(f"    行{err['line']}: {err['content'][:100]}")
                    report.append("")

        report_text = "\n".join(report)

        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(report_text)
            except Exception:
                pass

        return report_text

    def search_errors(self, keyword=None, error_type=None):
        """搜索错误"""
        results = []

        if not os.path.exists(self.log_dir):
            return results

        for f in os.listdir(self.log_dir):
            if not f.endswith(".log"):
                continue

            file_path = os.path.join(self.log_dir, f)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as log_file:
                    for i, line in enumerate(log_file, 1):
                        # 检查是否是错误行
                        if not re.search(r'\[ERROR\]|error|failed|exception', line, re.IGNORECASE):
                            continue

                        # 关键词过滤
                        if keyword and keyword.lower() not in line.lower():
                            continue

                        # 错误类型过滤
                        if error_type:
                            detected_type = self._extract_error_type(line)
                            if error_type.lower() not in detected_type.lower():
                                continue

                        results.append({
                            "file": f,
                            "line": i,
                            "content": line.strip()[:200]
                        })
            except Exception:
                continue

        return results
