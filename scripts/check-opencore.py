#!/usr/bin/env python3
"""Check for OpenCore updates, download latest release, merge config, and prepare EFI."""

import json
import os
import plistlib
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile

GITHUB_API = "https://api.github.com/repos"


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


def download_file(url, dest):
    headers = {"User-Agent": "Yoga-9-15IMH5-Build"}
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=300) as resp:
        with open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)


def download_extra_drivers(extra_drivers, drivers_dir):
    """Download extra drivers (e.g. HfsPlus.efi, apfs_aligned.efi) from external repos.

    extra_drivers format:
      {"DriverName.efi": "repo/name"}  (legacy, root path)
      {"DriverName.efi": {"repo": "repo/name", "path": "sub/dir"}}  (with path)
    """
    for driver_name, source in extra_drivers.items():
        dest = os.path.join(drivers_dir, driver_name)
        if os.path.exists(dest):
            print(f"  Extra driver already present: {driver_name}")
            continue
        if isinstance(source, str):
            repo = source
            path = ""
        else:
            repo = source["repo"]
            path = source.get("path", "")
        api_path = f"{path}/{driver_name}" if path else driver_name
        url = f"{GITHUB_API}/{repo}/contents/{api_path}"
        try:
            entries = _make_request(url)
            download_url = entries.get("download_url", "")
            if not download_url:
                print(f"  Warning: no download URL for {driver_name} from {repo}")
                continue
            print(f"  Downloading extra driver: {driver_name} from {repo}/{api_path}")
            download_file(download_url, dest)
        except Exception as e:
            print(f"  Warning: failed to download {driver_name} from {repo}: {e}")


def download_resources(output_dir):
    """Download OpenCanopy Resources (Font, Image, Label) from OcBinaryData."""
    repo = "acidanthera/OcBinaryData"
    resource_dirs = ["Font", "Image", "Label"]
    resources_base = os.path.join(output_dir, "EFI", "OC", "Resources")

    for res_dir in resource_dirs:
        local_dir = os.path.join(resources_base, res_dir)
        if os.path.isdir(local_dir) and os.listdir(local_dir):
            print(f"  Resources/{res_dir} already present, skipping download")
            continue

        api_url = f"{GITHUB_API}/{repo}/contents/Resources/{res_dir}"
        try:
            entries = _make_request(api_url)
            if not isinstance(entries, list):
                print(f"  Warning: unexpected response for Resources/{res_dir}")
                continue
            os.makedirs(local_dir, exist_ok=True)
            for entry in entries:
                if entry.get("type") != "file":
                    continue
                name = entry["name"]
                download_url = entry.get("download_url", "")
                if not download_url:
                    continue
                dest = os.path.join(local_dir, name)
                print(f"  Downloading Resources/{res_dir}/{name}")
                download_file(download_url, dest)
        except Exception as e:
            print(f"  Warning: failed to download Resources/{res_dir}: {e}")

    # Download Image subdirectories (e.g. Acidanthera/GoldenGate)
    image_dir = os.path.join(resources_base, "Image")
    if os.path.isdir(image_dir) and not any(
        os.path.isdir(os.path.join(image_dir, d)) for d in os.listdir(image_dir)
    ):
        _download_resource_subdir(repo, "Resources/Image", image_dir)


def _download_resource_subdir(repo, api_path, local_dir):
    """Recursively download resource directories from a GitHub repo."""
    api_url = f"{GITHUB_API}/{repo}/contents/{api_path}"
    try:
        entries = _make_request(api_url)
        if not isinstance(entries, list):
            return
        for entry in entries:
            name = entry["name"]
            if entry.get("type") == "dir":
                sub_local = os.path.join(local_dir, name)
                os.makedirs(sub_local, exist_ok=True)
                _download_resource_subdir(repo, f"{api_path}/{name}", sub_local)
            elif entry.get("type") == "file":
                download_url = entry.get("download_url", "")
                if download_url:
                    dest = os.path.join(local_dir, name)
                    if not os.path.exists(dest):
                        print(f"  Downloading {api_path}/{name}")
                        download_file(download_url, dest)
    except Exception as e:
        print(f"  Warning: failed to download {api_path}: {e}")


def extract_opencore(zip_path, output_dir, drivers):
    """Extract OpenCore files from the RELEASE zip."""
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename

            # Extract X64/EFI files
            if "X64/EFI/" in name and not info.is_dir():
                rel_path = name.split("X64/EFI/", 1)[1]
                dest = os.path.join(output_dir, "EFI", rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)

            # Extract Docs/Sample.plist
            if name.endswith("Docs/Sample.plist") and not info.is_dir():
                dest = os.path.join(output_dir, "Sample.plist")
                with zf.open(info) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    # Filter drivers - only keep the ones we need
    drivers_dir = os.path.join(output_dir, "EFI", "OC", "Drivers")
    if os.path.isdir(drivers_dir):
        for f in os.listdir(drivers_dir):
            if f.endswith(".efi") and f not in drivers and f != "OpenRuntime.efi":
                os.remove(os.path.join(drivers_dir, f))
                print(f"  Removed unused driver: {f}")


def _convert_from_json(obj):
    """Convert JSON-serialized bytes back to bytes."""
    if isinstance(obj, dict):
        if "__bytes__" in obj:
            return bytes.fromhex(obj["__bytes__"])
        return {k: _convert_from_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_from_json(i) for i in obj]
    return obj


def _set_nested(d, path, value):
    """Set a value in a nested dict using dot-separated path."""
    keys = path.split(".")
    for key in keys[:-1]:
        if key not in d:
            d[key] = {}
        d = d[key]
    d[keys[-1]] = value


def merge_config(sample_plist_path, overrides_path, output_path):
    """Merge Sample.plist with oc-overrides.json to produce config.plist."""
    with open(sample_plist_path, "rb") as f:
        config = plistlib.load(f)

    with open(overrides_path) as f:
        overrides_raw = json.load(f)

    overrides = _convert_from_json(overrides_raw)

    applied = 0
    for path, value in overrides.items():
        _set_nested(config, path, value)
        applied += 1

    with open(output_path, "wb") as f:
        plistlib.dump(config, f, sort_keys=False)

    print(f"  Merged {applied} overrides into config.plist")
    return config


def diff_configs(old_path, new_config):
    """Compare old config with new merged config and report changes."""
    if not os.path.exists(old_path):
        return ["No previous config found"]

    with open(old_path, "rb") as f:
        old = plistlib.load(f)

    changes = []

    def _compare(old_d, new_d, path=""):
        for key in new_d:
            full_path = f"{path}.{key}" if path else key
            if key not in old_d:
                changes.append(f"+ {full_path}")
            elif isinstance(new_d[key], dict) and isinstance(old_d.get(key), dict):
                _compare(old_d[key], new_d[key], full_path)
            elif old_d.get(key) != new_d[key]:
                changes.append(f"~ {full_path}")

    _compare(old, new_config)
    return changes


def main():
    config_path = os.environ.get("CONFIG_PATH", "config/device-config.json")
    overrides_path = os.environ.get("OVERRIDES_PATH", "config/oc-overrides.json")
    output_dir = os.environ.get("OUTPUT_DIR", "build-output/opencore")

    with open(config_path) as f:
        config = json.load(f)

    oc_config = config.get("opencore", {})
    repo = oc_config.get("repo", "acidanthera/OpenCorePkg")
    current_version = oc_config.get("current_version", "")
    drivers = oc_config.get("drivers", [])

    print(f"Last built OpenCore version: {current_version or '(none)'}")
    print(f"Checking {repo} for updates...")

    try:
        release = get_latest_release(repo)
    except Exception as e:
        print(f"Error checking for updates: {e}")
        print("Skipping OpenCore update")
        output_path = os.environ.get("GITHUB_OUTPUT", "/tmp/opencore-output.txt")
        with open(output_path, "a") as f:
            f.write("opencore_updated=false\n")
        return

    latest_version = release["tag_name"].lstrip("v")
    print(f"Latest OpenCore version: {latest_version}")

    if latest_version == current_version:
        print("Already up to date, downloading current version for EFI assembly...")

    is_update = latest_version != current_version
    if is_update:
        if current_version:
            print(f"New version available: {current_version} -> {latest_version}")
        else:
            print(f"OpenCore version will be set to: {latest_version}")

    # Find RELEASE asset
    asset = None
    for a in release.get("assets", []):
        if "RELEASE" in a["name"].upper() and a["name"].endswith(".zip"):
            asset = a
            break

    if not asset:
        print("No RELEASE asset found!")
        output_path = os.environ.get("GITHUB_OUTPUT", "/tmp/opencore-output.txt")
        with open(output_path, "a") as f:
            f.write("opencore_updated=false\n")
        return

    # Download
    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, asset["name"])
    print(f"Downloading {asset['name']}...")
    download_file(asset["browser_download_url"], zip_path)

    # Extract
    print("Extracting OpenCore files...")
    extract_opencore(zip_path, output_dir, drivers)

    # Download extra drivers (e.g. HfsPlus.efi, apfs_aligned.efi)
    extra_drivers = oc_config.get("extra_drivers", {})
    if extra_drivers:
        drivers_dir = os.path.join(output_dir, "EFI", "OC", "Drivers")
        print("Downloading extra drivers...")
        download_extra_drivers(extra_drivers, drivers_dir)

    # Download OpenCanopy Resources (Font, Image, Label)
    print("Downloading OpenCanopy Resources...")
    download_resources(output_dir)

    # Merge Sample.plist with overrides → config.plist
    sample_plist = os.path.join(output_dir, "Sample.plist")
    config_output = os.path.join(output_dir, "EFI", "OC", "config.plist")

    if os.path.exists(sample_plist) and os.path.exists(overrides_path):
        print("Merging Sample.plist with oc-overrides.json...")
        new_config = merge_config(sample_plist, overrides_path, config_output)

        # Compare with old config if exists
        old_config_path = os.path.join("EFI", "OC", "config.plist")
        if os.path.exists(old_config_path):
            changes = diff_configs(old_config_path, new_config)
            if changes:
                print(f"\nConfig changes ({len(changes)}):")
                for c in changes:
                    print(f"  {c}")
                with open(os.path.join(output_dir, "config-changes.txt"), "w") as f:
                    f.write("\n".join(changes))
            else:
                print("  No config changes")
    else:
        print("  Warning: Sample.plist or oc-overrides.json not found, skipping merge")

    # Clean up zip
    os.remove(zip_path)

    # Update version in device-config.json
    if is_update:
        config["opencore"]["current_version"] = latest_version
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        if current_version:
            print(f"\nUpdated device-config.json: OpenCore {current_version} -> {latest_version}")
        else:
            print(f"\nSet device-config.json: OpenCore version = {latest_version}")

    # Output
    output_path = os.environ.get("GITHUB_OUTPUT", "/tmp/opencore-output.txt")
    with open(output_path, "a") as f:
        f.write("opencore_updated=true\n")
        f.write(f"opencore_version={latest_version}\n")

    print(f"\nOpenCore {latest_version} ready for assembly.")


if __name__ == "__main__":
    main()
