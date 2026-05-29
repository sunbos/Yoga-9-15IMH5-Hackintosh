#!/usr/bin/env python3
import json
import os
import plistlib
import shutil
import subprocess
import sys

def _safe_int(v, default=-1):
    """Convert to int, returning default on failure."""
    try:
        return int(v)
    except (ValueError, TypeError):
        return default

def minimize_resources(kext_path, codec, codec_id, keep_layouts):
    resources_dir = os.path.join(kext_path, "Contents", "Resources")
    if not os.path.exists(resources_dir):
        print("No Resources directory found (already minimized)")
        return

    # Note: PinConfigs.kext is deleted by AppleALC's "Merge Pinconfigs" build phase
    # (Tools/merge_pinconfigs.sh merges its data into the main Info.plist then removes it),
    # so there is no need to process it here.

    for item in os.listdir(resources_dir):
        item_path = os.path.join(resources_dir, item)
        if os.path.isdir(item_path) and item != codec:
            shutil.rmtree(item_path)
            print(f"Removed codec resource: {item}")

    # Prune HDAConfigDefault in the main Info.plist (merged from PinConfigs by build phase)
    prune_main_info_plist(kext_path, codec_id, keep_layouts)

def strip_binary(kext_path):
    binary_path = os.path.join(kext_path, "Contents", "MacOS", "AppleALC")
    if os.path.exists(binary_path):
        result = subprocess.run(["strip", "-S", "-x", binary_path], capture_output=True, text=True)
        if result.returncode == 0:
            size = os.path.getsize(binary_path)
            print(f"Stripped AppleALC binary: {size/1024:.0f}KB")
        else:
            print(f"Strip warning: {result.stderr.strip()}")

def prune_main_info_plist(kext_path, codec_id, keep_layouts):
    """Prune HDAConfigDefault entries from the main AppleALC Info.plist.

    The "Merge Pinconfigs" build phase copies all 657+ entries from
    PinConfigs.kext into the main Info.plist. We only need entries
    matching the target codec and layout.
    """
    info_path = os.path.join(kext_path, "Contents", "Info.plist")
    if not os.path.exists(info_path):
        print(f"No main Info.plist found at {info_path}")
        return
    with open(info_path, "rb") as f:
        plist = plistlib.load(f)

    personalities = plist.get("IOKitPersonalities", {})
    alc_personality = personalities.get("as.vit9696.AppleALC", {})
    hda_configs = alc_personality.get("HDAConfigDefault", [])
    if not hda_configs:
        print("No HDAConfigDefault in main Info.plist (already pruned?)")
        return

    original_count = len(hda_configs)
    codec_id = _safe_int(codec_id)
    keep_set = set(_safe_int(x) for x in keep_layouts)
    kept = [
        e for e in hda_configs
        if isinstance(e, dict)
        and _safe_int(e.get("CodecID")) == codec_id
        and _safe_int(e.get("LayoutID")) in keep_set
    ]
    # Fallback: if no exact match (e.g. custom layout not in upstream),
    # keep all entries for this codec
    if not kept:
        kept = [
            e for e in hda_configs
            if isinstance(e, dict) and _safe_int(e.get("CodecID")) == codec_id
        ]
        if kept:
            print(f"No exact HDAConfigDefault match for layout {keep_layouts}, "
                  f"keeping all {len(kept)} entries for codec {codec_id}")

    if not kept:
        print(f"WARNING: No HDAConfigDefault entries matched codec {codec_id}, "
              f"keeping original {original_count} entries to avoid breaking audio")
        return

    alc_personality["HDAConfigDefault"] = kept
    with open(info_path, "wb") as f:
        plistlib.dump(plist, f)
    print(f"Main Info.plist HDAConfigDefault: {original_count} -> {len(kept)} "
          f"(removed {original_count - len(kept)} entries)")

def inject_custom_layouts(source_dir, codec, keep_layouts):
    patches_dir = os.environ.get("PATCHES_DIR", "patches/applealc")
    if not os.path.isdir(patches_dir):
        print(f"No custom layout patches dir: {patches_dir}")
        return
    codec_dir = os.path.join(source_dir, "Resources", codec)
    if not os.path.exists(codec_dir):
        os.makedirs(codec_dir, exist_ok=True)
    injected = 0
    for lid in keep_layouts:
        for prefix in ("layout", "Platforms"):
            src = os.path.join(patches_dir, f"{prefix}{lid}.xml")
            dst = os.path.join(codec_dir, f"{prefix}{lid}.xml")
            if not os.path.exists(src):
                continue
            if os.path.exists(dst):
                print(f"Upstream already has {prefix}{lid}.xml, skipping custom injection")
                continue
            shutil.copy2(src, dst)
            injected += 1
            print(f"Injected custom {prefix}{lid}.xml")
    if injected > 0:
        print(f"Injected {injected} custom layout files")

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

    for cache_file in ("Resources.md5", "Resources.tmp.md5"):
        cache_path = os.path.join(source_dir, cache_file)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print(f"Removed build cache: {cache_file}")

    kern_res = os.path.join(source_dir, "AppleALC", "kern_resources.cpp")
    if os.path.exists(kern_res):
        os.remove(kern_res)
        print("Removed kern_resources.cpp cache to force regeneration")

    codec_dir = os.path.join(resources_dir, codec)
    if not os.path.exists(codec_dir):
        return
    layout_ids = set(str(l) for l in keep_layouts)
    xml_removed = 0
    for item in list(os.listdir(codec_dir)):
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
        base = os.path.join(codec_dir, item)
        os.remove(base)
        xml_removed += 1
        for suffix in (".zlib", ".zlib.md5", ".md5"):
            cache = base + suffix
            if os.path.exists(cache):
                os.remove(cache)
    print(f"Pruned {xml_removed} unneeded layout/Platforms XMLs from {codec} (kept layouts {keep_layouts})")

def prune_codec_info_plist(source_dir, codec, keep_layouts):
    info_path = os.path.join(source_dir, "Resources", codec, "Info.plist")
    if not os.path.exists(info_path):
        print(f"No Info.plist found at {info_path}")
        return
    with open(info_path, "rb") as f:
        plist = plistlib.load(f)

    files_dict = plist.get("Files", {})
    keep_set = set(_safe_int(x) for x in keep_layouts)

    for key in ("Layouts", "Platforms"):
        entries = files_dict.get(key, [])
        original_count = len(entries)
        existing_ids = {_safe_int(e.get("Id")) for e in entries if isinstance(e, dict)}
        kept = [e for e in entries if isinstance(e, dict) and _safe_int(e.get("Id")) in keep_set]
        added = 0
        for lid in keep_layouts:
            if _safe_int(lid) not in existing_ids:
                prefix = "layout" if key == "Layouts" else "Platforms"
                kept.append({
                    "Id": _safe_int(lid),
                    "Path": f"{prefix}{lid}.xml.zlib",
                })
                added += 1
                print(f"Added missing {key} entry for layout {lid}")
        files_dict[key] = kept
        removed = original_count - (len(kept) - added)
        print(f"Info.plist {key}: {original_count} -> {len(kept)} (removed {removed}, added {added})")

    pin_configs = plist.get("PinConfigurations")
    if isinstance(pin_configs, list):
        original_pc = len(pin_configs)
        plist["PinConfigurations"] = [p for p in pin_configs if isinstance(p, dict) and _safe_int(p.get("LayoutID")) in keep_set]
        print(f"Info.plist PinConfigurations: {original_pc} -> {len(plist['PinConfigurations'])}")

    with open(info_path, "wb") as f:
        plistlib.dump(plist, f)

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
    codec_id = audio_config["codec_id"]
    keep_layouts = audio_config["keep_layouts"]

    prune_source_resources(source_dir, codec, keep_layouts)
    inject_custom_layouts(source_dir, codec, keep_layouts)
    prune_codec_info_plist(source_dir, codec, keep_layouts)
    build(source_dir)

    kext_path = os.path.join(source_dir, "build", "Release", "AppleALC.kext")
    if not os.path.exists(kext_path):
        for root, dirs, files in os.walk(os.path.join(source_dir, "build")):
            if "AppleALC.kext" in dirs:
                kext_path = os.path.join(root, "AppleALC.kext")
                break

    minimize_resources(kext_path, codec, codec_id, keep_layouts)
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
