#!/usr/bin/env python3
"""
ESPHome external components release helper.

Keeps only selected components in this repo:
  components/<name>/

Workflow:
  - Import upstream ESPHome component dirs for a given ESPHome tag.
  - Keep your changes as a linear patch stack on top of the last import commit.
  - For a new ESPHome release, auto-reapply the patch stack; if no conflicts -> done.

Requires:
  - git
  - tar (supports --strip-components; GNU tar and bsdtar do)
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional
import yaml

UPSTREAM_REMOTE_NAME = "upstream"
UPSTREAM_REMOTE_URL = "https://github.com/esphome/esphome.git"

# In upstream ESPHome repo, components live here:
UPSTREAM_COMPONENT_ROOT = "esphome/components"

# In your external components repo, you publish here:
LOCAL_COMPONENT_ROOT = "components"

COMPONENTS_FILE = ".components.list"
UPSTREAM_VERSION_FILE = ".upstream_version"
VERSIONS_FILE = ".versions.yml"

IMPORT_COMMIT_PREFIX = "Import ESPHome "


def run(cmd: List[str], *, capture: bool = False, check: bool = True) -> str:
    print("+", " ".join(cmd))
    if capture:
        return subprocess.check_output(cmd, text=True).strip()
    subprocess.run(cmd, check=check)
    return ""


def read_versions(src_dir: str) -> dict:
    """Read .versions.yml and return the parsed content."""
    versions_path = os.path.join(src_dir, VERSIONS_FILE)
    if os.path.exists(versions_path):
        with open(versions_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if data else {"latest": "", "supported": []}
    return {"latest": "", "supported": []}


def update_versions(version: str, src_dir: str) -> None:
    """Update .versions.yml to add a new version and set it as latest."""
    versions = read_versions(src_dir)
    supported = versions.get("supported", [])
    
    # Add version if not already in list, maintaining order
    if version not in supported:
        supported.append(version)
    
    # Update latest
    versions["latest"] = version
    versions["supported"] = sorted(
        supported,
        key=lambda v: tuple(map(int, v.split("."))),
        reverse=True
    )
    
    versions_path = os.path.join(src_dir, VERSIONS_FILE)
    with open(versions_path, "w", encoding="utf-8") as f:
        yaml.dump(versions, f, default_flow_style=False, sort_keys=False)


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def ensure_git_repo(src_dir: str) -> None:
    if not os.path.isdir(os.path.join(src_dir, ".git")):
        die(f"Not a git repository. Run this from the repo root: {src_dir}")


def ensure_clean_worktree(src_dir: str) -> None:
    status = run(["git", "-C", src_dir, "status", "--porcelain"], capture=True)
    if status.strip():
        die("Working tree not clean. Commit/stash first:\n" + status)


def ensure_remote(src_dir: str) -> None:
    remotes = run(["git", "-C", src_dir, "remote"], capture=True).split()
    if UPSTREAM_REMOTE_NAME not in remotes:
        run(["git", "-C", src_dir, "remote", "add", UPSTREAM_REMOTE_NAME, UPSTREAM_REMOTE_URL])


def fetch_upstream_tags(src_dir: str) -> None:
    run(["git", "-C", src_dir, "fetch", UPSTREAM_REMOTE_NAME, "--tags"])


def verify_upstream_tag(tag: str, src_dir: str) -> None:
    try:
        run(["git", "-C", src_dir, "rev-parse", "--verify", f"refs/tags/{tag}^{{}}"], capture=True)
    except subprocess.CalledProcessError:
        die(
            f"Upstream tag '{tag}' not found in fetched tags. "
            f"Check https://github.com/esphome/esphome/releases for the exact tag name."
        )


def read_components(src_dir: str) -> List[str]:
    comps: List[str] = []
    comp_file = os.path.join(src_dir, COMPONENTS_FILE)
    if os.path.exists(comp_file):
        with open(comp_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                comps.append(line)
    if not comps:
        die(f"{COMPONENTS_FILE} is empty.")
    return comps


def write_components_file_if_missing(comps: List[str], src_dir: str) -> None:
    comp_file = os.path.join(src_dir, COMPONENTS_FILE)
    if os.path.exists(comp_file):
        return
    with open(comp_file, "w", encoding="utf-8") as f:
        f.write("\n".join(comps) + "\n")
    run(["git", "-C", src_dir, "add", COMPONENTS_FILE], check=False)


def last_import_commit(src_dir: str) -> str:
    """
    Finds the most recent commit whose subject starts with "Import ESPHome ".
    Assumes you keep a linear history (recommended).
    """
    try:
        return run(
            ["git", "-C", src_dir, "log", "--grep", f"^{IMPORT_COMMIT_PREFIX}", "-n", "1", "--format=%H"],
            capture=True,
        )
    except subprocess.CalledProcessError:
        return ""


def import_components_from_upstream(tag: str, comps: List[str], src_dir: str) -> None:
    local_root = os.path.join(src_dir, LOCAL_COMPONENT_ROOT)
    os.makedirs(local_root, exist_ok=True)

    # Remove current published components so the import is a clean replacement.
    for c in comps:
        dest = os.path.join(local_root, c)
        if os.path.isdir(dest):
            shutil.rmtree(dest)

    # Extract each component from upstream tag into components/<name>
    for c in comps:
        upstream_path = f"{UPSTREAM_COMPONENT_ROOT}/{c}"

        # git archive outputs paths like: esphome/components/<c>/...
        # strip the first two components (esphome/components) so it becomes <c>/...
        p1 = subprocess.Popen(["git", "-C", src_dir, "archive", tag, upstream_path], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(
            ["tar", "-x", "-C", local_root, "--strip-components=2"],
            stdin=p1.stdout,
        )
        assert p1.stdout is not None
        p1.stdout.close()
        rc2 = p2.wait()
        rc1 = p1.wait()
        if rc1 != 0 or rc2 != 0:
            die(f"Failed to import '{c}' from upstream tag '{tag}'")

    with open(os.path.join(src_dir, UPSTREAM_VERSION_FILE), "w", encoding="utf-8") as f:
        f.write(tag + "\n")

    run(["git", "-C", src_dir, "add", LOCAL_COMPONENT_ROOT, UPSTREAM_VERSION_FILE])


def commit_import(tag: str, comps: List[str], src_dir: str) -> None:
    msg = f"{IMPORT_COMMIT_PREFIX}{tag} ({','.join(comps)})"
    run(["git", "-C", src_dir, "commit", "-m", msg])


def create_annotated_tag(tag: str, message: str, src_dir: str, force: bool = False) -> None:
    # Check if tag exists
    tag_list = run(["git", "-C", src_dir, "tag", "--list", tag], capture=True)
    if tag_list.strip():
        if force:
            # Delete existing tag before creating
            run(["git", "-C", src_dir, "tag", "-d", tag])
        else:
            print(f"Tag '{tag}' already exists. Use --force-tag to overwrite.")
            return
    args = ["git", "-C", src_dir, "tag", "-a", tag, "-m", message]
    run(args)


def format_patch_stack(base_commit: str, outdir: str, src_dir: str) -> List[str]:
    """
    Creates patch files for base_commit..HEAD and returns them sorted.
    """
    run(["git", "-C", src_dir, "format-patch", f"{base_commit}..HEAD", "-o", outdir])
    patches = sorted(glob.glob(os.path.join(outdir, "*.patch")))
    if not patches:
        die("No patch commits found after the last import commit. Nothing to apply.")
    return patches


def apply_patches(patches: List[str], src_dir: str) -> None:
    # Use 3-way apply to reduce conflicts when upstream context shifts slightly.
    cmd = ["git", "-C", src_dir, "am", "--3way"] + patches
    try:
        run(cmd)
    except subprocess.CalledProcessError:
        print(
            "\nPatch apply failed.\n"
            "Resolve conflicts, then run:\n"
            "  git am --continue\n"
            "Or abort with:\n"
            "  git am --abort\n",
            file=sys.stderr,
        )
        sys.exit(2)


def update_readme_badges(src_dir: str) -> None:
    """Call update_readme_badges.py to refresh README with version badges."""
    update_script = os.path.join(src_dir, "update_readme_badges.py")
    
    if not os.path.exists(update_script):
        print(f"Warning: {update_script} not found, skipping README update")
        return
    
    try:
        # Run script in the repo directory so relative paths work
        subprocess.run(["python3", update_script], cwd=src_dir, check=True)
    except Exception as e:
        print(f"Warning: Failed to update README badges: {e}", file=sys.stderr)


def delete_branch_and_tag(tag: str, src_dir: str, push: bool = False) -> None:
    """Delete a release branch and tag locally and optionally on origin."""
    branch = f"release/zet-{tag}"
    
    # Delete local branch
    run(["git", "-C", src_dir, "branch", "-D", branch], check=False)
    
    # Delete local tag
    run(["git", "-C", src_dir, "tag", "-d", tag], check=False)
    
    if push:
        # Delete remote branch
        run(["git", "-C", src_dir, "push", "origin", "--delete", branch], check=False)
        
        # Delete remote tag
        run(["git", "-C", src_dir, "push", "origin", "--delete", f"tag {tag}"], check=False)


def list_releases(src_dir: str) -> None:
    """List all releases (tags starting with zet-)."""
    tags = run(
        ["git", "-C", src_dir, "tag", "-l", "zet-*"],
        capture=True,
    ).split("\n")
    tags = [t.strip() for t in tags if t.strip()]
    
    versions_data = read_versions(src_dir)
    latest = versions_data.get("latest", "")
    
    if not tags:
        print("No releases found.")
        return
    
    print(f"\nAvailable releases (latest: {latest}):\n")
    for tag in sorted(tags, reverse=True):
        version = tag.replace("zet-", "")
        is_latest = " [LATEST]" if version == latest else ""
        print(f"  {tag}{is_latest}")


def detect_newer_versions(src_dir: str) -> List[str]:
    """Detect upstream ESPHome versions newer than current latest."""
    fetch_upstream_tags(src_dir)
    
    versions_data = read_versions(src_dir)
    current_latest = versions_data.get("latest", "")
    supported = versions_data.get("supported", [])
    
    if not current_latest:
        print("No latest version set in .versions.yml")
        return []
    
    # Get all upstream tags
    all_tags = run(
        ["git", "-C", src_dir, "tag", "-l"],
        capture=True,
    ).split("\n")
    all_tags = [t.strip() for t in all_tags if t.strip()]
    
    # Filter for ESPHome version tags (numeric pattern)
    version_tags = [t for t in all_tags if t and not t.startswith("zet-")]
    
    # Simple version comparison (assuming YYYY.M.P format)
    def parse_version(v: str) -> tuple:
        """Parse version string like 2026.1.0 into comparable tuple."""
        try:
            parts = v.split(".")
            return tuple(int(p) for p in parts)
        except (ValueError, AttributeError):
            return (0, 0, 0)
    
    current_version = parse_version(current_latest)
    newer = []
    
    for tag in version_tags:
        tag_version = parse_version(tag)
        if tag_version > current_version and tag not in supported:
            newer.append(tag)
    
    return sorted(newer, reverse=True)


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a release branch and tag."""
    src_dir = args.src_dir or os.getcwd()
    ensure_git_repo(src_dir)
    
    tag = args.tag
    if tag.startswith("zet-"):
        version = tag[len("zet-"):]
    else:
        version = tag
        tag = f"zet-{tag}"
    
    print(f"Deleting release: {tag}")
    delete_branch_and_tag(version, src_dir, push=args.push)
    
    if args.push:
        print(f"Deleted {tag} from local and remote.")
    else:
        print(f"Deleted {tag} locally. Use --push to also delete from remote.")


def cmd_list(args: argparse.Namespace) -> None:
    """List all available releases."""
    src_dir = args.src_dir or os.getcwd()
    ensure_git_repo(src_dir)
    list_releases(src_dir)


def cmd_detect(args: argparse.Namespace) -> None:
    """Detect and optionally create releases for newer upstream versions."""
    src_dir = args.src_dir or os.getcwd()
    ensure_git_repo(src_dir)
    
    newer = detect_newer_versions(src_dir)
    
    if not newer:
        print("No newer ESPHome versions found.")
        return
    
    print(f"\nFound {len(newer)} newer ESPHome version(s):")
    for version in newer:
        print(f"  - {version}")
    
    if args.auto_create:
        print("\nAuto-creating releases...")
        for version in newer:
            print(f"\nCreating release for {version}...")
            # Create a release for each newer version
            args_release = argparse.Namespace(
                esphome_tag=version,
                branch=f"release/zet-{version}",
                push=args.push,
                force_tag=False,
                src_dir=src_dir,
            )
            try:
                cmd_release(args_release)
            except Exception as e:
                print(f"Error creating release for {version}: {e}", file=sys.stderr)
                if not args.continue_on_error:
                    sys.exit(1)


def cmd_init(args: argparse.Namespace) -> None:
    src_dir = args.src_dir or os.getcwd()
    ensure_git_repo(src_dir)
    ensure_clean_worktree(src_dir)
    ensure_remote(src_dir)
    fetch_upstream_tags(src_dir)

    # Support zet- prefix
    full_tag = args.esphome_tag
    if full_tag.startswith("zet-"):
        upstream_tag = full_tag[len("zet-"):]
    else:
        upstream_tag = full_tag

    verify_upstream_tag(upstream_tag, src_dir)

    comps = read_components(src_dir)
    write_components_file_if_missing(comps, src_dir)

    import_components_from_upstream(upstream_tag, comps, src_dir)
    commit_import(upstream_tag, comps, src_dir)
    
    # Initialize .versions.yml
    update_versions(upstream_tag, src_dir)
    update_readme_badges(src_dir)
    run(["git", "-C", src_dir, "add", VERSIONS_FILE, "README.md"])

    print("\nInit done.")
    print("Now add your changes as commits, then tag the result, e.g.:")
    print(f"  git tag -a {full_tag} -m \"External components for ESPHome {full_tag}\"")


def cmd_release(args: argparse.Namespace) -> None:
    """
    Create a new release branch from the last import commit:
      - snapshot current patch stack
      - checkout new branch at last import commit
      - import new upstream components
      - replay patch stack
      - tag
    """
    src_dir = args.src_dir or os.getcwd()
    ensure_git_repo(src_dir)
    ensure_clean_worktree(src_dir)
    ensure_remote(src_dir)
    fetch_upstream_tags(src_dir)

    # Support zet- prefix
    full_tag = args.esphome_tag
    if full_tag.startswith("zet-"):
        upstream_tag = full_tag[len("zet-"):]
    else:
        upstream_tag = full_tag

    verify_upstream_tag(upstream_tag, src_dir)

    comps = read_components(src_dir)
    base = last_import_commit(src_dir)
    if not base:
        die("Could not find a previous import commit. Run `init <tag>` first.")

    branch = args.branch or f"release/{full_tag}"
    existing_branches = run(["git", "-C", src_dir, "branch", "--list", branch], capture=True)
    if existing_branches.strip():
        print(f"Branch {branch} already exists, switching to it.")
        run(["git", "-C", src_dir, "switch", branch])
        # Assume code and patches are already applied, just tag and push
        create_annotated_tag(
            full_tag,
            f"External components for ESPHome {full_tag}",
            src_dir,
            force=args.force_tag,
        )
        print("\nRelease already existed on branch:", branch)
        print("Tag created:", full_tag)
        if args.push:
            run(["git", "-C", src_dir, "push", "-u", "origin", branch])
            run(["git", "-C", src_dir, "push", "origin", f"refs/tags/{full_tag}"])
            print("Pushed branch + tag.")
        return
    else:
        with tempfile.TemporaryDirectory(prefix="esphome_patches_") as td:
            patches = format_patch_stack(base, td, src_dir)
            run(["git", "-C", src_dir, "switch", "-c", branch, base])
            import_components_from_upstream(upstream_tag, comps, src_dir)
            commit_import(upstream_tag, comps, src_dir)
            apply_patches(patches, src_dir)
        create_annotated_tag(
            full_tag,
            f"External components for ESPHome {full_tag}",
            src_dir,
            force=args.force_tag,
        )
        print("\nRelease created on branch:", branch)
        print("Tag created:", full_tag)
        if args.push:
            run(["git", "-C", src_dir, "push", "-u", "origin", branch])
            run(["git", "-C", src_dir, "push", "origin", f"refs/tags/{full_tag}"])
            print("Pushed branch + tag.")
        
        # Update .versions.yml on main branch
        print("\nUpdating .versions.yml on main branch...")
        run(["git", "-C", src_dir, "switch", "main"])
        run(["git", "-C", src_dir, "pull", "origin", "main"])
        update_versions(upstream_tag, src_dir)
        update_readme_badges(src_dir)
        run(["git", "-C", src_dir, "add", VERSIONS_FILE, "README.md"])
        run(["git", "-C", src_dir, "commit", "-m", f"Update versions: add {upstream_tag} as latest\n\nAlso updates README with current badges"])
        if args.push:
            run(["git", "-C", src_dir, "push", "origin", "main"])
            print("Pushed updated versions and README to main.")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_init = sub.add_parser("init", help="Import upstream component dirs for the first time")
    ap_init.add_argument("esphome_tag", help="ESPHome git tag (e.g. 2026.1.0)")
    ap_init.add_argument("--src-dir", help="Source directory where the repository lies (default: current directory)")
    ap_init.set_defaults(func=cmd_init)

    ap_rel = sub.add_parser("release", help="Import a new ESPHome version and replay your patch stack")
    ap_rel.add_argument("esphome_tag", help="New ESPHome git tag (e.g. 2026.2.0)")
    ap_rel.add_argument("--branch", help="Branch name to create (default: release/<tag>)")
    ap_rel.add_argument("--push", action="store_true", help="Push branch + tag to origin")
    ap_rel.add_argument("--force-tag", action="store_true", help="Force-create/move the release tag (NOT recommended)")
    ap_rel.add_argument("--src-dir", help="Source directory where the repository lies (default: current directory)")
    ap_rel.set_defaults(func=cmd_release)

    ap_del = sub.add_parser("delete", help="Delete a release branch and tag")
    ap_del.add_argument("tag", help="Release tag to delete (e.g. 2026.1.0 or zet-2026.1.0)")
    ap_del.add_argument("--push", action="store_true", help="Also delete from remote origin")
    ap_del.add_argument("--src-dir", help="Source directory where the repository lies (default: current directory)")
    ap_del.set_defaults(func=cmd_delete)

    ap_list = sub.add_parser("list", help="List all available releases")
    ap_list.add_argument("--src-dir", help="Source directory where the repository lies (default: current directory)")
    ap_list.set_defaults(func=cmd_list)

    ap_detect = sub.add_parser("detect", help="Detect newer upstream ESPHome versions")
    ap_detect.add_argument("--auto-create", action="store_true", help="Automatically create releases for newer versions")
    ap_detect.add_argument("--push", action="store_true", help="Push branches and tags when auto-creating")
    ap_detect.add_argument("--continue-on-error", action="store_true", help="Continue if one release fails during auto-create")
    ap_detect.add_argument("--src-dir", help="Source directory where the repository lies (default: current directory)")
    ap_detect.set_defaults(func=cmd_detect)

    args = ap.parse_args()
    args.func(args)



# Move main() definition above this block if not already
if __name__ == "__main__":
    main()
