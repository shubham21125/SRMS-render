# SRMS — Full UI & Animation Audit Report

**Date:** September 23, 2026  
**Audited System:** Student Result Management System (SRMS) — Phase 1–3 Fixed  
**Scope:** Public Site (Home, Login, Search Result, Reset Password), Admin Console (Dashboard, Students, Results, Attendance, Reports, Analytics), Parent/Student Portal (Dashboard, Results, Consolidated Marksheet, Attendance, Chatbot), Animation Engines (GSAP 3, ScrollTrigger, Lenis, anime.js, CSS transitions).

---

## 1. Executive Summary

This comprehensive audit analyzed all public, administrative, and parent-facing pages across both active themes (**Brutalist Heritage** light theme and **Dark Blue Glassmorphism / Obsidian & Gold** dark theme) as well as the complete animation stack.

### Top 10 Ranked Issues

| Rank | Issue | Category | Severity | User Impact |
|:---:|:---|:---:|:---:|:---|
| **1** | **Dashboard Stat Counter Double-Firing Glitch**<br>`admin_dashboard.html` calls `window.SRMSList.initCounters()` 500ms after `counters.js` has already started counting. Numbers count up, abruptly snap back to `0`, and count up a second time. | UI / Animation | **High** | Highly visible visual defect every time an admin lands on the main dashboard. |
| **2** | **Universal CSS Transition Performance Trap**<br>`dark-mode.css` applies `*, *::before, *::after { transition: background-color 0.28s, color 0.2s, border-color 0.22s, box-shadow 0.22s; }` across every DOM node. | Performance | **High** | Forces style recalculations across thousands of elements during scroll, hover, and DOM updates, fighting 60fps GSAP tweens. |
| **3** | **Parent Portal locked into Hardcoded Dark Theme**<br>`parent_base.html` hardcodes `--paper: #0c0b11 !important;`, `--surface: #171523 !important;`, and `--charcoal: #f5f2ed !important;` in inline styles. Selecting light mode in localStorage or toggling theme produces clashing light/dark artifacts. | Theme / UI | **High** | Breaks theme switching on the parent portal; renders light theme toggle ineffective or visually broken. |
| **4** | **13 Concurrent Infinite SVG Tweens on Login Page**<br>`login.html` runs 13 unpaused `repeat: -1` GSAP tweens simultaneously on the character SVG (glow, rings, bobbing, blinking, floating icons) with **no** `prefers-reduced-motion` check. | Performance / a11y | **High** | Constant GPU/CPU draw on login screens; causes dizziness/nausea for motion-sensitive users. |
| **5** | **Excessive Interactive Delays on Form Buttons & Inputs**<br>`reveal.js` imposes artificial entrance delays of `0.7s` (buttons) and `0.5s` (form fields), plus `login.html` delays Sign In button by `1.1s`. | UX / Latency | **High** | Users feel noticeable latency when loading forms, waiting over 1 second just for submit buttons to appear and become clickable. |
| **6** | **Global Link Interception in `transitions.js`**<br>`transitions.js` intercepts all `<a>` clicks, calls `e.preventDefault()`, and animates main opacity to `0` with a 300ms delay. Does not guard for Bootstrap modals, dropdowns, or hash links. | UX / Robustness | **Medium** | Risk of frozen white/blank pages if navigation is interrupted, or broken dropdowns/anchor jumps. |
| **7** | **Custom Cursor Animating Layout Properties (`left`/`top`)**<br>`#cursor-dot` and `#cursor-ring` in `index.html` update `left` and `top` inline styles on every mousemove and every RAF frame instead of GPU-composited `transform: translate3d()`. | Performance | **Medium** | Continuous CPU reflows and layout recalculations during desktop browsing on the landing page. |
| **8** | **Academic Grading Discrepancy on Parent Dashboard**<br>`parent/dashboard.html` hardcodes an obsolete 5-tier grading scale (`avg_marks >= 90 ? A+ : A`) where 85% yields "A", conflicting with official NEP 2020 marksheets where 80%+ is "O" (Outstanding). | Academic / UI | **Medium** | Parents see conflicting grades between their dashboard summary card and official result cards. |
| **9** | **Mobile Dual-Hamburger Icon Conflict**<br>On viewports $\le 768\text{px}$, `mobile-performance.js` dynamically inserts `.sidebar-mobile-toggle` into `.navbar-public`, while `topbar.html` already renders `.navbar-toggler`. | Mobile UX | **Medium** | Two identical hamburger icons appear side-by-side on mobile topbars, creating cognitive friction. |
| **10** | **Ghost / Dead Code: anime.js Suite Leftover**<br>`anime.min.js` (17.7KB) is stored in `static/js/vendor/` and referenced in an orphaned HTML comment in `login.html`, but is never executed anywhere in the project. | Cleanliness | **Low** | Unused vendor asset creating confusion about conflicting animation suites. |

---

## 2. UI/UX Findings

| Page / Section | Issue | Severity | Suggested Fix |
|:---|:---|:---:|:---|
| **Public: Home** (`index.html`) | 6 overlapping animation loops run on the hero simultaneously (Canvas particles, DOM particles, video scrub, typed text cursor, notice ticker, and custom cursor). | **Medium** | Consolidate hero effects: drop DOM particles in favor of the existing canvas particles; throttle resize/scroll listeners. |
| **Public: Home** (`index.html`) | Horizontal Showcase section has un-debounced resize listeners and card 3D tilt fires `gsap.to()` on every unthrottled mousemove pixel. | **Medium** | Wrap card mousemove in `SRMSPerf.rafThrottle()` to limit updates to 1 per animation frame. |
| **Public: Login** (`login.html`) | Password toggle button `<button id="togglePass">` has no `aria-label` or accessible text. | **Medium** | Add `aria-label="Toggle password visibility"` and `type="button"` to prevent form submission side-effects. |
| **Public: Reset Password** (`admin_forgot_password.html`, `admin_verify_otp.html`, `admin_reset_password.html`) | Uses undeclared font `'Syne', sans-serif;` on headers and submit buttons. In Light mode, OTP input has dark `rgba(0,0,0,0.2)` background with low text contrast. | **Medium** | Replace `'Syne'` with `var(--font-heading)` (`Playfair Display` or `Source Sans 3`). Use theme tokens `var(--surface)` and `var(--adm-border)` for OTP input styling. |
| **Public: Search Result** (`search_result.html`) | Footer is forcefully hidden via CSS (`display: none !important`), and card uses hardcoded dark glass styles even in light mode. | **Low** | Allow footer rendering on search results or align bottom spacing; bind card colors to CSS theme variables. |
| **Admin: Dashboard** (`admin_dashboard.html`) | Quick Action buttons use `.btn-outline-warning` with yellow/gold hover glows (`rgba(245,197,24,0.25)`), clashing with the Indigo Admin Console theme (`#4F46E5`). "Attendance Reports" is missing from Quick Actions. | **Medium** | Restyle Quick Actions using `--adm-primary` / `--adm-border` tokens and add an "Attendance Reports" quick-link tile. |
| **Admin: Manage Students** (`manage_students.html`) | Filter dropdowns use Brutalist public tokens `style="background:var(--surface);border-color:var(--rim);"` causing pitch-black borders (`#121212`) inside light admin cards (`#E7E9F2`). | **Medium** | Replace with standard Bootstrap classes `.form-select-sm` or Admin variables (`var(--adm-border)`). |
| **Admin: Declare Result** (`add_result.html`) | Dynamic subject entry table injected via AJAX has hardcoded white row borders `border-bottom: 1px solid rgba(255,255,255,0.05)` which are invisible on light mode. Inputs are constrained to 70px. | **Medium** | Use `var(--adm-border)` for row borders and wrap table in `.table-responsive` with min-width on columns for touch devices. |
| **Admin: Attendance Reports** (`attendance_reports.html`) | Metric strip uses public gold tokens (`var(--gold)`, `rgba(217,164,65,0.15)`) instead of Admin Indigo/Emerald tokens. | **Low** | Standardize badge and icon backgrounds to `--adm-primary-light` and `--adm-success-bg`. |
| **Admin: Analytics** (`admin_analytics.html`) | Chart.js defaults are hardcoded to dark colors (`#9999AA`, grid `rgba(255,255,255,0.05)`). In light mode, axes and tick labels have low contrast ratio (2.8:1). | **High** | Dynamically detect `data-theme` or `admin-page` and supply light/dark palette to `Chart.defaults`. |
| **Parent: Dashboard** (`parent/dashboard.html`) | Hardcoded grade evaluation logic (`{% if avg_marks >= 90 %}A+...{% endif %}`) uses an obsolete non-NEP scale with no "O" or "D" grades. | **High** | Replace with NEP 2020 grading standard: $\ge 80 \rightarrow \text{O}$, $\ge 70 \rightarrow \text{A+}$, $\ge 60 \rightarrow \text{A}$, $\ge 55 \rightarrow \text{B+}$, $\ge 50 \rightarrow \text{B}$, $\ge 45 \rightarrow \text{C}$, $\ge 40 \rightarrow \text{D}$, $< 40 \rightarrow \text{F}$. |
| **Parent: Attendance** (`parent/attendance.html`) | Year dropdown only contains hardcoded static years `2024`, `2025`, `2026`. When filtering by custom date range, the calendar heatmap disappears completely because `calendar_weeks` is set to `[]`. | **Medium** | Generate dynamic year range in context. Generate multi-month calendar grids for all months within the chosen date range so heatmaps persist. |
| **Parent: Base / Styles** (`parent_base.html`) | Contains ~300 lines of inline `<style>` with `!important` color overrides and attribute selector hacks (`a.btn[style*="var(--surface)"]`). | **Medium** | Move parent portal styling to a dedicated `parent-theme.css` stylesheet and eliminate `[style*="..."]` CSS selector hacks. |
| **Chatbot Widget** (`chatbot_widget.html`) | On narrow screens ($360\text{px} - 375\text{px}$), the chat window can overflow horizontally if media query fails or between 480px and 540px. Trigger button pulses infinitely with no reduced-motion override. | **Low** | Set `right: 12px; left: 12px; width: auto;` on mobile/tablet viewports; disable `@keyframes chatPulse` when `prefers-reduced-motion: reduce`. |

---

## 3. Animation Findings

| File / Module | Element / Trigger | Issue Identified | Severity | Suggested Fix |
|:---|:---|:---|:---:|:---|
| **`admin_dashboard.html`** & **`main.js`** | `.counter[data-target]` / Page Load | **Counter Double-Firing Conflict:** `main.js` calls `counters.init()` on DOM ready, then `admin_dashboard.html` executes `setTimeout(SRMSList.initCounters, 500)`, resetting the count to 0 mid-flight. | **High** | Remove the redundant `setTimeout` in `admin_dashboard.html`; let `counters.js` handle it once. |
| **`dark-mode.css`** (L15–17) | `*, *::before, *::after` / Global | Universal transition on 4 properties forces browser to calculate transition trees on every DOM mutation, drag, and GSAP frame. | **High** | Scope transition to root elements: `html, body, .card, .navbar, .sidebar { transition: background-color 0.25s, border-color 0.25s; }`. |
| **`index.html`** (L660–674) | `#cursor-dot`, `#cursor-ring` / `mousemove` + RAF | Animates `style.left` and `style.top` on every mousemove and RAF tick, triggering layout reflow instead of GPU compositing. | **Medium** | Switch to `style.transform = 'translate3d(' + x + 'px, ' + y + 'px, 0)'` with `will-change: transform`. |
| **`index.html`** (L8-24) | `#scroll-progress` / Global | Animates `background-position` via infinite keyframes (`shimmerBar`) on an element with fixed position, z-index 9999, and drop shadow. | **Low** | Use CSS `transform: scaleX()` for progress bar fill; remove infinite gradient shimmer on low-power devices. |
| **`login.html`** (L275–307) | `#charScene` (13 SVG elements) / Infinite | 13 separate infinite GSAP animations running continuously on the main thread with no pause when tab is inactive or user prefers reduced motion. | **High** | Wrap in `if (!isReduced)` and pause tweens on `document.visibilitychange` when `document.hidden`. |
| **`login.html`** (L220–235) | `#loginCard`, Form Fields, Buttons / Page Load | Excessive sequential delays (`delay: 0.85s` for inputs, `delay: 1.1s` for submit button). Fast users must wait 1.5s to click submit. | **High** | Compress timeline: inputs `delay: 0.2s`, submit button `delay: 0.35s` (total entrance $< 500\text{ms}$). |
| **`reveal.js`** (L111, 144) | Form fields & Buttons / Page Load | Form fields have `delay: 0.5s` and buttons have `delay: 0.7s` in standard mode. Creates perceptible UI lag on form pages. | **High** | Reduce delay to max 150ms (`delay: lite ? 0.05 : 0.15`). |
| **`transitions.js`** (L36–69) | `document.addEventListener('click')` / Anchor clicks | Global click handler intercepts links, calls `preventDefault()`, fades opacity to 0, and forces `window.location.href` after 300ms. Fails on modals, dropdowns, and download links. | **Medium** | Check `link.getAttribute('data-bs-toggle')`, `#` anchors, and `download` attributes; add timeout fallback to prevent blank-page lockup. |
| **`base.html`** (L359–360) | `.navbar-public .nav-link:not(.nav-cta)` / `mouseenter` | Empty GSAP tween: `gsap.to(link, { duration: 0.12 })` has duration but **no animation properties**. Wastes CPU creating empty tweens. | **Low** | Remove the empty tween or specify the target property (e.g., `color: 'var(--gold)'`). |
| **`base.html`** (L294–296) | `#loaderFill` / Page Loader | Animates `width: '100%'` (layout-triggering property) instead of `scaleX` and `transformOrigin: 'left'`. | **Low** | Change to `transform: scaleX(1)` with `transformOrigin: 'left center'`. |
| **`admin_analytics.html`** (L500–503) | `.progress-fill` / Page Load | Animates `width` from 0 to N% via GSAP `fromTo`, causing layout reflows on all analytics rows. | **Low** | Use `scaleX` or standard CSS transition on `width`. |
| **`static/js/vendor/`** | `anime.min.js` | 17.7KB vendor script bundled in static directory but not referenced or executed anywhere in the codebase. | **Low** | Remove or archive `anime.min.js` to eliminate dead vendor bloat. |

---

## 4. Cross-Theme Analysis & Token Inconsistencies

### 1. Theme Architecture Overview
The application defines three distinct visual design languages:
1. **Public Site:** *Brutalist Heritage* — Cream paper backgrounds (`#F5F2ED`), charcoal borders (`#121212`), gold accents (`#D9A441`), zero border-radii (`--radius: 0px`).
2. **Admin Console:** *Modern Professional* — Slate/indigo backgrounds (`#F3F5FA`), rounded cards (`--adm-radius-md: 12px`), indigo primary (`#4F46E5`), subtle shadows.
3. **Parent Portal:** *Obsidian & Gold* — Deep space background (`#0c0b11`), glass cards (`#171523`), gold borders, modern rounded corners.

### 2. Discovered Token Leaks & Bleeds
- **Admin Pages using Public Brutalist Tokens:**  
  In `manage_students.html`, `manage_classes.html`, and `manage_subject.html`, form controls declare:
  ```html
  style="background:var(--surface); border-color:var(--rim); color:var(--text-primary);"
  ```
  In Admin light mode, `--rim` resolves to `#121212` (pure black) from `style.css`, producing harsh, black-bordered inputs that clash with the soft `#E7E9F2` border system of `admin-theme.css`.
- **Admin Topbar vs Sidebar Palette Clash:**  
  The Admin topbar uses `.navbar-public` with gold accents and gold icons, while the sidebar underneath uses Indigo (`#4F46E5`) for active links and hover states.
- **Parent Portal Locked Dark:**  
  `parent_base.html` applies `!important` to `--paper`, `--surface`, and `--charcoal`. As a result, switching between light and dark modes has no effect on the parent portal body, but partially affects bootstrap utility classes, resulting in unreadable text contrast when a user has `srms-theme=light` stored in their browser.
- **Chart.js Color Invariance:**  
  In `admin_analytics.html`, grid lines and ticks are hardcoded to dark-mode values (`#9999AA`, `rgba(255,255,255,0.05)`). When Admin is viewed in light mode, the charts remain dark-themed with poor readability.

---

## 5. Quick Wins (< 10 Minutes Each)

The following 10 items can be resolved immediately without architectural refactoring:

1. **Fix Counter Reset Glitch on Admin Dashboard**  
   In `resultapp/templates/admin_dashboard.html`, delete line 126 (`setTimeout(function () { window.SRMSList.initCounters({ duration: 1.2 }); }, 500);`). Let `counters.js` run it once without resetting.
2. **Eliminate Universal CSS Transition Trap**  
   In `resultapp/static/css/dark-mode.css`, replace line 15 `*, *::before, *::after` with targeted selectors (`html, body, .card, .navbar, .sidebar`).
3. **Remove Empty Nav-Link Tween in `base.html`**  
   In `resultapp/templates/base.html` lines 358–360, remove the empty `gsap.to(link, { duration: 0.12 })` listener.
4. **Remove Production Debug Console Logs**  
   In `resultapp/templates/base.html` lines 316–318, remove `console.log("SplitText version:...", ...)`.
5. **Fix Login Password Toggle Accessibility**  
   In `resultapp/templates/login.html` line 192, add `aria-label="Toggle password visibility"` and `type="button"`.
6. **Correct Parent Dashboard NEP 2020 Grading Scale**  
   In `resultapp/templates/parent/dashboard.html` line 76, align grades with NEP 2020 standard (80%+ = O, 70%+ = A+, 60%+ = A, 55%+ = B+, 50%+ = B, 45%+ = C, 40%+ = D, <40% = F).
7. **Replace Orphaned `'Syne'` Font References**  
   In `admin_forgot_password.html`, `admin_verify_otp.html`, and `admin_dashboard.html`, replace `font-family:'Syne',sans-serif;` with `'Source Sans 3', sans-serif;` or `'Playfair Display', serif;`.
8. **Cut Button & Input Delays in `reveal.js`**  
   In `resultapp/static/js/animations/reveal.js`, change button delay from `0.7s` to `0.15s` and form fields delay from `0.5s` to `0.15s`.
9. **Fix Custom Cursor Layout Reflows**  
   In `resultapp/templates/index.html` lines 663–671, change `dot.style.left/top` to `dot.style.transform = translate3d(mx + 'px', my + 'px', 0)`.
10. **Delete Dead `anime.min.js` File**  
    Remove unused `resultapp/static/js/vendor/anime.min.js` and clean up the comment in `login.html`.

---

## 6. Conclusion & Next Steps

The SRMS application has robust functional capabilities, rich aesthetics, and strong visual foundations. The main friction points stem from:
1. **Conflicting scripts** (e.g. `counters.js` vs `admin-list.js` competing on the dashboard).
2. **Artificial entrance delays** that slow down perceived page performance.
3. **CSS token leaks** between the Brutalist public theme, Indigo admin theme, and Obsidian parent portal.

Applying the **Quick Wins** above will immediately eliminate the visible glitches (counter jumping, slow submit buttons, cursor lag) without breaking any page logic. Refactoring cross-theme tokens and unifying the parent portal stylesheet can be handled as a focused follow-up pass.
