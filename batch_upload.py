#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量上传脚本示例
演示如何批量上传多个视频到AcFun
"""

import os
import subprocess
import sys
import time
from pathlib import Path

def find_video_files(directory="."):
    """查找指定目录下的视频文件"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    video_files = []
    
    for ext in video_extensions:
        pattern = f"*{ext}"
        video_files.extend(Path(directory).glob(pattern))
    
    return sorted(video_files)

def find_cover_for_video(video_path):
    """为视频文件查找对应的封面图片"""
    video_stem = video_path.stem
    video_dir = video_path.parent
    
    # 查找同名的图片文件
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
    
    for ext in image_extensions:
        cover_path = video_dir / f"{video_stem}{ext}"
        if cover_path.exists():
            return cover_path
    
    # 如果没有同名图片，查找是否有默认封面
    for ext in image_extensions:
        cover_path = video_dir / f"cover{ext}"
        if cover_path.exists():
            return cover_path
    
    return None

def upload_video(video_path, cover_path, channel_id=63, base_title="", tags=None):
    """上传单个视频"""
    if tags is None:
        tags = ["批量上传", "自动化"]
    
    # 生成标题
    video_name = video_path.stem
    title = f"{base_title}{video_name}" if base_title else video_name
    
    # 构建上传命令
    cmd = [
        sys.executable, "acfun_cli.py",
        str(video_path),
        "-c", str(cover_path),
        "-t", title,
        "--cid", str(channel_id),
        "-d", f"通过批量上传工具自动上传的视频: {video_name}",
        "--tags"] + tags + [
        "--type", "3"  # 原创
    ]
    
    print(f"\n正在上传: {video_path.name}")
    print(f"封面: {cover_path.name}")
    print(f"标题: {title}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print(f"✓ {video_path.name} 上传成功")
            return True
        else:
            print(f"✗ {video_path.name} 上传失败")
            return False
            
    except KeyboardInterrupt:
        print(f"\n用户取消了 {video_path.name} 的上传")
        raise
    except Exception as e:
        print(f"✗ {video_path.name} 上传出错: {e}")
        return False

def main():
    print("AcFun 批量上传工具")
    print("=" * 40)
    
    # 配置参数
    directory = input("请输入视频文件目录 (默认当前目录): ").strip() or "."
    channel_id = input("请输入频道ID (默认63-游戏区): ").strip() or "63"
    base_title = input("请输入标题前缀 (可选): ").strip()
    tags_input = input("请输入标签，用空格分隔 (默认: 批量上传 自动化): ").strip()
    
    # 处理标签
    if tags_input:
        tags = tags_input.split()
    else:
        tags = ["批量上传", "自动化"]
    
    # 查找视频文件
    print(f"\n正在扫描目录: {directory}")
    video_files = find_video_files(directory)
    
    if not video_files:
        print("未找到视频文件！")
        return
    
    print(f"找到 {len(video_files)} 个视频文件:")
    
    # 检查每个视频文件的封面
    upload_list = []
    for video_path in video_files:
        cover_path = find_cover_for_video(video_path)
        if cover_path:
            print(f"  ✓ {video_path.name} -> {cover_path.name}")
            upload_list.append((video_path, cover_path))
        else:
            print(f"  ✗ {video_path.name} (未找到封面)")
    
    if not upload_list:
        print("\n没有可上传的视频文件（缺少封面）")
        return
    
    print(f"\n准备上传 {len(upload_list)} 个视频")
    print("配置信息:")
    print(f"  频道ID: {channel_id}")
    print(f"  标题前缀: {base_title or '(无)'}")
    print(f"  标签: {', '.join(tags)}")
    
    # 确认上传
    choice = input("\n是否开始批量上传? (y/N): ").lower().strip()
    if choice not in ['y', 'yes']:
        print("已取消批量上传")
        return
    
    # 开始批量上传
    success_count = 0
    total_count = len(upload_list)
    
    print(f"\n开始批量上传 ({total_count} 个文件)")
    print("=" * 50)
    
    try:
        for i, (video_path, cover_path) in enumerate(upload_list, 1):
            print(f"\n[{i}/{total_count}]", end=" ")
            
            if upload_video(video_path, cover_path, int(channel_id), base_title, tags):
                success_count += 1
            
            # 上传间隔，避免请求过快
            if i < total_count:
                print("等待5秒后继续...")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print("\n\n用户取消了批量上传")
    
    # 上传结果总结
    print("\n" + "=" * 50)
    print("批量上传完成")
    print(f"成功: {success_count}/{total_count}")
    print(f"失败: {total_count - success_count}/{total_count}")

if __name__ == "__main__":
    main() 