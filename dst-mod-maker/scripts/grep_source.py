#!/usr/bin/env python3
"""Search installed DST Lua source; never mix source and annotation trees."""
import argparse
import fnmatch
import os
import re
import sys
import zipfile
from pathlib import Path

from locate_scripts import find_game_root, game_bundle, valid_scripts_dir

# Official top-level directories in the 762172 source bundle. Unknown trees in a
# fallback snapshot are intentionally excluded; use the ZIP for newer layouts.
SOURCE_DIRS = {"behaviours", "brains", "cameras", "components", "languages",
               "map", "nis", "prefabs", "scenarios", "screens", "stategraphs",
               "tools", "util", "widgets"}
EXCLUDED = {"mods", "ai_skill", "references", "lsp-dst", "backup", "third_party"}


def safe_snapshot_files(base):
    for path in sorted(base.iterdir()):
        if path.is_symlink():
            continue
        if path.is_file() and path.suffix == ".lua":
            yield path
        elif path.is_dir() and path.name in SOURCE_DIRS:
            for sub in sorted(path.rglob("*.lua")):
                parts = sub.relative_to(base).parts
                if not any(p.startswith((".", "_backup")) or p.lower() in EXCLUDED for p in parts) and not sub.is_symlink():
                    try:
                        sub.resolve().relative_to(base.resolve())
                    except ValueError:
                        continue
                    yield sub


def source_files(bundle, snapshot):
    if bundle:
        with zipfile.ZipFile(bundle) as zf:
            names = set(zf.namelist())
            prefix = "scripts/" if "scripts/modutil.lua" in names else ""
            if not all(prefix + name in names for name in ("modutil.lua", "mods.lua", "entityscript.lua")):
                raise ValueError("ZIP does not contain the expected official Lua source layout")
            for name in sorted(zf.namelist()):
                # Official archives normally use scripts/; permit root-level Lua
                # in a separately supplied archive with a flat layout.
                if name.startswith(prefix) and name.endswith(".lua"):
                    rel = name[len(prefix):]
                    parts = rel.split("/")
                    if not any(p.startswith(".") or p.lower() in EXCLUDED for p in parts):
                        yield "scripts/" + rel, lambda name=name: zf.read(name).decode("utf-8", errors="replace")
    else:
        for p in safe_snapshot_files(snapshot):
            yield "scripts/" + p.relative_to(snapshot).as_posix(), lambda p=p: p.read_text(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pattern", help="regular expression; use --literal for exact text")
    ap.add_argument("--game-root")
    ap.add_argument("--scripts-dir", help="unpacked fallback; use --snapshot to explicitly select it")
    ap.add_argument("--scripts-zip")
    ap.add_argument("--snapshot", action="store_true", help="explicitly prefer the supplied unpacked snapshot")
    ap.add_argument("--file", action="append", default=[], help="path glob e.g. components/*.lua or scripts/modutil.lua")
    ap.add_argument("-C", "--context", type=int, default=0)
    ap.add_argument("--limit", type=int, default=40, help="maximum matching lines (not context lines)")
    ap.add_argument("-i", "--ignore-case", action="store_true")
    ap.add_argument("--literal", action="store_true")
    args = ap.parse_args()
    if args.limit < 1 or args.context < 0:
        ap.error("limit must be positive and context non-negative")
    try:
        rx = re.compile(re.escape(args.pattern) if args.literal else args.pattern,
                        re.IGNORECASE if args.ignore_case else 0)
    except re.error as exc:
        ap.error(str(exc))
    root = find_game_root(args.game_root)
    if args.game_root and root is None:
        ap.error("invalid --game-root")
    bundle = Path(args.scripts_zip) if args.scripts_zip else game_bundle(root)
    snapshot = valid_scripts_dir(args.scripts_dir or os.environ.get("DST_SCRIPTS_DIR"))
    if args.scripts_zip and not bundle.is_file():
        ap.error("invalid --scripts-zip")
    if args.scripts_dir and snapshot is None:
        ap.error("invalid --scripts-dir (must contain official source layout)")
    if args.snapshot:
        if not snapshot or args.scripts_zip:
            ap.error("--snapshot requires --scripts-dir or DST_SCRIPTS_DIR; cannot combine with --scripts-zip")
        bundle = None
    if not bundle and not snapshot:
        print("ERROR: no official source available. Annotations can answer signatures, not implementation behaviour.", file=sys.stderr)
        return 2
    print(f"# source: {bundle or snapshot}", file=sys.stderr)
    if not bundle:
        print("# WARNING: unpacked snapshot; version and freshness unverified", file=sys.stderr)
    elif args.scripts_zip and (not game_bundle(root) or bundle.resolve() != game_bundle(root).resolve()):
        print("# NOTE: explicit archive; version and freshness unverified", file=sys.stderr)
    hits = 0
    try:
        for name, read_text in source_files(bundle, snapshot):
            if args.file and not any(fnmatch.fnmatch(name, g) or fnmatch.fnmatch(name[8:], g) for g in args.file):
                continue
            lines = read_text().splitlines()
            emitted = set()
            for i, line in enumerate(lines):
                if not rx.search(line):
                    continue
                hits += 1
                if hits > args.limit:
                    print(f"# truncated at {args.limit}; narrow --file or pattern", file=sys.stderr)
                    return 0
                for j in range(max(0, i - args.context), min(len(lines), i + args.context + 1)):
                    if j not in emitted:
                        print(f"{name}:{j+1}:{lines[j].rstrip()}")
                        emitted.add(j)
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        print(f"ERROR: failed to read source: {exc}", file=sys.stderr)
        return 2
    if hits == 0:
        print("# no hits; check spelling and source scope before assuming absence", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
