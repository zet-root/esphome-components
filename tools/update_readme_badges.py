#!/usr/bin/env python3
"""
Update README.md with build status badges for all supported ESPHome versions.

Reads .versions.yml and inserts/updates a badge section in README showing:
- Which versions are supported
- Build status for each version branch
"""

import os
import re
import subprocess
import yaml


def read_versions(src_dir: str) -> dict:
    """Read .versions.yml and return the parsed content."""
    versions_path = os.path.join(src_dir, ".versions.yml")
    if os.path.exists(versions_path):
        with open(versions_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data and data.get("supported"):
                # Sort supported versions in descending order
                data["supported"] = sorted(
                    data["supported"],
                    key=lambda v: tuple(map(int, v.split("."))),
                    reverse=True
                )
            return data if data else {"latest": "", "supported": []}
    return {"latest": "", "supported": []}


def _read_release_versions_from_remote(src_dir: str) -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "-C", src_dir, "ls-remote", "--heads", "origin", "release/zet-*"]
        ).decode("utf-8")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    versions = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/heads/release/zet-"):
            versions.append(ref.split("refs/heads/release/zet-")[1])
    return sorted(set(versions), key=lambda v: tuple(map(int, v.split("."))), reverse=True)


def _read_release_versions_local(src_dir: str) -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "-C", src_dir, "show-ref", "--heads", "refs/heads/release/zet-*"]
        ).decode("utf-8")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    versions = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/heads/release/zet-"):
            versions.append(ref.split("refs/heads/release/zet-")[1])
    return sorted(set(versions), key=lambda v: tuple(map(int, v.split("."))), reverse=True)


def _filter_versions_to_release_branches(src_dir: str, versions: list[str]) -> list[str]:
    remote_versions = _read_release_versions_from_remote(src_dir)
    if remote_versions:
        return [v for v in versions if v in remote_versions]

    local_versions = _read_release_versions_local(src_dir)
    if local_versions:
        return [v for v in versions if v in local_versions]

    return versions


def generate_badge_section(versions_data: dict, repo: str = "zet-root/esphome-components") -> str:
    """Generate the badge section for README."""
    latest = versions_data.get("latest", "")
    supported = versions_data.get("supported", [])
    
    if not supported:
        return ""
    
    lines = ["## Build Status by Version", ""]
    lines.append("| Version | Status |")
    lines.append("|---------|--------|")
    
    for version in supported:
        label = f"{version} (latest)" if version == latest else version
        badge = (
            f'[![{label}](https://github.com/{repo}/actions/workflows/esphome-compile.yml/badge.svg?branch=release/zet-{version})]'
            f'(https://github.com/{repo}/actions/workflows/esphome-compile.yml?query=branch%3Arelease%2Fzet-{version})'
        )
        lines.append(f"| `{version}` | {badge} |")
    
    lines.append("")
    return "\n".join(lines)


def update_readme(src_dir: str, repo: str = "zet-root/esphome-components") -> None:
    """Update README.md with the badge section."""
    readme_path = os.path.join(src_dir, "README.md")
    if not os.path.exists(readme_path):
        print(f"README.md not found at {readme_path}")
        return
    
    versions_data = read_versions(src_dir)
    if not versions_data.get("supported"):
        print("No supported versions in .versions.yml")
        return

    filtered_supported = _filter_versions_to_release_branches(src_dir, versions_data.get("supported", []))
    if filtered_supported != versions_data.get("supported", []):
        versions_data = dict(versions_data)
        versions_data["supported"] = filtered_supported
        if versions_data.get("latest") not in filtered_supported:
            versions_data["latest"] = filtered_supported[0] if filtered_supported else ""
    
    badge_section = generate_badge_section(versions_data, repo)
    
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find the badge section or insert it after the first badge (if exists)
    # Pattern to find existing badge section
    pattern = r"## Build Status by Version\s*\|.*?\n(?:\|.*?\n)*"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    
    if match:
        # Replace existing section
        content = content[:match.start()] + badge_section + content[match.end():]
    else:
        # Find the position to insert (after the main badge, before "## Install / Use")
        insert_pattern = r"(!\[ESPHome Compile\].*?\)\n\n)(A small collection)"
        match = re.search(insert_pattern, content, re.MULTILINE | re.DOTALL)
        
        if match:
            # Insert after the main badge
            insert_pos = match.end(1)
            content = content[:insert_pos] + badge_section + "\n" + content[insert_pos:]
        else:
            # Fallback: insert before "## Install / Use"
            install_pattern = r"## Install / Use"
            match = re.search(install_pattern, content)
            if match:
                content = content[:match.start()] + badge_section + "\n" + content[match.start():]
            else:
                print("Could not find insertion point in README")
                return
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Updated README.md with {len(versions_data.get('supported', []))} version badges")


def main() -> None:
    import argparse
    
    ap = argparse.ArgumentParser(description="Update README.md with ESPHome version badges")
    ap.add_argument("--src-dir", help="Source directory (default: current directory)")
    ap.add_argument("--repo", default="zet-root/esphome-components", help="GitHub repo (owner/name)")
    
    args = ap.parse_args()
    src_dir = args.src_dir or os.getcwd()
    
    update_readme(src_dir, args.repo)


if __name__ == "__main__":
    main()
