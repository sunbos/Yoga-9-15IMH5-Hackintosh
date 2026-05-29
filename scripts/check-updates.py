#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.error
import urllib.request

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
    # Fallback: query the repo's actual default branch
    try:
        repo_info = _make_request(f"{GITHUB_API}/{repo}")
        default_branch = repo_info["default_branch"]
        data = _make_request(f"{GITHUB_API}/{repo}/commits/{default_branch}")
        return data["sha"]
    except Exception as e:
        raise RuntimeError(f"No master or main branch found for {repo}: {e}") from e

def get_latest_release_tag(repo):
    try:
        url = f"{GITHUB_API}/{repo}/releases/latest"
        data = _make_request(url)
        return data.get("tag_name", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ""
        raise

def _collect_current_shas(config):
    """Collect current SHA/tag values from all tracked repos."""
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
        except Exception as e:
            print(f"{name}: error - {e}")
            current_sha[name] = None
    for name, info in config.get("download_repos", {}).items():
        try:
            tag = get_latest_release_tag(info["repo"])
            current_sha[f"dl_{name}"] = tag
        except Exception as e:
            print(f"{name}: error - {e}")
            current_sha[f"dl_{name}"] = None
    for name, info in config.get("raw_downloads", {}).items():
        repo = info.get("repo", "")
        if not repo:
            continue
        try:
            sha = get_latest_sha(repo)
            current_sha[f"raw_{name}"] = sha
        except Exception as e:
            print(f"{name}: error - {e}")
            current_sha[f"raw_{name}"] = None
    return current_sha

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

    current_sha = _collect_current_shas(config)

    if force:
        print("force_build=true, skipping update check")
        needs_build = True
    else:
        needs_build = False
        for key, value in current_sha.items():
            if value is None:
                needs_build = True
                continue
            short = value[:8] if len(value) > 8 else value
            last = last_sha.get(key, "")
            last_short = last[:8] if len(last) > 8 else last
            if value != last:
                print(f"{key}: new {short} (was {last_short or 'none'})")
                needs_build = True
            else:
                print(f"{key}: no change {short}")

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as out:
            out.write(f"needs_build={'true' if needs_build else 'false'}\n")
    else:
        print(f"GITHUB_OUTPUT not set, needs_build={needs_build}")

    # Preserve last known values for repos that failed this run,
    # so a transient failure doesn't trigger unnecessary rebuilds next time
    for key, value in current_sha.items():
        if value is None and key in last_sha:
            current_sha[key] = last_sha[key]

    current_sha_path = os.environ.get("CURRENT_SHA_PATH", "/tmp/current-sha.json")
    with open(current_sha_path, "w") as f:
        json.dump({k: v for k, v in current_sha.items() if v is not None}, f, indent=2)

if __name__ == "__main__":
    main()
