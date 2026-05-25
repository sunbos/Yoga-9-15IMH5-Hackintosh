#!/usr/bin/env python3
import json
import os
import plistlib
import shutil
import subprocess
import sys

def minimize_firmware(source_dir, firmware_name):
    fw_dir = os.path.join(source_dir, "itlwm", "firmware")
    for f in os.listdir(fw_dir):
        if f != firmware_name:
            os.remove(os.path.join(fw_dir, f))
    print(f"Firmware minimized: kept only {firmware_name}")

def clean_cache(source_dir):
    for path in [
        os.path.join(source_dir, "include", "FwBinary.cpp"),
    ]:
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed cache: {path}")
    derived_data = os.path.expanduser("~/Library/Developer/Xcode/DerivedData")
    if os.path.exists(derived_data):
        for d in os.listdir(derived_data):
            if "AirportItlwm" in d or "itlwm" in d:
                shutil.rmtree(os.path.join(derived_data, d))
                print(f"Removed DerivedData: {d}")

def build(source_dir, target):
    subprocess.run(["xcodebuild", "clean", "-project", "itlwm.xcodeproj",
                    "-target", target, "-configuration", "Release",
                    "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_REQUIRED=NO",
                    "CODE_SIGNING_ALLOWED=NO"],
                   cwd=source_dir, capture_output=True, text=True)
    cmd = [
        "xcodebuild", "-project", "itlwm.xcodeproj",
        "-target", target, "-configuration", "Release",
        "MACOSX_DEPLOYMENT_TARGET=10.15",
        "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_REQUIRED=NO",
        "CODE_SIGNING_ALLOWED=NO",
    ]
    print(f"Building: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=source_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Build FAILED:\n{result.stderr[-2000:]}")
        sys.exit(1)
    print("Build succeeded")

def minimize_plist(kext_path, pci_id):
    info_path = os.path.join(kext_path, "Contents", "Info.plist")
    with open(info_path, "rb") as f:
        plist = plistlib.load(f)
    for personality_name, personality in plist.get("IOKitPersonalities", {}).items():
        if "IOPCIMatch" in personality:
            personality["IOPCIMatch"] = pci_id
            print(f"Set IOPCIMatch={pci_id} for {personality_name}")
    with open(info_path, "wb") as f:
        plistlib.dump(plist, f)
    subprocess.run(["plutil", "-lint", info_path], capture_output=True)

def strip_binary(kext_path):
    binary_path = os.path.join(kext_path, "Contents", "MacOS", "AirportItlwm")
    if os.path.exists(binary_path):
        result = subprocess.run(["strip", "-S", "-x", binary_path], capture_output=True, text=True)
        if result.returncode == 0:
            size = os.path.getsize(binary_path)
            print(f"Stripped AirportItlwm binary: {size/1024:.0f}KB")
        else:
            print(f"Strip warning: {result.stderr.strip()}")

def main():
    config_path = os.environ.get("CONFIG_PATH", "config/device-config.json")
    with open(config_path) as f:
        config = json.load(f)

    source_dir = os.environ.get("SOURCE_DIR", "itlwm")
    firmware_name = config["wifi"]["firmware"]
    pci_id = config["wifi"]["pci_id"]
    build_target = config["wifi"]["build_target"]

    minimize_firmware(source_dir, firmware_name)
    clean_cache(source_dir)
    build(source_dir, build_target)

    kext_path = os.path.join(source_dir, "build", "Release", "Ventura", "AirportItlwm.kext")
    if not os.path.exists(kext_path):
        kext_path = os.path.join(source_dir, "build", "Release", build_target, "AirportItlwm.kext")
    if not os.path.exists(kext_path):
        for root, dirs, files in os.walk(os.path.join(source_dir, "build")):
            if "AirportItlwm.kext" in dirs:
                kext_path = os.path.join(root, "AirportItlwm.kext")
                break

    minimize_plist(kext_path, pci_id)
    strip_binary(kext_path)

    output_dir = os.environ.get("OUTPUT_DIR", "build-output")
    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, "AirportItlwm.kext")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(kext_path, dest)
    print(f"Output: {dest}")

if __name__ == "__main__":
    main()
