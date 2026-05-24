#!/usr/bin/env python3
import json
import os
import plistlib
import shutil
import subprocess
import sys

def minimize_firmware(source_dir, firmware_prefix):
    fw_dir = os.path.join(source_dir, "IntelBluetoothFirmware", "fw")
    for f in os.listdir(fw_dir):
        if not f.startswith(firmware_prefix):
            os.remove(os.path.join(fw_dir, f))
    kept = [f for f in os.listdir(fw_dir) if f.startswith(firmware_prefix)]
    print(f"Firmware minimized: kept {len(kept)} files with prefix '{firmware_prefix}'")

def clean_cache(source_dir):
    for path in [
        os.path.join(source_dir, "IntelBluetoothFirmware", "FwBinary.cpp"),
    ]:
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed cache: {path}")

def apply_patches(source_dir, patches):
    for patch_file in patches:
        patch_path = os.path.join(os.environ.get("GITHUB_WORKSPACE", "."), patch_file)
        result = subprocess.run(
            ["git", "apply", patch_path],
            cwd=source_dir, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Patch {patch_file} FAILED:\n{result.stderr}")
            sys.exit(1)
        print(f"Applied patch: {patch_file}")

def build(source_dir, target):
    cmd = [
        "xcodebuild", "-project", "IntelBluetoothFirmware.xcodeproj",
        "-target", target, "-configuration", "Release",
        "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_REQUIRED=NO", "CODE_SIGNING_ALLOWED=NO",
        "LILU_KEXTPATH=$(SRCROOT)/Lilu.kext",
    ]
    print(f"Building {target}: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=source_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Build {target} FAILED:")
        print(result.stdout[-3000:] if result.stdout else "")
        print(result.stderr[-3000:] if result.stderr else "")
        sys.exit(1)
    print(f"Build {target} succeeded")

def minimize_plist(kext_path, keep_personalities):
    info_path = os.path.join(kext_path, "Contents", "Info.plist")
    with open(info_path, "rb") as f:
        plist = plistlib.load(f)
    personalities = plist.get("IOKitPersonalities", {})
    to_remove = [k for k in personalities if k not in keep_personalities]
    for k in to_remove:
        del personalities[k]
        print(f"Removed personality: {k}")
    with open(info_path, "wb") as f:
        plistlib.dump(plist, f)
    subprocess.run(["plutil", "-lint", info_path], capture_output=True)

def strip_binary(kext_path):
    kext_name = os.path.basename(kext_path)
    binary_name = kext_name.replace(".kext", "")
    binary_path = os.path.join(kext_path, "Contents", "MacOS", binary_name)
    if os.path.exists(binary_path):
        result = subprocess.run(["strip", "-S", "-x", binary_path], capture_output=True, text=True)
        if result.returncode == 0:
            size = os.path.getsize(binary_path)
            print(f"Stripped {binary_name} binary: {size/1024:.0f}KB")
        else:
            print(f"Strip warning: {result.stderr.strip()}")

def main():
    config_path = os.environ.get("CONFIG_PATH", "config/device-config.json")
    with open(config_path) as f:
        config = json.load(f)

    source_dir = os.environ.get("SOURCE_DIR", "IntelBluetoothFirmware")
    bt_config = config["bluetooth"]
    firmware_prefix = bt_config["firmware_prefix"]
    suffix = bt_config["personality_suffix"]
    patches = bt_config.get("patches", [])

    minimize_firmware(source_dir, firmware_prefix)
    clean_cache(source_dir)
    apply_patches(source_dir, patches)

    output_dir = os.environ.get("OUTPUT_DIR", "build-output")
    os.makedirs(output_dir, exist_ok=True)

    targets = [
        ("IntelBluetoothFirmware", "IntelBluetoothFirmware.kext", [f"IntelBluetoothFirmware_{suffix}"]),
        ("IntelBTPatcher", "IntelBTPatcher.kext", ["IntelBTPatcher"]),
    ]

    for target, kext_name, keep_pers in targets:
        build(source_dir, target)
        kext_path = os.path.join(source_dir, "build", "Release", kext_name)
        if not os.path.exists(kext_path):
            for root, dirs, files in os.walk(os.path.join(source_dir, "build")):
                if kext_name in dirs:
                    kext_path = os.path.join(root, kext_name)
                    break
        minimize_plist(kext_path, keep_pers)
        strip_binary(kext_path)
        dest = os.path.join(output_dir, kext_name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(kext_path, dest)
        print(f"Output: {dest}")

if __name__ == "__main__":
    main()
