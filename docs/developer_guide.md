# 开发者指南

## 项目结构

```
ros_gui_launcher/
├── launcher_gui.py      # 主程序入口
├── launcher_core.py     # 核心启动器模块
├── process_manager.py   # 进程管理器模块
├── config_manager.py    # 配置管理器模块
├── monitor.py          # 监控模块
├── updater.py          # 更新模块
├── security.py         # 安全模块
├── build.py            # 打包脚本
├── tests/              # 测试目录
└── docs/               # 文档目录
```

## 开发环境

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试

```bash
# 单元测试
python -m pytest tests/unit/

# 集成测试
python -m pytest tests/integration/

# 性能测试
python -m pytest tests/performance/
```

## 代码规范

### 代码风格

- 遵循PEP 8规范
- 使用类型提示
- 编写文档字符串

### 提交规范

使用语义化提交信息：
- `feat:` 新功能
- `fix:` 修复bug
- `perf:` 性能优化
- `style:` 代码样式
- `docs:` 文档
- `test:` 测试
- `chore:` 其他

## 发布流程

1. 更新版本号
2. 运行测试
3. 打包
4. 创建发布说明
5. 推送到GitHub