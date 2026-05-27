#!/usr/bin/env python3
"""
共享工具函数模块
"""
import json
import os
import plistlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

GITHUB_API = "https://api.github.com/repos"


def make_request(url):
    """
    向 GitHub API 发送请求
    """
    headers = {"User-Agent": "Yoga-9-15IMH5-Build"}
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_latest_sha(repo):
    """
    获取仓库的最新提交 SHA
    """
    for branch in ("master", "main"):
        try:
            url = f"{GITHUB_API}/{repo}/commits/{branch}"
            data = make_request(url)
            return data["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
    raise RuntimeError(f"No master or main branch found for {repo}")


def get_latest_release_tag(repo):
    """
    获取仓库的最新 release 标签
    """
    try:
        url = f"{GITHUB_API}/{repo}/releases/latest"
        data = make_request(url)
        return data.get("tag_name", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ""
        raise


def get_latest_release(repo):
    """
    获取仓库的最新 release 信息
    """
    url = f"{GITHUB_API}/{repo}/releases/latest"
    return make_request(url)


def load_config():
    """
    加载配置文件
    """
    config_path = os.environ.get("CONFIG_PATH", "config/device-config.json")
    with open(config_path) as f:
        return json.load(f)


def strip_binary(kext_path):
    """
    剥离二进制文件的调试符号
    """
    kext_name = os.path.basename(kext_path)
    binary_name = kext_name.replace(".kext", "")
    binary_path = os.path.join(kext_path, "Contents", "MacOS", binary_name)
    if os.path.exists(binary_path):
        result = subprocess.run(
            ["strip", "-S", "-x", binary_path], capture_output=True, text=True
        )
        if result.returncode == 0:
            size = os.path.getsize(binary_path)
            print(f"Stripped {binary_name} binary: {size/1024:.0f}KB")
        else:
            print(f"Strip warning: {result.stderr.strip()}")


def find_kext_in_build(source_dir, kext_name):
    """
    在 build 目录中查找 kext
    """
    kext_path = os.path.join(source_dir, "build", "Release", kext_name)
    if os.path.exists(kext_path):
        return kext_path

    for root, dirs, files in os.walk(os.path.join(source_dir, "build")):
        if kext_name in dirs:
            return os.path.join(root, kext_name)
    return None


def copy_kext_to_output(kext_path, output_dir):
    """
    复制 kext 到输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, os.path.basename(kext_path))
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(kext_path, dest)
    print(f"Output: {dest}")


def extract_archive(archive_path, output_dir, kext_names):
    """
    从归档中提取指定的 kext
    """
    import tempfile

    tmp_dir = tempfile.mkdtemp()
    try:
        if archive_path.endswith(".zip"):
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(tmp_dir)
        else:
            print(f"Unsupported archive format: {archive_path}")
            return

        for root, dirs, files in os.walk(tmp_dir):
            dirs[:] = [d for d in dirs if d != "__MACOSX"]
            for d in dirs:
                if d in kext_names:
                    src = os.path.join(root, d)
                    dst = os.path.join(output_dir, d)
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    print(f"Extracted: {d}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
