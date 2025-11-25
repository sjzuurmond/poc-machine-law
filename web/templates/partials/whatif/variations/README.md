# What-If Scenario Panel Variations

This directory contains **4 different frontend implementations** of the what-if preview panel. Each variation offers a different user experience for exploring hypothetical scenarios.

## 🎯 Overview

All variations share the same core functionality:
- Real-time slider-based adjustments
- Automatic calculation with HTMX
- Live impact preview
- Support for Inkomen, Huur, and Vermogen
- Shows Zorgtoeslag, Huurtoeslag, and Participatiewet results

---

## 📋 Variation 1: Compact Side-by-Side

**File:** `compact_sidebyside.html` + `compact_results.html`

**Design Philosophy:** Exact implementation of the ASCII art specification - clean, minimal, split-pane layout.

### Features:
- ✅ **Split view**: Parameters left, results right
- ✅ **Compact design**: Fits in a single screen
- ✅ **Border-based separation**: Classic 2-column layout
- ✅ **Minimalist styling**: Focus on content over decoration
- ✅ **Color-coded changes**: Green (increase), Red (decrease), Gray (no change)

### Best For:
- Users who want a simple, no-nonsense interface
- Desktop/laptop users with wide screens
- When you need maximum information density

### Screenshot Description:
```
┌─ Jouw Gegevens ────────────┬─ Effect op regelingen ─────┐
│ Inkomen: €35.000           │ Zorgtoeslag: €156/mnd      │
│ [━━━━━●────] €0-€80k       │ ↓ was €180/mnd (-€24)      │
│                            │                            │
│ Huur: €800/mnd             │ Huurtoeslag: €245/mnd      │
│ [━━━●──────] €0-€2k        │ ↑ was €198/mnd (+€47)      │
└────────────────────────────┴────────────────────────────┘
```

### Usage:
```html
<!-- Route: /whatif/variations/compact -->
<a href="/whatif/variations/compact?bsn={{ bsn }}">
  Compact What-If View
</a>
```

---

## 📦 Variation 2: Dashboard Widget (Embeddable)

**File:** `dashboard_widget.html` + `widget_results.html`

**Design Philosophy:** A collapsible widget that lives on the main dashboard - always accessible without navigation.

### Features:
- ✅ **Collapsible design**: Expands/collapses on demand
- ✅ **Gradient styling**: Beautiful purple-blue gradient
- ✅ **Embeddable**: Can be included directly in dashboard
- ✅ **Color-coded sliders**: Different color per parameter
- ✅ **Quick access**: No page navigation needed

### Best For:
- Users who want quick "what-if" checks without leaving the dashboard
- Mobile-responsive design with collapsible sections
- When you want to encourage experimentation

### Screenshot Description:
```
╔══════════════════════════════════════════╗
║ 🔮 Wat-als Preview                    ▼ ║
╠══════════════════════════════════════════╣
║ 💼 Inkomen: €35.000                      ║
║ [━━━━━●────────────────────] €0-€80k     ║
║                                          ║
║ 🏠 Huur/mnd: €800                        ║
║ [━━━●──────────────────────] €0-€2k      ║
║                                          ║
║ 💰 Vermogen: €10.000                     ║
║ [━●────────────────────────] €0-€100k    ║
║                                          ║
║ ┌─ Live Impact ────────────────────┐    ║
║ │ 🏥 Zorgtoeslag     €156 (+€24)   │    ║
║ │ 🏠 Huurtoeslag     €245 (-€47)   │    ║
║ │ TOTAAL/mnd         €401          │    ║
║ └──────────────────────────────────┘    ║
╚══════════════════════════════════════════╝
```

### Usage:
```html
<!-- Include in dashboard.html -->
{% include "partials/whatif/variations/dashboard_widget.html" %}
```

---

## 🎨 Variation 3: Full-Screen Interactive with Charts

**File:** `fullscreen_interactive.html` + `fullscreen_results.html`

**Design Philosophy:** Rich, visual, full-screen experience with gradient cards and percentage indicators.

### Features:
- ✅ **Card-based layout**: Each parameter in its own beautiful card
- ✅ **Visual feedback**: Progress bars showing percentage
- ✅ **Gradient backgrounds**: Colorful, modern design
- ✅ **Large typography**: Easy to read, accessible
- ✅ **Icon-enhanced**: SVG icons for each category
- ✅ **Detailed results**: Shows percentage changes and detailed breakdowns

### Best For:
- Users who want a premium, polished experience
- Presentations or demos
- When visual appeal matters
- Users who appreciate modern UI design

### Screenshot Description:
```
╔═══════════════════════════════════════════════════════════╗
║        ⚡ Wat-als Scenario Explorer                        ║
╠═══════════════════════════════════════════════════════════╣
║ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        ║
║ │ 💼 Inkomen  │  │ 🏠 Huur     │  │ 💰 Vermogen │        ║
║ │ €35.000     │  │ €800/mnd    │  │ €10.000     │        ║
║ │ [━━━━━●────]│  │ [━━━●──────]│  │ [━●────────]│        ║
║ │ ▓▓▓▓▓░░░░░  │  │ ▓▓▓▓░░░░░░  │  │ ▓░░░░░░░░░  │        ║
║ │ 44%         │  │ 40%         │  │ 10%         │        ║
║ └─────────────┘  └─────────────┘  └─────────────┘        ║
║                                                            ║
║ ╔══════════ 📊 Impact op je regelingen ═════════╗        ║
║ ║ ┌─ Zorgtoeslag ──┐ ┌─ Huurtoeslag ─┐          ║        ║
║ ║ │ €156/mnd       │ │ €245/mnd      │          ║        ║
║ ║ │ 📈 +€24 (+15%) │ │ 📉 -€47 (-16%)│          ║        ║
║ ║ └────────────────┘ └───────────────┘          ║        ║
║ ║                                                 ║        ║
║ ║ TOTAAL: €401/mnd  (verschil: +€23)            ║        ║
║ ╚═════════════════════════════════════════════════╝        ║
╚═══════════════════════════════════════════════════════════╝
```

### Usage:
```html
<!-- Route: /whatif/variations/fullscreen -->
<a href="/whatif/variations/fullscreen?bsn={{ bsn }}">
  Full-Screen What-If
</a>
```

---

## 🎪 Variation 4: Modal/Overlay Quick Preview

**File:** `modal_overlay.html` + `modal_results.html`

**Design Philosophy:** Floating action button that opens a modal overlay - non-intrusive, always available.

### Features:
- ✅ **Floating button**: Fixed bottom-right corner
- ✅ **Modal overlay**: Darkened backdrop for focus
- ✅ **Quick access**: Available from any page
- ✅ **Smooth animations**: Fade in/out transitions
- ✅ **Keyboard support**: ESC to close
- ✅ **Click-away**: Close by clicking outside

### Best For:
- Users who want quick what-if checks while browsing
- Multi-step workflows where you need frequent reference
- When screen real estate is limited
- Power users who value keyboard shortcuts

### Screenshot Description:
```
┌─────────────────────────────────────────┐
│ [Dashboard content visible behind...]   │
│                                          │
│    ╔═══════════════════════════╗        │
│    ║ 🔮 Wat-als Preview    ✕  ║        │
│    ╠═══════════════════════════╣        │
│    ║ 💼 Inkomen: €35.000       ║        │
│    ║ [━━━━━●───────] €0-€80k   ║        │
│    ║                           ║        │
│    ║ 🏠 Huur/mnd: €800         ║        │
│    ║ [━━━●─────────] €0-€2k    ║        │
│    ║                           ║        │
│    ║ ┌─ Impact ──────────┐    ║        │
│    ║ │ 🏥 Zorgtoeslag €156│    ║        │
│    ║ │ 🏠 Huurtoeslag €245│    ║        │
│    ║ │ TOTAAL: €401       │    ║        │
│    ║ └────────────────────┘    ║        │
│    ╠═══════════════════════════╣        │
│    ║ [Volledige weergave]  [X]║        │
│    ╚═══════════════════════════╝        │
│                                          │
│  ┌──────────────┐                       │
│  │ 🔮 Wat-als?  │ ← Floating button     │
│  └──────────────┘                       │
└─────────────────────────────────────────┘
```

### Usage:
```html
<!-- Include anywhere in your layout -->
{% include "partials/whatif/variations/modal_overlay.html" %}

<!-- Button is automatically placed bottom-right -->
<!-- Click to open modal -->
```

---

## 🔧 Implementation Details

### Backend Requirements

All variations use the same backend endpoint:

```python
# Route: POST /whatif/direct-manipulation/calculate
@router.post("/direct-manipulation/calculate")
async def calculate_direct_manipulation(
    request: Request,
    bsn: str,
    templates=Depends(get_templates),
    engine: EngineInterface = Depends(get_engine),
) -> HTMLResponse:
    # Calculate and return results
```

### HTMX Integration

All variations use HTMX for real-time updates:

```html
<form
  hx-post="/whatif/direct-manipulation/calculate?bsn={{ bsn }}"
  hx-target="#results"
  hx-trigger="input changed delay:400ms from:input"
  hx-indicator="#loading"
>
```

### Alpine.js State Management

Each variation uses Alpine.js for client-side state:

```javascript
x-data="{
  inkomen_werk: 35000,
  huur_per_maand: 800,
  vermogen: 10000,
  formatMoney(v) { return '€' + v.toLocaleString('nl-NL') }
}"
```

---

## 🎨 Styling Approach

### Color Scheme

- **Blue**: Income/earnings related
- **Green**: Housing/rent related
- **Purple**: Assets/vermogen related
- **Gradients**: Premium feel, modern design

### Responsive Design

All variations are responsive:
- **Desktop**: Full feature set
- **Tablet**: Adjusted layout
- **Mobile**: Stacked/collapsed views

---

## 🚀 Quick Start

### Option 1: Add to Router

```python
# In web/routers/whatif.py

@router.get("/variations/compact", response_class=HTMLResponse)
async def compact_variation(...):
    template = templates.get_template("partials/whatif/variations/compact_sidebyside.html")
    return HTMLResponse(template.render(...))

@router.get("/variations/fullscreen", response_class=HTMLResponse)
async def fullscreen_variation(...):
    template = templates.get_template("partials/whatif/variations/fullscreen_interactive.html")
    return HTMLResponse(template.render(...))
```

### Option 2: Embed in Dashboard

```html
<!-- In dashboard.html -->
{% include "partials/whatif/variations/dashboard_widget.html" %}
<!-- or -->
{% include "partials/whatif/variations/modal_overlay.html" %}
```

---

## 📊 Comparison Matrix

| Feature | Compact | Widget | Fullscreen | Modal |
|---------|---------|--------|------------|-------|
| Screen Space | Medium | Small | Large | Overlay |
| Visual Polish | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Mobile-Friendly | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Information Density | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Ease of Access | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Best For | Desktop power users | Dashboard integration | Presentations | Quick checks |

---

## 💡 Recommendations

### Use **Compact Side-by-Side** when:
- You want the exact ASCII art design
- Users are on desktop/laptop
- Information density is priority

### Use **Dashboard Widget** when:
- You want to embed in the main dashboard
- Users need quick access without navigation
- Mobile users are important

### Use **Fullscreen Interactive** when:
- Visual appeal is important
- You're doing a demo or presentation
- You want to impress stakeholders

### Use **Modal/Overlay** when:
- Screen real estate is limited
- Users are performing multi-step workflows
- You want non-intrusive always-available access

---

## 🔄 Switching Between Variations

You can easily test all variations by visiting:

```
/whatif/variations/compact?bsn=100000001
/whatif/variations/fullscreen?bsn=100000001
```

Or embed in dashboard:
```html
<!-- Choose one -->
{% include "partials/whatif/variations/dashboard_widget.html" %}
{% include "partials/whatif/variations/modal_overlay.html" %}
```

---

## 📝 Customization

All variations are built with Tailwind CSS and can be easily customized:

- **Colors**: Modify gradient colors in each template
- **Ranges**: Adjust min/max/step in slider inputs
- **Laws**: Add more laws by extending the results templates
- **Animations**: Modify Alpine.js transitions

---

## 🐛 Troubleshooting

### Sliders not updating:
- Check HTMX is loaded
- Verify endpoint `/whatif/direct-manipulation/calculate` exists
- Check browser console for errors

### Alpine.js not working:
- Ensure Alpine.js is loaded in `base.html`
- Check `x-data` attributes are present

### Styling issues:
- Verify Tailwind CSS is properly configured
- Check for CSS conflicts with existing styles

---

**Created**: 2025-11-25
**Last Updated**: 2025-11-25
**Version**: 1.0.0
