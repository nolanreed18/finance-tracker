> **How this applies to Finance Tracker.** This is the Dark Desk guide as
> written for a hand-built dashboard. The app is Streamlit, so the *look* is
> taken whole (sections 1 and 3 to 8: the tokens, type, colour meanings,
> components and behaviour rules) and lives in `app/theme.py` (palettes and
> the stylesheet) and `app/ui.py` (the helpers). The *frame* (section 2) is
> adapted, not copied: Streamlit provides the top bar and sidebar, the page
> scrolls like a document, and the app stays phone-friendly (three stat cards
> across a 380px screen, nothing wider than the window). Charts go through
> Streamlit's own chart theme (the series palette in section 7, in order)
> rather than Plotly. The dark look is the default; the light palette in
> `theme.py` is its companion for daylight, mapped role for role. Section 13
> is the checklist for every screen, minus the window-never-scrolls item.
>
> Rules of thumb that matter most here: tokens only, no inline hex; every
> number mono and tabular; missing is `—`, never 0; colour means something
> (gradient = selected, cyan = the key value, emerald = good, amber = the
> exception, rose = error, violet = a second category); mark the exception,
> never the normal case; empty is a state with a sentence, not an error.

# Dark Desk: a UI style guide for data-dense web apps

> **For Claude Code:** this file sets the look, layout and interaction rules for this
> app. Follow it on every screen you build or change. Where it conflicts with a library
> default, this file wins. Sections 1-9 are the rules; sections 10-12 are a working
> starter (`style.css`, `index.html`, `app.js`) to copy, not just to read. Section 13 is
> the checklist to run before calling a screen done.

**For the person reading this:** save it in your project root (as `DESIGN.md`, say) and
add one line to your `CLAUDE.md`: *"All UI follows DESIGN.md."* It comes from a
data-heavy internal dashboard. It covers only the style and layout, not what that app
shows. Nothing here depends on a framework: plain HTML, CSS and a little JS. It works
the same with React or Vue if you keep the tokens and class names.

---

## 1. The character in one paragraph

A dark, quiet workspace for reading numbers. Near-black navy background, translucent
navy panels with a background blur, hairline borders on everything, and **one** accent
gradient (blue to cyan) that means "this is selected". Labels are small, UPPERCASE and
tracked. Every number is monospaced. The screen is a **frame, not a document**: the
window never scrolls. A top bar and a left control sidebar stay put, and the content
area fills what is left, with scrolling inside cards. Little on screen is decoration.
Colour is used to *mean* something (selected, good, attention, error), never as
ornament.

---

## 2. Layout

```
┌───────────────────────────────────────────────────────────────────────────┐
│ (●) 12:04:31 NEXT REFRESH ▾      ( Overview | Explore | Table | ⚙ )     … │  top bar, 62px
├──────────────────┬────────────────────────────────────────────────────────┤
│ SECTION LABEL    │ Page title                         [ +4.2% ] [ 3 gaps ] │  page head
│ [ select      ▾] │ Sep 1 – Sep 30 · weekdays only (mono subtitle)          │
│                  ├────────────────────────────────────────────────────────┤
│ SECTION LABEL    │ ┌stat┐ ┌stat┐ ┌stat┐ ┌stat┐                           │
│ [ A | B | C ]    │ ┌──────────── card ───────────┐ ┌──── card ─────────┐  │
│                  │ │ ⌁ Chart title      [badge]  │ │ ▦ Table           │  │
│ SECTION LABEL    │ │                             │ │ sticky header      │  │
│ [chip][chip][..] │ │   chart fills the card      │ │ rows scroll here   │  │
│                  │ │                             │ │                    │  │
│ ...              │ └─────────────────────────────┘ └────────────────────┘  │
│ [  Refresh   ]   │                                                        │
└──────────────────┴────────────────────────────────────────────────────────┘
   sidebar 330px                 main content (fills the rest)
```

- **Top bar, 62px**, a three-column grid: `minmax(0,1fr) auto minmax(0,1fr)`.
  - Left: a **status pill**, a round gradient icon beside a mono value and an
    uppercase label (a countdown, a sync state, a run state). Clicking it opens a
    detail modal.
  - Centre: the **page tabs**, a row of pills inside one rounded capsule. Settings is
    an icon-only pill at the end, behind a thin divider.
  - Right: optional status items. The side tracks may shrink and ellipsise; **the tabs
    are never clipped**.
- **Sidebar, 330px fixed**, one column of control sections, 17px apart, each a label
  above its control. It scrolls if it has to. A sidebar section belongs to specific
  pages (`data-for="page1 page2"`). **A control the current page ignores is hidden,
  not left on screen.** An optional footer at the bottom holds the one big action
  (Refresh, Run).
- **Main content**: one `.page` per tab, absolutely positioned to fill the area. Only
  the active one is shown. Each page has:
  - a **page head**: a title, a one-line mono subtitle, and tags on the right;
  - a **page body**: a stat row, then a CSS grid of cards that fills the remaining
    height.
- **Cards** are the unit of content. Each has a header strip (an icon in cyan, a bold
  title, an optional mono badge) and a body: a chart, a scrolling table, or notes.
  Charts fill their card. Tables scroll inside it, with a sticky header.
- **When there are too many tabs** (more than about 8), group them. Show only group
  heads (UPPERCASE, a tinted icon disc, a chevron) plus the current page. Hovering a
  head opens its group to the right, and the bar stays centred. Don't keep shrinking
  pills to fit.
- **Desktop first** (1280-2560px). Below about 1280px the card grid collapses to one
  column. When the bar gets tight, the tab labels drop to icons, each keeping its
  name in a `title`.

---

## 3. Tokens

Use these, and only these. If a value is needed twice, it becomes a token.

| Token | Value | Use |
|---|---|---|
| `--bg-dark` | `#0b0f19` | page background |
| `--bg-panel` | `rgba(13,18,30,0.95)` + `blur(20px)` | top bar, sidebar, page head (at 0.6) |
| `--bg-card` | `rgba(18,25,41,0.75)` | cards, inputs, buttons, tiles |
| `--bg-card-hover` | `rgba(28,38,61,0.85)` | hover state of the above |
| `--bg-popover` | `#0f1626` | menus, modals (opaque) |
| `--bg-table-head` | `#0f172a` | sticky table headers, option lists, tips |
| `--track` | `#1e293b` | slider tracks, progress bars, off switches |
| `--border-color` | `rgba(255,255,255,0.08)` | every hairline |
| `--border-strong` | `rgba(255,255,255,0.2)` | hover border on neutral items |
| `--accent-blue` | `#3b82f6` | focus/hover border, primary |
| `--accent-cyan` | `#06b6d4` | heading icons, key numbers, links, readouts |
| `--accent-emerald` | `#10b981` | done, good, positive |
| `--accent-amber` | `#f59e0b` | attention: something is not the usual case |
| `--accent-rose` | `#f43f5e` | error, failure |
| `--text-primary` | `#f8fafc` | values, titles |
| `--text-secondary` | `#94a3b8` | labels, body copy, chart text |
| `--text-muted` | `#64748b` | captions, helper text, units |
| radii | `16px` cards · `10px` inputs/tiles · `6px` buttons/segments · `999px` pills | |
| `--shadow-main` | `0 10px 30px -10px rgba(0,0,0,0.5)` | popovers, modals, toasts only |

**The one gradient**: `linear-gradient(135deg, rgba(37,99,235,0.85), rgba(6,182,212,0.7))`
on the active tab. A softer version (`0.3` / `0.2` alpha, cyan border, faint cyan glow)
marks the active segment, chip or tile. It means *selected* and nothing else.

---

## 4. Type

- **Inter** (300-700) for words and **JetBrains Mono** (400-600) for numbers, both from
  Google Fonts. Icons are **Font Awesome 6** solid.
- **Every number, date, time, ID or code is mono with `font-variant-numeric: tabular-nums`**
  and right-aligned in tables, so columns line up digit for digit.
- **Microlabels**: section labels, column headers, stat labels and menu heads are 10-11.5px,
  weight 600-700, UPPERCASE, letter-spacing 0.5-0.8px, in secondary or muted grey.
- Titles are small and bold rather than big: page title 15px/700, card title 13px/700.
  Hierarchy comes from weight, case and colour, not size.
- **Two type scales.** The shell (top bar, tabs, sidebar) stays at its design size: it is
  a dense control column at a fixed width. Everything in the main content is written as
  `calc(Npx * var(--main-text-scale))` with the scale at **1.2**, so one number resizes
  the whole reading area. Charts get the same factor in JS (`TEXT_SCALE`, `ts(n)`),
  because SVG text can't inherit from CSS. **Change the two together.**

---

## 5. What each colour means

| Colour | Means | Examples |
|---|---|---|
| blue to cyan gradient | selected / active | current tab, active segment, chosen tile, on switch |
| cyan | the key value or an affordance | heading icons, the headline number, slider readouts, text links |
| emerald | done, good, positive | finished progress bar, "complete" pill, positive figure |
| amber | **attention**: not the normal case | partial data, stale, unsaved changes, non-default setting |
| rose | error | failed request banner, failed job |
| violet `#c084fc` | a second category beside the main one | weekend vs weekday, an alternate group |
| greys | hierarchy | primary for values, secondary for labels, muted for captions |

Rules:

- **Mark the exception, never the normal case.** If 90% of items are "normal", they
  carry no tag. A tag on every row teaches the eye to skip tags, and then the one that
  matters gets skipped too.
- Amber is never decorative. If something is amber, there is a reason, and its
  tooltip says it.
- A sign is printed (`+4.2`, `−1.3`), not carried only by red or green.

---

## 6. Components

All of them are in the starter CSS (section 10). Pick from this list before
inventing a new one.

| Component | Class | Use it for |
|---|---|---|
| Status pill | `.status-pill` (`.busy`, `.late`) | the app's one live state, top left |
| Tab pill | `.page-pill` (`.active`, `.pill-icon`) | page navigation |
| Section | `.nav-section` > `.section-label` + control | every sidebar control |
| Section head | `.section-head` + `.link-group` / `.badge` | a label with "All \| Reset" links or a count |
| Select | `.custom-select` | one choice from many |
| Search / text | `.search-wrap` > `i` + `.text-input` | filtering a list |
| Date range | `.date-range` > `.date-picker` ×2 | from / to |
| Segmented | `.seg-group` (`.seg-3`, `.seg-4`) > `.seg-btn` | one of 2-5 options, all visible |
| Chips | `.chip-grid` > `.chip-tile` | toggle many small mono options |
| Tiles | `.tile-list` > `.tile` (`.tile-name`, `.tile-meta`, `.tile-tag`) | choosing one of a few "things" with a second line of detail |
| Pick list | `.pick-list` > `.pick-row` (`.pick-check`, `.pick-name`, `.pick-meta`) | multi-select from a long, searchable list |
| Switch | `.switch-row` > `span` + `.switch` | on/off, the whole row clickable |
| Slider | `.slider-box` > `.slider-head` + `.custom-range` | a number in a range, value in cyan mono |
| Buttons | `.btn`, `.btn.primary`, `.btn.active`, `.btn-ghost`, `.btn-link`, `.icon-btn` | actions |
| Badge | `.badge` (`.zero`) | a count or short mono value beside a label |
| Page head | `.page-head` > `h2` + `.sub` + `.head-tags` > `.tag` (`.accent`, `.warn`, `.good`) | every page |
| Stat card | `.stat-card` > `.stat-label` + `.stat-value` (`.cyan`, `.green`, `.red`) + `.stat-note` | headline numbers |
| Card | `.card` > `.card-head` (h3 with icon, `.helper-badge`) + `.card-plot` / `.card-scroll` / `.card-notes` | all content |
| Data table | `.data-table` (`th.left`, `td.left`, `.unit`, `tr.selected`, `.key`, `.muted`, `.pos`, `.neg`) | any grid of numbers |
| Popover menu | `.menu` > `.menu-head` + `.menu-body` | per-card settings behind a gear |
| Modal | `.modal-backdrop` > `.modal-panel` (`.modal-head`, `.modal-body`, `.modal-foot`) | detail views |
| Toast | `.toast.show` | "Saved", "Copied": brief, bottom centre, 2.2s |
| Loader | `.loader` > `.spinner` | centred while a page loads |
| Empty state | `.state-panel` > `i.big` + `h3` + `p` | nothing to show yet: say why and what to do |
| Error banner | `.page-error` | a failed request, top centre of the page |
| Help tip | `.help-tip` (built by `app.js`) | sidebar help, shown on hover |

---

## 7. Charts

Plotly (2.26) with one shared layout function. Every chart goes through it.

- Transparent paper and plot background: the card is the background.
- Grid lines `rgba(255,255,255,0.05)`, axis lines `0.12`, no zero line, chart text
  `#94a3b8` Inter. The hover label is `#0f172a` with mono white text, `hovermode: 'x unified'`.
- Legend horizontal, top left, transparent. No mode bar on small charts
  (`displayModeBar: false`); add one only on an enlarged view.
- **Series colours**, in this default order, chosen to stay apart under colour-blindness
  on this dark surface:

  | | Blue | Teal | Orange | Pink | Gold | Violet | Green | Sky | Red | Slate |
  |---|---|---|---|---|---|---|---|---|---|---|
  | strong | `#4f91f2` | `#02a998` | `#dc701c` | `#d863a0` | `#b48c05` | `#9f79e6` | `#47ab4f` | `#0aa0d2` | `#e3645e` | `#5b6777` |
  | soft | `#abcdfe` | `#84decf` | `#faba94` | `#f8b3d3` | `#e3c885` | `#d1befe` | `#a6dba7` | `#8bd6fa` | `#feb5ae` | `#edf2fa` |

  Use the strong row first. A soft tone is the *companion* of its strong one (a forecast
  beside its actual). Slate is for a neutral reference line. A single reference or
  estimate line can be white `#f8fafc`, dashed. A user-picked or highlighted item is
  amber `#ffa94d`.
- A series keeps its colour when others are added or removed: store the colour on the
  series, not on its position.
- **Heat-map / colour-scale cells**: default **Viridis**; for signed values (changes,
  differences) **Berlin**, centred on 0 and symmetric. Both stop lists are in `app.js`.
  Every sequential ramp runs dark (low) to bright (high), so the low end sinks into the
  dark table. Text on a shaded cell stays white unless white falls below 3:1 contrast,
  then it switches to `#0b0f19`. No rainbow, no red-green ramps.
- **Stacked charts that share an x axis are one figure** with two y domains, not two
  divs, so a spike in the lower chart sits under the point that caused it, and one
  hover reads both.
- **Offer named, researched presets** (seven colour scales, five line styles) rather
  than free colour pickers or min/max/mid editors. Presets look better and are faster
  to use.

---

## 8. Behaviour and copy rules

1. **Readability beats fitting.** Don't cram controls side by side or shrink spacing to
   avoid a scroll bar. A sidebar that scrolls is fine. Ask before compressing.
2. **Labels go above controls**, full width, not beside them. No icons on section
   labels. Buttons, tiles and chips do carry icons.
3. **Help text is a hover tip, warnings are printed.** The notes under sidebar controls
   are hidden and appear in a tip beside the sidebar when you hover the section (after
   450ms; instantly for 600ms after another tip closes). A click, a scroll or Escape
   puts it away. A note that is a *warning* stays printed, so nothing that needs
   attention waits for a hover.
4. **The page head carries results and warnings only.** The subtitle states the window
   being shown plus anything that is not the default. Tags are for a headline result or
   an amber warning, not for repeating sidebar settings or counting rows.
5. **Hide what does not apply; disable what applies but is unavailable.** A control the
   current page ignores is hidden. An option that exists but can't be used right now
   stays visible, greyed, with a `title` saying why, so the shape of the choices stays
   readable.
6. **Missing is not zero.** A missing value prints as a dash `—` and is left out of any
   colour scale. A zero is a number. Never let a partial sum pass as a whole one.
7. **Empty is a state, not an error.** Use the empty-state panel: an icon, a short
   heading, one sentence saying why it's empty and what to do. An empty slot in a grid
   (a chart cell with nothing chosen) is itself the button that fills it.
8. **One word per concept, everywhere.** If it's a "Profile" in one place, it's a
   "Profile" in every picker, prompt and confirm dialog.
9. **Unsaved work is visible.** A saved-views picker turns amber when the view has
   drifted from what was saved, and switching away asks first, naming what will be
   lost.
10. **Expanding UI stays at home.** A menu or bar that grows stays centred where it
    rests, and is nudged only by the least needed to keep the pointer on its target.
    Never let a layout slide after the cursor.
11. **Motion is short and uniform**: 0.15-0.25s `ease` for hovers, one shared curve for
    anything that moves. Hover means the border turns accent blue and the background
    steps up a shade; tiles lift 1px. Respect `prefers-reduced-motion`.
12. **Prefer one request and repaint.** Changing a colour, line style or sort order is a
    repaint, not a new fetch.
13. **Per-browser conveniences** (last tab, collapsed panes) go in `localStorage`,
    wrapped in `try/catch`. Shared or important state belongs on the server.
14. **Element ids are prefixed per page** (`ov-`, `ex-`, ...) so every page can live in
    one DOM without collisions. Page-specific CSS is scoped to `#page-<name>`.
15. **Errors say what happened in a sentence**, not a code: "Couldn't load the table:
    the server returned 500", plus what still works.

---

## 9. Gotchas worth knowing in advance

- **`[hidden]` does nothing to an element whose CSS sets `display: flex` or `grid`.**
  The starter has a global `[hidden] { display: none !important; }` for this. Keep it.
- **Without `color-scheme: dark` the browser draws light scrollbars and pickers** on
  the dark page. The starter sets it on `:root`, with thin slate scrollbars.
- **Plotly measures its container when it draws.** Draw a chart only once its page is
  visible, and resize visible charts when switching pages or resizing the window
  (`app.js` does both). A chart container needs `min-height: 0` inside a flex column,
  or the chart sets the container's size instead of the other way round.
- **Never clear `innerHTML` on a div Plotly owns.** Plotly leaves a marker class
  behind, and the next `Plotly.react` silently draws nothing. Use `Plotly.purge(el)`.
- **Grid items that hold nowrap text** (pills in the top bar) floor at their content
  width even with `min-width: 0`. Give them `max-width: 100%` so they ellipsise
  instead of sliding under the tabs.
- **A flex child that should scroll needs `min-height: 0`** (or `min-width: 0`),
  otherwise it grows to its content and the page scrolls instead of the card.

---

## 10. Starter: `style.css`

```css
/* style.css: Dark Desk. Tokens first; the shell (top bar, tabs, sidebar) at design
   size; everything in the main content scaled by --main-text-scale. */

:root {
    --bg-dark: #0b0f19;
    --bg-panel: rgba(13, 18, 30, 0.95);
    --bg-card: rgba(18, 25, 41, 0.75);
    --bg-card-hover: rgba(28, 38, 61, 0.85);
    --bg-card-active: rgba(37, 99, 235, 0.2);
    --bg-popover: #0f1626;
    --bg-table-head: #0f172a;
    --track: #1e293b;
    --border-color: rgba(255, 255, 255, 0.08);
    --border-strong: rgba(255, 255, 255, 0.2);
    --border-highlight: rgba(59, 130, 246, 0.5);
    --accent-blue: #3b82f6;
    --accent-cyan: #06b6d4;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-rose: #f43f5e;
    --accent-violet: #c084fc;
    --good-text: #34d399;
    --warn-text: #fcd34d;
    --error-text: #fda4af;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --grad-active: linear-gradient(135deg, rgba(37, 99, 235, 0.85), rgba(6, 182, 212, 0.7));
    --grad-soft: linear-gradient(135deg, rgba(37, 99, 235, 0.3), rgba(6, 182, 212, 0.2));
    --shadow-main: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    --radius-lg: 16px;
    --radius-md: 10px;
    --radius-sm: 6px;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', ui-monospace, monospace;
    --sidebar-w: 330px;
    --topbar-h: 62px;
    --main-text-scale: 1.2;   /* keep equal to TEXT_SCALE in app.js */
    color-scheme: dark;       /* native scrollbars, date pickers and dropdowns render dark */
}

* { margin: 0; padding: 0; box-sizing: border-box; scrollbar-width: thin; scrollbar-color: #334155 transparent; }
[hidden] { display: none !important; }

body {
    font-family: var(--font-sans);
    background: var(--bg-dark);
    color: var(--text-primary);
    height: 100vh; width: 100vw; overflow: hidden;
}
.app-shell { display: flex; flex-direction: column; height: 100vh; width: 100vw; }
.app-body  { display: flex; flex: 1; min-height: 0; }

/* ============================ TOP BAR ============================ */
.top-bar {
    height: var(--topbar-h); flex-shrink: 0;
    display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: center; gap: 16px; padding: 0 20px;
    background: var(--bg-panel);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--border-color);
    z-index: 20;
}

.status-pill {
    display: flex; align-items: center; gap: 12px;
    justify-self: start; min-width: 0; max-width: 100%; overflow: hidden;
    padding: 6px 12px 6px 8px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 999px;
    color: var(--text-primary); font-family: var(--font-sans); text-align: left;
    cursor: pointer; transition: all 0.25s ease;
}
.status-pill:hover { background: var(--bg-card-hover); border-color: var(--accent-blue); }
.status-ring {
    width: 32px; height: 32px; flex-shrink: 0; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
    color: #fff; font-size: 13px;
}
.status-body { display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }
.status-value {
    font-family: var(--font-mono); font-size: 15px; font-weight: 600;
    letter-spacing: 0.5px; font-variant-numeric: tabular-nums;
}
.status-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px;
    color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.status-caret { font-size: 9px; color: var(--text-muted); transition: color 0.15s ease; }
.status-pill:hover .status-caret { color: var(--accent-cyan); }
.status-pill.busy { border-color: rgba(16, 185, 129, 0.45); box-shadow: 0 0 14px rgba(16, 185, 129, 0.18); }
.status-pill.busy .status-ring {
    background: linear-gradient(135deg, var(--accent-emerald), var(--accent-cyan));
    animation: pulse 2s ease-in-out infinite;
}
.status-pill.late { border-color: rgba(245, 158, 11, 0.55); box-shadow: 0 0 14px rgba(245, 158, 11, 0.2); }
.status-pill.late .status-ring { background: linear-gradient(135deg, var(--accent-amber), #f97316); }
.status-pill.late .status-value { color: var(--warn-text); }
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
    50%      { box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); }
}

.page-nav {
    justify-self: center;
    display: flex; align-items: center; gap: 4px; padding: 4px;
    background: rgb(15, 22, 39);
    border: 1px solid var(--border-color); border-radius: 999px;
}
.page-pill {
    display: flex; align-items: center; gap: 6px; padding: 8px 13px;
    border: none; border-radius: 999px; background: transparent;
    color: var(--text-secondary); font-family: var(--font-sans); font-size: 12px; font-weight: 600;
    white-space: nowrap; cursor: pointer;
    transition: background-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}
.page-pill i { font-size: 12px; }
.page-pill:hover { color: var(--text-primary); background: rgba(255, 255, 255, 0.06); }
.page-pill.active { background: var(--grad-active); color: #fff; box-shadow: 0 2px 14px rgba(59, 130, 246, 0.4); }
.page-pill.pill-icon { padding: 8px 11px; }
.page-pill.pill-icon i { font-size: 13px; }
.nav-divider { width: 1px; height: 18px; margin: 0 2px; background: var(--border-color); flex-shrink: 0; }
.top-meta { display: flex; gap: 10px; align-items: center; justify-content: flex-end; min-width: 0; }

/* ============================ SIDEBAR ============================ */
.sidebar {
    width: var(--sidebar-w); min-width: var(--sidebar-w);
    display: flex; flex-direction: column; gap: 17px; padding: 18px 16px;
    overflow-y: auto;
    background: var(--bg-panel);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid var(--border-color);
    z-index: 10;
}
.nav-section { display: flex; flex-direction: column; gap: 9px; }
.section-label {
    font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px;
    color: var(--text-secondary);
}
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.link-group { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-muted); }
.btn-link {
    background: transparent; border: none; padding: 0; cursor: pointer;
    color: var(--accent-cyan); font-family: var(--font-sans); font-size: 11px; font-weight: 600;
    transition: color 0.15s ease;
}
.btn-link:hover { color: #fff; text-decoration: underline; }
.btn-link:disabled { color: var(--text-muted); cursor: not-allowed; text-decoration: none; }

.helper-text { font-size: 10.5px; color: var(--text-muted); line-height: 1.45; }
.helper-text b { color: var(--text-secondary); }
.help-warn, .help-warn b { color: var(--warn-text); }
/* Notes under sidebar controls become hover tips (app.js); a warning stays printed. */
.sidebar .nav-section > .helper-text { display: none; }
.sidebar .nav-section > .helper-text.help-warn { display: block; }
.input-label { font-size: 11px; color: var(--text-muted); display: block; }

.custom-select {
    width: 100%; padding: 9px 12px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
    color: var(--text-primary); font-size: 13px; font-family: var(--font-sans);
    outline: none; cursor: pointer; transition: all 0.2s ease;
}
.custom-select:hover, .custom-select:focus { border-color: var(--accent-blue); background: var(--bg-card-hover); }
.custom-select option, .custom-select optgroup { background: var(--bg-table-head); color: var(--text-primary); }

.search-wrap { position: relative; }
.search-wrap i {
    position: absolute; left: 11px; top: 50%; transform: translateY(-50%);
    font-size: 11px; color: var(--text-muted); pointer-events: none;
}
.text-input {
    width: 100%; padding: 8px 11px 8px 30px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
    color: var(--text-primary); font-size: 12.5px; font-family: var(--font-sans); outline: none;
}
.text-input.no-icon { padding-left: 11px; }
.text-input::placeholder { color: var(--text-muted); }
.text-input:hover, .text-input:focus { border-color: var(--accent-blue); background: var(--bg-card-hover); }

.date-range { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.date-picker {
    width: 100%; padding: 7px 9px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-primary); font-size: 12px; font-family: var(--font-sans);
    outline: none; color-scheme: dark; cursor: pointer;
}
.date-picker:hover, .date-picker:focus { border-color: var(--accent-blue); }

.seg-group { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.seg-group.seg-3 { grid-template-columns: repeat(3, 1fr); }
.seg-group.seg-4 { grid-template-columns: repeat(4, 1fr); }
.seg-btn {
    padding: 7px 6px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-secondary); font-family: var(--font-sans); font-size: 11px; font-weight: 600;
    cursor: pointer; transition: all 0.15s ease;
}
.seg-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.seg-btn.active, .chip-tile.active {
    background: var(--grad-soft); border-color: var(--accent-cyan); color: #fff;
    box-shadow: 0 0 8px rgba(6, 182, 212, 0.25);
}
.seg-btn:disabled { opacity: 0.35; cursor: not-allowed; }

.chip-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(46px, 1fr)); gap: 6px; }
.chip-tile {
    padding: 6px 4px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-secondary); font-size: 11px; font-weight: 600; font-family: var(--font-mono);
    text-align: center; cursor: pointer; user-select: none; transition: all 0.15s ease;
}
.chip-tile:hover { background: var(--bg-card-hover); color: var(--text-primary); border-color: var(--border-strong); }

.tile-list { display: flex; flex-direction: column; gap: 8px; }
.tile {
    width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 8px;
    padding: 10px 12px; text-align: left; color: inherit; font-family: inherit;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
    cursor: pointer; transition: all 0.2s ease;
}
.tile:hover { background: var(--bg-card-hover); border-color: var(--border-strong); transform: translateY(-1px); }
.tile.active {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.25), rgba(6, 182, 212, 0.15));
    border-color: var(--accent-blue); box-shadow: 0 0 12px rgba(59, 130, 246, 0.25);
}
.tile:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
.tile-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.tile-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.tile-meta { font-size: 10px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tile-tag {
    font-size: 10px; font-weight: 700; padding: 3px 7px; border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.06); color: var(--text-secondary); white-space: nowrap;
}
.tile-tag.green  { background: rgba(16, 185, 129, 0.18); color: var(--good-text); }
.tile-tag.violet { background: rgba(168, 85, 247, 0.18); color: var(--accent-violet); }

.pick-list { display: flex; flex-direction: column; gap: 4px; max-height: 232px; overflow-y: auto; padding-right: 3px; }
.pick-row {
    display: flex; align-items: center; gap: 9px; padding: 6px 9px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    cursor: pointer; user-select: none; transition: all 0.15s ease;
}
.pick-row:hover { background: var(--bg-card-hover); border-color: var(--border-strong); }
.pick-row.active { border-color: var(--accent-blue); background: rgba(37, 99, 235, 0.14); }
.pick-check {
    width: 14px; height: 14px; flex-shrink: 0; border-radius: 3px; border: 1px solid var(--text-muted);
    display: flex; align-items: center; justify-content: center; font-size: 9px; color: transparent;
}
.pick-row.active .pick-check { background: var(--accent-blue); border-color: var(--accent-blue); color: #fff; }
.pick-body { flex: 1; min-width: 0; }
.pick-name { font-size: 11.5px; font-weight: 500; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pick-row.active .pick-name { color: var(--text-primary); font-weight: 600; }
.pick-meta { font-size: 9.5px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.switch-row {
    display: flex; align-items: center; justify-content: space-between; padding: 9px 12px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
    cursor: pointer; user-select: none;
}
.switch-row:hover { background: var(--bg-card-hover); }
.switch-row span { font-size: 12.5px; color: var(--text-secondary); }
.switch-row.active span { color: var(--text-primary); }
.switch {
    position: relative; flex-shrink: 0; width: 34px; height: 18px; border-radius: 999px;
    background: var(--track); border: 1px solid var(--border-color); transition: all 0.2s ease;
}
.switch::after {
    content: ''; position: absolute; top: 2px; left: 2px; width: 12px; height: 12px; border-radius: 50%;
    background: var(--text-muted); transition: all 0.2s ease;
}
.switch-row.active .switch { background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan)); border-color: var(--accent-cyan); }
.switch-row.active .switch::after { left: 18px; background: #fff; }

.slider-box {
    display: flex; flex-direction: column; gap: 9px; padding: 11px 12px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
}
.slider-head { display: flex; align-items: baseline; justify-content: space-between; font-size: 11px; color: var(--text-muted); }
.slider-head b { font-family: var(--font-mono); font-size: 11.5px; font-weight: 600; color: var(--accent-cyan); }
.custom-range {
    -webkit-appearance: none; appearance: none; width: 100%; height: 5px; border-radius: 3px;
    background: var(--track); outline: none; cursor: pointer;
}
.custom-range::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none; width: 16px; height: 16px; border-radius: 50%;
    background: var(--accent-blue); border: 2px solid #fff; box-shadow: 0 0 10px rgba(59, 130, 246, 0.8);
    transition: transform 0.15s ease;
}
.custom-range::-webkit-slider-thumb:hover { transform: scale(1.2); }
.custom-range::-moz-range-thumb {
    width: 12px; height: 12px; border-radius: 50%;
    background: var(--accent-blue); border: 2px solid #fff; box-shadow: 0 0 10px rgba(59, 130, 246, 0.8);
}

.badge {
    font-size: 10.5px; font-family: var(--font-mono); padding: 2px 8px; border-radius: 12px;
    background: rgba(59, 130, 246, 0.2); color: var(--accent-cyan); border: 1px solid rgba(59, 130, 246, 0.3);
}
.badge.zero { background: rgba(100, 116, 139, 0.15); color: var(--text-muted); border-color: var(--border-color); }

.btn {
    display: flex; align-items: center; justify-content: center; gap: 7px; padding: 9px 14px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-primary); font-family: var(--font-sans); font-size: 12px; font-weight: 600;
    cursor: pointer; transition: all 0.2s ease;
}
.btn:hover { background: var(--bg-card-hover); border-color: var(--accent-blue); }
.btn.block { width: 100%; }
.btn.primary { background: linear-gradient(135deg, rgba(37, 99, 235, 0.55), rgba(6, 182, 212, 0.4)); border-color: var(--accent-cyan); }
.btn.primary:hover { background: linear-gradient(135deg, rgba(37, 99, 235, 0.75), rgba(6, 182, 212, 0.55)); }
.btn.active { background: rgba(6, 182, 212, 0.2); border-color: var(--accent-cyan); color: var(--accent-cyan); box-shadow: 0 0 10px rgba(6, 182, 212, 0.3); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-ghost {
    display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; white-space: nowrap;
    background: var(--bg-card-hover); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-secondary); font-family: var(--font-sans); font-size: 11.5px; font-weight: 600;
    cursor: pointer; transition: all 0.15s ease;
}
.btn-ghost:hover { background: var(--bg-card-active); border-color: var(--border-highlight); color: var(--text-primary); }
.icon-btn {
    width: 24px; height: 24px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-muted); font-size: 11px; cursor: pointer; transition: all 0.15s ease;
}
.icon-btn:hover { color: var(--accent-cyan); border-color: var(--accent-cyan); background: rgba(6, 182, 212, 0.14); }

.sidebar-footer { margin-top: auto; padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.sidebar-footer:not(:has(> :not([hidden]))) { display: none; }

/* ============================ MAIN ============================ */
.main-content { flex: 1; min-width: 0; position: relative; background: var(--bg-dark); }
.page { position: absolute; inset: 0; display: flex; flex-direction: column; }

.page-head {
    display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
    flex-shrink: 0; padding: 14px 20px 12px 20px;
    background: rgba(13, 18, 30, 0.6); border-bottom: 1px solid var(--border-color);
}
.page-head h2 { font-size: calc(15px * var(--main-text-scale)); font-weight: 700; letter-spacing: -0.2px; }
.page-head .sub {
    display: block; margin-top: 3px;
    font-size: calc(11px * var(--main-text-scale)); color: var(--text-muted); font-family: var(--font-mono);
}
.head-tags { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; }
.tag {
    font-size: calc(10.5px * var(--main-text-scale)); font-weight: 600; padding: 4px 10px; border-radius: 999px;
    background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-secondary); white-space: nowrap;
}
.tag.accent { border-color: rgba(6, 182, 212, 0.4); color: var(--accent-cyan); }
.tag.good   { border-color: rgba(16, 185, 129, 0.4); color: var(--good-text); }
.tag.warn   { border-color: rgba(245, 158, 11, 0.5); color: var(--warn-text); }

.page-body {
    flex: 1; min-height: 0; overflow: auto;
    display: flex; flex-direction: column; gap: 14px; padding: 14px 18px 18px 18px;
}
.stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; flex-shrink: 0; }
.stat-card {
    display: flex; flex-direction: column; gap: 4px; padding: 12px 16px;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
}
.stat-label { font-size: calc(11px * var(--main-text-scale)); font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; color: var(--text-muted); }
.stat-value { font-size: calc(18px * var(--main-text-scale)); font-weight: 700; font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.stat-value.cyan  { color: var(--accent-cyan); }
.stat-value.green { color: var(--accent-emerald); }
.stat-value.red   { color: var(--accent-rose); }
.stat-note { font-size: calc(10.5px * var(--main-text-scale)); font-family: var(--font-mono); color: var(--text-muted); }

.card-grid {
    flex: 1; min-height: 360px;
    display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(360px, 1fr); gap: 14px;
}
.card {
    display: flex; flex-direction: column; min-width: 0; min-height: 0; position: relative;
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg);
    overflow: hidden;
}
.card-head {
    display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-shrink: 0;
    padding: 10px 16px; background: rgba(15, 23, 42, 0.75); border-bottom: 1px solid var(--border-color);
}
.card-head h3 {
    display: flex; align-items: center; gap: 8px; white-space: nowrap;
    font-size: calc(13px * var(--main-text-scale)); font-weight: 700;
}
.card-head h3 i { color: var(--accent-cyan); }
.card-actions { display: flex; align-items: center; gap: 6px; min-width: 0; }
.helper-badge {
    font-size: calc(11px * var(--main-text-scale)); font-family: var(--font-mono); padding: 4px 10px; white-space: nowrap;
    background: rgba(30, 41, 59, 0.8); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis;
}
.card-plot   { flex: 1; min-height: 0; }
.card-scroll { flex: 1; min-height: 0; overflow: auto; }
.card-notes  {
    flex: 1; min-height: 0; overflow: auto; padding: 12px 16px;
    font-size: calc(12px * var(--main-text-scale)); color: var(--text-secondary); line-height: 1.55;
}
.card-notes h4 {
    font-size: calc(10.5px * var(--main-text-scale)); font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px;
    color: var(--text-muted); margin: 10px 0 5px 0;
}
.card-notes h4:first-child { margin-top: 0; }
.card-notes b { color: var(--text-primary); }

.data-table {
    width: 100%; min-width: max-content; border-collapse: separate; border-spacing: 0;
    font-size: calc(12px * var(--main-text-scale));
}
.data-table thead th {
    position: sticky; top: 0; z-index: 2; background: var(--bg-table-head); color: var(--text-muted);
    font-size: calc(10px * var(--main-text-scale)); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
    text-align: right; padding: 9px 13px; white-space: nowrap;
    border-bottom: 1px solid var(--border-color); border-left: 1px solid rgba(255, 255, 255, 0.04);
}
.data-table .unit { color: var(--accent-cyan); font-weight: 600; text-transform: none; letter-spacing: 0; margin-left: 4px; }
.data-table tbody td {
    padding: 7px 13px; text-align: right; white-space: nowrap;
    font-family: var(--font-mono); font-variant-numeric: tabular-nums; color: var(--text-primary);
    border-bottom: 1px solid rgba(255, 255, 255, 0.04); border-left: 1px solid rgba(255, 255, 255, 0.04);
}
.data-table th.left, .data-table td.left { text-align: left; border-left: none; }
.data-table td.left { font-family: var(--font-sans); }
.data-table tbody tr:hover td { background: rgba(30, 41, 59, 0.55); }
.data-table tbody tr.selected td { background: rgba(37, 99, 235, 0.1); }
.data-table td.key { color: var(--accent-cyan); font-weight: 700; }
.data-table td.muted { color: var(--text-muted); }
.pos { color: var(--good-text); }
.neg { color: #fb7185; }

/* ---- popover menu (a card's gear) ---- */
.menu {
    position: fixed; z-index: 90; width: 320px; max-height: min(640px, calc(100vh - 24px));
    display: flex; flex-direction: column;
    background: var(--bg-popover); border: 1px solid var(--border-color); border-radius: var(--radius-md);
    box-shadow: var(--shadow-main);
}
.menu-head {
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    padding: 10px 10px 10px 14px; border-bottom: 1px solid var(--border-color);
    font-size: calc(11px * var(--main-text-scale)); font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.6px; color: var(--text-muted);
}
.menu-body { padding: 12px 14px 14px 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }

/* ---- modal ---- */
.modal-backdrop {
    position: fixed; inset: 0; z-index: 100;
    display: flex; align-items: flex-start; justify-content: center; padding: 78px 20px 40px 20px;
    background: rgba(4, 7, 13, 0.72); backdrop-filter: blur(3px);
}
.modal-panel {
    width: 100%; max-width: 820px; max-height: 100%;
    display: flex; flex-direction: column; overflow: hidden;
    background: var(--bg-popover); border: 1px solid var(--border-color); border-radius: var(--radius-lg);
    box-shadow: var(--shadow-main);
}
.modal-head {
    display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
    padding: 16px 20px; background: rgba(15, 23, 42, 0.9); border-bottom: 1px solid var(--border-color);
}
.modal-head h3 { display: flex; align-items: center; gap: 9px; font-size: 15px; font-weight: 700; }
.modal-head h3 i { color: var(--accent-cyan); }
.modal-sub { display: block; margin-top: 4px; font-size: 11.5px; font-family: var(--font-mono); color: var(--text-muted); }
.modal-close {
    width: 28px; height: 28px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    background: transparent; border: 1px solid var(--border-color); border-radius: var(--radius-sm);
    color: var(--text-secondary); cursor: pointer; transition: all 0.15s ease;
}
.modal-close:hover { background: var(--bg-card-hover); color: #fff; border-color: var(--accent-blue); }
.modal-close.small { width: 22px; height: 22px; font-size: 10px; }
.modal-body { overflow: auto; }
.modal-foot {
    padding: 11px 20px; border-top: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.8);
    font-size: 11px; color: var(--text-muted); line-height: 1.6;
}
.modal-foot code { font-family: var(--font-mono); color: var(--text-secondary); }

/* ---- feedback: toast, loader, empty state, error ---- */
.toast {
    position: fixed; bottom: 22px; left: 50%; z-index: 60;
    transform: translateX(-50%) translateY(12px);
    display: flex; align-items: center; gap: 9px; padding: 10px 18px;
    background: rgba(15, 23, 42, 0.97); border: 1px solid var(--accent-cyan); border-radius: 999px;
    font-size: calc(12px * var(--main-text-scale)); color: var(--text-primary); box-shadow: var(--shadow-main);
    opacity: 0; pointer-events: none; transition: opacity 0.2s ease, transform 0.2s ease;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.toast i { color: var(--accent-cyan); }

.loader {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 30;
    display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 22px 34px;
    background: rgba(11, 15, 25, 0.88); border: 1px solid var(--border-color); border-radius: var(--radius-lg);
    backdrop-filter: blur(10px); font-size: calc(12.5px * var(--main-text-scale)); color: var(--text-secondary);
}
.spinner {
    width: 32px; height: 32px; border-radius: 50%;
    border: 3px solid rgba(59, 130, 246, 0.2); border-top-color: var(--accent-cyan);
    animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.state-panel {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 30;
    display: flex; flex-direction: column; align-items: center; gap: 13px; text-align: center; max-width: 420px;
    padding: 26px 34px; background: rgba(11, 15, 25, 0.9); border: 1px solid var(--border-color);
    border-radius: var(--radius-lg); backdrop-filter: blur(10px);
    font-size: calc(12.5px * var(--main-text-scale)); color: var(--text-secondary);
}
.state-panel i.big { font-size: calc(26px * var(--main-text-scale)); color: var(--text-muted); }
.state-panel h3 { font-size: calc(14px * var(--main-text-scale)); font-weight: 600; color: var(--text-primary); }
.state-panel p { font-size: calc(11.5px * var(--main-text-scale)); line-height: 1.55; color: var(--text-muted); }

.page-error {
    position: absolute; top: 20px; left: 50%; transform: translateX(-50%); z-index: 31; max-width: 640px;
    display: flex; align-items: flex-start; gap: 10px; padding: 12px 18px;
    background: rgba(244, 63, 94, 0.15); border: 1px solid rgba(244, 63, 94, 0.5); border-radius: var(--radius-md);
    color: var(--error-text); font-size: calc(12.5px * var(--main-text-scale));
}
.page-error i { color: var(--accent-rose); margin-top: 2px; }

/* ---- help tip: the sidebar's notes, on hover (built by app.js) ---- */
.help-tip {
    position: fixed; z-index: 1000; left: 0; top: 0; max-width: 320px; padding: 10px 12px;
    background: var(--bg-table-head); border: 1px solid rgba(59, 130, 246, 0.35); border-radius: var(--radius-md);
    box-shadow: var(--shadow-main); font-size: 12px; line-height: 1.5; color: var(--text-secondary);
    pointer-events: none; opacity: 0; visibility: hidden;
    transition: opacity 0.12s ease, visibility 0s linear 0.12s;
}
.help-tip.show { opacity: 1; visibility: visible; transition: opacity 0.12s ease; }
.help-tip::before {
    content: ''; position: absolute; left: -6px; top: 11px; width: 10px; height: 10px; transform: rotate(45deg);
    background: var(--bg-table-head);
    border-left: 1px solid rgba(59, 130, 246, 0.35); border-bottom: 1px solid rgba(59, 130, 246, 0.35);
}
.help-tip b { color: var(--text-primary); }
.help-tip-note + .help-tip-note { margin-top: 7px; }

/* ---- narrower windows ---- */
@media (max-width: 1280px) {
    .card-grid { grid-template-columns: 1fr; grid-auto-rows: minmax(320px, auto); }
}
@media (max-width: 1100px) {
    .page-pill span { display: none; }   /* tabs keep their icons and their title */
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition-duration: 1ms !important; animation-duration: 1ms !important; }
}
```

---

## 11. Starter: `index.html`

```html
<!DOCTYPE html>
<!-- index.html: the shell, one of each control, and a page with stats, a chart and a table. -->
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="app-shell">

    <header class="top-bar">
        <button class="status-pill" id="status-pill" title="Click for detail">
            <div class="status-ring"><i class="fa-solid fa-bolt"></i></div>
            <div class="status-body">
                <span class="status-value" id="status-value">--:--:--</span>
                <span class="status-label">Next refresh</span>
            </div>
            <i class="fa-solid fa-chevron-down status-caret"></i>
        </button>

        <nav class="page-nav" aria-label="Pages">
            <button class="page-pill active" data-page="overview" title="Overview"><i class="fa-solid fa-gauge-high"></i><span>Overview</span></button>
            <button class="page-pill" data-page="explore" title="Explore"><i class="fa-solid fa-chart-line"></i><span>Explore</span></button>
            <button class="page-pill" data-page="reports" title="Reports"><i class="fa-solid fa-table-cells"></i><span>Reports</span></button>
            <span class="nav-divider"></span>
            <button class="page-pill pill-icon" data-page="settings" title="Settings"><i class="fa-solid fa-gear"></i></button>
        </nav>

        <div class="top-meta"></div>
    </header>

    <div class="app-body">
        <aside class="sidebar">
            <div class="nav-section" data-for="overview explore">
                <label class="section-label">Profile</label>
                <select class="custom-select">
                    <option>Unsaved profile</option>
                    <option>Morning view</option>
                </select>
                <small class="helper-text">A saved set of every control on this page. <b>Unsaved</b> means the page has drifted from it.</small>
            </div>

            <div class="nav-section" data-for="overview explore">
                <label class="section-label">Date Range</label>
                <div class="seg-group seg-4">
                    <button class="seg-btn">7D</button>
                    <button class="seg-btn active">30D</button>
                    <button class="seg-btn">90D</button>
                    <button class="seg-btn">1Y</button>
                </div>
                <div class="date-range">
                    <input type="date" class="date-picker" value="2026-09-01">
                    <input type="date" class="date-picker" value="2026-09-30">
                </div>
            </div>

            <div class="nav-section" data-for="overview">
                <label class="section-label">Source</label>
                <div class="tile-list">
                    <button class="tile active"><div class="tile-main"><span class="tile-name">Primary</span><span class="tile-meta">Updated hourly</span></div><span class="tile-tag green">LIVE</span></button>
                    <button class="tile"><div class="tile-main"><span class="tile-name">Archive</span><span class="tile-meta">Daily snapshot</span></div><span class="tile-tag">DAILY</span></button>
                    <button class="tile" disabled title="Not connected yet"><div class="tile-main"><span class="tile-name">External</span><span class="tile-meta">Not connected</span></div></button>
                </div>
            </div>

            <div class="nav-section" data-for="overview">
                <div class="section-head">
                    <label class="section-label">Bands</label>
                    <div class="link-group"><button class="btn-link">All</button><span>|</span><button class="btn-link">Reset</button></div>
                </div>
                <div class="chip-grid">
                    <button class="chip-tile">P10</button><button class="chip-tile active">P25</button>
                    <button class="chip-tile active">P50</button><button class="chip-tile active">P75</button>
                    <button class="chip-tile">P90</button>
                </div>
                <small class="helper-text">Shaded ranges drawn behind the main line.</small>
            </div>

            <div class="nav-section" data-for="explore reports">
                <div class="section-head">
                    <label class="section-label">Series</label>
                    <span class="badge">2</span>
                </div>
                <div class="search-wrap"><i class="fa-solid fa-magnifying-glass"></i><input class="text-input" placeholder="Search series..."></div>
                <div class="pick-list">
                    <div class="pick-row active"><div class="pick-check"><i class="fa-solid fa-check"></i></div><div class="pick-body"><div class="pick-name">Series A</div><div class="pick-meta">Group 1 · units</div></div></div>
                    <div class="pick-row active"><div class="pick-check"><i class="fa-solid fa-check"></i></div><div class="pick-body"><div class="pick-name">Series B</div><div class="pick-meta">Group 1 · units</div></div></div>
                    <div class="pick-row"><div class="pick-check"><i class="fa-solid fa-check"></i></div><div class="pick-body"><div class="pick-name">Series C</div><div class="pick-meta">Group 2 · units</div></div></div>
                </div>
            </div>

            <div class="nav-section" data-for="overview explore">
                <label class="section-label">Smoothing</label>
                <div class="slider-box">
                    <div class="slider-head"><span>Window</span><b id="smooth-out">7 days</b></div>
                    <input type="range" class="custom-range" id="smooth" min="1" max="28" value="7">
                </div>
            </div>

            <div class="nav-section" data-for="overview explore reports">
                <label class="section-label">Display</label>
                <div class="switch-row active"><span>Show reference line</span><div class="switch"></div></div>
                <small class="helper-text help-warn">Two sources are stale: shown with their last good value.</small>
            </div>

            <div class="sidebar-footer">
                <button class="btn primary block" id="refresh"><i class="fa-solid fa-rotate"></i> Refresh Data</button>
            </div>
        </aside>

        <main class="main-content">
            <section class="page" id="page-overview">
                <div class="page-head">
                    <div>
                        <h2>Overview</h2>
                        <span class="sub">Sep 1 – Sep 30 · weekdays only</span>
                    </div>
                    <div class="head-tags">
                        <span class="tag accent">+4.2% vs prior</span>
                        <span class="tag warn" title="Three days have no data">3 days missing</span>
                    </div>
                </div>
                <div class="page-body">
                    <div class="stat-row">
                        <div class="stat-card"><span class="stat-label">Average</span><span class="stat-value cyan">1,284.6</span><span class="stat-note">30 days</span></div>
                        <div class="stat-card"><span class="stat-label">Peak</span><span class="stat-value">1,902.0</span><span class="stat-note">Sep 18</span></div>
                        <div class="stat-card"><span class="stat-label">Change</span><span class="stat-value green">+52.3</span><span class="stat-note">vs prior 30</span></div>
                        <div class="stat-card"><span class="stat-label">Misses</span><span class="stat-value red">−3</span><span class="stat-note">below band</span></div>
                    </div>
                    <div class="card-grid">
                        <div class="card">
                            <div class="card-head">
                                <h3><i class="fa-solid fa-chart-line"></i> Trend</h3>
                                <div class="card-actions">
                                    <span class="helper-badge">daily</span>
                                    <button class="icon-btn" id="trend-gear" title="Chart settings"><i class="fa-solid fa-gear"></i></button>
                                </div>
                            </div>
                            <div class="card-plot" id="trend-chart"></div>
                        </div>
                        <div class="card">
                            <div class="card-head"><h3><i class="fa-solid fa-table"></i> Detail</h3><span class="helper-badge">30 rows</span></div>
                            <div class="card-scroll"><table class="data-table" id="detail-table"></table></div>
                        </div>
                    </div>
                </div>
            </section>

            <section class="page" id="page-explore" hidden>
                <div class="page-head"><div><h2>Explore</h2><span class="sub">Sep 1 – Sep 30</span></div></div>
                <div class="state-panel">
                    <i class="fa-solid fa-chart-area big"></i>
                    <h3>Nothing chosen yet</h3>
                    <p>Pick one or more series in the sidebar to draw them here.</p>
                </div>
            </section>

            <section class="page" id="page-reports" hidden>
                <div class="page-head"><div><h2>Reports</h2><span class="sub">Sep 1 – Sep 30</span></div></div>
                <div class="loader"><div class="spinner"></div>Loading reports…</div>
            </section>

            <section class="page" id="page-settings" hidden>
                <div class="page-head"><div><h2>Settings</h2></div></div>
                <div class="page-error"><i class="fa-solid fa-triangle-exclamation"></i>Couldn't load settings: the server returned 500. Everything else still works.</div>
            </section>
        </main>
    </div>
</div>

<div class="menu" id="trend-menu" hidden>
    <div class="menu-head">Chart settings <button class="modal-close small" id="trend-menu-close"><i class="fa-solid fa-xmark"></i></button></div>
    <div class="menu-body">
        <div class="nav-section">
            <label class="section-label">Line</label>
            <div class="seg-group seg-3"><button class="seg-btn active">Linear</button><button class="seg-btn">Smooth</button><button class="seg-btn">Stepped</button></div>
        </div>
    </div>
</div>

<div class="modal-backdrop" id="status-modal" hidden>
    <div class="modal-panel">
        <div class="modal-head">
            <div><h3><i class="fa-solid fa-bolt"></i> Status</h3><span class="modal-sub">last checked 12:04:31</span></div>
            <button class="modal-close" id="status-close"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body"><div class="card-notes"><h4>Sources</h4><p>Everything is up to date.</p></div></div>
        <div class="modal-foot">Times are local.</div>
    </div>
</div>

<div class="toast" id="toast"><i class="fa-solid fa-circle-check"></i><span id="toast-text"></span></div>
<script src="app.js"></script>
</body>
</html>
```

---

## 12. Starter: `app.js`

```js
// app.js: pages, controls, help tips, toast, and the one chart layout.
(() => {
    /* ---- charts: one layout for every chart; text scaled like the CSS ---- */
    const TEXT_SCALE = 1.2;                       // keep equal to --main-text-scale
    const ts = n => Math.round(n * TEXT_SCALE * 10) / 10;
    const PLOT_CONFIG = { displayModeBar: false, responsive: true };
    function plotLayout(overrides) {
        return Object.assign({
            paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Inter, sans-serif', size: ts(11), color: '#94a3b8' },
            margin: { l: 52, r: 14, t: 10, b: 42 },
            showlegend: true,
            legend: { orientation: 'h', x: 0, y: 1.12, font: { size: ts(10) }, bgcolor: 'rgba(0,0,0,0)' },
            hovermode: 'x unified',
            hoverlabel: { bgcolor: '#0f172a', bordercolor: '#334155',
                          font: { family: 'JetBrains Mono, monospace', size: ts(11), color: '#f8fafc' } },
            xaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false, linecolor: 'rgba(255,255,255,0.12)', tickfont: { size: ts(10) } },
            yaxis: { gridcolor: 'rgba(255,255,255,0.05)', zeroline: false, linecolor: 'rgba(255,255,255,0.12)', tickfont: { size: ts(10) } },
        }, overrides || {});
    }
    // Series colours in default order (strong), and each one's companion (soft).
    const SERIES = ['#4f91f2', '#02a998', '#dc701c', '#d863a0', '#b48c05', '#9f79e6', '#47ab4f', '#0aa0d2', '#e3645e', '#5b6777'];
    const SERIES_SOFT = ['#abcdfe', '#84decf', '#faba94', '#f8b3d3', '#e3c885', '#d1befe', '#a6dba7', '#8bd6fa', '#feb5ae', '#edf2fa'];
    // Colour scales for shaded cells: Viridis by default, Berlin (centred on 0) for signed values.
    const RAMPS = {
        viridis: ['#440154', '#48186a', '#472d7b', '#424086', '#3b528b', '#33638d', '#2c728e', '#26828e', '#21918c', '#1fa088', '#28ae80', '#3fbc73', '#5ec962', '#84d44b', '#addc30', '#d8e219', '#fde725'],
        berlin:  ['#9eb0ff', '#79abed', '#519fd3', '#3685ad', '#286886', '#1d4b61', '#14303e', '#111a20', '#190c09', '#2b0e01', '#411201', '#5b1d08', '#7d341e', '#9e513f', '#be6f63', '#df8f89', '#ffadad'],
    };
    const hexRgb = h => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
    // [r,g,b] for t in 0..1 along a ramp.
    function rampColor(t, stops) {
        const at = Math.max(0, Math.min(1, t)) * (stops.length - 1);
        const i = Math.min(stops.length - 2, Math.floor(at)), f = at - i;
        const a = hexRgb(stops[i]), b = hexRgb(stops[i + 1]);
        return a.map((x, k) => Math.round(x + (b[k] - x) * f));
    }
    // Text on a shaded cell: white while white reaches 3:1, else the page's dark.
    function inkFor(rgb) {
        const lin = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
        const L = 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
        return 1.05 / (L + 0.05) >= 3 ? '' : '#0b0f19';
    }

    /* ---- per-browser preferences: always wrapped, never required ---- */
    const store = {
        get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
        set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private window */ } },
    };

    /* ---- pages: one visible; sidebar sections follow data-for ---- */
    const drawn = new Set();
    function showPage(name) {
        document.querySelectorAll('.page').forEach(p => { p.hidden = p.id !== `page-${name}`; });
        document.querySelectorAll('.page-pill').forEach(b => b.classList.toggle('active', b.dataset.page === name));
        document.querySelectorAll('.sidebar [data-for]').forEach(s => { s.hidden = !s.dataset.for.split(' ').includes(name); });
        store.set('app.page', name);
        if (!drawn.has(name) && PAGES[name]) { drawn.add(name); PAGES[name](); }   // draw on first visit, once visible
        resizeCharts();
    }
    function resizeCharts() {
        document.querySelectorAll('.page:not([hidden]) .js-plotly-plot').forEach(el => {
            if (el.data && el._fullLayout) Plotly.Plots.resize(el);
        });
    }
    let resizeTimer = null;
    window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(resizeCharts, 120); });
    document.querySelectorAll('.page-pill').forEach(b => b.addEventListener('click', () => showPage(b.dataset.page)));

    /* ---- controls ---- */
    document.querySelectorAll('.seg-group').forEach(g => g.addEventListener('click', e => {
        const b = e.target.closest('.seg-btn'); if (!b || b.disabled) return;
        g.querySelectorAll('.seg-btn').forEach(x => x.classList.toggle('active', x === b));
    }));
    document.querySelectorAll('.chip-tile').forEach(c => c.addEventListener('click', () => c.classList.toggle('active')));
    document.querySelectorAll('.pick-row').forEach(r => r.addEventListener('click', () => r.classList.toggle('active')));
    document.querySelectorAll('.switch-row').forEach(r => r.addEventListener('click', () => r.classList.toggle('active')));
    document.querySelectorAll('.tile-list').forEach(l => l.addEventListener('click', e => {
        const t = e.target.closest('.tile'); if (!t || t.disabled) return;
        l.querySelectorAll('.tile').forEach(x => x.classList.toggle('active', x === t));
    }));
    const smooth = document.getElementById('smooth'), smoothOut = document.getElementById('smooth-out');
    if (smooth) smooth.addEventListener('input', () => { smoothOut.textContent = `${smooth.value} day${smooth.value === '1' ? '' : 's'}`; });

    /* ---- toast ---- */
    function toast(message) {
        const el = document.getElementById('toast');
        document.getElementById('toast-text').textContent = message;
        el.classList.add('show');
        clearTimeout(toast.timer);
        toast.timer = setTimeout(() => el.classList.remove('show'), 2200);
    }
    const refresh = document.getElementById('refresh');
    if (refresh) refresh.addEventListener('click', () => toast('Data refreshed'));

    /* ---- modal and popover ---- */
    const modal = document.getElementById('status-modal');
    document.getElementById('status-pill').addEventListener('click', () => { modal.hidden = false; });
    document.getElementById('status-close').addEventListener('click', () => { modal.hidden = true; });
    modal.addEventListener('click', e => { if (e.target === modal) modal.hidden = true; });
    const menu = document.getElementById('trend-menu');
    document.getElementById('trend-gear').addEventListener('click', e => {
        const r = e.currentTarget.getBoundingClientRect();
        menu.style.left = `${Math.max(12, r.right - 320)}px`;
        menu.style.top = `${r.bottom + 6}px`;
        menu.hidden = !menu.hidden;
    });
    document.getElementById('trend-menu-close').addEventListener('click', () => { menu.hidden = true; });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') { modal.hidden = true; menu.hidden = true; } });

    /* ---- help tips: a section's hidden notes, beside the sidebar, on hover ---- */
    const tip = Object.assign(document.createElement('div'), { className: 'help-tip' });
    document.body.appendChild(tip);
    let tipTimer = null, warmUntil = 0;
    document.querySelectorAll('.sidebar .nav-section').forEach(sec => {
        sec.addEventListener('mouseenter', () => {
            const notes = [...sec.querySelectorAll(':scope > .helper-text')].filter(n => getComputedStyle(n).display === 'none');
            if (!notes.length) return;
            clearTimeout(tipTimer);
            tipTimer = setTimeout(() => {
                tip.innerHTML = notes.map(n => `<div class="help-tip-note">${n.innerHTML}</div>`).join('');
                const r = sec.getBoundingClientRect(), side = sec.closest('.sidebar').getBoundingClientRect();
                tip.style.left = `${side.right + 12}px`;
                tip.style.top = `${Math.max(8, r.top)}px`;
                tip.classList.add('show');
            }, Date.now() < warmUntil ? 0 : 450);
        });
        sec.addEventListener('mouseleave', () => {
            clearTimeout(tipTimer);
            if (tip.classList.contains('show')) warmUntil = Date.now() + 600;
            tip.classList.remove('show');
        });
    });
    // A click, a scroll or Escape puts the tip away; it opens again when the pointer next enters a section.
    const hideTip = () => { clearTimeout(tipTimer); tip.classList.remove('show'); };
    document.addEventListener('pointerdown', hideTip);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') hideTip(); });
    document.querySelector('.sidebar').addEventListener('scroll', hideTip);

    /* ---- the demo page (replace with real data) ---- */
    const days = Array.from({ length: 30 }, (_, i) => new Date(2026, 8, i + 1));
    const base = days.map((_, i) => 1200 + 180 * Math.sin(i / 4) + 40 * Math.cos(i * 1.7));
    function drawOverview() {
        const lo = base.map(v => v - 120), hi = base.map(v => v + 120);
        Plotly.newPlot('trend-chart', [
            { x: days, y: hi, type: 'scatter', mode: 'lines', line: { width: 0 }, hoverinfo: 'skip', showlegend: false },
            { x: days, y: lo, type: 'scatter', mode: 'lines', line: { width: 0 }, fill: 'tonexty',
              fillcolor: 'rgba(79,145,242,0.14)', name: 'P25–P75', hoverinfo: 'skip' },
            { x: days, y: base, type: 'scatter', mode: 'lines', name: 'Actual', line: { color: SERIES[0], width: 2 } },
            { x: days, y: base.map((v, i) => v + 60 * Math.sin(i / 2)), type: 'scatter', mode: 'lines', name: 'Estimate',
              line: { color: '#f8fafc', width: 1.5, dash: 'dash' } },
            { x: days, y: base.map((v, i) => 80 * Math.sin(i / 3)), type: 'bar', name: 'Change', yaxis: 'y2',
              marker: { color: base.map((v, i) => Math.sin(i / 3) >= 0 ? 'rgba(2,169,152,0.55)' : 'rgba(227,100,94,0.55)') } },
        ], plotLayout({
            margin: { l: 56, r: 52, t: 34, b: 36 },
            yaxis2: { overlaying: 'y', side: 'right', showgrid: false, zeroline: false, tickfont: { size: ts(10) } },
        }), PLOT_CONFIG);

        const table = document.getElementById('detail-table');
        const changes = base.map((v, i) => i ? v - base[i - 1] : null);
        const lo2 = Math.min(...base), hi2 = Math.max(...base);
        table.innerHTML = `<thead><tr><th class="left">Day</th><th>Value<span class="unit">units</span></th><th>Change</th></tr></thead><tbody>` +
            days.map((d, i) => {
                const rgb = rampColor((base[i] - lo2) / (hi2 - lo2), RAMPS.viridis);
                const ch = changes[i];
                const chText = ch === null ? '—' : `${ch >= 0 ? '+' : '−'}${Math.abs(ch).toFixed(1)}`;
                return `<tr><td class="left">${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', weekday: 'short' })}</td>` +
                       `<td style="background:rgb(${rgb});color:${inkFor(rgb)}">${base[i].toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>` +
                       `<td class="${ch === null ? 'muted' : ch >= 0 ? 'pos' : 'neg'}">${chText}</td></tr>`;
            }).join('') + '</tbody>';
    }
    const PAGES = { overview: drawOverview };

    /* ---- the status pill's clock (replace with your app's live state) ---- */
    const statusValue = document.getElementById('status-value');
    const tick = () => { statusValue.textContent = new Date().toLocaleTimeString('en-GB'); };
    tick(); setInterval(tick, 1000);

    showPage(store.get('app.page', 'overview'));
})();
```

---

## 13. Before calling a screen done

- [ ] Only the tokens are used: no new hex values, radii or shadows invented inline.
- [ ] Every number is mono and tabular; table numbers are right-aligned; missing values
      print as `—`.
- [ ] The window doesn't scroll; cards and lists scroll inside themselves; table headers
      are sticky.
- [ ] Sidebar sections not used by this page are hidden; unavailable options are greyed
      with a reason in their `title`.
- [ ] The page head's subtitle says what window or selection is shown; its tags are
      results or warnings only.
- [ ] Amber appears only where something is genuinely unusual, with a tooltip saying what.
- [ ] Charts go through `plotLayout()`, use the series palette in order, and redraw
      correctly after a page switch and a window resize.
- [ ] Empty, loading and error states are all designed, each with a sentence that says
      why.
- [ ] Hovering a sidebar section with notes shows its tip; a warning note stays printed.
- [ ] Checked at 1280px and at 1920px wide; nothing in the top bar overlaps; no console
      errors.
