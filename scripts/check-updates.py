#!/usr/bin/env python3
import json
import os
import sys
import urllib.request

GITHUB_API = "https://api.github.com/repos"

def get_latest_sha(repo):
    url = f"{GITHUB_API}/{repo}/commits/master"
    req = urllib.request.Request(url, headers={"User-Agent": "Yoga-9-15IMH5-Build"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        return data["sha"]

def main():
    config_path = os.environ.get("CONFIG_PATH", "config/device-config.json")
    sha_path = os.environ.get("SHA_PATH", "last-build-sha.json")
    force = os.environ.get("FORCE_BUILD", "false").lower() == "true"

    with open(config_path) as f:
        config = json.load(f)

    if os.path.exists(sha_path):
        with open(sha_path) as f:
            last_sha = json.load(f)
    else:
        last_sha = {}

    if force:
        print("force_build=true, skipping update check")
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write("needs_build=true\n")
        repos_to_check = {
            "itlwm": config["upstream_repos"]["itlwm"],
            "intelbt": config["upstream_repos"]["intelbt"],
            "applealc": config["upstream_repos"]["applealc"],
            "lilu": config["upstream_repos"]["lilu"],
        }
        current_sha = {}
        for name, repo in repos_to_check.items():
            try:
                sha = get_latest_sha(repo)
                current_sha[name] = sha
                print(f"{name}: current {sha[:8]}")
            except Exception as e:
                print(f"{name}: error - {e}")
        current_sha_path = os.environ.get("CURRENT_SHA_PATH", "/tmp/current-sha.json")
        with open(current_sha_path, "w") as f:
            json.dump(current_sha, f, indent=2)
        return

    repos_to_check = {
        "itlwm": config["upstream_repos"]["itlwm"],
        "intelbt": config["upstream_repos"]["intelbt"],
        "applealc": config["upstream_repos"]["applealc"],
        "lilu": config["upstream_repos"]["lilu"],
    }

    needs_build = False
    current_sha = {}
    for name, repo in repos_to_check.items():
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

    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write(f"needs_build={'true' if needs_build else 'false'}\n")

    current_sha_path = os.environ.get("CURRENT_SHA_PATH", "/tmp/current-sha.json")
    with open(current_sha_path, "w") as f:
        json.dump(current_sha, f, indent=2)

if __name__ == "__main__":
    main()
