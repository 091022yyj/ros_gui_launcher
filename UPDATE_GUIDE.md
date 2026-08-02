# 远程更新指南

## 快速开始

### 1. 准备GitHub仓库

```bash
# 1. 在GitHub上创建新仓库 ros_gui_launcher
# 2. 初始化本地仓库
cd /home/ub/ros_gui_launcher
git init
git add .
git commit -m "初始提交"
git remote add origin https://github.com/你的用户名/ros_gui_launcher.git
git push -u origin main
```

### 2. 创建GitHub Token

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token"
3. 选择 "repo" 权限
4. 复制生成的Token

### 3. 配置更新服务器

编辑 `update_config.json`：

```json
{
  "update_server": "https://api.github.com",
  "repo_owner": "你的GitHub用户名",
  "repo_name": "ros_gui_launcher",
  "current_version": "2.0.0",
  "check_interval": 3600,
  "auto_update": false
}
```

### 4. 发布更新

```bash
cd /home/ub/ros_gui_launcher
python3 publish_update.py
```

按提示输入：
- 新版本号（如 2.1.0）
- GitHub Token

### 5. 用户获取更新

用户在程序中点击 "🔄 检查更新" 按钮即可。

---

## 详细步骤

### 步骤1：创建GitHub仓库

1. 登录GitHub
2. 点击右上角 "+" -> "New repository"
3. 仓库名：`ros_gui_launcher`
4. 选择 "Public"（免费）
5. 点击 "Create repository"

### 步骤2：上传代码到GitHub

```bash
cd /home/ub/ros_gui_launcher

# 初始化git（如果还没有）
git init

# 添加文件
git add .
git commit -m "v2.0.0 发布"

# 连接远程仓库
git remote add origin https://github.com/你的用户名/ros_gui_launcher.git

# 推送
git push -u origin main
```

### 步骤3：创建Personal Access Token

1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 填写Note：`ros_gui_launcher_update`
4. 勾选权限：`repo` (完整权限)
5. 点击 "Generate token"
6. **立即复制Token**（只显示一次）

### 步骤4：发布新版本

```bash
cd /home/ub/ros_gui_launcher

# 修改版本号（可选）
# 编辑 update_config.json 中的 current_version

# 运行发布脚本
python3 publish_update.py
```

脚本会：
1. 打包程序（生成dist/ros_gui_launcher）
2. 创建GitHub Release
3. 上传可执行文件

### 步骤5：用户更新

用户有两种方式获取更新：

**方式1：程序内更新**
- 打开ROS GUI启动器
- 点击 "🔄 检查更新" 按钮
- 如果有新版本，会提示下载

**方式2：手动下载**
- 访问你的GitHub仓库 Releases页面
- 下载最新版本的 `ros_gui_launcher`

---

## 版本号规范

使用语义化版本号：`主版本.次版本.修订号`

- 主版本：重大更新，不兼容的API修改
- 次版本：新增功能，向后兼容
- 修订号：Bug修复，向后兼容

示例：
- 2.0.0 -> 2.0.1（Bug修复）
- 2.0.1 -> 2.1.0（新增功能）
- 2.1.0 -> 3.0.0（重大更新）

---

## 常见问题

### Q: Token泄露了怎么办？
A: 立即访问 https://github.com/settings/tokens 删除该Token，然后生成新的。

### Q: 用户无法检查更新？
A: 检查：
1. update_config.json 中的 repo_owner 和 repo_name 是否正确
2. 仓库是否是Public
3. 网络连接是否正常

### Q: 如何回滚版本？
A: 在GitHub Releases中删除对应版本的Release即可。

### Q: 可以只更新部分文件吗？
A: 当前版本是整体更新。如需增量更新，需要额外实现差分算法。

---

## 高级配置

### 自定义更新服务器

如果不想用GitHub，可以搭建自己的更新服务器：

```json
{
  "update_server": "http://your-server.com/api",
  "repo_owner": "",
  "repo_name": "",
  "current_version": "2.0.0",
  "check_interval": 3600,
  "auto_update": false
}
```

服务器需要实现以下接口：
- GET /latest.json - 返回最新版本信息
- GET /download/{version} - 下载更新包

### 自动更新

设置 `"auto_update": true` 可以在启动时自动检查并下载更新。

---

## 文件说明

- `update_config.json` - 更新配置文件
- `publish_update.py` - 发布更新脚本
- `UPDATE_GUIDE.md` - 本指南

如有问题，请提交Issue到GitHub仓库。
