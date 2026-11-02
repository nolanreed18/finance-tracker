"""The app's look: Dark Desk (DESIGN.md), as Streamlit theme options plus the
stylesheet that finishes what the options can't reach.

Dark is the default: a near-black navy page, translucent navy panels and
cards with hairline borders, small uppercase labels, every number in a
monospace face, and one blue-to-cyan gradient that means "selected" (and
the main action). The light palette is its daylight companion, mapped role
for role, behind the Dark mode switch.

Streamlit reads its theme options at the start of every script run, so
apply() changes the theme for the whole process (the app has one user) and
the browser repaints on the next run; ui.setup() takes care of the timing.
Colours mean something: the gradient = selected, cyan = the key value or a
link, emerald = good or done, amber = attention (the exception, never the
normal case), rose = overdue or an error, violet = a second category, grey
= hierarchy. Never a colour for looks.
"""

from html import escape

from streamlit import config

LIGHT = "light"
DARK = "dark"
MODES = [LIGHT, DARK]
DEFAULT = DARK

# Inter for words, JetBrains Mono for numbers; Streamlit adds the stylesheet
# links to the page. The URLs are what Google Fonts hands out.
FONT = ("Inter:https://fonts.googleapis.com/css2"
        "?family=Inter:wght@300;400;500;600;700&display=swap")
CODE_FONT = ("JetBrains Mono:https://fonts.googleapis.com/css2"
             "?family=JetBrains+Mono:wght@400;500;600&display=swap")
MONO = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'

# Chart series, in order: DESIGN.md's "strong" row, told apart under
# colour-blindness on either background. A series keeps its colour when
# others come and go.
CHART_COLORS = ["#4f91f2", "#02a998", "#dc701c", "#d863a0", "#b48c05", "#9f79e6",
                "#47ab4f", "#0aa0d2", "#e3645e", "#5b6777"]

# The accents (DESIGN.md section 3), by what they mean.
BLUE, CYAN, EMERALD, AMBER, ROSE = "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#f43f5e"

# Theme options both modes share. Titles are small and bold: hierarchy comes
# from weight, case and colour, not size (the page title is 15px x 1.2).
SHARED = {
    "font": FONT,
    "headingFont": "Inter",
    "codeFont": CODE_FONT,
    "baseFontSize": 15,
    "headingFontSizes": ["1.2rem", "1.05rem", "0.72rem", "0.95rem", "0.9rem", "0.85rem"],
    "headingFontWeights": [700, 700, 700, 700, 600, 600],
    "baseRadius": "10px",
    "buttonRadius": "6px",
    "showWidgetBorder": True,
    "showSidebarBorder": True,
    "chartCategoricalColors": CHART_COLORS,
    # Badges and coloured text (:blue-badge[...] and friends).
    "blueColor": BLUE,
    "greenColor": EMERALD,
    "orangeColor": AMBER,
    "redColor": ROSE,
    "grayColor": "#64748b",
}

# Streamlit's options take solid colours, so the translucent panel and card
# tones are given here as they land on the page background; the stylesheet
# (TOKENS) uses the real translucent values.
PALETTES = {
    DARK: {
        "base": "dark",
        "primaryColor": BLUE,
        "backgroundColor": "#0b0f19",                 # --bg-dark
        "secondaryBackgroundColor": "#101725",        # --bg-card on --bg-dark
        "textColor": "#f8fafc",                       # --text-primary
        "linkColor": CYAN,
        "borderColor": "#1f222b",                     # --border-color on --bg-dark
        "codeBackgroundColor": "#0f172a",
        "dataframeBorderColor": "#1f222b",
        "dataframeHeaderBackgroundColor": "#0f172a",  # --bg-table-head
        "violetColor": "#c084fc",
        "sidebar.backgroundColor": "#0d121e",         # --bg-panel on --bg-dark
        "sidebar.secondaryBackgroundColor": "#101725",
    },
    LIGHT: {
        "base": "light",
        "primaryColor": "#2563eb",
        "backgroundColor": "#f8fafc",
        "secondaryBackgroundColor": "#ffffff",
        "textColor": "#0f172a",
        "linkColor": "#0e7490",
        "borderColor": "#e2e8f0",
        "codeBackgroundColor": "#f1f5f9",
        "dataframeBorderColor": "#e2e8f0",
        "dataframeHeaderBackgroundColor": "#f1f5f9",
        "violetColor": "#8b5cf6",
        "sidebar.backgroundColor": "#f1f5f9",
        "sidebar.secondaryBackgroundColor": "#ffffff",
    },
}

# The stylesheet's tokens: DESIGN.md section 3 for dark, the same roles in
# daylight for light. Nothing in the stylesheet is a bare hex: it's a token.
TOKENS = {
    DARK: {
        "text": "#f8fafc", "text2": "#94a3b8", "muted": "#64748b",
        "panel": "rgba(13, 18, 30, 0.95)", "card": "rgba(18, 25, 41, 0.75)",
        "card-hover": "rgba(28, 38, 61, 0.85)", "popover": "#0f1626", "table-head": "#0f172a",
        "track": "#1e293b", "border": "rgba(255, 255, 255, 0.08)",
        "border-strong": "rgba(255, 255, 255, 0.2)", "blue": BLUE, "cyan": CYAN,
        "good-text": "#34d399", "warn-text": "#fcd34d", "error-text": "#fda4af",
        "scheme": "dark", "thumb": "#334155",
    },
    LIGHT: {
        "text": "#0f172a", "text2": "#475569", "muted": "#64748b",
        "panel": "rgba(241, 245, 249, 0.95)", "card": "#ffffff", "card-hover": "#f1f5f9",
        "popover": "#ffffff", "table-head": "#f1f5f9", "track": "#e2e8f0",
        "border": "#e2e8f0", "border-strong": "#94a3b8", "blue": "#2563eb", "cyan": "#0e7490",
        "good-text": "#047857", "warn-text": "#b45309", "error-text": "#be123c",
        "scheme": "light", "thumb": "#cbd5e1",
    },
}

# The one gradient: it means "selected" (and the main action). The soft one
# marks the active segment or pill.
GRADIENT = "linear-gradient(135deg, rgba(37, 99, 235, 0.85), rgba(6, 182, 212, 0.7))"
GRADIENT_SOFT = "linear-gradient(135deg, rgba(37, 99, 235, 0.3), rgba(6, 182, 212, 0.2))"
GRADIENT_BUTTON = "linear-gradient(135deg, rgba(37, 99, 235, 0.55), rgba(6, 182, 212, 0.4))"
GRADIENT_BUTTON_HOVER = "linear-gradient(135deg, rgba(37, 99, 235, 0.75), rgba(6, 182, 212, 0.55))"
SHADOW = "0 10px 30px -10px rgba(0, 0, 0, 0.5)"


def options(mode: str) -> dict:
    """Every theme option for a mode, keyed as in config.toml ("primaryColor",
    "sidebar.backgroundColor")."""
    if mode not in MODES:
        raise ValueError(f"unknown theme mode {mode!r}")
    return {**SHARED, **PALETTES[mode]}


def apply(mode: str) -> None:
    """Make this the process's theme from the next script run on."""
    for key, value in options(mode).items():
        config.set_option(f"theme.{key}", value)


def current() -> str | None:
    """The mode the process's theme options are in right now, or None when
    they're something else (Streamlit's defaults, before apply() has run)."""
    background = config.get_option("theme.backgroundColor")
    for mode in MODES:
        if PALETTES[mode]["backgroundColor"] == background:
            return mode
    return None


def stylesheet(mode: str) -> str:
    """A <style> element finishing the look for this mode: panels, cards,
    microlabels, mono numbers, segmented controls, the gradient."""
    t = TOKENS[mode]
    tokens = " ".join(f"--ct-{k}: {v};" for k, v in t.items() if k != "scheme")
    return f"""<style>
:root {{ {tokens} --ct-mono: {MONO}; --ct-ease: 0.2s ease; color-scheme: {t["scheme"]}; }}
* {{ scrollbar-width: thin; scrollbar-color: var(--ct-thumb) transparent; }}

/* The shell: top bar and sidebar are translucent panels with a hairline. */
[data-testid="stHeader"] {{ background: var(--ct-panel); backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px); border-bottom: 1px solid var(--ct-border); }}
[data-testid="stSidebar"] {{ background: var(--ct-panel); backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px); border-right: 1px solid var(--ct-border); }}
[data-testid="stMainBlockContainer"] {{ padding-top: 4.5rem; }}

/* Page navigation: pills; the current page carries the gradient and a glow. */
[data-testid="stSidebarNavLink"] {{ border-radius: 999px; padding: 0.45rem 0.9rem;
    transition: background var(--ct-ease), color var(--ct-ease); }}
[data-testid="stSidebarNavLink"] span {{ font-weight: 600; font-size: 0.8rem;
    color: var(--ct-text2); }}
[data-testid="stSidebarNavLink"]:hover {{ background: var(--ct-card-hover); }}
[data-testid="stSidebarNavLink"]:hover span {{ color: var(--ct-text); }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{ background: {GRADIENT};
    box-shadow: 0 2px 14px rgba(59, 130, 246, 0.4); }}
[data-testid="stSidebarNavLink"][aria-current="page"] span {{ color: #fff; }}

/* Page head: a small bold title and a one-line mono subtitle. */
[data-testid="stHeading"] h1 {{ letter-spacing: -0.2px; padding-bottom: 0.1rem; }}
.ct-sub {{ font-family: var(--ct-mono); font-size: 0.78rem; color: var(--ct-muted);
          margin-top: -0.4rem; }}

/* Section headings (st.subheader) are microlabels: small, uppercase, tracked. */
[data-testid="stHeading"] h3 {{ font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em; color: var(--ct-text2);
    padding-top: 0.75rem; padding-bottom: 0.1rem; }}

/* Labels above inputs: the same microlabel, full width, no icons. */
:is([data-testid="stTextInput"], [data-testid="stNumberInput"], [data-testid="stSelectbox"],
    [data-testid="stMultiSelect"], [data-testid="stDateInput"], [data-testid="stTimeInput"],
    [data-testid="stTextArea"], [data-testid="stRadio"], [data-testid="stFileUploader"])
    > [data-testid="stWidgetLabel"] p {{
    font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--ct-text2); }}

/* Inputs: card surfaces with a hairline; hover and focus turn the border blue
   and step the surface up a shade. */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div,
[data-baseweb="textarea"] {{ background: var(--ct-card); border-color: var(--ct-border);
    border-radius: 10px; transition: border-color var(--ct-ease), background var(--ct-ease); }}
:is([data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"]):hover {{
    border-color: var(--ct-blue); background: var(--ct-card-hover); }}
[data-testid="stNumberInput"] input, [data-testid="stDateInput"] input {{
    font-family: var(--ct-mono); font-variant-numeric: tabular-nums; }}
[data-testid="InputInstructions"] {{ display: none; }}  /* "Press Enter" sits on the value */

/* Stat cards: a muted microlabel over a big mono number. Their columns may
   shrink below Streamlit's 120px minimum so three fit on a phone. */
[data-testid="stColumn"]:has([data-testid="stMetric"]) {{ min-width: 0; }}
[data-testid="stMetric"] {{ background: var(--ct-card); border: 1px solid var(--ct-border);
    border-radius: 10px; padding: 12px 14px; transition: border-color var(--ct-ease); }}
[data-testid="stMetric"]:hover {{ border-color: var(--ct-blue); }}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{ overflow: visible;
    white-space: normal; text-overflow: clip; }}
[data-testid="stMetricLabel"] p {{ font-size: 0.66rem; font-weight: 600; line-height: 1.3;
    text-transform: uppercase; letter-spacing: 0.04em; color: var(--ct-muted); }}
[data-testid="stMetricValue"] {{ font-family: var(--ct-mono); font-size: 1.45rem;
    font-weight: 700; font-variant-numeric: tabular-nums; color: var(--ct-text); }}

/* Cards (ui.card; the key becomes a class on the bordered block). */
[class*="st-key-card-"] {{
    background: var(--ct-card); border: 1px solid var(--ct-border); border-radius: 16px;
    padding: 0.9rem 1rem; transition: border-color var(--ct-ease), background var(--ct-ease); }}
[class*="st-key-card-"]:hover {{ border-color: var(--ct-blue); background: var(--ct-card-hover); }}
/* A card's text-and-button row: the text column shrinks, the button column
   keeps its width, and nothing inside scrolls. */
[class*="st-key-card-"] [data-testid="stHorizontalBlock"] {{ overflow: visible; }}
[class*="st-key-card-"] [data-testid="stColumn"]:first-child {{ min-width: 0; }}
/* An amount set as a heading inside a card is a key value: mono, tabular. */
[class*="st-key-card-"] h4 {{ font-family: var(--ct-mono); font-variant-numeric: tabular-nums;
    text-align: right; color: var(--ct-text); }}

/* Badges: small mono pills with a hairline in their own colour. */
.stMarkdownBadge {{ font-family: var(--ct-mono); font-size: 0.7rem !important; font-weight: 600;
    padding: 1px 8px; border-radius: 999px; vertical-align: middle; letter-spacing: 0.02em;
    border: 1px solid color-mix(in srgb, currentColor 35%, transparent); }}

/* Buttons: the gradient means the main action; others are quiet cards that
   turn blue on hover. Radius 6px (the theme's buttonRadius). */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
    background: {GRADIENT_BUTTON}; color: var(--ct-text); font-weight: 600;
    border: 1px solid var(--ct-cyan); transition: background var(--ct-ease); }}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primary"]:focus-visible,
[data-testid="stBaseButton-primaryFormSubmit"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:focus-visible {{ background: {GRADIENT_BUTTON_HOVER};
    color: var(--ct-text); border-color: var(--ct-cyan); }}
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{
    background: var(--ct-card); font-weight: 600; border: 1px solid var(--ct-border);
    color: var(--ct-text); transition: border-color var(--ct-ease), background var(--ct-ease); }}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-secondaryFormSubmit"]:hover {{ border-color: var(--ct-blue);
    background: var(--ct-card-hover); color: var(--ct-text); }}
[data-testid="stBaseButton-secondary"]:disabled {{ opacity: 0.4; }}
a[data-testid="stBaseLinkButton-primary"] {{ background: {GRADIENT_BUTTON};
    border: 1px solid var(--ct-cyan); color: var(--ct-text); }}

/* Horizontal radios become a segmented control: one of a few, all visible;
   the chosen one carries the soft gradient, a cyan edge and a faint glow. */
[data-testid="stRadio"] [role="radiogroup"] {{ gap: 5px; flex-wrap: wrap; }}
[data-testid="stRadioOption"] {{ margin: 0; padding: 6px 12px; border-radius: 6px;
    background: var(--ct-card); border: 1px solid var(--ct-border); color: var(--ct-text2);
    font-size: 0.78rem; font-weight: 600; cursor: pointer; transition: all 0.15s ease; }}
[data-testid="stRadioOption"] > div > div > div:not([data-testid]) {{ display: none; }}  /* the dot */
[data-testid="stRadioOption"] p {{ font-size: 0.78rem; }}
[data-testid="stRadioOption"]:hover {{ background: var(--ct-card-hover); color: var(--ct-text); }}
[data-testid="stRadioOption"][data-selected="true"],
[data-testid="stRadioOption"]:has(input:checked) {{ background: {GRADIENT_SOFT};
    border-color: var(--ct-cyan); color: var(--ct-text);
    box-shadow: 0 0 8px rgba(6, 182, 212, 0.25); }}

/* Sub-pages (ui.sections): bigger pills, a hairline under the row. */
[class*="st-key-sections-"] {{ border-bottom: 1px solid var(--ct-border); padding-bottom: 0.6rem;
    margin-bottom: 0.2rem; }}
[class*="st-key-sections-"] [data-testid="stRadioOption"] {{ padding: 7px 14px; }}
[class*="st-key-sections-"] [data-testid="stRadioOption"] p {{ font-size: 0.85rem; }}

/* Progress bars: the track token, the gradient as the fill. */
[data-testid="stProgress"] > div > div {{ background: var(--ct-track); border-radius: 999px; }}
[data-testid="stProgress"] > div > div > div {{ background: {GRADIENT}; border-radius: 999px; }}
[data-testid="stProgress"] p {{ font-family: var(--ct-mono); font-size: 0.75rem;
    color: var(--ct-text2); font-variant-numeric: tabular-nums; }}

/* Tables: a sticky microlabel header; numbers right-aligned by Streamlit. */
[data-testid="stDataFrame"] {{ border: 1px solid var(--ct-border); border-radius: 10px;
    overflow: hidden; }}

/* Captions and helper text are muted; checkbox and toggle labels are body copy. */
[data-testid="stCaptionContainer"] p {{ color: var(--ct-muted); font-size: 0.78rem; }}
[data-testid="stCheckbox"] p, [data-testid="stToggle"] p {{ font-size: 0.85rem;
    color: var(--ct-text2); }}
[data-testid="stAlert"] {{ border-radius: 10px; }}

/* Expanders and tabs aren't used (DESIGN.md), but if one slips in it still fits. */
[data-testid="stExpander"] details {{ background: var(--ct-card); border-radius: 12px; }}
[data-testid="stExpanderIcon"] {{ color: var(--ct-cyan); }}

/* Empty states (ui.empty): say why it's empty and what to do. */
.ct-empty {{ display: flex; flex-direction: column; align-items: center; gap: 6px;
    text-align: center; padding: 26px 24px; border: 1px solid var(--ct-border);
    border-radius: 16px; background: var(--ct-card); color: var(--ct-text2);
    font-size: 0.9rem; backdrop-filter: blur(10px); }}
.ct-empty .ct-icon {{ font-family: "Material Symbols Rounded"; font-size: 31px; line-height: 1;
    color: var(--ct-muted); margin-bottom: 4px; }}
.ct-empty h3 {{ font-size: 1rem; font-weight: 600; margin: 0; padding: 0; color: var(--ct-text); }}
.ct-empty p {{ margin: 0; font-size: 0.85rem; color: var(--ct-muted); line-height: 1.55; }}

/* A small mono note (the signed-in address in the sidebar). */
.ct-note {{ font-family: var(--ct-mono); font-size: 0.75rem; color: var(--ct-muted);
    overflow-wrap: anywhere; }}

/* Toasts: brief, bottom centre, a cyan hairline. */
[data-testid="stToast"] {{ background: var(--ct-popover); border: 1px solid var(--ct-cyan);
    border-radius: 999px; box-shadow: {SHADOW}; color: var(--ct-text); }}

@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{ transition-duration: 1ms !important; animation-duration: 1ms !important; }}
}}
</style>"""


def subtitle(text: str) -> str:
    """The page head's mono subtitle, as HTML for st.html."""
    return f'<div class="ct-sub">{escape(text)}</div>'


def note(text: str) -> str:
    """A small mono note, as HTML for st.html (plain text: no links made)."""
    return f'<div class="ct-note">{escape(text)}</div>'


# While nobody is signed in, the sidebar (and its page list) stays out of sight.
LOCKED = ('<style>[data-testid="stSidebar"], [data-testid="stExpandSidebarButton"] '
          '{ display: none; }</style>')


def empty_state(icon: str, title: str, text: str) -> str:
    """An empty-state panel (a Material Symbols icon name, a heading, one
    sentence), as HTML for st.html."""
    return (f'<div class="ct-empty"><span class="ct-icon">{escape(icon)}</span>'
            f'<h3>{escape(title)}</h3><p>{escape(text)}</p></div>')
