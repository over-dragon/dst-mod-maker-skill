#!/usr/bin/env python3
"""Locate installed DST and a fallback source snapshot. Read-only."""
import argparse
import json
import os
import re
import sys
from pathlib import Path

GAME = "Don't Starve Together"


def steam_roots(explicit=None):
    home = Path.home()
    candidates = [explicit, os.environ.get("STEAM_ROOT"),
                  home / ".steam/steam", home / ".local/share/Steam",
                  home / ".var/app/com.valvesoftware.Steam/data/Steam",
                  home / "Library/Application Support/Steam"]
    if os.name == "nt":
        for var in ("ProgramFiles(x86)", "ProgramFiles"):
            if os.environ.get(var):
                candidates.append(Path(os.environ[var]) / "Steam")
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                candidates.append(winreg.QueryValueEx(key, "SteamPath")[0])
        except OSError:
            pass
        for drive in ("C:", "D:", "E:", "F:"):
            candidates.extend(Path(drive + "/") / name for name in ("Steam", "SteamLibrary"))
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        root = Path(candidate).expanduser()
        if not root.is_dir() or root.resolve() in seen:
            continue
        seen.add(root.resolve())
        yield root
        vdf = root / "steamapps/libraryfolders.vdf"
        if vdf.is_file():
            try:
                contents = vdf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for value in re.findall(r'"(?:path|\d+)"\s+"([^"\n]+)"', contents):
                library = Path(value.replace("\\\\", "\\"))
                if library.is_dir() and library.resolve() not in seen:
                    seen.add(library.resolve())
                    yield library


def game_bundle(root):
    if root is None:
        return None
    for path in (root / "data/databundles/scripts.zip",
                 root / "Contents/data/databundles/scripts.zip",
                 root / "dontstarve_steam.app/Contents/data/databundles/scripts.zip"):
        if path.is_file():
            return path
    return None


def find_game_root(explicit=None, steam_root=None):
    requested = explicit or os.environ.get("DST_GAME_ROOT")
    if requested:
        root = Path(requested).expanduser()
        return root if root.is_dir() else None
    for steam in steam_roots(steam_root):
        root = steam / "steamapps/common" / GAME
        if game_bundle(root):
            return root
    return None


def valid_scripts_dir(path):
    if not path:
        return None
    root = Path(path).expanduser()
    for candidate in (root, root / "scripts"):
        if all((candidate / name).is_file() for name in ("modutil.lua", "mods.lua", "entityscript.lua")) and (candidate / "prefabs").is_dir():
            return candidate
    return None


def derive_steam_root(game_root):
    for p in [game_root] + list(game_root.parents):
        if p.name.lower() == "steamapps":
            return p.parent
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game-root")
    ap.add_argument("--steam-root")
    ap.add_argument("--scripts-dir", help="unpacked fallback snapshot")
    ap.add_argument("--scripts-zip", help="explicit official source bundle")
    ap.add_argument("--skill-root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = find_game_root(args.game_root, args.steam_root)
    bundle = Path(args.scripts_zip) if args.scripts_zip else game_bundle(root)
    if bundle and not bundle.is_file():
        bundle = None
    snapshot = valid_scripts_dir(args.scripts_dir or os.environ.get("DST_SCRIPTS_DIR"))
    if (args.game_root and not root) or (args.scripts_zip and not bundle) or (args.scripts_dir and not snapshot):
        print("ERROR: invalid explicit game/source path", file=sys.stderr)
        return 2
    ver = root / "version.txt" if root else None
    steam = derive_steam_root(root) if root else None
    workshop = steam / "steamapps/workshop/content/322330" if steam else None
    skill = Path(args.skill_root) if args.skill_root else Path(__file__).resolve().parent.parent
    lib = skill / "references/lsp-dst/scripts"
    version = ver.read_text(encoding="utf-8", errors="replace").strip() if ver and ver.is_file() else None
    installed = game_bundle(root)
    result = {"game_root": str(root) if root else None,
              "version": version,
              "source_version": version if bundle and installed and bundle.resolve() == installed.resolve() else None,
              "scripts_zip": str(bundle) if bundle else None,
              "scripts_zip_size": bundle.stat().st_size if bundle else None,
              "scripts_dir": str(snapshot) if snapshot else None,
              "source_kind": "explicit_zip" if args.scripts_zip else "installed_zip" if bundle else "unverified_snapshot" if snapshot else "annotation_only",
              "mods_dir": str(root / "mods") if root and (root / "mods").is_dir() else None,
              "workshop_dir": str(workshop) if workshop and workshop.is_dir() else None,
              "annotation_library": str(lib) if lib.is_dir() else None}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for k, v in result.items():
            print(f"{k}: {v}")
    if not bundle:
        print("HINT: no installed source bundle; snapshot version is unverified, or use annotations for signatures only.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
