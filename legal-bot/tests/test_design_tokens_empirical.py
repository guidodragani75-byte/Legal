"""
Empirical Unit Test Suite for DESIGN.md
Challenger M1.1
Tests CSS syntax, variable alias resolution, color validity, WCAG 2.1 compliance,
and adversarial stress-testing.
"""

import os
import unittest
from tests.verify_design_tokens import (
    DESIGN_MD_PATH,
    parse_root_css_variables,
    parse_markdown_table_tokens,
    resolve_variable,
    parse_color_to_rgb,
    blend_over_background,
    calculate_contrast_ratio,
    evaluate_wcag_level,
    run_all_checks
)

class TestDesignSystemTokensEmpirical(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(DESIGN_MD_PATH, "r", encoding="utf-8", errors="replace") as f:
            cls.content = f.read()
        cls.root_vars, cls.duplicates = parse_root_css_variables(cls.content)
        cls.table_tokens = parse_markdown_table_tokens(cls.content)
        cls.report = run_all_checks()

    def test_file_exists_and_non_empty(self):
        self.assertTrue(os.path.exists(DESIGN_MD_PATH))
        self.assertGreater(len(self.content), 1000)

    def test_no_duplicate_css_variables(self):
        self.assertEqual(len(self.duplicates), 0, f"Found duplicate tokens: {self.duplicates}")

    def test_all_markdown_table_tokens_in_root(self):
        missing = [t for t in self.table_tokens if t not in self.root_vars]
        self.assertEqual(missing, [], f"Tokens mentioned in tables missing from :root: {missing}")

    def test_all_aliases_resolve_without_cycles(self):
        self.assertEqual(self.report["unresolved_aliases"], [])

    def test_all_color_values_are_valid_hex_or_rgba(self):
        self.assertEqual(self.report["color_validity"]["invalid"], [])
        self.assertGreaterEqual(self.report["color_validity"]["valid_count"], 50)

    def test_taxonomy_prefixes_strictly_followed(self):
        self.assertEqual(self.report["taxonomy_compliance"], [])

    def test_wcag_contrast_primary_text_aaa(self):
        canvas_rgb = parse_color_to_rgb(self.root_vars["--color-bg-canvas"])[:3]
        surface_rgb = parse_color_to_rgb(self.root_vars["--color-bg-surface"])[:3]
        primary_text_rgb = parse_color_to_rgb(self.root_vars["--color-text-primary"])[:3]

        ratio_canvas = calculate_contrast_ratio(primary_text_rgb, canvas_rgb)
        ratio_surface = calculate_contrast_ratio(primary_text_rgb, surface_rgb)

        self.assertGreaterEqual(ratio_canvas, 7.0, "Primary text vs Canvas must meet AAA (>= 7.0)")
        self.assertGreaterEqual(ratio_surface, 7.0, "Primary text vs Surface must meet AAA (>= 7.0)")

    def test_wcag_contrast_secondary_text_aaa(self):
        canvas_rgb = parse_color_to_rgb(self.root_vars["--color-bg-canvas"])[:3]
        surface_rgb = parse_color_to_rgb(self.root_vars["--color-bg-surface"])[:3]
        sec_text_rgb = parse_color_to_rgb(self.root_vars["--color-text-secondary"])[:3]

        ratio_canvas = calculate_contrast_ratio(sec_text_rgb, canvas_rgb)
        ratio_surface = calculate_contrast_ratio(sec_text_rgb, surface_rgb)

        self.assertGreaterEqual(ratio_canvas, 7.0, "Secondary text vs Canvas must meet AAA (>= 7.0)")
        self.assertGreaterEqual(ratio_surface, 7.0, "Secondary text vs Surface must meet AAA (>= 7.0)")

    def test_wcag_contrast_muted_text_aa(self):
        canvas_rgb = parse_color_to_rgb(self.root_vars["--color-bg-canvas"])[:3]
        surface_rgb = parse_color_to_rgb(self.root_vars["--color-bg-surface"])[:3]
        muted_text_rgb = parse_color_to_rgb(self.root_vars["--color-text-muted"])[:3]

        ratio_canvas = calculate_contrast_ratio(muted_text_rgb, canvas_rgb)
        ratio_surface = calculate_contrast_ratio(muted_text_rgb, surface_rgb)

        self.assertGreaterEqual(ratio_canvas, 4.5, "Muted text vs Canvas must meet AA (>= 4.5)")
        self.assertGreaterEqual(ratio_surface, 4.5, "Muted text vs Surface must meet AA (>= 4.5)")

    def test_wcag_contrast_gold_primary_cta_aaa(self):
        gold_rgb = parse_color_to_rgb(self.root_vars["--color-accent-gold"])[:3]
        inverse_text_rgb = parse_color_to_rgb(self.root_vars["--color-text-inverse"])[:3]

        ratio = calculate_contrast_ratio(inverse_text_rgb, gold_rgb)
        self.assertGreaterEqual(ratio, 7.0, f"CTA button text contrast must be AAA (>= 7.0), got {ratio}")

    def test_all_status_badges_meet_wcag_aa(self):
        for badge in self.report["badge_contrasts"]:
            self.assertIn(badge["level"], ["AA", "AAA"], f"Status badge {badge['status_token']} fails WCAG: {badge['ratio_on_badge_bg']}")

    def test_facebook_channel_tokens_defined(self):
        self.assertIn("--color-channel-fb", self.root_vars)
        self.assertIn("--color-channel-fb-bg", self.root_vars)
        self.assertIn("--color-channel-fb-border", self.root_vars)

    def test_typography_scale_defined(self):
        for size_var in ["--font-size-hero", "--font-size-title", "--font-size-subheading", "--font-size-body", "--font-size-caption", "--font-size-micro"]:
            self.assertIn(size_var, self.root_vars)

    def test_spacing_and_radius_scales(self):
        for sp in ["--space-1", "--space-2", "--space-3", "--space-4", "--space-5", "--space-6", "--space-8", "--space-10", "--space-12"]:
            self.assertIn(sp, self.root_vars)
        for rad in ["--radius-xs", "--radius-sm", "--radius-md", "--radius-lg", "--radius-xl", "--radius-full"]:
            self.assertIn(rad, self.root_vars)

if __name__ == "__main__":
    unittest.main()
