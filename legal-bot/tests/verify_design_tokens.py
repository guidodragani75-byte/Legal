"""
Empirical Verification Harness for DESIGN.md tokens and WCAG 2.1 compliance.
Challenger M1.1
"""

import os
import re
import sys
import json
import math

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESIGN_MD_PATH = os.path.join(PROJECT_ROOT, "DESIGN.md")

def parse_root_css_variables(design_md_content):
    """Extracts all variable definitions from :root { ... } blocks in DESIGN.md."""
    root_match = re.search(r":root\s*\{([^}]+)\}", design_md_content, re.DOTALL)
    if not root_match:
        return {}
    
    root_content = root_match.group(1)
    variables = {}
    duplicates = []
    
    for line in root_content.splitlines():
        line = line.strip()
        if not line or line.startswith("/*") or line.startswith("*") or line.startswith("//"):
            continue
        var_match = re.match(r"^(--[\w-]+)\s*:\s*([^;]+);", line)
        if var_match:
            var_name = var_match.group(1).strip()
            var_value = var_match.group(2).strip()
            # Remove inline comment if present
            if "/*" in var_value:
                var_value = var_value.split("/*")[0].strip()
            if var_name in variables:
                duplicates.append((var_name, variables[var_name], var_value))
            variables[var_name] = var_value
            
    return variables, duplicates

def parse_markdown_table_tokens(design_md_content):
    """Finds all tokens mentioned in markdown tables (--[a-z0-9-]+)."""
    table_tokens = set(re.findall(r"`(--[\w-]+)`", design_md_content))
    return table_tokens

def resolve_variable(var_name, variables, visited=None):
    """Resolves var(--other-var) recursively to concrete value."""
    if visited is None:
        visited = set()
    if var_name in visited:
        raise ValueError(f"Circular dependency detected in variable: {var_name}")
    visited.add(var_name)
    
    if var_name not in variables:
        return None
    val = variables[var_name]
    var_ref_match = re.match(r"^var\(\s*(--[\w-]+)\s*\)$", val)
    if var_ref_match:
        target = var_ref_match.group(1)
        return resolve_variable(target, variables, visited.copy())
    return val

def parse_color_to_rgb(color_str):
    """Parses hex (#fff, #ffffff, #ffffff88) or rgb/rgba into (r, g, b, a) [0-255, 0-255, 0-255, 0.0-1.0]."""
    color_str = color_str.strip()
    # Hex
    hex_match = re.match(r"^#([0-9a-fA-F]{3,8})$", color_str)
    if hex_match:
        h = hex_match.group(1)
        if len(h) == 3:
            r = int(h[0]*2, 16)
            g = int(h[1]*2, 16)
            b = int(h[2]*2, 16)
            return (r, g, b, 1.0)
        elif len(h) == 6:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return (r, g, b, 1.0)
        elif len(h) == 8:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            a = int(h[6:8], 16) / 255.0
            return (r, g, b, a)
    # rgb or rgba
    rgb_match = re.match(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+))?\s*\)$", color_str)
    if rgb_match:
        r = int(rgb_match.group(1))
        g = int(rgb_match.group(2))
        b = int(rgb_match.group(3))
        a = float(rgb_match.group(4)) if rgb_match.group(4) is not None else 1.0
        return (r, g, b, a)
    return None

def blend_over_background(fg_rgba, bg_rgb):
    """Alpha-blends fg_rgba over solid bg_rgb."""
    r_fg, g_fg, b_fg, a_fg = fg_rgba
    r_bg, g_bg, b_bg = bg_rgb[:3]
    r = r_fg * a_fg + r_bg * (1.0 - a_fg)
    g = g_fg * a_fg + g_bg * (1.0 - a_fg)
    b = b_fg * a_fg + b_bg * (1.0 - a_fg)
    return (round(r), round(g), round(b))

def srgb_channel_to_linear(c_255):
    """Converts 8-bit sRGB channel to linear luminance value per WCAG 2.1."""
    c_norm = c_255 / 255.0
    if c_norm <= 0.04045:
        return c_norm / 12.92
    else:
        return math.pow((c_norm + 0.055) / 1.055, 2.4)

def calculate_relative_luminance(rgb):
    """Calculates relative luminance L per WCAG 2.1 specification."""
    r_lin = srgb_channel_to_linear(rgb[0])
    g_lin = srgb_channel_to_linear(rgb[1])
    b_lin = srgb_channel_to_linear(rgb[2])
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

def calculate_contrast_ratio(rgb1, rgb2):
    """Calculates contrast ratio (L1 + 0.05) / (L2 + 0.05)."""
    l1 = calculate_relative_luminance(rgb1)
    l2 = calculate_relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, 2)

def evaluate_wcag_level(ratio, is_large_text=False):
    """Evaluates WCAG level: AAA, AA, or FAIL."""
    if is_large_text:
        if ratio >= 4.5:
            return "AAA"
        elif ratio >= 3.0:
            return "AA"
        else:
            return "FAIL"
    else:
        if ratio >= 7.0:
            return "AAA"
        elif ratio >= 4.5:
            return "AA"
        else:
            return "FAIL"

def run_all_checks():
    report = {
        "token_counts": {},
        "duplicates": [],
        "unresolved_aliases": [],
        "color_validity": {},
        "contrast_ratios": [],
        "table_discrepancies": [],
        "taxonomy_compliance": [],
        "overall_status": "PASS"
    }

    if not os.path.exists(DESIGN_MD_PATH):
        report["overall_status"] = "FAIL"
        report["error"] = "DESIGN.md not found"
        return report

    with open(DESIGN_MD_PATH, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    variables, duplicates = parse_root_css_variables(content)
    report["token_counts"]["root_variables_count"] = len(variables)
    report["duplicates"] = duplicates
    if duplicates:
        report["overall_status"] = "FAIL"

    table_tokens = parse_markdown_table_tokens(content)
    report["token_counts"]["markdown_table_tokens_count"] = len(table_tokens)

    # Check unresolvable aliases
    resolved_vars = {}
    for var_name, raw_val in variables.items():
        try:
            resolved = resolve_variable(var_name, variables)
            if resolved is None:
                report["unresolved_aliases"].append((var_name, raw_val, "Target variable not defined"))
                report["overall_status"] = "FAIL"
            else:
                resolved_vars[var_name] = resolved
        except ValueError as err:
            report["unresolved_aliases"].append((var_name, raw_val, str(err)))
            report["overall_status"] = "FAIL"

    # Check color validity for color tokens
    color_tokens = {k: v for k, v in resolved_vars.items() if any(prefix in k for prefix in ["--color-", "--border-", "--bg", "--surface", "--primary", "--accent"])}
    
    parsed_colors = {}
    invalid_colors = []
    for k, v in color_tokens.items():
        parsed = parse_color_to_rgb(v)
        if parsed is not None:
            parsed_colors[k] = parsed
        else:
            invalid_colors.append((k, v))
            
    report["color_validity"]["valid_count"] = len(parsed_colors)
    report["color_validity"]["invalid"] = invalid_colors
    if invalid_colors:
        report["overall_status"] = "FAIL"

    # Check Taxonomy compliance per §7.2
    valid_prefixes = (
        "--color-bg-", "--color-text-", "--color-accent-", "--color-status-",
        "--color-channel-", "--font-", "--font-size-", "--line-height-",
        "--space-", "--radius-", "--shadow-", "--bp-", "--border-", "--backdrop-",
        # Backward compatibility aliases explicitly allowed in DESIGN.md §2.7:
        "--bg", "--surface", "--surface-hover", "--surface-card", "--border",
        "--text", "--text-muted", "--text-secondary", "--accent-laboral",
        "--accent-laboral-glow", "--accent-sucesiones", "--accent-sucesiones-glow",
        "--primary", "--primary-hover"
    )
    taxonomy_violations = []
    for var_name in variables:
        if not any(var_name.startswith(p) for p in valid_prefixes):
            taxonomy_violations.append(var_name)
    report["taxonomy_compliance"] = taxonomy_violations
    if taxonomy_violations:
        report["overall_status"] = "FAIL"

    # WCAG Contrast calculations
    canvas_rgb = parsed_colors.get("--color-bg-canvas", (11, 17, 32, 1.0))[:3]
    surface_rgb = parsed_colors.get("--color-bg-surface", (17, 24, 39, 1.0))[:3]
    elevated_rgb = parsed_colors.get("--color-bg-surface-elevated", (30, 41, 59, 1.0))[:3]

    text_tokens = [
        ("--color-text-primary", False),
        ("--color-text-secondary", False),
        ("--color-text-muted", False),
        ("--color-text-dim", True), # Used for large or micro labels
    ]

    for token_name, is_large in text_tokens:
        if token_name in parsed_colors:
            text_rgb = parsed_colors[token_name][:3]
            ratio_canvas = calculate_contrast_ratio(text_rgb, canvas_rgb)
            level_canvas = evaluate_wcag_level(ratio_canvas, is_large)
            ratio_surface = calculate_contrast_ratio(text_rgb, surface_rgb)
            level_surface = evaluate_wcag_level(ratio_surface, is_large)
            ratio_elevated = calculate_contrast_ratio(text_rgb, elevated_rgb)
            level_elevated = evaluate_wcag_level(ratio_elevated, is_large)

            report["contrast_ratios"].append({
                "token": token_name,
                "hex": variables.get(token_name),
                "is_large_text": is_large,
                "vs_canvas": {"ratio": ratio_canvas, "level": level_canvas},
                "vs_surface": {"ratio": ratio_surface, "level": level_surface},
                "vs_elevated": {"ratio": ratio_elevated, "level": level_elevated},
            })

    # Gold Accent CTA Check (Obsidian inverse text over Gold background)
    gold_rgb = parsed_colors.get("--color-accent-gold", (197, 160, 89, 1.0))[:3]
    inverse_text_rgb = parsed_colors.get("--color-text-inverse", (11, 17, 32, 1.0))[:3]
    gold_cta_ratio = calculate_contrast_ratio(inverse_text_rgb, gold_rgb)
    report["contrast_ratios"].append({
        "token": "--color-text-inverse vs --color-accent-gold (Primary CTA Button)",
        "ratio": gold_cta_ratio,
        "level": evaluate_wcag_level(gold_cta_ratio, False)
    })

    # Status badges contrast check
    status_tokens = [
        ("--color-status-pending", "--color-status-pending-bg"),
        ("--color-status-draft", "--color-status-draft-bg"),
        ("--color-status-scheduled", "--color-status-scheduled-bg"),
        ("--color-status-published", "--color-status-published-bg"),
        ("--color-status-error", "--color-status-error-bg"),
    ]

    badge_contrasts = []
    for fg_name, bg_name in status_tokens:
        if fg_name in parsed_colors and bg_name in parsed_colors:
            fg_rgb = parsed_colors[fg_name][:3]
            bg_rgba = parsed_colors[bg_name]
            blended_on_surface = blend_over_background(bg_rgba, surface_rgb)
            badge_ratio = calculate_contrast_ratio(fg_rgb, blended_on_surface)
            badge_contrasts.append({
                "status_token": fg_name,
                "text_color": variables.get(fg_name),
                "bg_token": bg_name,
                "bg_value": variables.get(bg_name),
                "ratio_on_badge_bg": badge_ratio,
                "level": evaluate_wcag_level(badge_ratio, False)
            })
    report["badge_contrasts"] = badge_contrasts

    # Check section 2.2 claims vs actual calculated values
    claims = [
        ("--color-text-primary", 17.8, 15.4),
        ("--color-text-secondary", 12.2, 10.5),
        ("--color-text-muted", 6.7, 5.8),
        ("--color-text-dim", 3.8, 3.2),
    ]
    discrepancies = []
    for token, claimed_canvas, claimed_surface in claims:
        entry = next((e for e in report["contrast_ratios"] if e.get("token") == token), None)
        if entry:
            act_canvas = entry["vs_canvas"]["ratio"]
            act_surface = entry["vs_surface"]["ratio"]
            # Allow 0.2 tolerance due to rounding
            if abs(act_canvas - claimed_canvas) > 0.2:
                discrepancies.append(f"{token} canvas claimed {claimed_canvas} vs actual {act_canvas}")
            if abs(act_surface - claimed_surface) > 0.2:
                discrepancies.append(f"{token} surface claimed {claimed_surface} vs actual {act_surface}")
    report["table_discrepancies"] = discrepancies

    return report

if __name__ == "__main__":
    rep = run_all_checks()
    print(json.dumps(rep, indent=2))
