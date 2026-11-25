#!/usr/bin/env python3
"""Regression tests for the bundled read-only tools (no installed game needed)."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import check_mod
import grep_source
import locate_scripts


def run_tool(module, args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with patch.object(sys, "argv", [module.__file__, *map(str, args)]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = module.main()
    return code, stdout.getvalue(), stderr.getvalue()


class SourceTests(unittest.TestCase):
    def test_zip_preferred_and_snapshot_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            bundle = game / "data/databundles/scripts.zip"
            bundle.parent.mkdir(parents=True)
            with zipfile.ZipFile(bundle, "w") as zf:
                zf.writestr("scripts/modutil.lua", "function TestSymbol() end -- current\n")
                zf.writestr("scripts/mods.lua", "")
                zf.writestr("scripts/entityscript.lua", "")
            snapshot = root / "snapshot"
            for name in ("modutil.lua", "mods.lua", "entityscript.lua", "prefabs/sample.lua", "ai_skill/lsp-dst/annotation.lua", ".hidden/file.lua"):
                p = snapshot / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("function TestSymbol() end -- stale\n", encoding="utf-8")
            args = ["TestSymbol", "--game-root", game, "--scripts-dir", snapshot]
            code, out, err = run_tool(grep_source, args)
            self.assertEqual(code, 0)
            self.assertIn("current", out)
            self.assertNotIn("stale", out)
            code, out, err = run_tool(grep_source, args + ["--snapshot"])
            self.assertEqual(code, 0)
            self.assertIn("stale", out)
            self.assertNotIn("ai_skill", out)
            self.assertNotIn(".hidden", out)
            self.assertIn("unverified", err)

    def test_steam_libraryfolders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            steam = root / "main"
            library = root / "external library"
            (steam / "steamapps").mkdir(parents=True)
            bundle = library / "steamapps/common" / locate_scripts.GAME / "data/databundles/scripts.zip"
            bundle.parent.mkdir(parents=True)
            bundle.touch()
            value = str(library).replace("\\", "\\\\")
            (steam / "steamapps/libraryfolders.vdf").write_text(f'"libraryfolders" {{ "1" {{ "path" "{value}" }} }}', encoding="utf-8")
            with patch.dict(os.environ, {"DST_GAME_ROOT": ""}):
                self.assertEqual(locate_scripts.find_game_root(steam_root=steam), bundle.parents[2])


class CheckTests(unittest.TestCase):
    def test_lexical_scan(self):
        valid = ['-- comment (', 'local x = "("', 'local x = [=[function (]=]',
                 '--[=[ if ( ]=]\nlocal function f() if true then return 1 end end',
                 'for i = 1, 3 do repeat print(i) until true end']
        invalid = ['local function f()', 'local x = )', 'local x = "', 'if true then', '--[[unfinished']
        for source in valid:
            with self.subTest(source=source):
                self.assertEqual(check_mod.scan(*check_mod.lex(source)), [])
        for source in invalid:
            with self.subTest(source=source):
                self.assertTrue(check_mod.scan(*check_mod.lex(source)))

    def test_incomplete_scan_and_error_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "modmain.lua"
            path.write_text('local x = "("', encoding="utf-8")
            self.assertEqual(run_tool(check_mod, [root, "--no-luac", "--json"])[0], 3)
            path.write_text("local function f()", encoding="utf-8")
            self.assertEqual(run_tool(check_mod, [root, "--no-luac", "--json"])[0], 1)

    def test_resource_paths_comments_and_dynamics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "images").mkdir()
            (root / "images/icon.tex").touch()
            tokens, _ = check_mod.lex('''-- Asset("IMAGE", "missing.tex")
Asset('IMAGE', 'images/icon.tex')
Asset("IMAGE", "icon.tex")
Asset("IMAGE", geticon())''')
            kinds = [f["kind"] for f in check_mod.asset_findings(tokens, root, root / "modmain.lua")]
            self.assertEqual(kinds, ["ASSET_OK", "ASSET_UNRESOLVED", "ASSET_UNCHECKED"])

    def test_atlas_texture_paths_and_element_aliases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "images/avatars").mkdir(parents=True)
            (root / "images/icon.tex").touch()
            (root / "images/avatars/local.tex").touch()
            (root / "modmain.lua").write_text("return", encoding="utf-8")
            files = {
                "images/avatars/valid.xml": '<Atlas><Texture filename="local.tex"/><Elements><Element name="other.tex"/></Elements></Atlas>',
                "images/avatars/missing.xml": '<Atlas><Texture filename="icon.tex"/></Atlas>',
                "images/avatars/parent.xml": '<Atlas><Texture filename="../icon.tex"/></Atlas>',
                "images/avatars/external.xml": '<Atlas><Texture filename="../../../outside.tex"/></Atlas>',
                "images/avatars/absolute.xml": '<Atlas><Texture filename="D:/game/texture.tex"/></Atlas>',
                "images/avatars/invalid.xml": '<Atlas><Texture',
                "images/avatars/no_texture.xml": '<Atlas><Elements/></Atlas>',
                "images/unrelated.xml": '<Config><Texture filename="unrelated.tex"/></Config>',
            }
            for rel, source in files.items():
                (root / rel).write_text(source, encoding="utf-8")
            code, out, _ = run_tool(check_mod, [root, "--no-luac", "--json"])
            self.assertEqual(code, 3)
            report = json.loads(out)
            self.assertEqual({Path(f["file"]).name: f["kind"] for f in report["assets"]}, {
                "valid.xml": "ATLAS_TEXTURE_OK",
                "missing.xml": "ATLAS_TEXTURE_UNRESOLVED",
                "parent.xml": "ATLAS_TEXTURE_OK",
                "external.xml": "ATLAS_TEXTURE_UNCHECKED",
                "absolute.xml": "ATLAS_TEXTURE_UNCHECKED",
                "invalid.xml": "XML_UNCHECKED",
                "no_texture.xml": "ATLAS_TEXTURE_UNCHECKED",
            })
            self.assertEqual(report["summary"]["atlas_textures_unresolved"], 1)
            self.assertEqual(report["summary"]["atlas_textures_unchecked"], 3)
            self.assertEqual(report["summary"]["xml_unchecked"], 1)

    def test_new_mod_findings_from_literal_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = {
                "modmain.lua": 'modimport("main/init")\nmodimport("postinit/components/pickable")',
                "postinit/components/pickable.lua": "-- fixture",
                "main/init.lua": 'Assets = { Asset("ANIM", "anim/hammer.zip") }',
                "main/prefabs.lua": 'PrefabFiles = {"my_item"}\nAddPrefabPostInit("my_item", fn)\nGLOBAL.RegisterSinglePrefab(p)',
                "main/recipe.lua": '''-- Ingredient("not_real", 1)
AddRecipe2("my_item", { Ingredient("gold", 1), Ingredient("twigs", 2) }, TECH.SCIENCE_ONE, { image="hammer.tex" })''',
                "scripts/prefabs/my_item.lua": 'local assets = { Asset("ANIM", "anim/hammer.zip") }; return Prefab("my_item", fn, assets)',
            }
            for rel, source in sources.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(source, encoding="utf-8")
            code, out, _ = run_tool(check_mod, [root, "--no-luac", "--new-mod", "--json"])
            self.assertEqual(code, 3)  # diagnostic hints do not override syntax evidence
            findings = json.loads(out)["new_mod"]
            self.assertEqual({f["kind"] for f in findings}, {"DIRECT_POSTINIT_IMPORT", "GLOBAL_DECL_OUTSIDE_INIT", "RECIPE_FILTER_UNSPECIFIED", "INGREDIENT_UNVERIFIED", "DUPLICATE_PREFAB_ASSET", "HOOK_IN_ASSEMBLY", "MANUAL_PREFAB_REGISTRATION"})
            self.assertEqual([f["detail"] for f in findings if f["kind"] == "INGREDIENT_UNVERIFIED"], ["'gold' absent from bundled prefab annotations and literal local Prefab declarations; verify current source or dependency"])

    def test_modimport_targets_from_nested_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main").mkdir()
            (root / "main/language.lua").touch()
            (root / "main/init.lua").write_text(
                'modimport("main/language")\nenv.modimport("main/language.lua")\n'
                'modimport "main/languag"\nmodimport("main/" .. name)\n'
                'modimport("../external")\nother.modimport("ignored")\n'
                '-- modimport("example")\n', encoding="utf-8")
            code, out, _ = run_tool(check_mod, [root, "--no-luac", "--new-mod", "--json"])
            self.assertEqual(code, 3)
            findings = json.loads(out)["new_mod"]
            self.assertEqual([(f["line"], f["kind"]) for f in findings],
                             [(3, "MODIMPORT_MISSING"), (4, "MODIMPORT_UNCHECKED"),
                              (5, "MODIMPORT_UNCHECKED")])
            self.assertIn("main/languag.lua", findings[0]["detail"])

    def test_new_mod_conventions_allow_valid_custom_prefabs_and_filters(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = {
                "modmain.lua": 'modimport("main/init")\nmodimport("main/recipe")\nmodimport("main/components")',
                "main/init.lua": 'PrefabFiles = {"custom_material"}',
                "main/components.lua": 'modimport("postinit/components/pickable")',
                "postinit/components/pickable.lua": 'AddComponentPostInit("pickable", fn)',
                "main/recipe.lua": 'AddRecipe2("product", { Ingredient("goldnugget", 1), Ingredient("custom_material", 1) }, TECH.SCIENCE_ONE, { image="hammer.tex" }, {"TOOLS", "LIGHT"})',
                "scripts/prefabs/custom_material.lua": 'return Prefab("custom_material", fn)',
            }
            for rel, source in sources.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(source, encoding="utf-8")
            _, out, _ = run_tool(check_mod, [root, "--no-luac", "--new-mod", "--json"])
            self.assertEqual(json.loads(out)["new_mod"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
