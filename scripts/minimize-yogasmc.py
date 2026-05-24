#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys


def strip_binary(kext_path):
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


def build(source_dir):
    cmd = [
        "xcodebuild",
        "-project",
        "YogaSMC.xcodeproj",
        "-target",
        "BuildAll",
        "-configuration",
        "Release",
        "CODE_SIGN_IDENTITY=-",
        "CODE_SIGNING_REQUIRED=NO",
        "CODE_SIGNING_ALLOWED=NO",
    ]
    print(f"Building: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=source_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print("Build FAILED:")
        for line in result.stderr.splitlines():
            if (
                "error:" in line.lower()
                or "undefined" in line.lower()
                or "ld:" in line.lower()
            ):
                print(f"  {line}")
        print(result.stderr[-3000:] if result.stderr else "")
        sys.exit(1)
    print("Build succeeded")


def main():
    source_dir = os.environ.get("SOURCE_DIR", "YogaSMC")

    build(source_dir)

    kext_path = os.path.join(source_dir, "build", "Release", "YogaSMC.kext")
    if not os.path.exists(kext_path):
        for root, dirs, files in os.walk(os.path.join(source_dir, "build")):
            if "YogaSMC.kext" in dirs:
                kext_path = os.path.join(root, "YogaSMC.kext")
                break

    if not os.path.exists(kext_path):
        print("ERROR: YogaSMC.kext not found in build output")
        sys.exit(1)

    strip_binary(kext_path)

    output_dir = os.environ.get("OUTPUT_DIR", "build-output")
    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, "YogaSMC.kext")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(kext_path, dest)
    print(f"Output: {dest}")


if __name__ == "__main__":
    main()
