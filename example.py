#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AcFun 上传工具使用示例
这个脚本展示了如何使用 acfun_cli.py 进行视频上传
"""

import subprocess
import sys
import os

def run_upload_example():
    """运行上传示例"""
    
    # 检查必要文件是否存在
    if not os.path.exists("test.mp4"):
        print("警告: test.mp4 文件不存在，请确保有测试视频文件")
        return
    
    if not os.path.exists("test.png"):
        print("警告: test.png 文件不存在，请确保有测试封面文件")
        return
    
    # 基本上传命令
    cmd = [
        sys.executable, "acfun_cli.py",
        "test.mp4",                    # 视频文件
        "-c", "test.png",              # 封面图片
        "-t", "测试视频上传",           # 标题
        "--cid", "63",                 # 频道ID (游戏区)
        "-d", "这是一个测试视频",       # 描述
        "--tags", "测试", "演示",      # 标签
        "--type", "3"                  # 原创
    ]
    
    print("执行命令:")
    print(" ".join(cmd))
    print("\n" + "="*50)
    
    try:
        # 执行命令
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n" + "="*50)
            print("上传成功！")
        else:
            print("\n" + "="*50)
            print(f"上传失败，返回码: {result.returncode}")
            
    except KeyboardInterrupt:
        print("\n用户取消了上传")
    except Exception as e:
        print(f"\n执行出错: {e}")

def show_help():
    """显示帮助信息"""
    cmd = [sys.executable, "acfun_cli.py", "-h"]
    subprocess.run(cmd)

if __name__ == "__main__":
    print("AcFun 上传工具示例")
    print("=" * 30)
    
    if len(sys.argv) > 1 and sys.argv[1] == "help":
        show_help()
    else:
        print("这个示例将上传 test.mp4 到 AcFun")
        print("请确保:")
        print("1. test.mp4 和 test.png 文件存在")
        print("2. 已安装依赖: pip install -r requirements.txt")
        print("3. 准备好 AcFun 账号")
        print()
        
        choice = input("是否继续? (y/N): ").lower().strip()
        if choice == 'y' or choice == 'yes':
            run_upload_example()
        else:
            print("已取消")
            print("\n使用 'python example.py help' 查看完整帮助") 