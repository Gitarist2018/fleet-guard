#!/usr/bin/env python3
"""Safely discover Docker Compose projects and enroll validated ones in Fleet Guard.

This is a *config-only companion* to the existing Fleet Guard agent. It does
not update/restart containers, and does not enable maintenance permissions.

It intentionally errs on the side of refusing auto-enrollment when the Compose
source cannot be reproduced reliably (Portainer paths, stack.env, differing
mounts, changed image references, explicitly supplied --env-file).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

PREFIX = "com.docker.compose."
MANAGER_MARKERS = ("portainer", "dockge", "dockhand")


class DiscoveryError(Exception):
    pass


def run(cmd: list[str], timeout: int = 35) -> str:
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError(f"Could not execute {' '.join(cmd[:2])}: {type(exc).__name__}") from exc
    if cp.returncode:
        # Do not leak stderr from Compose validation: interpolation may include secrets.
        raise DiscoveryError(f"{' '.join(cmd[:2])} returned exit status {cp.returncode}")
    return cp.stdout


def get_containers() -> list[dict]:
    ids = run(["docker", "ps", "-aq"], timeout=30).split()
    if not ids:
        return []
    items = []
    for start in range(0, len(ids), 100):
        data = json.loads(run(["docker", "inspect", *ids[start:start + 100]], timeout=45))
        if not isinstance(data, list):
            raise DiscoveryError("Docker inspect did not return a JSON array")
        items.extend(data)
    return items


def label(container: dict, name: str) -> str:
    return str(((container.get("Config") or {}).get("Labels") or {}).get(PREFIX + name) or "")


def manager_mounts(containers: list[dict]) -> list[tuple[Path, Path, str]]:
    mappings = []
    for container in containers:
        image = str((container.get("Config") or {}).get("Image", "")).lower()
        name = str(container.get("Name", "")).lower()
        manager = next((m for m in MANAGER_MARKERS if m in image or m in name), None)
        if manager is None:
            continue
        for mount in container.get("Mounts") or []:
            if mount.get("Type") != "bind":
                continue
            destination = mount.get("Destination")
            source = mount.get("Source")
            if destination and source and Path(source).is_absolute() and Path(destination).is_absolute():
                mappings.append((Path(destination), Path(source), manager))
    return mappings


def under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_source(raw: str, cwd: Path, mappings: list[tuple[Path, Path, str]]) -> tuple[Path, str | None]:
    source = Path(raw)
    if not source.is_absolute():
        source = cwd / source
    if source.exists():
        return source.resolve(), None
    candidates = [(destination, source_base, manager) for destination, source_base, manager in mappings
                  if under(source, destination)]
    if not candidates:
        return source, None
    candidates.sort(key=lambda item: len(item[0].parts), reverse=True)
    longest = len(candidates[0][0].parts)
    best = [x for x in candidates if len(x[0].parts) == longest]
    resolved = {(base / source.relative_to(destination)).resolve() for destination, base, _ in best}
    if len(resolved) != 1:
        raise DiscoveryError("Compose label path maps to multiple host paths")
    return resolved.pop(), best[0][2]


def inspect_inventory(containers: list[dict], mappings: list[tuple[Path, Path, str]]) -> dict:
    projects = {}
    standalone = []
    for container in containers:
        name = str(container.get("Name") or "").lstrip("/")
        project, service = label(container, "project"), label(container, "service")
        if label(container, "oneoff").lower() in ("true", "1"):
            continue
        if not project or not service:
            standalone.append(name)
            continue
        item = projects.setdefault(project, {"services": set(), "containers": [], "label_sets": set()})
        item["services"].add(service)
        item["containers"].append(container)
        item["label_sets"].add((label(container, "project.working_dir"),
                                label(container, "project.config_files"),
                                label(container, "project.environment_file")))
    result = {}
    for project, item in sorted(projects.items()):
        result[project] = evaluate(project, item, mappings)
    return {"projects": result, "standalone": sorted(set(standalone))}


def evaluate(project: str, item: dict, mappings: list[tuple[Path, Path, str]]) -> dict:
    services = sorted(item["services"])
    output = {"services": services, "eligible": False, "reason": "", "working_dir": None,
              "files": [], "manager": None}
    try:
        if len(item["label_sets"]) != 1:
            raise DiscoveryError("Inconsistent Compose source labels across containers")
        raw_dir, raw_files, raw_env = next(iter(item["label_sets"]))
        if not raw_dir or not raw_files:
            raise DiscoveryError("Compose working_dir/config_files labels missing")
        if not Path(raw_dir).is_absolute():
            raise DiscoveryError("Compose working_dir label must be absolute")
        raw_parts = [s.strip() for s in raw_files.split(",")]
        if not all(raw_parts):
            raise DiscoveryError("Empty Compose file label")
        raw_root = Path(raw_dir)
        root, manager = resolve_source(raw_dir, raw_root, mappings)
        files = []
        for source in raw_parts:
            f, mapped_by = resolve_source(source, raw_root, mappings)
            manager = manager or mapped_by
            files.append(f)
        if not root.is_dir() or not all(f.is_file() for f in files):
            raise DiscoveryError("Working directory or Compose file unavailable on host")
        output["working_dir"] = str(root)
        output["files"] = [str(f) for f in files]
        output["manager"] = manager
        if raw_env:
            raise DiscoveryError("Explicit --env-file label: agent config cannot reproduce it")
        if manager:
            raise DiscoveryError(f"Source managed inside {manager}; manual path/env review required")
        if any((p / "stack.env").exists() for p in {root, files[0].parent}):
            raise DiscoveryError("stack.env found; additional variable source may be required")
        args = ["docker", "compose", "-p", project, "--project-directory", str(root)]
        for f in files:
            args += ["-f", str(f)]
        model = json.loads(run(args + ["config", "--format", "json"], timeout=40))
        definitions = model.get("services") or {}
        for container in item["containers"]:
            service = label(container, "service")
            definition = definitions.get(service)
            if not isinstance(definition, dict):
                raise DiscoveryError(f"Service {service} absent from resolved Compose model")
            if str(definition.get("image") or "") != str((container.get("Config") or {}).get("Image") or ""):
                raise DiscoveryError(f"Service {service} image differs from deployed container")
            expected_bind = {(str(v.get("target")), str(v.get("source")))
                             for v in definition.get("volumes", []) if isinstance(v, dict) and v.get("type") == "bind"}
            actual_bind = {(str(m.get("Destination")), str(m.get("Source")))
                           for m in container.get("Mounts") or [] if m.get("Type") == "bind"}
            if expected_bind != actual_bind:
                raise DiscoveryError(f"Service {service} bind mounts differ from deployed container")
        output["eligible"] = True
        output["reason"] = "Compose source, images and bind mounts match the running configuration"
    except DiscoveryError as exc:
        output["reason"] = str(exc)
    except (ValueError, TypeError, OSError) as exc:
        output["reason"] = "Could not validate Compose configuration: " + type(exc).__name__
    return output


def apply_config(config_path: Path, inventory: dict, confirm_scope: bool) -> tuple[list[str], list[str]]:
    if not config_path.is_file():
        raise DiscoveryError(f"Fleet Guard config file does not exist: {config_path}")
    if config_path.is_symlink():
        raise DiscoveryError("Refusing to edit a symlinked config file")
    current = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(current.get("compose_projects", {}), dict):
        raise DiscoveryError("Invalid compose_projects configuration")
    if "compose_update" in current.get("allowed_actions", []) and not confirm_scope:
        raise DiscoveryError("compose_update is enabled; use --approve-new-projects to acknowledge expanded update permissions")
    configured = current.setdefault("compose_projects", {})
    enrolled, existing = [], []
    for name, project in inventory["projects"].items():
        if not project["eligible"]:
            continue
        if name in configured:
            existing.append(name)
            continue
        configured[name] = {"working_dir": project["working_dir"], "files": project["files"]}
        enrolled.append(name)
    if not enrolled:
        return enrolled, existing
    backup = config_path.with_name(config_path.name + ".bak-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    shutil.copy2(config_path, backup, follow_symlinks=False)
    os.chmod(backup, 0o600)
    fd, temporary = tempfile.mkstemp(prefix="." + config_path.name + ".", dir=config_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(current, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(config_path.stat().st_mode) & 0o600)
        os.replace(temporary, config_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return enrolled, existing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("/etc/fleet-agent/config.json"))
    parser.add_argument("--apply", action="store_true", help="Add only verified, previously unconfigured projects")
    parser.add_argument("--approve-new-projects", action="store_true", help="Acknowledge update permission extension if compose_update already allowed")
    parser.add_argument("--json", action="store_true", help="Print machine-readable discovery report (never tokens)")
    args = parser.parse_args(argv)
    try:
        containers = get_containers()
        inventory = inspect_inventory(containers, manager_mounts(containers))
        if args.json:
            print(json.dumps(inventory, ensure_ascii=False, indent=2))
        else:
            projects = inventory["projects"]
            print(f"Compose projects discovered: {len(projects)}; standalone containers: {len(inventory['standalone'])}")
            for name, item in projects.items():
                result = "AUTO-READY" if item["eligible"] else "REVIEW"
                print(f"{result:10} {name:24} {len(item['services']):>2} services  {item['reason']}")
                if item["eligible"]:
                    print(f"            {item['working_dir']}")
            if inventory["standalone"]:
                print("Standalone (agent policy controls updates): " + ", ".join(inventory["standalone"]))
        if args.apply:
            added, existing = apply_config(args.config, inventory, args.approve_new_projects)
            print(f"ADDED {len(added)} verified Compose project(s): {', '.join(added) or '-'}")
            print(f"UNCHANGED {len(existing)} previously registered project(s)")
            if added:
                print("Config saved; restart fleet-agent to load new project mapping (no containers changed).")
        return 0
    except (DiscoveryError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
