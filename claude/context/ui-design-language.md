# UI DESIGN LANGUAGE

**Binding for every screen.** Written session 02 after two rejected frontend
passes. Read this before writing any component.

The mockup in `claude/source/` is dark. **We do not follow its palette.** Product
spec §7 leaves the UI to the participant as long as behaviour and data
relationships stay clear, so the mockup's *layout and field placement are
binding* and its colours are not.

---

## 1. The look

Anthropic's own palette, applied to a dense operations product: bone and sand
grounds, **Claude orange as the single action colour**, dusty rose carrying the
surfaces, and brown rather than grey for text and rules.

The target is premium and warm — considered, not clinical, and not the default
blue-on-white SaaS dashboard that reads as machine-generated.

**Pink is not an accent.** It is roughly a quarter of the surface area: KPI card
grounds, table headers, row hovers, stat buttons and every hairline are rose
rather than neutral grey. If a screen looks grey, the rose tokens are not being
used.

Structure — and only structure — is still Odoo's: top menu bar, control bar,
status pills, stat buttons, kanban/list toggle. Take no Odoo colour.

---

## 2. Tokens

Defined in `project/frontend/src/index.css`. Never hardcode a colour in a
component. The one exception is Recharts, which cannot read CSS custom
properties; its palette is mirrored at the top of `Dashboard.jsx` and must be
updated with this file.

```
--espresso  #3b2e28   top bar
--bg        #f4efe9   page, warm sand
--surface   #fffcf9   cards, warm white
--surface-2 #f9ede8   ROSE — table headers, hovers, KPI grounds, stat buttons
--surface-3 #f2ded7   ROSE — deeper fill, avatars, grey badges
--border    #e7d9d1   ROSE — every hairline
--border-2  #d9c5ba   ROSE — control borders

--text      #241e1a   warm near-black
--text-dim  #6b5f55   brown, secondary
--text-faint#9c8f84   brown, labels and meta

--primary   #d97757   Claude orange — the ONLY action colour
--primary-dark #bd5c3d
--primary-wash #fbebe3

--rose #c0757b · --green #5b7d58 · --amber #a97a24 · --red #b5504a
--purple #856b9c    each with a matching --*-wash for badge fills
```

Semantic colours are muted to sit with the warm ground — sage rather than
emerald, brick rather than scarlet. Do not substitute saturated web defaults.

Radius 8px on cards and modals, 5px on controls and inputs, 3px on badges.

---

## 3. Type

A classical pairing. Serif for what is **read**, sans for what is **operated**.

| Family | Used for |
|---|---|
| `--font-serif` Source Serif 4 | `h1`–`h4`, `.card-title`, `.kpi .value`, `.smart .n`, `.avatar`, the brand |
| `--font-sans` Inter | body, labels, controls, table cells, badges |

Serif numerals in the KPI figures are the point of the pairing — they make money
look considered. Base size 13px, line-height 1.55.

---

## 4. Rules

1. **One action colour.** `--primary` marks primary action and active state.
   Nothing else is orange.
2. **Colour carries meaning or it is warm neutral.** State, sign, severity.
   Never decoration.
3. **Hairlines, not shadows.** Shadows only on floating layers — dropdown,
   popover, modal.
4. **Tabular numerals on every number.** Class `mono` on any money, count, hour
   or percentage cell; money also gets `num` to right-align.
5. **Density over air.** Table rows 10px vertical padding. Enterprise users
   scan; do not pad screens out to feel spacious.
6. **No gradients, no full-round pills except avatars, no icon fonts, no emoji.**
7. **Derived values are never inputs.** If the server computes it, render text —
   never a disabled input styled to look editable.

---

## 5. Copy

This is where the first pass failed hardest. **Write labels, not explanations.**

- State what the field is. Do not explain what it does or what will happen.
  `End date`, not `End date — blank for an open-ended contract`.
- No reassurance. A wizard step does not need a banner promising nothing has
  been created yet.
- No narration of the architecture. The dashboard does not announce that it
  aggregates six models.
- No marketing. The login screen is not the place for a tagline.
- Errors come from the server, verbatim. `api.js` already flattens DRF field
  errors into readable text — surface that string, do not rewrite it.
- Sub-headings carry counts or periods, not adjectives: `22 records`,
  `2026-02-01 to 2026-02-28`.
- Symbols: `+`/`−` for deltas, `—` for empty. Not arrows, not "N/A", not
  "No data available yet".

If a sentence would sound odd printed on a bank statement, cut it.

---

## 6. Structure

```
topbar      espresso, six menus fixed by spec, widget + user chip right
page        max 1600px, 22/24px padding
page-head   serif h1 + faint sub + right-aligned actions
toolbar     filters left, view toggle right
card        warm white, rose hairline, 16px
table-wrap  scrolls horizontally; the page body never does
```

State machines render as `.steps` pills, related-record counts as `.smart` stat
buttons, record forms in `.modal`. Kanban and list must open the *same* form.

---

## 7. Checklist before committing a screen

- [ ] No colour literal outside `index.css` (Recharts excepted, and mirrored)
- [ ] Rose surfaces actually used — the screen is not grey
- [ ] Headings and figures in serif, controls in sans
- [ ] Every number cell has `mono`; money also has `num`
- [ ] No sentence explaining a field, a rule, or the system to the user
- [ ] Empty state is one short clause
- [ ] Errors render the server's message
- [ ] Wide content scrolls inside `.table-wrap`, not the page
- [ ] Works at 1280px without horizontal scroll
