#!/usr/bin/env python3
import fnmatch
import os
import shutil
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import (
    make_request,
    get_latest_release,
    load_config,
    extract_archive,
)


GITHUB_API = "https://api.github.com/repos"


def resolve_raw_download(info):
    """
    解析原始下载链接
    """
    if "url" in info:
        return info["url"]
    repo = info["repo"]
    path = info["path"]
    pattern = info["pattern"]
    url = f"{GITHUB_API}/{repo}/contents/{path}"
    entries = make_request(url)
    matches = [e for e in entries if e.get("type") == "file" and fnmatch.fnmatch(e["name"], pattern)]
    if not matches:
        raise RuntimeError(f"No file matching '{pattern}' in {repo}/{path}")
    matches.sort(key=lambda e: e["name"], reverse=True)
    download_url = matches[0]["download_url"]
    print(f"  Resolved {pattern} -> {matches[0]['name']}")
    return download_url


def download_file(url, dest_path):
    """
    下载文件
    """
    print(f"Downloading {os.path.basename(dest_path)}...")
    urllib.request.urlretrieve(url, dest_path)


def select_best_asset(assets):
    """
    选择最佳的 release asset
    """
    release_assets = [a for a in assets if "RELEASE" in a["name"].upper()]
    if release_assets:
        return release_assets[0]
    zip_assets = [a for a in assets if a["name"].endswith(".zip")]
    if zip_assets:
        return zip_assets[0]
    kext_assets = [a for a in assets if a["name"].endswith(".kext")]
    if kext_assets:
        return kext_assets[0]
    return None


def main():
    config = load_config()
    output_dir = os.environ.get("OUTPUT_DIR", "build-output")
    os.makedirs(output_dir, exist_ok=True)

    # 处理 download_repos
    download_repos = config.get("download_repos", {})
    for name, info in download_repos.items():
        repo = info["repo"]
        kexts = info["kexts"]
        try:
            release = get_latest_release(repo)
            tag = release["tag_name"]
            print(f"\n{name}: {repo} latest release = {tag}")
            asset = select_best_asset(release.get("assets", []))
            if asset:
                tmp_dir = tempfile.mkdtemp()
                try:
                    tmp_file = os.path.join(tmp_dir, asset["name"])
                    download_file(asset["browser_download_url"], tmp_file)
                    extract_archive(tmp_file, output_dir, kexts)
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            else:
                print(f"  No suitable asset found in release {tag}")
        except Exception as e:
            print(f"{name}: error - {e}")

    # 处理 raw_downloads
    raw_downloads = config.get("raw_downloads", {})
    for name, info in raw_downloads.items():
        kexts = info["kexts"]
        try:
            raw_url = resolve_raw_download(info)
            asset_name = raw_url.split("/")[-1]
            print(f"\n{name}: downloading {asset_name}")
            tmp_dir = tempfile.mkdtemp()
            try:
                tmp_file = os.path.join(tmp_dir, asset_name)
                download_file(raw_url, tmp_file)
                extract_archive(tmp_file, output_dir, kexts)
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception as e:
            print(f"{name}: error - {e}")

    # 打印结果
    print(f"\nDownloaded kexts in {output_dir}:")
    for item in sorted(os.listdir(output_dir)):
        if item.endswith(".kext"):
            print(f"  {item}")


if __name__ == "__main__":
    import sys
    main()
