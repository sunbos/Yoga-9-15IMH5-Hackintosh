#!/usr/bin/env python3
import json
import os
import plistlib
import shutil
import subprocess
import sys

def minimize_resources(kext_path, codec, keep_layouts):
    resources_dir = os.path.join(kext_path, "Contents", "Resources")
    if not os.path.exists(resources_dir):
        print("No Resources directory found (already minimized)")
        return

    pinconfigs_path = os.path.join(resources_dir, "PinConfigs.kext")
    if os.path.exists(pinconfigs_path):
        minimize_pinconfigs(pinconfigs_path, codec, keep_layouts)

    for item in os.listdir(resources_dir):
        item_path = os.path.join(resources_dir, item)
        if os.path.isdir(item_path) and item != codec and item != "PinConfigs.kext":
            shutil.rmtree(item_path)
            print(f"Removed codec resource: {item}")

def minimize_pinconfigs(pinconfigs_path, codec, keep_layouts):
    info_path = os.path.join(pinconfigs_path, "Contents", "Info.plist")
    if not os.path.exists(info_path):
        return
    with open(info_path, "rb") as f:
        plist = plistlib.load(f)
    personalities = plist.get("IOKitPersonalities", {})
    codec_key = None
    for k, v in personalities.items():
        if isinstance(v, dict) and v.get("CodecID") == codec:
            codec_key = k
            break
    if codec_key is None:
        for k in list(personalities.keys()):
            if k != f"hda-gfx-{codec}":
                del personalities[k]
        codec_key = list(personalities.keys())[0] if personalities else None

    if codec_key and "Layouts" in personalities.get(codec_key, {}):
        layouts = personalities[codec_key]["Layouts"]
        original_count = len(layouts)
        personalities[codec_key]["Layouts"] = [
            l for l in layouts if l.get("LayoutID") in keep_layouts
        ]
        kept = len(personalities[codec_key]["Layouts"])
        print(f"PinConfigs: kept {kept}/{original_count} layouts for {codec}")

    to_remove = [k for k in personalities if k != codec_key]
    for k in to_remove:
        del personalities[k]
        print(f"Removed PinConfigs personality: {k}")

    with open(info_path, "wb") as f:
        plistlib.dump(plist, f)

def strip_binary(kext_path):
    binary_path = os.path.join(kext_path, "Contents", "MacOS", "AppleALC")
    if os.path.exists(binary_path):
        result = subprocess.run(["strip", "-S", "-x", binary_path], capture_output=True, text=True)
        if result.returncode == 0:
            size = os.path.getsize(binary_path)
            print(f"Stripped AppleALC binary: {size/1024:.0f}KB")
        else:
            print(f"Strip warning: {result.stderr.strip()}")

def prune_source_resources(source_dir, codec, keep_layouts):
    resources_dir = os.path.join(source_dir, "Resources")
    if not os.path.exists(resources_dir):
        print("No Resources directory found in source")
        return
    removed = 0
    for item in os.listdir(resources_dir):
        item_path = os.path.join(resources_dir, item)
        if os.path.isdir(item_path) and item != codec and item != "PinConfigs.kext":
            shutil.rmtree(item_path)
            removed += 1
    print(f"Pruned {removed} codec resource dirs from source (kept {codec} + PinConfigs.kext)")

    codec_dir = os.path.join(resources_dir, codec)
    if not os.path.exists(codec_dir):
        return
    layout_ids = set(str(l) for l in keep_layouts)
    xml_removed = 0
    for item in os.listdir(codec_dir):
        if not item.endswith(".xml"):
            continue
        name = item.replace(".xml", "")
        is_layout = name.startswith("layout")
        is_platforms = name.startswith("Platforms")
        if not is_layout and not is_platforms:
            continue
        lid = name.replace("layout", "").replace("Platforms", "")
        if lid in layout_ids:
            continue
        os.remove(os.path.join(codec_dir, item))
        xml_removed += 1
    print(f"Pruned {xml_removed} unneeded layout/Platforms XMLs from {codec} (kept layouts {keep_layouts})")

def build(source_dir):
    cmd = [
        "xcodebuild", "-project", "AppleALC.xcodeproj",
        "-target", "AppleALC", "-configuration", "Release",
        "-arch", "x86_64",
        "MACOSX_DEPLOYMENT_TARGET=10.13",
        "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_REQUIRED=NO", "CODE_SIGNING_ALLOWED=NO",
        "LILU_KEXTPATH=$(SRCROOT)/Lilu.kext",
    ]
    print(f"Building: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=source_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print("Build FAILED:")
        for line in result.stderr.splitlines():
            if "error:" in line.lower() or "undefined" in line.lower() or "ld:" in line.lower():
                print(f"  {line}")
        print(result.stderr[-3000:] if result.stderr else "")
        sys.exit(1)
    print("Build succeeded")

def main():
    config_path = os.environ.get("CONFIG_PATH", "config/device-config.json")
    with open(config_path) as f:
        config = json.load(f)

    source_dir = os.environ.get("SOURCE_DIR", "AppleALC")
    audio_config = config["audio"]
    codec = audio_config["codec"]
    keep_layouts = audio_config["keep_layouts"]

    prune_source_resources(source_dir, codec, keep_layouts)
    build(source_dir)

    kext_path = os.path.join(source_dir, "build", "Release", "AppleALC.kext")
    if not os.path.exists(kext_path):
        for root, dirs, files in os.walk(os.path.join(source_dir, "build")):
            if "AppleALC.kext" in dirs:
                kext_path = os.path.join(root, "AppleALC.kext")
                break

    minimize_resources(kext_path, codec, keep_layouts)
    strip_binary(kext_path)

    output_dir = os.environ.get("OUTPUT_DIR", "build-output")
    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, "AppleALC.kext")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(kext_path, dest)
    print(f"Output: {dest}")

if __name__ == "__main__":
    main()
