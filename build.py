import subprocess
import sys
import os
import shutil

def build_application(clean=False, debug=False, onefile=True):
    """构建应用程序"""
    cmd = [sys.executable, "-m", "PyInstaller"]
    
    if clean:
        cmd.append("--clean")
    
    if debug:
        cmd.append("--debug")
    
    # 当使用.spec文件时，不添加--onefile选项
    cmd.append("ros_gui_launcher.spec")
    
    print("开始打包...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("打包成功！")
        print("输出文件：dist/ros_gui_launcher")
        
        # 复制配置文件到dist目录
        dist_dir = os.path.join(os.path.dirname(__file__), "dist")
        config_files = ["update_config.json", "style.qss"]
        
        for config_file in config_files:
            src = os.path.join(os.path.dirname(__file__), config_file)
            dst = os.path.join(dist_dir, config_file)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"已复制: {config_file}")
    else:
        print("打包失败：")
        print(result.stderr)
    
    return result.returncode == 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="打包ROS GUI启动器")
    parser.add_argument("--clean", action="store_true", help="清理旧文件")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--dir", action="store_true", help="打包为目录")
    
    args = parser.parse_args()
    build_application(clean=args.clean, debug=args.debug, onefile=not args.dir)