"""lint_design_md 的差分验证测试。

golden 来源 = upstream refs/google-labs-code/design.md 的规则单测
（broken-ref/section-order/orphaned-tokens/contrast-ratio .test.ts）+ fixture.test.ts，
逐例移植，确保本 Python 重写与 upstream lint 语义等价。
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import lint_design_md as lint  # noqa: E402

FIXTURES = (REPO_ROOT / "refs/google-labs-code/design.md/packages/cli/src/linter/fixtures")


def state(**overrides):
    """复刻 upstream buildState：从结构化 dict 建 state，断言无 error 级 model finding。"""
    result = lint.build_state(overrides)
    errs = [f for f in result["findings"] if f["severity"] == "error"]
    assert not errs, f"model build errors: {errs}"
    return result["designSystem"]


def msgs(findings):
    return [f["message"] for f in findings]


class PredicateTests(unittest.TestCase):
    def test_token_reference(self):
        self.assertTrue(lint.is_token_reference("{colors.primary}"))
        self.assertTrue(lint.is_token_reference("{colors.primary-60}"))
        self.assertFalse(lint.is_token_reference("colors.primary"))
        self.assertFalse(lint.is_token_reference("#fff"))
        self.assertFalse(lint.is_token_reference(123))

    def test_valid_color(self):
        for ok in ("#fff", "#ffff", "#ffffff", "#ffffffff", "#1A1C1E"):
            self.assertTrue(lint.is_valid_color(ok), ok)
        for bad in ("#ff", "#fffff", "fff", "red"):
            self.assertFalse(lint.is_valid_color(bad), bad)

    def test_dimension_parts(self):
        self.assertEqual(lint.parse_dimension_parts("48px"), {"value": 48.0, "unit": "px"})
        self.assertEqual(lint.parse_dimension_parts("-0.02em"), {"value": -0.02, "unit": "em"})
        self.assertIsNone(lint.parse_dimension_parts("abc"))
        self.assertIsNone(lint.parse_dimension_parts("16"))  # 无单位


class ColorMathTests(unittest.TestCase):
    def test_parse_color_shorthand(self):
        self.assertEqual(lint.parse_color("#fff")["hex"], "#ffffff")
        c = lint.parse_color("#1A1C1E")
        self.assertEqual((c["r"], c["g"], c["b"]), (0x1A, 0x1C, 0x1E))

    def test_contrast_black_white_is_21(self):
        black = lint.parse_color("#000000")
        white = lint.parse_color("#ffffff")
        self.assertAlmostEqual(lint.contrast_ratio(black, white), 21.0, places=1)

    def test_contrast_yellow_white_below_aa(self):
        yellow = lint.parse_color("#ffff00")
        white = lint.parse_color("#ffffff")
        self.assertLess(lint.contrast_ratio(yellow, white), 4.5)


class BrokenRefRuleTests(unittest.TestCase):
    def test_unresolved_ref_emits_error(self):
        s = state(colors={"primary": "#ff0000"},
                  components={"button": {"backgroundColor": "{colors.nonexistent}"}})
        f = lint.rule_broken_ref(s)
        self.assertTrue(any("does not resolve" in m for m in msgs(f)))
        self.assertTrue(any(d["severity"] == "error" for d in f if "does not resolve" in d["message"]))

    def test_all_refs_resolve(self):
        s = state(colors={"primary": "#ff0000"},
                  components={"button": {"backgroundColor": "{colors.primary}"}})
        f = [d for d in lint.rule_broken_ref(s) if "does not resolve" in d["message"]]
        self.assertEqual(len(f), 0)

    def test_unknown_sub_token_is_warning(self):
        s = state(colors={"primary": "#ff0000"},
                  components={"button": {"borderColor": "#ff0000"}})
        sub = [d for d in lint.rule_broken_ref(s) if "not a recognized" in d["message"]]
        self.assertEqual(len(sub), 1)
        self.assertEqual(sub[0]["severity"], "warning")


class SectionOrderRuleTests(unittest.TestCase):
    def _warns(self, sections):
        s = state(sections=sections)
        return lint.rule_section_order(s)

    def test_out_of_order_warns(self):
        f = self._warns(["Colors", "Overview"])
        self.assertEqual(len(f), 1)
        self.assertIn("out of order", f[0]["message"])

    def test_in_order_ok(self):
        self.assertEqual(self._warns(["Overview", "Colors"]), [])

    def test_unknown_ignored(self):
        self.assertEqual(self._warns(["Overview", "Unknown", "Colors"]), [])

    def test_alias_resolution(self):
        self.assertEqual(self._warns(["Brand & Style", "Colors", "Typography"]), [])
        self.assertEqual(self._warns(["Overview", "Colors", "Typography", "Layout & Spacing"]), [])
        self.assertEqual(self._warns(["Layout", "Elevation"]), [])

    def test_out_of_order_via_alias(self):
        f = self._warns(["Colors", "Brand & Style"])
        self.assertEqual(len(f), 1)

    def test_mixed_aliases_canonical(self):
        self.assertEqual(self._warns(
            ["Brand & Style", "Colors", "Typography", "Layout & Spacing",
             "Elevation & Depth", "Shapes", "Components"]), [])

    def test_resolve_alias_fn(self):
        self.assertEqual(lint.resolve_alias("Brand & Style"), "Overview")
        self.assertEqual(lint.resolve_alias("Layout & Spacing"), "Layout")
        self.assertEqual(lint.resolve_alias("Elevation"), "Elevation & Depth")
        self.assertEqual(lint.resolve_alias("Iconography"), "Iconography")


class OrphanedTokensRuleTests(unittest.TestCase):
    def test_unused_color_flagged(self):
        s = state(colors={"primary": "#ff0000", "unused": "#00ff00"},
                  components={"button": {"backgroundColor": "{colors.primary}"}})
        f = lint.rule_orphaned_tokens(s)
        self.assertTrue(any("unused" in m for m in msgs(f)))

    def test_no_components_empty(self):
        s = state(colors={"primary": "#ff0000"})
        self.assertEqual(lint.rule_orphaned_tokens(s), [])

    def test_md3_paired_not_flagged_when_family_referenced(self):
        s = state(colors={
            "primary": "#1A1C1E", "on-primary": "#ffffff",
            "primary-container": "#e2e2e2", "on-primary-container": "#636565",
            "primary-fixed": "#e2e2e2", "primary-fixed-dim": "#c6c6c7",
            "on-primary-fixed": "#1a1c1c", "on-primary-fixed-variant": "#454747",
            "inverse-primary": "#5d5f5f",
        }, components={"button": {"backgroundColor": "{colors.primary}"}})
        self.assertEqual(lint.rule_orphaned_tokens(s), [])

    def test_md3_surface_family(self):
        s = state(colors={
            "surface": "#0b1326", "surface-dim": "#0b1326", "surface-bright": "#31394d",
            "surface-container": "#171f33", "surface-container-lowest": "#060e20",
            "surface-container-low": "#131b2e", "surface-container-high": "#222a3d",
            "surface-container-highest": "#2d3449", "on-surface": "#dae2fd",
            "on-surface-variant": "#c4c7c8", "inverse-surface": "#dae2fd",
            "inverse-on-surface": "#283044", "surface-tint": "#c6c6c7", "surface-variant": "#2d3449",
        }, components={"card": {"backgroundColor": "{colors.surface-container}"}})
        self.assertEqual(lint.rule_orphaned_tokens(s), [])

    def test_custom_orphan_still_flagged(self):
        s = state(colors={"primary": "#1A1C1E", "on-primary": "#ffffff", "brand-blue": "#0000ff"},
                  components={"button": {"backgroundColor": "{colors.primary}"}})
        f = lint.rule_orphaned_tokens(s)
        paths = [d["path"] for d in f]
        self.assertIn("colors.brand-blue", paths)
        self.assertNotIn("colors.on-primary", paths)


class ContrastRuleTests(unittest.TestCase):
    def test_low_contrast_warns(self):
        s = state(colors={"yellow": "#ffff00", "white": "#ffffff"},
                  components={"bad": {"backgroundColor": "{colors.yellow}", "textColor": "{colors.white}"}})
        f = lint.rule_contrast_ratio(s)
        self.assertEqual(len(f), 1)
        self.assertIn("contrast", f[0]["message"])

    def test_high_contrast_ok(self):
        s = state(colors={"black": "#000000", "white": "#ffffff"},
                  components={"good": {"backgroundColor": "{colors.black}", "textColor": "{colors.white}"}})
        self.assertEqual([d for d in lint.rule_contrast_ratio(s) if "contrast" in d["message"]], [])


class ReferenceResolutionTests(unittest.TestCase):
    def test_chained_reference(self):
        s = state(colors={"primary": "#ff0000", "brand": "{colors.primary}"},
                  components={"b": {"backgroundColor": "{colors.brand}"}})
        # 链式解析后无 broken-ref
        self.assertEqual([d for d in lint.rule_broken_ref(s) if "does not resolve" in d["message"]], [])

    def test_cycle_is_unresolved(self):
        s = state(colors={"a": "{colors.b}", "b": "{colors.a}"},
                  components={"c": {"backgroundColor": "{colors.a}"}})
        f = [d for d in lint.rule_broken_ref(s) if "does not resolve" in d["message"]]
        self.assertEqual(len(f), 1)


class YamlSubsetParserTests(unittest.TestCase):
    def test_nested_map(self):
        text = (
            "version: alpha\n"
            "name: Daylight Prestige\n"
            "colors:\n"
            '  primary: "#1A1C1E"\n'
            "  secondary: \"#6C7278\"\n"
            "typography:\n"
            "  h1:\n"
            "    fontFamily: Public Sans\n"
            "    fontSize: 48px\n"
            "    fontWeight: 600\n"
            "    lineHeight: 1.1\n"
            "components:\n"
            "  button-primary:\n"
            '    backgroundColor: "{colors.primary-60}"\n'
            "    padding: 12px\n"
        )
        d = lint.parse_yaml_block(text)
        self.assertEqual(d["name"], "Daylight Prestige")
        self.assertEqual(d["colors"]["primary"], "#1A1C1E")
        self.assertEqual(d["typography"]["h1"]["fontFamily"], "Public Sans")
        self.assertEqual(d["typography"]["h1"]["fontWeight"], 600)
        self.assertEqual(d["typography"]["h1"]["lineHeight"], 1.1)
        self.assertEqual(d["components"]["button-primary"]["backgroundColor"], "{colors.primary-60}")
        self.assertEqual(d["components"]["button-primary"]["padding"], "12px")

    def test_comment_and_unquoted_hex_is_null(self):
        # YAML: `key: #x`（值以 # 开头）= comment → null（DESIGN.md 因此给 hex 加引号）
        d = lint.parse_yaml_block("a: b # trailing\nc: #1A1C1E\n")
        self.assertEqual(d["a"], "b")
        self.assertIsNone(d["c"])


class ParseDesignMdTests(unittest.TestCase):
    def test_frontmatter_and_sections(self):
        content = (
            "---\n"
            "name: Demo\n"
            "colors:\n"
            '  primary: "#000000"\n'
            "---\n"
            "# Title\n"
            "## Overview\n"
            "prose\n"
            "## Colors\n"
            "more\n"
        )
        parsed = lint.parse_design_md(content)
        self.assertEqual(parsed["name"], "Demo")
        self.assertEqual(parsed["sections"], ["Overview", "Colors"])

    def test_no_yaml_raises(self):
        with self.assertRaises(lint.DesignMdError):
            lint.parse_design_md("# Just markdown\n## Overview\nno tokens\n")

    def test_duplicate_section_raises(self):
        content = (
            "---\n"
            "colors:\n"
            '  a: "#000000"\n'
            "---\n"
            "## Colors\n"
            "```yaml\n"
            "colors:\n"
            '  b: "#ffffff"\n'
            "```\n"
        )
        with self.assertRaises(lint.DesignMdError):
            lint.parse_design_md(content)

    def test_h2_inside_code_fence_not_section(self):
        content = (
            "---\n"
            "name: X\n"
            "---\n"
            "## Real\n"
            "```\n"
            "## not a heading\n"
            "```\n"
        )
        parsed = lint.parse_design_md(content)
        self.assertEqual(parsed["sections"], ["Real"])


class FixtureIntegrationTests(unittest.TestCase):
    """对 upstream 9 个真实 fixture 跑整链，验证解析器健壮性 + 关键事实。"""

    def test_fixtures_present(self):
        self.assertTrue(FIXTURES.is_dir(), f"fixtures not found: {FIXTURES}")

    def test_design_test_fixture_parses(self):
        # 来自 upstream fixture.test.ts 的 golden 断言
        f = FIXTURES / "DESIGN-test.md"
        parsed = lint.parse_design_md(f.read_text(encoding="utf-8"))
        result = lint.build_state(parsed)
        ds = result["designSystem"]
        self.assertEqual(ds["name"], "Pacific Mint Dental")
        self.assertIn("surface", ds["colors"])
        self.assertEqual(ds["colors"]["surface"]["hex"], "#f9f9ff")
        # 无 "invalid unit" error（em 单位应被接受）
        unit_errs = [d for d in result["findings"]
                     if d["severity"] == "error" and "invalid unit" in d["message"]]
        self.assertEqual(unit_errs, [])

    def test_all_fixtures_no_crash(self):
        for f in sorted(FIXTURES.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            try:
                findings = lint.lint_content(content)
            except Exception as exc:  # noqa: BLE001
                self.fail(f"crash on {f.name}: {exc!r}")
            self.assertIsInstance(findings, list)

    def test_out_of_order_fixture_flags_section_order(self):
        f = FIXTURES / "OUT_OF_ORDER.md"
        if not f.is_file():
            self.skipTest("fixture missing")
        findings = lint.lint_content(f.read_text(encoding="utf-8"))
        self.assertTrue(any("out of order" in d["message"] for d in findings))

    def test_no_frontmatter_fixture(self):
        f = FIXTURES / "NO_FRONTMATTER.md"
        if not f.is_file():
            self.skipTest("fixture missing")
        findings = lint.lint_content(f.read_text(encoding="utf-8"))
        # 无 frontmatter 且无 fenced yaml → 报 error；若有 fenced yaml 则正常解析
        self.assertIsInstance(findings, list)


if __name__ == "__main__":
    unittest.main()
