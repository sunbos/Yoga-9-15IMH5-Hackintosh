#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request

GITHUB_API = "https://api.github.com/repos"

def _make_request(url):
    headers = {"User-Agent": "Yoga-9-15IMH5-Build"}
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get_latest_sha(repo):
    for branch in ("master", "main"):
        try:
            url = f"{GITHUB_API}/{repo}/commits/{branch}"
            data = _make_request(url)
            return data["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
    raise RuntimeError(f"No master or main branch found for {repo}")

def get_latest_release_tag(repo):
    try:
        url = f"{GITHUB_API}/{repo}/releases/latest"
        data = _make_request(url)
        return data.get("tag_name", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ""
        raise

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
            "yogasmc": config["upstream_repos"]["yogasmc"],
        }
        current_sha = {}
        for name, repo in repos_to_check.items():
            try:
                sha = get_latest_sha(repo)
                current_sha[name] = sha
                print(f"{name}: current {sha[:8]}")
            except Exception as e:
                print(f"{name}: error - {e}")
        for name, info in config.get("download_repos", {}).items():
            try:
                tag = get_latest_release_tag(info["repo"])
                current_sha[f"dl_{name}"] = tag
                print(f"{name}: current release {tag}")
            except Exception as e:
                print(f"{name}: error - {e}")
        for name, info in config.get("raw_downloads", {}).items():
            repo = info.get("repo", "")
            if not repo:
                continue
            try:
                sha = get_latest_sha(repo)
                current_sha[f"raw_{name}"] = sha
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
        "yogasmc": config["upstream_repos"]["yogasmc"],
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

    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write(f"needs_build={'true' if needs_build else 'false'}\n")

    current_sha_path = os.environ.get("CURRENT_SHA_PATH", "/tmp/current-sha.json")
    with open(current_sha_path, "w") as f:
        json.dump(current_sha, f, indent=2)

if __name__ == "__main__":
    main()
