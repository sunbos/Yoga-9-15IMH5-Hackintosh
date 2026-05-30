#!/usr/bin/env python3
import fnmatch
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

GITHUB_API = "https://api.github.com/repos"

def _version_sort_key(name):
    """Extract version number from filename for semantic sorting.

    Handles patterns like: AMFIPass-v1.10.0-RELEASE.zip -> (1, 10, 0)
    For date-stamped names like IO80211FamilyLegacy-2024-05-20-RELEASE.zip,
    extracts the full date: (2024, 5, 20).
    Falls back to (0,) if no version found.
    """
    # Prefer explicit version prefix (v1.2.3)
    m = re.search(r"v(\d+(?:\.\d+)+)", name)
    if m:
        return tuple(int(x) for x in m.group(1).split("."))
    # Date-stamped names (2024-05-20)
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", name)
    if m:
        return tuple(int(x) for x in m.groups())
    # Fall back to longest dotted number sequence
    matches = re.findall(r"(\d+(?:\.\d+)+)", name)
    if matches:
        return tuple(int(x) for x in max(matches, key=lambda s: s.count(".")).split("."))
    return (0,)

def _make_request(url):
    headers = {"User-Agent": "Yoga-9-15IMH5-Build"}
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 2:
                wait = 2 ** (attempt + 1)
                try:
                    wait = int(e.headers.get("Retry-After", wait))
                except (ValueError, TypeError):
                    pass
                print(f"  HTTP {e.code}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError as e:
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                print(f"  Network error ({e.reason}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise

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
    matches.sort(key=lambda e: _version_sort_key(e["name"]), reverse=True)
    download_url = matches[0]["download_url"]
    print(f"  Resolved {pattern} -> {matches[0]['name']}")
    return download_url

def download_and_extract(download_url, asset_name, output_dir, kext_names):
    tmp_dir = tempfile.mkdtemp()
    try:
        tmp_file = os.path.join(tmp_dir, asset_name)
        print(f"Downloading {asset_name}...")
        req = urllib.request.Request(download_url, headers={"User-Agent": "Yoga-9-15IMH5-Build"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    with open(tmp_file, "wb") as f:
                        shutil.copyfileobj(resp, f)
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt < 2:
                    wait = 2 ** (attempt + 1)
                    try:
                        wait = int(e.headers.get("Retry-After", wait))
                    except (ValueError, TypeError):
                        pass
                    print(f"  HTTP {e.code}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                raise
            except urllib.error.URLError as e:
                if attempt < 2:
                    wait = 2 ** (attempt + 1)
                    print(f"  Network error ({e.reason}), retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                raise
        if os.path.getsize(tmp_file) == 0:
            raise RuntimeError(f"Downloaded file is empty: {asset_name}")

        if asset_name.endswith(".zip"):
            with zipfile.ZipFile(tmp_file) as zf:
                zf.extractall(tmp_dir)
        elif asset_name.endswith(".kext"):
            if os.path.isdir(tmp_file):
                dst = os.path.join(output_dir, os.path.basename(tmp_file))
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(tmp_file, dst)
                print(f"Extracted: {os.path.basename(tmp_file)}")
            else:
                print(f"  Skipping direct .kext file download (not a directory): {asset_name}")
                return
            return
        else:
            print(f"  Unsupported format: {asset_name}")
            return

        found = set()
        wanted = set(kext_names)
        # Walk extracted tree and copy any .kext directory that matches
        # a requested name. Works for flat (kext.zip/Foo.kext) and nested
        # (kext.zip/release/Foo/Release/Foo.kext) layouts alike.
        for root, dirs, files in os.walk(tmp_dir):
            dirs[:] = [d for d in dirs if d != "__MACOSX"]
            for d in dirs:
                if d.endswith(".kext") and d in wanted and d not in found:
                    src = os.path.join(root, d)
                    dst = os.path.join(output_dir, d)
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    print(f"Extracted: {d}")
                    found.add(d)
        missing = wanted - found
        if missing:
            raise RuntimeError(f"Missing kexts in {asset_name}: {missing}")
    finally:
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

def select_nightly_asset(assets, pattern=None):
    """Select the best nightly build asset.

    Prefers assets matching the given pattern, then falls back to the
    most recently named zip file (date-stamped names sort lexicographically).
    """
    import fnmatch as _fnmatch
    zips = [a for a in assets if a["name"].endswith(".zip")]
    if not zips:
        return None
    if pattern:
        matched = [a for a in zips if _fnmatch.fnmatch(a["name"], pattern)]
        if matched:
            matched.sort(key=lambda a: a["name"], reverse=True)
            return matched[0]
    zips.sort(key=lambda a: a["name"], reverse=True)
    return zips[0]

def main():
    config_path = os.environ.get("CONFIG_PATH", "config/device-config.json")
    with open(config_path) as f:
        config = json.load(f)

    output_dir = os.environ.get("OUTPUT_DIR", "build-output")
    os.makedirs(output_dir, exist_ok=True)

    errors = 0

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
                errors += 1
        except Exception as e:
            print(f"{name}: error - {e}")
            errors += 1

    nightly = config.get("nightly_builds", {})
    if nightly:
        repo = nightly["repo"]
        asset_pattern = nightly.get("asset_pattern")
        all_kexts = []
        for info in nightly.get("kexts", {}).values():
            all_kexts.extend(info["kexts"])
        try:
            release = get_latest_release(repo)
            tag = release["tag_name"]
            print(f"\nnightly: {repo} latest = {tag}")
            asset = select_nightly_asset(release.get("assets", []), asset_pattern)
            if asset:
                download_and_extract(asset["browser_download_url"], asset["name"], output_dir, all_kexts)
            else:
                print(f"  No suitable asset found in release {tag}")
                errors += 1
        except Exception as e:
            print(f"nightly: error - {e}")
            errors += 1

    raw_downloads = config.get("raw_downloads", {})
    for name, info in raw_downloads.items():
        kexts = info["kexts"]
        try:
            raw_url = resolve_raw_download(info)
            asset_name = raw_url.split("/")[-1]
            print(f"\n{name}: downloading {asset_name}")
            download_and_extract(raw_url, asset_name, output_dir, kexts)
        except Exception as e:
            print(f"{name}: error - {e}")
            errors += 1

    print(f"\nDownloaded kexts in {output_dir}:")
    for item in sorted(os.listdir(output_dir)):
        if item.endswith(".kext"):
            print(f"  {item}")

    if errors:
        print(f"\n{errors} download(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
