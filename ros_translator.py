#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS报错翻译模块
- 自动检测英文报错并翻译成中文
- 支持自定义翻译词典
- 支持手动翻译
"""
import os
import re
import json


class ROSTranslator:
    """ROS报错翻译器"""

    def __init__(self, dict_file=None):
        self.dict_file = dict_file or os.path.join(
            os.path.dirname(__file__), "translation_dict.json")
        self.translations = {}
        self.custom_translations = {}
        self._load_translations()

    def _load_translations(self):
        """加载翻译词典"""
        # 内置常见ROS错误翻译
        self.translations = {
            # 连接相关
            "unable to connect to ROS master": "无法连接到ROS主节点",
            "cannot connect to rosmaster": "无法连接到ROS主节点",
            "rosmaster is not running": "ROS主节点未运行",
            "failed to contact master": "连接主节点失败",
            "connection refused": "连接被拒绝",
            "timeout exceeded": "超时",
            "connection timed out": "连接超时",

            # 包相关
            "package not found": "未找到包",
            "cannot find package": "无法找到包",
            "package '[package]' not found": "未找到包 '[package]'",
            "unknown package": "未知包",
            "missing package": "缺少包",

            # 节点相关
            "node not found": "未找到节点",
            "cannot find node": "无法找到节点",
            "node '[node]' not found": "未找到节点 '[node]'",
            "failed to start node": "启动节点失败",
            "node already running": "节点已在运行",

            # 话题相关
            "topic not found": "未找到话题",
            "cannot find topic": "无法找到话题",
            "no publishers on topic": "话题上没有发布者",
            "no subscribers on topic": "话题上没有订阅者",

            # 参数相关
            "parameter not found": "未找到参数",
            "cannot find parameter": "无法找到参数",
            "invalid parameter": "无效参数",
            "parameter '[param]' not set": "参数 '[param]' 未设置",

            # 文件相关
            "file not found": "文件未找到",
            "cannot open file": "无法打开文件",
            "no such file or directory": "没有此类文件或目录",
            "permission denied": "权限被拒绝",
            "file exists": "文件已存在",

            # 编译相关
            "compilation failed": "编译失败",
            "build error": "构建错误",
            "syntax error": "语法错误",
            "undefined symbol": "未定义符号",
            "missing dependency": "缺少依赖",

            # 运行时相关
            "segmentation fault": "段错误",
            "out of memory": "内存不足",
            "runtime error": "运行时错误",
            "illegal instruction": "非法指令",
            "bus error": "总线错误",

            # TF相关
            "tf transform exception": "TF变换异常",
            "lookup would require extrapolation into the past": "查找需要向过去外推",
            "lookup would require extrapolation into the future": "查找需要向未来外推",
            "frame '[frame]' does not exist": "坐标系 '[frame]' 不存在",

            # 传感器相关
            "sensor not found": "未找到传感器",
            "device not available": "设备不可用",
            "failed to open device": "打开设备失败",

            # 网络相关
            "network is unreachable": "网络不可达",
            "no route to host": "无路由到主机",
            "address already in use": "地址已被使用",

            # 通用错误
            "error": "错误",
            "warning": "警告",
            "fatal": "致命错误",
            "critical": "严重错误",
            "failed": "失败",
            "success": "成功",
            "not found": "未找到",
            "invalid": "无效",
            "timeout": "超时",
            "denied": "被拒绝",
        }

        # 加载自定义翻译词典
        self._load_custom_dict()

    def _load_custom_dict(self):
        """加载自定义翻译词典"""
        if os.path.exists(self.dict_file):
            try:
                with open(self.dict_file, "r", encoding="utf-8") as f:
                    self.custom_translations = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.custom_translations = {}

    def save_custom_dict(self):
        """保存自定义翻译词典"""
        try:
            with open(self.dict_file, "w", encoding="utf-8") as f:
                json.dump(self.custom_translations, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def add_translation(self, english, chinese):
        """添加自定义翻译"""
        self.custom_translations[english.lower()] = chinese
        self.save_custom_dict()

    def remove_translation(self, english):
        """移除自定义翻译"""
        if english.lower() in self.custom_translations:
            del self.custom_translations[english.lower()]
            self.save_custom_dict()

    def translate(self, text):
        """翻译文本"""
        if not text:
            return text

        # 检查是否是错误/警告信息
        is_error = bool(re.search(r'\[ERROR\]|\[FATAL\]|\berror\b|\bfailed\b|\bexception\b', text, re.IGNORECASE))
        is_warning = bool(re.search(r'\[WARN\]|warning', text, re.IGNORECASE))

        if not is_error and not is_warning:
            return text

        translated = text

        # 优先使用自定义翻译
        for english, chinese in self.custom_translations.items():
            if english.lower() in translated.lower():
                translated = re.sub(
                    re.escape(english),
                    f"{chinese} ({english})",
                    translated,
                    flags=re.IGNORECASE
                )

        # 使用内置翻译
        for english, chinese in self.translations.items():
            if english.lower() in translated.lower():
                # 避免重复翻译
                if f"({english})" not in translated:
                    translated = re.sub(
                        re.escape(english),
                        f"{chinese} ({english})",
                        translated,
                        flags=re.IGNORECASE
                    )

        return translated

    def translate_error(self, error_text):
        """翻译错误信息"""
        return self.translate(error_text)

    def translate_output(self, output_text):
        """翻译输出文本（逐行处理）"""
        lines = output_text.split("\n")
        translated_lines = []

        for line in lines:
            translated_lines.append(self.translate(line))

        return "\n".join(translated_lines)

    def get_translation_dict(self):
        """获取完整翻译词典"""
        full_dict = dict(self.translations)
        full_dict.update(self.custom_translations)
        return full_dict

    def search_translation(self, keyword):
        """搜索翻译词典"""
        results = []
        keyword_lower = keyword.lower()

        for english, chinese in self.translations.items():
            if keyword_lower in english.lower() or keyword_lower in chinese.lower():
                results.append({"english": english, "chinese": chinese, "type": "builtin"})

        for english, chinese in self.custom_translations.items():
            if keyword_lower in english.lower() or keyword_lower in chinese.lower():
                results.append({"english": english, "chinese": chinese, "type": "custom"})

        return results
