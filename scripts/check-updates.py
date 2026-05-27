#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import (
    get_latest_sha,
    get_latest_release_tag,
    load_config,
)


def check_repo_updates(config, last_sha, force):
    """
    检查所有仓库的更新
    """
    current_sha = {}
    needs_build = force

    # 检查上游仓库
    upstream_repos = {
        "itlwm": config["upstream_repos"]["itlwm"],
        "intelbt": config["upstream_repos"]["intelbt"],
        "applealc": config["upstream_repos"]["applealc"],
        "lilu": config["upstream_repos"]["lilu"],
        "yogasmc": config["upstream_repos"]["yogasmc"],
    }

    for name, repo in upstream_repos.items():
        try:
            sha = get_latest_sha(repo)
            current_sha[name] = sha
            last = last_sha.get(name, "")
            if sha != last:
                print(f"{name}: new commit {sha[:8]} (was {last[:8] if last else 'none'})")
                needs_build = True
            else:
                print(f"{name}: no change {sha[:8]}")
        except Exception as e:
            print(f"{name}: error checking - {e}")
            needs_build = True

    # 检查下载仓库
    for name, info in config.get("download_repos", {}).items():
        repo = info["repo"]
        try:
            tag = get_latest_release_tag(repo)
            key = f"dl_{name}"
            current_sha[key] = tag
            last = last_sha.get(key, "")
            if tag != last:
                print(f"{name}: new release {tag} (was {last or 'none'})")
                needs_build = True
            else:
                print(f"{name}: no change {tag}")
        except Exception as e:
            print(f"{name}: error checking release - {e}")
            needs_build = True

    # 检查原始下载仓库
    for name, info in config.get("raw_downloads", {}).items():
        repo = info.get("repo", "")
        if not repo:
            continue
        try:
            sha = get_latest_sha(repo)
            key = f"raw_{name}"
            current_sha[key] = sha
            last = last_sha.get(key, "")
            if sha != last:
                print(f"{name}: new commit {sha[:8]} (was {last[:8] if last else 'none'})")
                needs_build = True
            else:
                print(f"{name}: no change {sha[:8]}")
        except Exception as e:
            print(f"{name}: error checking - {e}")
            needs_build = True

    return current_sha, needs_build


def main():
    sha_path = os.environ.get("SHA_PATH", "last-build-sha.json")
    force = os.environ.get("FORCE_BUILD", "false").lower() == "true"

    config = load_config()

    # 加载上次构建的 SHA
    if os.path.exists(sha_path):
        with open(sha_path) as f:
            last_sha = json.load(f)
    else:
        last_sha = {}

    if force:
        print("force_build=true, skipping update check")
        needs_build = True
    else:
        needs_build = False

    # 检查更新
    current_sha, needs_build = check_repo_updates(config, last_sha, force)

    # 输出结果
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write(f"needs_build={'true' if needs_build else 'false'}\n")

    # 保存当前 SHA
    current_sha_path = os.environ.get("CURRENT_SHA_PATH", "/tmp/current-sha.json")
    with open(current_sha_path, "w") as f:
        json.dump(current_sha, f, indent=2)


if __name__ == "__main__":
    main()
