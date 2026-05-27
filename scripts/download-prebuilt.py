#!/usr/bin/env python3
import fnmatch
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

GITHUB_API = "https://api.github.com/repos"

def _make_request(url):
    headers = {"User-Agent": "Yoga-9-15IMH5-Build"}
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get_latest_release(repo):
    url = f"{GITHUB_API}/{repo}/releases/latest"
    return _make_request(url)

def resolve_raw_download(info):
    if "url" in info:
        return info["url"]
    repo = info["repo"]
    path = info["path"]
    pattern = info["pattern"]
    url = f"{GITHUB_API}/{repo}/contents/{path}"
    entries = _make_request(url)
    matches = [e for e in entries if e.get("type") == "file" and fnmatch.fnmatch(e["name"], pattern)]
    if not matches:
        raise RuntimeError(f"No file matching '{pattern}' in {repo}/{path}")
    matches.sort(key=lambda e: e["name"], reverse=True)
    download_url = matches[0]["download_url"]
    print(f"  Resolved {pattern} -> {matches[0]['name']}")
    return download_url

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
        dirs[:] = [d for d in dirs if d != "__MACOSX"]
        for d in dirs:
            if d in kext_names:
                src = os.path.join(root, d)
                dst = os.path.join(output_dir, d)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"Extracted: {d}")

    shutil.rmtree(tmp_dir, ignore_errors=True)


def download_raw(raw_url, asset_name, output_dir, kext_names):
    tmp_dir = tempfile.mkdtemp()
    tmp_file = os.path.join(tmp_dir, asset_name)
    print(f"Downloading raw: {asset_name}...")
    urllib.request.urlretrieve(raw_url, tmp_file)

    if asset_name.endswith(".zip"):
        with zipfile.ZipFile(tmp_file) as zf:
            zf.extractall(tmp_dir)
    else:
        print(f"  Unsupported format: {asset_name}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
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

    shutil.rmtree(tmp_dir, ignore_errors=True)

def select_best_asset(assets):
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
            asset = select_best_asset(release.get("assets", []))
            if asset:
                download_and_extract(asset["browser_download_url"], asset["name"], output_dir, kexts)
            else:
                print(f"  No suitable asset found in release {tag}")
        except Exception as e:
            print(f"{name}: error - {e}")

    raw_downloads = config.get("raw_downloads", {})
    for name, info in raw_downloads.items():
        kexts = info["kexts"]
        try:
            raw_url = resolve_raw_download(info)
            asset_name = raw_url.split("/")[-1]
            print(f"\n{name}: downloading {asset_name}")
            download_raw(raw_url, asset_name, output_dir, kexts)
        except Exception as e:
            print(f"{name}: error - {e}")

    print(f"\nDownloaded kexts in {output_dir}:")
    for item in sorted(os.listdir(output_dir)):
        if item.endswith(".kext"):
            print(f"  {item}")

if __name__ == "__main__":
    main()
