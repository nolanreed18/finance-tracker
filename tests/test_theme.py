"""The look: two complete palettes, the dark one (Dark Desk, DESIGN.md) being
the default and what config.toml draws first, applied through Streamlit's
theme options."""

import tomllib
from pathlib import Path

import pytest
from streamlit import config

import theme

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def back_to_default():
    yield
    theme.apply(theme.DEFAULT)


def flat(section: dict, prefix: str = "") -> dict:
    out = {}
    for key, value in section.items():
        if isinstance(value, dict):
            out.update(flat(value, f"{prefix}{key}."))
        else:
            out[f"{prefix}{key}"] = value
    return out


def test_both_modes_set_the_same_options_and_dark_is_the_default():
    light, dark = theme.options(theme.LIGHT), theme.options(theme.DARK)
    assert set(light) == set(dark)
    assert (light["base"], dark["base"]) == ("light", "dark")
    assert theme.DEFAULT == theme.DARK
    assert dark["backgroundColor"] == "#0b0f19" and dark["linkColor"] == theme.CYAN
    with pytest.raises(ValueError):
        theme.options("sepia")


def test_config_toml_draws_the_dark_look_first():
    with open(ROOT / ".streamlit" / "config.toml", "rb") as handle:
        configured = flat(tomllib.load(handle)["theme"])
    assert configured == theme.options(theme.DARK)


def test_apply_switches_the_process_theme():
    theme.apply(theme.DARK)
    assert theme.current() == theme.DARK
    assert config.get_option("theme.backgroundColor") == theme.PALETTES[theme.DARK]["backgroundColor"]
    assert config.get_option("theme.sidebar.backgroundColor") == "#0d121e"
    theme.apply(theme.LIGHT)
    assert theme.current() == theme.LIGHT
    assert config.get_option("theme.backgroundColor") == theme.PALETTES[theme.LIGHT]["backgroundColor"]
    config.set_option("theme.backgroundColor", "#123456")      # neither palette: not applied yet
    assert theme.current() is None


def test_the_stylesheet_carries_its_mode_tokens():
    light, dark = theme.stylesheet(theme.LIGHT), theme.stylesheet(theme.DARK)
    assert light.startswith("<style>") and light.endswith("</style>")
    assert "--ct-card: #ffffff;" in light and "--ct-card: rgba(18, 25, 41, 0.75);" in dark
    assert "color-scheme: dark;" in dark and "color-scheme: light;" in light
    assert "st-key-card-" in light and "stRadioOption" in light
    assert "stSidebarNavLink" in dark and "prefers-reduced-motion" in dark
    assert "stBaseButton-primaryFormSubmit" in light     # form Save/Add buttons too
    assert "stSidebar" in theme.LOCKED


def test_the_stylesheet_takes_its_colours_from_the_tokens():
    """DESIGN.md: only the tokens are used; no new hex values invented inline.
    The gradient, its glow and plain white for text on it are the exceptions
    the guide itself defines."""
    import re
    body = theme.stylesheet(theme.DARK).split(":root", 1)[1].split("}", 1)[1]
    assert re.findall(r"#[0-9a-fA-F]{3,6}\b", body) == ["#fff"]


def test_html_helpers_escape_text():
    assert theme.subtitle("<b>") == '<div class="ct-sub">&lt;b&gt;</div>'
    panel = theme.empty_state("inbox", "No leads", "Try <later>")
    assert ">inbox<" in panel and "Try &lt;later&gt;" in panel
    assert theme.note("me@example.com") == '<div class="ct-note">me@example.com</div>'
