#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
import time
from base64 import b64decode
from hashlib import sha1
from math import ceil
from mimetypes import guess_type
from pathlib import Path
import getpass
import requests


class AcFunUploader:
    def __init__(self):
        self.session = requests.Session()
        # 设置通用请求头
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": "https://member.acfun.cn",
            "Referer": "https://member.acfun.cn/"
        })
        
        # API 端点
        self.LOGIN_URL = "https://id.app.acfun.cn/rest/web/login/signin"
        self.TOKEN_URL = "https://member.acfun.cn/video/api/getKSCloudToken"
        self.FRAGMENT_URL = "https://upload.kuaishouzt.com/api/upload/fragment"
        self.COMPLETE_URL = "https://upload.kuaishouzt.com/api/upload/complete"
        self.FINISH_URL = "https://member.acfun.cn/video/api/uploadFinish"
        self.C_VIDEO_URL = "https://member.acfun.cn/video/api/createVideo"
        self.C_DOUGA_URL = "https://member.acfun.cn/video/api/createDouga"
        self.QINIU_URL = "https://member.acfun.cn/common/api/getQiniuToken"
        self.COVER_URL = "https://member.acfun.cn/common/api/getUrlAfterUpload"

    def log(self, *msg):
        """输出日志信息"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f'[{timestamp}]', *msg)

    def calc_sha1(self, data: bytes) -> str:
        """计算数据的SHA1哈希值"""
        sha1_obj = sha1()
        sha1_obj.update(data)
        return sha1_obj.hexdigest()

    def load_cookies(self, cookie_file: str) -> bool:
        """从文件加载cookie，支持Netscape和JSON格式"""
        try:
            if not os.path.exists(cookie_file):
                self.log(f"Cookie文件不存在: {cookie_file}")
                return False
            
            with open(cookie_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 判断文件格式
            if content.startswith('# Netscape HTTP Cookie File') or '\t' in content:
                # Netscape格式
                cookie_count = self._load_netscape_cookies(content)
                self.log(f"从Netscape格式文件加载了 {cookie_count} 个cookie")
            else:
                # JSON格式
                cookies_data = json.loads(content)
                for cookie in cookies_data:
                    self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
                self.log(f"从JSON格式文件加载了 {len(cookies_data)} 个cookie")
            
            # 测试cookie是否有效
            return self.test_login()
        except Exception as e:
            self.log(f"加载cookie文件失败: {e}")
            return False

    def _load_netscape_cookies(self, content: str) -> int:
        """加载Netscape格式的cookie"""
        lines = content.split('\n')
        cookie_count = 0
        
        for line in lines:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            
            # Netscape格式: domain	flag	path	secure	expiration	name	value
            parts = line.split('\t')
            if len(parts) >= 7:
                domain = parts[0]
                path = parts[2]
                secure = parts[3].upper() == 'TRUE'
                expiration = parts[4]
                name = parts[5]
                value = parts[6]
                
                # 设置cookie
                self.session.cookies.set(
                    name=name,
                    value=value,
                    domain=domain,
                    path=path,
                    secure=secure
                )
                cookie_count += 1
        
        return cookie_count

    def save_cookies(self, cookie_file: str):
        """保存cookie到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
            
            cookies_data = []
            for cookie in self.session.cookies:
                cookies_data.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path
                })
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, ensure_ascii=False, indent=2)
            
            self.log(f"Cookie已保存到: {cookie_file}")
        except Exception as e:
            self.log(f"保存cookie失败: {e}")

    def test_network_connectivity(self) -> bool:
        """测试网络连接"""
        test_urls = [
            "https://www.acfun.cn",
            "https://member.acfun.cn",
            "https://upload.kuaishouzt.com"
        ]
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    self.log(f"网络连接正常: {url}")
                else:
                    self.log(f"网络连接异常: {url} (状态码: {response.status_code})")
                    return False
            except Exception as e:
                self.log(f"网络连接失败: {url} ({e})")
                return False
        
        return True

    def test_login(self) -> bool:
        """测试登录状态"""
        try:
            # 使用一个简单的API来测试登录状态
            response = self.session.get("https://member.acfun.cn/video/api/getMyChannels")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    return result.get('result') == 0
                except:
                    # 如果不是JSON，可能是HTML页面，检查是否是登录页面
                    if "login" in response.text.lower() or "登录" in response.text:
                        return False
                    # 如果是其他HTML页面（如创作中心），说明已登录
                    return True
            return False
        except Exception as e:
            return False

    def login(self, username: str, password: str) -> bool:
        """用户名密码登录"""
        try:
            response = self.session.post(
                self.LOGIN_URL,
                data={
                    'username': username,
                    'password': password,
                    'key': '',
                    'captcha': ''
                }
            )
            
            result = response.json()
            if result.get('result') == 0:
                self.log('登录成功')
                return True
            else:
                self.log(f"登录失败: {result.get('error_msg', '账号密码错误')}")
                return False
        except Exception as e:
            self.log(f"登录过程中出错: {e}")
            return False

    def get_token(self, filename: str, filesize: int) -> tuple:
        """获取上传token"""
        response = self.session.post(
            self.TOKEN_URL,
            data={
                "fileName": filename,
                "size": filesize,
                "template": "1"
            }
        )
        result = response.json()
        return result["taskId"], result["token"], result["uploadConfig"]["partSize"]

    def upload_chunk(self, block: bytes, fragment_id: int, upload_token: str) -> bool:
        """上传分块"""
        import ssl
        import time
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # 创建专用的上传session
        upload_session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # 配置适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        upload_session.mount("http://", adapter)
        upload_session.mount("https://", adapter)
        
        # 设置请求头
        headers = {
            "Content-Type": "application/octet-stream",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        for attempt in range(3):
            try:
                # 添加延迟避免请求过快
                if attempt > 0:
                    time.sleep(2 ** attempt)  # 指数退避
                
                # 第一次尝试使用标准SSL
                verify_ssl = True if attempt == 0 else False
                
                response = upload_session.post(
                    self.FRAGMENT_URL,
                    params={
                        "fragment_id": fragment_id,
                        "upload_token": upload_token
                    },
                    data=block,
                    headers=headers,
                    timeout=(30, 120),  # (连接超时, 读取超时)
                    verify=verify_ssl,  # 第一次验证SSL，后续尝试跳过验证
                    stream=False
                )
                
                # 检查响应
                if response.status_code == 200:
                    result = response.json()
                    if result.get("result") == 1:
                        self.log(f"分块 {fragment_id + 1} 上传成功")
                        return True
                    else:
                        self.log(f"分块 {fragment_id + 1} 上传失败: {result}")
                else:
                    self.log(f"分块 {fragment_id + 1} HTTP错误: {response.status_code}")
                    
            except ssl.SSLError as e:
                self.log(f"分块 {fragment_id + 1} SSL错误，重试第 {attempt + 1} 次: {e}")
                if attempt == 2:  # 最后一次尝试
                    self.log("SSL连接持续失败，可能是网络问题或防火墙阻拦")
            except requests.exceptions.Timeout as e:
                self.log(f"分块 {fragment_id + 1} 超时，重试第 {attempt + 1} 次: {e}")
            except requests.exceptions.ConnectionError as e:
                self.log(f"分块 {fragment_id + 1} 连接错误，重试第 {attempt + 1} 次: {e}")
            except Exception as e:
                self.log(f"分块 {fragment_id + 1} 未知错误，重试第 {attempt + 1} 次: {e}")
        
        return False

    def complete_upload(self, fragment_count: int, upload_token: str):
        """完成上传"""
        import time
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # 创建专用的上传session
        upload_session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # 配置适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        upload_session.mount("http://", adapter)
        upload_session.mount("https://", adapter)
        
        headers = {
            "Content-Length": "0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Connection": "keep-alive"
        }
        
        for attempt in range(3):
            try:
                if attempt > 0:
                    time.sleep(2 ** attempt)
                
                response = upload_session.post(
                    self.COMPLETE_URL,
                    params={
                        "fragment_count": fragment_count,
                        "upload_token": upload_token
                    },
                    headers=headers,
                    timeout=(30, 60),
                    verify=True
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("result") == 1:
                        self.log("上传完成确认成功")
                        return
                    else:
                        self.log(f"完成上传失败: {result}")
                else:
                    self.log(f"完成上传HTTP错误: {response.status_code}")
                    
            except Exception as e:
                self.log(f"完成上传出错，重试第 {attempt + 1} 次: {e}")
                if attempt == 2:
                    self.log("完成上传失败，但文件可能已上传成功")

    def upload_finish(self, task_id: int):
        """上传完成处理"""
        response = self.session.post(
            self.FINISH_URL,
            data={"taskId": task_id}
        )
        
        if response.json()["result"] != 0:
            self.log(f"上传完成处理失败: {response.text}")

    def create_video(self, video_key: int, filename: str) -> int:
        """创建视频"""
        response = self.session.post(
            self.C_VIDEO_URL,
            data={
                "videoKey": video_key,
                "fileName": filename,
                "vodType": "ksCloud"
            },
            headers={
                "origin": "https://member.acfun.cn",
                "referer": "https://member.acfun.cn/upload-video"
            }
        )
        
        result = response.json()
        if result["result"] != 0:
            self.log(f"创建视频失败: {response.text}")
            return None
        
        self.upload_finish(video_key)
        return result["videoId"]

    def upload_cover(self, image_path: str) -> str:
        """上传封面图片"""
        # 生成随机文件名
        import random
        import string
        
        file_name = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # 获取七牛token
        response = self.session.post(
            self.QINIU_URL,
            data={"fileName": f"{file_name}.jpeg"}
        )
        
        token = response.json()["info"]["token"]
        
        # 上传图片
        with open(image_path, "rb") as f:
            chunk_data = f.read()
        
        self.upload_chunk(chunk_data, 0, token)
        self.complete_upload(1, token)
        
        # 获取上传后的URL
        response = self.session.post(
            self.COVER_URL,
            data={"bizFlag": "web-douga-cover", "token": token}
        )
        
        return response.json()["url"]

    def create_douga(self, file_path: str, title: str, channel_id: int, cover_path: str,
                     desc: str = "", tags: list = None, creation_type: int = 3, 
                     original_url: str = ""):
        """创建投稿"""
        if tags is None:
            tags = []
        
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # 获取上传token
        task_id, token, part_size = self.get_token(file_name, file_size)
        fragment_count = ceil(file_size / part_size)
        
        self.log(f"开始上传 {file_name}，共 {fragment_count} 个分块")
        
        # 上传视频文件
        with open(file_path, "rb") as f:
            for fragment_id in range(fragment_count):
                chunk_data = f.read(part_size)
                if not chunk_data:
                    break
                
                if not self.upload_chunk(chunk_data, fragment_id, token):
                    self.log(f"分块 {fragment_id + 1} 上传失败")
                    return False
        
        # 完成上传
        self.complete_upload(fragment_count, token)
        
        # 创建视频
        video_id = self.create_video(task_id, file_name)
        if not video_id:
            return False
        
        # 上传封面
        cover_url = self.upload_cover(cover_path)
        
        # 创建投稿
        data = {
            "title": title,
            "description": desc,
            "tagNames": json.dumps(tags),
            "creationType": creation_type,
            "channelId": channel_id,
            "coverUrl": cover_url,
            "videoInfos": json.dumps([{"videoId": video_id, "title": title}]),
            "isJoinUpCollege": "0"
        }
        
        if creation_type == 1:  # 转载
            data["originalLinkUrl"] = original_url
            data["originalDeclare"] = "0"
        else:  # 原创
            data["originalDeclare"] = "1"
        
        response = self.session.post(
            self.C_DOUGA_URL,
            data=data,
            headers={
                "origin": "https://member.acfun.cn",
                "referer": "https://member.acfun.cn/upload-video"
            }
        )
        
        result = response.json()
        if result["result"] == 0 and "dougaId" in result:
            self.log(f"视频投稿成功！AC号：{result['dougaId']}")
            return True
        else:
            self.log(f"视频投稿失败: {response.text}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="AcFun 命令行投稿工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python acfun_cli.py video.mp4 -c cover.png -t "视频标题" --cid 63
  python acfun_cli.py video.mp4 -c cover.png -t "视频标题" --cid 63 -u username -p password
  python acfun_cli.py video.mp4 -c cover.png -t "视频标题" --cid 63 --tags "游戏" "实况"
        """
    )
    
    parser.add_argument("file_path", help="视频文件路径")
    parser.add_argument("-c", "--cover", required=True, help="封面图片路径")
    parser.add_argument("-t", "--title", required=True, help="稿件标题")
    parser.add_argument("--cid", "--channel_id", type=int, required=True, help="频道ID")
    parser.add_argument("-d", "--desc", default="", help="稿件简介")
    parser.add_argument("--tags", nargs="*", default=[], help="稿件标签")
    parser.add_argument("--type", type=int, choices=[1, 3], default=3, 
                       help="创作类型 (1:转载, 3:原创)")
    parser.add_argument("--original_url", default="", help="转载来源URL (仅转载时需要)")
    parser.add_argument("-u", "--username", help="AcFun用户名")
    parser.add_argument("-p", "--password", help="AcFun密码")
    parser.add_argument("--cookie_file", default="cookies/ac_cookies.txt", 
                       help="Cookie文件路径")
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.file_path):
        print(f"错误: 视频文件不存在: {args.file_path}")
        sys.exit(1)
    
    if not os.path.exists(args.cover):
        print(f"错误: 封面文件不存在: {args.cover}")
        sys.exit(1)
    
    # 创建上传器
    uploader = AcFunUploader()
    
    # 尝试登录
    logged_in = False
    
    # 首先尝试使用cookie登录
    if uploader.load_cookies(args.cookie_file):
        uploader.log("使用Cookie登录成功")
        logged_in = True
    
    # 如果cookie登录失败，尝试用户名密码登录
    if not logged_in:
        username = args.username
        password = args.password
        
        if not username:
            username = input("请输入AcFun用户名: ")
        
        if not password:
            password = getpass.getpass("请输入AcFun密码: ")
        
        if uploader.login(username, password):
            logged_in = True
            # 保存新的cookie
            uploader.save_cookies(args.cookie_file)
        else:
            print("登录失败，请检查用户名和密码")
            sys.exit(1)
    
    if not logged_in:
        print("登录失败")
        sys.exit(1)
    
    # 测试网络连接
    uploader.log("正在测试网络连接...")
    if not uploader.test_network_connectivity():
        print("\n网络连接测试失败！")
        print("可能的解决方案:")
        print("1. 检查网络连接是否正常")
        print("2. 检查防火墙设置")
        print("3. 尝试使用VPN或更换网络环境")
        print("4. 检查DNS设置")
        
        choice = input("\n是否继续尝试上传? (y/N): ").lower().strip()
        if choice not in ['y', 'yes']:
            print("已取消上传")
            sys.exit(1)
    
    # 执行上传
    uploader.log("开始上传流程...")
    success = uploader.create_douga(
        file_path=args.file_path,
        title=args.title,
        channel_id=args.cid,
        cover_path=args.cover,
        desc=args.desc,
        tags=args.tags,
        creation_type=args.type,
        original_url=args.original_url
    )
    
    if success:
        uploader.log("上传完成！")
        print("\n🎉 视频上传成功！")
    else:
        uploader.log("上传失败")
        print("\n❌ 上传失败，可能的原因:")
        print("1. 网络连接不稳定")
        print("2. 文件格式不支持")
        print("3. 文件过大")
        print("4. 服务器临时故障")
        print("\n建议:")
        print("- 检查网络连接")
        print("- 稍后重试")
        print("- 确认视频文件格式正确")
        sys.exit(1)


if __name__ == "__main__":
    main() 