#!/usr/bin/env python3
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

GITHUB_API = "https://api.github.com/repos"

def get_latest_release(repo):
    url = f"{GITHUB_API}/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "Yoga-9-15IMH5-Build"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def download_and_extract(asset_url, asset_name, output_dir, kext_names):
    tmp_dir = tempfile.mkdtemp()
    tmp_file = os.path.join(tmp_dir, asset_name)
    print(f"Downloading {asset_name}...")
    urllib.request.urlretrieve(asset_url, tmp_file)

    if asset_name.endswith(".zip"):
        with zipfile.ZipFile(tmp_file) as zf:
            zf.extractall(tmp_dir)
    elif asset_name.endswith(".kext"):
        dst = os.path.join(output_dir, os.path.basename(tmp_file))
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(tmp_file, dst)
        print(f"Extracted: {os.path.basename(tmp_file)}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    for root, dirs, files in os.walk(tmp_dir):
        for d in dirs:
            if d.endswith(".kext") and any(d == k or d.startswith(k.replace(".kext", "")) for k in kext_names):
                src = os.path.join(root, d)
                dst = os.path.join(output_dir, d)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"Extracted: {d}")

    shutil.rmtree(tmp_dir, ignore_errors=True)

def main():
    config_path = os.environ.get("CONFIG_PATH", "config/device-config.json")
    with open(config_path) as f:
        config = json.load(f)

    output_dir = os.environ.get("OUTPUT_DIR", "build-output")
    os.makedirs(output_dir, exist_ok=True)

    download_repos = config.get("download_repos", {})
    for name, info in download_repos.items():
        repo = info["repo"]
        kexts = info["kexts"]
        try:
            release = get_latest_release(repo)
            tag = release["tag_name"]
            print(f"\n{name}: {repo} latest release = {tag}")
            for asset in release.get("assets", []):
                if asset["name"].endswith(".zip") or asset["name"].endswith(".kext"):
                    download_and_extract(asset["browser_download_url"], asset["name"], output_dir, kexts)
                    break
        except Exception as e:
            print(f"{name}: error - {e}")

    print(f"\nDownloaded kexts in {output_dir}:")
    for item in sorted(os.listdir(output_dir)):
        if item.endswith(".kext"):
            print(f"  {item}")

if __name__ == "__main__":
    main()
