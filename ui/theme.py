from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from string import Template
from typing import Dict, Tuple


@dataclass(frozen=True)
class ColorTokens:
    background: str
    background_deep: str
    panel: str
    panel_alt: str
    panel_elevated: str
    panel_overlay: str
    toolbar: str
    border: str
    border_soft: str
    border_strong: str
    accent: str
    accent_hover: str
    text_primary: str
    text_secondary: str
    text_muted: str
    text_inverse: str
    success: str
    warning: str
    danger: str
    info: str
    icon: str


@dataclass(frozen=True)
class SpacingTokens:
    xxs: int
    xs: int
    sm: int
    md: int
    lg: int
    xl: int
    xxl: int


@dataclass(frozen=True)
class FontSizeTokens:
    xs: int
    sm: int
    md: int
    lg: int
    xl: int
    xxl: int


@dataclass(frozen=True)
class RadiusTokens:
    sm: int
    md: int
    lg: int
    xl: int
    pill: int


@dataclass(frozen=True)
class ThemeTokens:
    colors: ColorTokens
    spacing: SpacingTokens
    font: FontSizeTokens
    radius: RadiusTokens


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    raw = str(value or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return (0, 0, 0)
    return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))


def rgba(value: str, alpha: float | int) -> str:
    r, g, b = hex_to_rgb(value)
    if isinstance(alpha, float) and 0.0 <= alpha <= 1.0:
        a = int(round(alpha * 255.0))
    else:
        a = int(alpha)
    a = max(0, min(255, a))
    return f"rgba({r}, {g}, {b}, {a})"


DARK_THEME = ThemeTokens(
    colors=ColorTokens(
        background="#0B1220",
        background_deep="#070D18",
        panel="#121C2E",
        panel_alt="#18243A",
        panel_elevated="#1C2B45",
        panel_overlay="#0F1828",
        toolbar="#152238",
        border="#2A3A57",
        border_soft="#24334D",
        border_strong="#354A6D",
        accent="#FF3B9A",
        accent_hover="#FF5FB2",
        text_primary="#E6EBF2",
        text_secondary="#B8C2D4",
        text_muted="#8A95A8",
        text_inverse="#F2F6FB",
        success="#2EC27E",
        warning="#F5A524",
        danger="#F16A78",
        info="#62B4F5",
        icon="#C6D1E4",
    ),
    spacing=SpacingTokens(xxs=2, xs=4, sm=8, md=12, lg=16, xl=24, xxl=32),
    font=FontSizeTokens(xs=10, sm=11, md=13, lg=15, xl=18, xxl=22),
    radius=RadiusTokens(sm=8, md=10, lg=12, xl=14, pill=20),
)


_RGBA_WHITE_RE = re.compile(r"rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*([0-9.]+)\s*\)")
_RGBA_ACCENT_A_RE = re.compile(r"rgba\(\s*255\s*,\s*(46|61)\s*,\s*(136|166)\s*,\s*([0-9.]+)\s*\)")
_RGBA_ACCENT_B_RE = re.compile(r"rgba\(\s*255\s*,\s*92\s*,\s*168\s*,\s*([0-9.]+)\s*\)")


def _legacy_color_replacements(theme: ThemeTokens) -> Dict[str, str]:
    c = theme.colors
    return {
        "#0B0F18": c.background,
        "#05070C": c.background_deep,
        "#14213A": c.panel_elevated,
        "#111827": c.panel,
        "#1F2937": c.panel_alt,
        "#273142": c.border,
        "#E5E7EB": c.text_primary,
        "#9CA3AF": c.text_secondary,
        "#6B7280": c.text_muted,
        "#FF2E88": c.accent,
        "#FF5CA8": c.accent_hover,
        "#182134": c.toolbar,
        "#C9D1D9": c.icon,
        "#0F1522": c.panel_overlay,
        "#1A2232": c.panel_alt,
        "#1D2433": c.panel_elevated,
        "#0E1728": c.panel_overlay,
        "#E9EEF6": c.text_primary,
        "#F8FAFC": c.text_inverse,
        "#F8FAFF": c.text_inverse,
        "#1A2742": c.panel_elevated,
        "#20304F": c.panel_elevated,
        "#9FB0C8": c.text_secondary,
        "#D3DEEE": c.text_secondary,
        "#D7E3F4": c.text_secondary,
        "#FFD1E9": c.accent_hover,
        "#CBD5E1": c.text_secondary,
        "#FCE7F3": c.accent_hover,
        "#162032": c.panel_elevated,
        "#F3F4F6": c.text_primary,
        "#22C55E": c.success,
        "#EF4444": c.danger,
        "#F59E0B": c.warning,
        "#CFE8FF": c.info,
        "#D1D5DB": c.text_secondary,
        "#E2E8F0": c.text_secondary,
        "#FDE68A": c.warning,
        "#161D29": c.panel_overlay,
        "#0F1726": c.panel_overlay,
        "#2A2230": c.panel_elevated,
        "#241D29": c.panel_overlay,
        "#202C3B": c.panel_elevated,
        "#FF79BB": c.accent_hover,
        "#DB2678": c.accent,
        "#EA4D9D": c.accent_hover,
        "#101A2B": c.panel_overlay,
        "#162136": c.panel,
        "#233553": c.panel_elevated,
        "#10182A": c.panel_overlay,
        "#182235": c.panel,
        "#18263D": c.panel_elevated,
        "#152033": c.panel,
        "#FF8CC2": c.accent_hover,
        "#FBCFE8": c.accent_hover,
        "#F9FAFB": c.text_inverse,
        "#FFFFFF": c.text_inverse,
        "#DCFCE7": c.success,
        "#FEE2E2": c.danger,
        "#FEF3C7": c.warning,
    }


def normalize_stylesheet(stylesheet: str, theme: ThemeTokens = DARK_THEME) -> str:
    normalized = str(stylesheet or "")
    for source, target in _legacy_color_replacements(theme).items():
        normalized = normalized.replace(source, target)

    text_r, text_g, text_b = hex_to_rgb(theme.colors.text_primary)
    accent_r, accent_g, accent_b = hex_to_rgb(theme.colors.accent)
    accent_hr, accent_hg, accent_hb = hex_to_rgb(theme.colors.accent_hover)

    normalized = _RGBA_WHITE_RE.sub(
        lambda m: f"rgba({text_r}, {text_g}, {text_b}, {m.group(1)})",
        normalized,
    )
    normalized = _RGBA_ACCENT_A_RE.sub(
        lambda m: f"rgba({accent_r}, {accent_g}, {accent_b}, {m.group(3)})",
        normalized,
    )
    normalized = _RGBA_ACCENT_B_RE.sub(
        lambda m: f"rgba({accent_hr}, {accent_hg}, {accent_hb}, {m.group(1)})",
        normalized,
    )
    return normalized


_THEME_OVERRIDE_DIR = Path(__file__).resolve().parent / "theme_overrides"


@lru_cache(maxsize=16)
def _read_override_template(name: str) -> str:
    path = _THEME_OVERRIDE_DIR / str(name or "").strip()
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def dropdown_menu_overrides(theme: ThemeTokens = DARK_THEME) -> str:
    template_text = _read_override_template("dropdowns.qss")
    if not template_text:
        return ""
    tokens = overlay_surface_tokens(theme)
    values = {
        "menu_bg": tokens["--surface"],
        "menu_bg_alt": tokens["--surface-2"],
        "menu_border": tokens["--border"],
        "menu_focus_border": tokens["--focus"],
        "menu_text": tokens["--text"],
        "menu_text_active": tokens["--text"],
        "menu_item_hover_bg": tokens["--hover"],
        "menu_item_selected_bg": tokens["--hover"],
        "menu_item_disabled_text": tokens["--text-muted"],
        "menu_separator": tokens["--border"],
        "menu_scrollbar_bg": tokens["--surface"],
        "menu_scrollbar_handle": rgba(tokens["--text-muted"], 0.56),
        "menu_scrollbar_handle_hover": rgba(tokens["--text-muted"], 0.72),
    }
    return Template(template_text).safe_substitute(values)


def overlay_surface_tokens(theme: ThemeTokens = DARK_THEME) -> Dict[str, str]:
    c = theme.colors
    # Shared tokens for overlays/popups (dropdowns, menus, tooltips, dialogs):
    # --surface, --surface-2, --text, --text-muted, --border, --hover, --focus
    return {
        "--surface": rgba(c.panel_overlay, 0.98),
        "--surface-2": rgba(c.panel_elevated, 0.98),
        "--text": c.text_primary,
        "--text-muted": rgba(c.text_secondary, 0.72),
        "--border": rgba(c.border, 0.56),
        "--hover": rgba(c.accent, 0.28),
        "--focus": rgba(c.accent, 0.58),
    }
