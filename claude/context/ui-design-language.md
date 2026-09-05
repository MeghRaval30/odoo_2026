# UI DESIGN LANGUAGE

**Binding for every screen.** Added session 02 after the first frontend pass was
rejected as looking machine-generated. Read this before writing any component.

The mockup in `claude/source/` is dark. **We do not follow its palette.** Product
spec §7 says explicitly that the UI is the participant's call as long as the
behaviour and data relationships stay clear, so the layout and field placement
of the mockup are binding and its colours are not.

---

## 1. Reference products

Copy these, in this order of precedence:

| Source | What we take |
|---|---|
| **Zoho Payroll / Zoho People** | Light surfaces, dense tables, restrained colour, form layout |
| **Razorpay Dashboard** | Type scale, spacing rhythm, KPI tiles, hairline borders |
| **Odoo** | *Structure only* — top menu bar, control bar, statusbar pills, stat buttons, kanban/list toggle |

Odoo contributes the information architecture. Zoho and Razorpay contribute how
it looks. Do not import Odoo's plum/purple chrome.

---

## 2. Tokens

Defined in `project/frontend/src/index.css`. Never hardcode a colour in a
component; the only exception is Recharts, which cannot read CSS custom
properties, and whose palette is mirrored at the top of `Dashboard.jsx`.

```
--navy      #16224a   top bar only
--bg        #f4f6f8   page
--surface   #ffffff   cards, tables, modals
--surface-2 #f7f9fb   table headers, hover
--border    #e3e8ee   every hairline
--text      #1a1f36   primary
--text-dim  #4f566b   secondary
--text-faint#8792a2   labels, meta
--primary   #2f7fe8   the ONLY accent
--green/amber/red/purple + matching --*-wash for badge fills
```

Radius 6px on cards, 4px on controls and badges. Base font 13px Inter.

---

## 3. Rules

1. **One accent.** `--primary` marks primary action and active state. Nothing
   else is blue.
2. **Colour carries meaning or it is grey.** State, sign, severity. Never
   decoration.
3. **Hairlines, not shadows.** Shadows only on floating layers — dropdown,
   popover, modal.
4. **Tabular numerals on every number.** Class `mono` on any money, count, hour
   or percentage cell. Money right-aligned via `num`.
5. **Density over air.** Table rows 10px vertical padding. Do not pad screens
   out to feel spacious; enterprise users scan.
6. **No gradients, no rounded-full pills except avatars, no icon fonts, no
   emoji in the interface.**
7. **Derived values are never inputs.** If the server computes it, render it as
   text — no disabled input styled to look editable.

---

## 4. Copy

This is where the first pass failed hardest. **Write labels, not explanations.**

- State what the field is. Do not explain what it does, why it matters, or what
  will happen. `End date`, not `End date — blank for an open-ended contract`.
- No reassurance. A wizard step does not need a banner promising that nothing
  has been created yet.
- No narration of the architecture to the user. The dashboard does not announce
  that it aggregates six models.
- No marketing. The login screen is not the place for a tagline.
- Errors come from the server, verbatim. `api.js` already flattens DRF field
  errors into readable text — surface that string, do not rewrite it.
- Sub-headings carry counts or periods, not adjectives: `22 records`,
  `2026-02-01 to 2026-02-28`.
- Symbols: `+`/`−` for deltas, `—` for empty. Not arrows, not "N/A", not
  "No data available yet".

If a sentence would sound odd printed on a bank statement, cut it.

---

## 5. Structure

```
topbar      navy, six menus fixed by spec, widget + user chip right
page        max 1600px, 20/24px padding
page-head   h1 + faint sub + right-aligned actions
toolbar     filters left, view toggle right
card        white, hairline, 16px
table-wrap  scrolls horizontally; the page body never does
```

State machines render as `.steps` pills, related-record counts as `.smart` stat
buttons, record forms in `.modal`. Kanban and list must open the *same* form.

---

## 6. Checklist before committing a screen

- [ ] No colour literal outside `index.css` (Recharts excepted)
- [ ] Every number cell has `mono`; money also has `num`
- [ ] No sentence explaining a field, a rule, or the system to the user
- [ ] Empty state is one short clause
- [ ] Errors render the server's message
- [ ] Wide content scrolls inside `.table-wrap`, not the page
- [ ] Works at 1280px without horizontal scroll
