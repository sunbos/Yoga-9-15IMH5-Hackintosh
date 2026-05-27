#!/usr/bin/env python3
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import strip_binary, find_kext_in_build, copy_kext_to_output


def build(source_dir):
    """
    构建 YogaSMC
    """
    cmd = [
        "xcodebuild",
        "-project",
        "YogaSMC.xcodeproj",
        "-target",
        "YogaSMC",
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
    output_dir = os.environ.get("OUTPUT_DIR", "build-output")

    # 构建
    build(source_dir)

    # 查找构建产物
    kext_path = find_kext_in_build(source_dir, "YogaSMC.kext")
    if not kext_path or not os.path.exists(kext_path):
        print("ERROR: YogaSMC.kext not found in build output")
        sys.exit(1)

    # 剥离调试符号并输出
    strip_binary(kext_path)
    copy_kext_to_output(kext_path, output_dir)


if __name__ == "__main__":
    main()
