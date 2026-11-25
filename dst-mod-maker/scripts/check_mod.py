#!/usr/bin/env python3
"""Read-only Lua 5.1 syntax/lexical scan, literal assets, optional new-mod diagnostics."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PureWindowsPath

SKIP_DIRS = {"_ai_work", ".git", "__pycache__"}
LONG_OPEN = re.compile(r"\[(=*)\[")
IDENT = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*")
ASSET_TYPES = {"IMAGE", "ATLAS", "ATLAS_BUILD", "ANIM", "SOUND", "SOUNDPACK", "SHADER"}


def iter_files(mod_dir, pattern):
    for path in sorted(mod_dir.rglob(pattern)):
        if not any(part in SKIP_DIRS or part.startswith("_backup") for part in path.relative_to(mod_dir).parts):
            yield path


def iter_lua(mod_dir):
    return iter_files(mod_dir, "*.lua")


def read(path):
    return path.read_text(encoding="utf-8-sig")


def lex(text):
    """Return (kind, value, line) tokens, plus lexical suspects; skip comments."""
    tokens, issues = [], []
    i, line = 0, 1
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            line += ch == "\n"
            i += 1
            continue
        comment = text.startswith("--", i)
        start = i + 2 if comment else i
        long = LONG_OPEN.match(text, start)
        if long:
            close = "]" + long.group(1) + "]"
            end = text.find(close, long.end())
            if end < 0:
                issues.append((line, "unterminated long comment/string"))
                break
            if not comment:
                tokens.append(("string", text[long.end():end], line))
            end += len(close)
            line += text.count("\n", i, end)
            i = end
            continue
        if comment:
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        if ch in "'\"":
            opening_line = line
            j = i + 1
            while j < len(text) and text[j] != ch:
                if text[j] == "\\" and j + 1 < len(text):
                    j += 1
                    line += text[j] == "\n"
                    j += 1
                elif text[j] in "\r\n":
                    break
                else:
                    j += 1
            if j >= len(text) or text[j] != ch:
                issues.append((opening_line, "unterminated short string"))
                break
            tokens.append(("string", text[i+1:j], opening_line))
            i = j + 1
            continue
        ident = IDENT.match(text, i)
        if ident:
            tokens.append(("word", ident.group(), line))
            i = ident.end()
        else:
            tokens.append(("symbol", ch, line))
            i += 1
    return tokens, issues


def scan(tokens, issues):
    """Detect unbalanced lexical delimiters/blocks; not a Lua parser."""
    brackets, blocks = [], []
    pairs = {")": "(", "]": "[", "}": "{"}
    for kind, value, line in tokens:
        if kind == "symbol":
            if value in "([{":
                brackets.append((value, line))
            elif value in pairs:
                if brackets and brackets[-1][0] == pairs[value]:
                    brackets.pop()
                else:
                    issues.append((line, f"unmatched {value}"))
        elif kind == "word":
            if value in {"function", "if", "do", "repeat"}:
                blocks.append((value, line))
            elif value in {"end", "until"}:
                expected = "repeat" if value == "until" else None
                if not blocks or (blocks[-1][0] == "repeat") != (expected == "repeat"):
                    issues.append((line, f"unmatched {value}"))
                else:
                    blocks.pop()
    issues.extend((line, f"unclosed {value}") for value, line in brackets + blocks)
    return issues


def choose_parser(explicit=None):
    # A generic luac may be 5.4. Only count a compatible 5.1 syntax parser.
    for name in ([explicit] if explicit else ["luac5.1", "luac-5.1", "luac", "lua5.1", "lua-5.1", "lua"]):
        executable = shutil.which(name)
        if not executable:
            continue
        try:
            result = subprocess.run([executable, "-v"], text=True, capture_output=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            continue
        version = (result.stdout + result.stderr).strip()
        if re.search(r"\bLua 5\.1(?:\.|\b)", version):
            return executable, "luac" if "luac" in Path(executable).name.lower() else "lua", version
    return None


def parse_file(parser, path):
    path_exe, kind, _ = parser
    if kind == "luac":
        command = [path_exe, "-p", str(path.resolve())]
        env = None
    else:
        # loadfile compiles without executing the mod's chunk.
        command = [path_exe, "-e", "local f,e=loadfile(os.getenv('DST_CHECK_LUA_FILE')); if not f then error(e,0) end"]
        env = dict(os.environ, DST_CHECK_LUA_FILE=str(path.resolve()))
    return subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=20, env=env)


def asset_findings(tokens, mod_dir, file):
    findings = []
    for i in range(len(tokens) - 5):
        window = tokens[i:i+6]
        values = [t[1] for t in window]
        if (window[0][:2] != ("word", "Asset") or values[1] != "("
                or window[2][0] != "string" or values[2] not in ASSET_TYPES or values[3] != ","):
            continue
        if window[4][0] != "string" or values[5] not in {")", ","} or "\\" in values[4]:
            findings.append({"file": str(file), "line": window[0][2], "kind": "ASSET_UNCHECKED", "detail": "dynamic or escaped asset path"})
            continue
        rel = Path(values[4])
        found = not rel.is_absolute() and ".." not in rel.parts and (mod_dir / rel).is_file()
        findings.append({"file": str(file), "line": window[0][2],
                         "kind": "ASSET_OK" if found else "ASSET_UNRESOLVED",
                         "detail": f"{values[4]} {'found at declared mod-relative path' if found else 'not found at declared mod-relative path; check external/official resources'}"})
    return findings


def atlas_findings(mod_dir):
    """Check local atlas Texture filenames relative to their XML, not Element names."""
    findings = []
    root_dir = mod_dir.resolve()
    for path in iter_files(mod_dir, "*.xml"):
        def note(kind, detail):
            findings.append({"file": str(path), "line": 0, "kind": kind, "detail": detail})

        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError, ValueError) as exc:
            note("XML_UNCHECKED", f"could not read XML: {exc}")
            continue
        if root.tag != "Atlas":
            continue
        textures = root.findall("Texture")
        if not textures:
            note("ATLAS_TEXTURE_UNCHECKED", "Atlas has no direct Texture declaration")
            continue
        for texture in textures:
            filename = texture.get("filename", "").strip()
            rel = Path(filename.replace("\\", "/"))
            if not filename or rel.is_absolute() or PureWindowsPath(filename).drive:
                note("ATLAS_TEXTURE_UNCHECKED", f"{filename!r}: not a relative texture filename; verify resource resolution")
                continue
            try:
                target = (path.parent / rel).resolve()
                target_rel = target.relative_to(root_dir)
                local = True
                found = target.is_file()
            except (OSError, RuntimeError, ValueError):
                local = found = False
            if found:
                note("ATLAS_TEXTURE_OK", f"{filename!r} found at {target_rel.as_posix()}")
            elif local:
                note("ATLAS_TEXTURE_UNRESOLVED", f"{filename!r} not found at XML-relative path {target_rel.as_posix()}; a registered official texture with the same name does not establish this reference")
            else:
                note("ATLAS_TEXTURE_UNCHECKED", f"{filename!r}: path outside mod or unresolved; verify actual resource resolution")
    return findings


def call_args(tokens, start):
    """Split simple parenthesized calls at top-level commas (not a Lua parser)."""
    stack, args, current = ["("], [], []
    closing = {")": "(", "]": "[", "}": "{"}
    for index in range(start + 2, len(tokens)):
        token = tokens[index]
        kind, value, _ = token
        if kind == "symbol":
            if value in "([{":
                stack.append(value)
            elif value in closing:
                if not stack or stack[-1] != closing[value]:
                    return None
                stack.pop()
                if not stack:
                    return args + ([current] if current or args else [])
            elif value == "," and len(stack) == 1:
                args.append(current)
                current = []
                continue
        current.append(token)
    return None


def literal(arg):
    if len(arg) == 1 and arg[0][0] == "string" and "\\" not in arg[0][1]:
        return arg[0][1]
    return None


def simple_calls(tokens):
    names = {"modimport", "AddRecipe2", "Ingredient", "Asset", "Prefab"}
    for i, (kind, name, line) in enumerate(tokens[:-1]):
        if kind != "word" or name not in names:
            continue
        if name == "modimport":
            prev = tokens[i-1][:2] if i else None
            if prev == ("word", "function") or prev == ("symbol", ":"):
                continue
            if prev == ("symbol", ".") and (i < 2 or tokens[i-2][:2] != ("word", "env")):
                continue
            if tokens[i+1][0] == "string":
                yield name, line, [[tokens[i+1]]]
                continue
        if tokens[i+1][:2] == ("symbol", "("):
            args = call_args(tokens, i)
            if args and (name == "modimport" or literal(args[0]) is not None):
                yield name, line, args


def new_mod_findings(token_files, mod_dir):
    """Advisory diagnostics for literal calls and this skill's new-mod conventions."""
    findings = []
    calls = {path: list(simple_calls(tokens)) for path, tokens in token_files.items()}
    catalog = Path(__file__).resolve().parent.parent / "references/lsp-dst/scripts/lan/prefab.lua"
    known = set()
    try:
        known.update(re.findall(r'^---\|\s*["\']([^"\']+)["\']', read(catalog), re.M))
    except (OSError, UnicodeError):
        pass
    has_catalog = bool(known)
    for entries in calls.values():
        known.update(literal(args[0]) for name, _, args in entries if name == "Prefab")

    def note(path, line, kind, detail):
        findings.append({"file": str(path), "line": line, "kind": kind, "detail": detail})

    def asset_key(args):
        if len(args) < 2 or literal(args[1]) is None:
            return None
        return tuple(tuple(t[:2] for t in arg) for arg in args)

    prefab_assets = set()
    for path, entries in calls.items():
        rel = path.relative_to(mod_dir).as_posix()
        if rel.startswith("scripts/prefabs/"):
            prefab_assets.update(key for name, _, args in entries if name == "Asset" and (key := asset_key(args)) is not None)

    for path, tokens in token_files.items():
        rel = path.relative_to(mod_dir).as_posix()
        hook_names = {
            "AddPrefabPostInit", "AddPrefabPostInitAny", "AddPlayerPostInit",
            "AddComponentPostInit", "AddClassPostConstruct", "AddBrainPostInit",
            "AddStategraphPostInit", "AddStategraphActionHandler", "AddComponentAction",
        }
        for i, (kind, name, line) in enumerate(tokens[:-1]):
            if kind != "word" or tokens[i+1][:2] != ("symbol", "("):
                continue
            if name in hook_names and (rel == "modmain.lua" or rel.startswith("main/")):
                note(path, line, "HOOK_IN_ASSEMBLY", f"{name}: move the implementation to postinit and import it from main")
            elif name == "RegisterSinglePrefab":
                note(path, line, "MANUAL_PREFAB_REGISTRATION", "check whether scripts/prefabs and PrefabFiles can replace manual registration and reload workarounds")
        if rel != "main/init.lua" and (rel == "modmain.lua" or rel.startswith(("main/", "postinit/"))):
            for i, (kind, name, line) in enumerate(tokens[:-1]):
                if kind == "word" and name in {"PrefabFiles", "Assets"} and tokens[i+1][:2] == ("symbol", "="):
                    prev = tokens[i-1][:2] if i else None
                    equality = i + 2 < len(tokens) and tokens[i+2][:2] == ("symbol", "=")
                    if not equality and prev not in {("word", "local"), ("symbol", "."), ("symbol", ":")}:
                        note(path, line, "GLOBAL_DECL_OUTSIDE_INIT", f"{name} belongs in main/init.lua for new mods")
        for name, line, args in calls[path]:
            first = literal(args[0])
            if name == "modimport":
                if first is None or PureWindowsPath(first).anchor:
                    note(path, line, "MODIMPORT_UNCHECKED", "verify the import path at runtime")
                    continue
                if rel == "modmain.lua" and first.startswith("postinit/"):
                    note(path, line, "DIRECT_POSTINIT_IMPORT", "modmain should import the corresponding main file, which forwards to postinit")
                filename = first if first.endswith(".lua") else first + ".lua"
                try:
                    target = (mod_dir / filename).resolve()
                    target.relative_to(mod_dir.resolve())
                    exists = target.is_file()
                except (ValueError, OSError, RuntimeError):
                    note(path, line, "MODIMPORT_UNCHECKED", f"cannot verify {filename!r} within the mod directory")
                    continue
                if not exists:
                    note(path, line, "MODIMPORT_MISSING", f"file missing relative to mod root: {filename}")
            elif name == "AddRecipe2":
                fifth = [t[:2] for t in args[4]] if len(args) >= 5 else []
                if not fifth or fifth in [[("word", "nil")], [("symbol", "{"), ("symbol", "}")]]:
                    note(path, line, "RECIPE_FILTER_UNSPECIFIED", f"{first}: check fifth-argument crafting filters; ordinary recipes should have a purpose category")
            elif name == "Ingredient" and has_catalog and first not in known:
                note(path, line, "INGREDIENT_UNVERIFIED", f"{first!r} absent from bundled prefab annotations and literal local Prefab declarations; verify current source or dependency")
            elif name == "Asset" and rel == "main/init.lua" and asset_key(args) in prefab_assets:
                note(path, line, "DUPLICATE_PREFAB_ASSET", f"{literal(args[1])!r} also declared in a prefab file; check if public loading is actually needed")
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mod_dir")
    ap.add_argument("--no-luac", action="store_true", help="use lexical scan only")
    ap.add_argument("--luac", help="explicit compatible Lua 5.1 parser executable")
    ap.add_argument("--new-mod", action="store_true", help="also check new-mod conventions and literal recipe declarations (advisory)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    mod_dir = Path(args.mod_dir)
    if not mod_dir.is_dir():
        ap.error("mod directory not found")
    files = list(iter_lua(mod_dir))
    if not files:
        ap.error("no Lua files under mod directory")
    parser = None if args.no_luac else choose_parser(args.luac)
    if args.luac and not parser and not args.no_luac:
        ap.error("specified parser is not available or not Lua 5.1")
    report = {"mod_dir": str(mod_dir), "lua_files": len(files),
              "parser": parser[2] if parser else None, "syntax": [], "assets": [], "file_checks": []}
    token_files = {}
    for path in files:
        try:
            text = read(path)
        except (OSError, UnicodeError) as exc:
            report["file_checks"].append({"file": str(path), "method": "unreadable"})
            report["syntax"].append({"file": str(path), "line": 0, "kind": "READ_ERROR", "detail": str(exc)})
            continue
        tokens, suspects = lex(text)
        if args.new_mod:
            token_files[path] = tokens
        method = "heuristic_only"
        if parser:
            try:
                result = parse_file(parser, path)
                method = "lua51_parse"
                if result.returncode:
                    report["syntax"].append({"file": str(path), "line": 0, "kind": "SYNTAX_ERROR", "detail": (result.stdout + result.stderr).strip()[:500]})
            except (OSError, subprocess.SubprocessError) as exc:
                report["syntax"].append({"file": str(path), "line": 0, "kind": "PARSER_UNAVAILABLE", "detail": str(exc)})
        if method == "heuristic_only":
            for line, detail in scan(tokens, suspects):
                report["syntax"].append({"file": str(path), "line": line, "kind": "SYNTAX_SUSPECT", "detail": detail})
        report["file_checks"].append({"file": str(path), "method": method})
        report["assets"].extend(asset_findings(tokens, mod_dir, path))
    report["assets"].extend(atlas_findings(mod_dir))
    if args.new_mod:
        report["new_mod"] = new_mod_findings(token_files, mod_dir)
    summary = report["summary"] = {
        "syntax_errors": sum(f["kind"] == "SYNTAX_ERROR" for f in report["syntax"]),
        "syntax_suspects": sum(f["kind"] == "SYNTAX_SUSPECT" for f in report["syntax"]),
        "parsed_files": sum(f["method"] == "lua51_parse" for f in report["file_checks"]),
        "heuristic_only_files": sum(f["method"] == "heuristic_only" for f in report["file_checks"]),
        "unreadable_files": sum(f["method"] == "unreadable" for f in report["file_checks"]),
        "assets_unresolved": sum(f["kind"] == "ASSET_UNRESOLVED" for f in report["assets"]),
        "assets_unchecked": sum(f["kind"] == "ASSET_UNCHECKED" for f in report["assets"]),
        "atlas_textures_unresolved": sum(f["kind"] == "ATLAS_TEXTURE_UNRESOLVED" for f in report["assets"]),
        "atlas_textures_unchecked": sum(f["kind"] == "ATLAS_TEXTURE_UNCHECKED" for f in report["assets"]),
        "xml_unchecked": sum(f["kind"] == "XML_UNCHECKED" for f in report["assets"]),
    }
    if args.new_mod:
        summary["new_mod_findings"] = len(report["new_mod"])
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"mod: {mod_dir} | Lua files: {len(files)} | parser: {report['parser'] or 'unavailable (heuristic only)'}")
        print(json.dumps(summary, ensure_ascii=False))
        for f in report["syntax"] + report["assets"] + report.get("new_mod", []):
            print(f"[{f['kind']}] {f['file']}:{f['line']} {f['detail']}")
        print("NOTE: a lexical scan does not establish syntax validity. Parsing and file existence do not establish DST runtime correctness.")
        if args.new_mod:
            print("NOTE: new_mod findings are advisory, do not change the syntax exit code, and must be checked against current source and dependencies.")
    if summary["syntax_errors"] or summary["syntax_suspects"]:
        return 1
    if summary["parsed_files"] != len(files):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
