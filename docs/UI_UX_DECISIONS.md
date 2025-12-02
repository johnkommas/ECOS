### UI/UX Decisions Log

This document records the design system and interaction rules applied to the ECOS FastAPI web UI to ensure consistency as the project evolves.

#### Brand & Layout
- Header: Sticky, translucent dark header with subtle gradient accent line and shadow. Contains logo (left) and product title/subtitle.
- Footer: Sticky at bottom with logo and legal copy: "Made with care and ❤ Copyright © 2025 Ioannis E. Kommas. All rights reserved". The heart is animated (heartbeat) and red.
- Main container width: 980px with 20px side padding.
- Surface: Glassy dark cards with soft inner highlight and border for depth.

#### Color System (CSS variables)
- Background: slate-900 `--bg: #0f172a`
- Panel/Card border: gray-800 `--border: #1f2937`
- Text: gray-200 `--text: #e5e7eb`
- Muted text: slate-400 `--muted: #94a3b8`
- Accent (actions): sky-400 `--accent: #38bdf8`
- Primary success: green-500/600 `--primary: #22c55e`, `--primary-600: #16a34a`
- Status badges: warn amber-500, ok emerald-500, info blue-400
- Danger (heart): red-500 `--danger: #ef4444`

#### Typography
- System UI stack for performance and OS-native feel: `-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Arial, Noto Sans`.
- Title sizes:
  - H1 (brand): 20px
  - H2 (card header): 16px
- Body: default 14–16px depending on OS.
- Subtle secondary text uses `--muted` color.

#### Components
- Button styles
  - Primary (Search): gradient sky-400 → sky-500, hover brightens.
  - Success (Fix): gradient green-500 → green-600.
  - Disabled state: reduced opacity, grayscale, pointer disabled.
- Card
  - Rounded radius 14px
  - Light border and soft shadows
  - Header with title + badge (ok/warn/info)
- Badges
  - Pill shape with semantic colors: ok (emerald), warn (amber), info (blue)
- Inputs
  - Rounded, dark field, focus ring accent (sky) and subtle glow.

#### Interaction Rules
- Search
  - User enters a document id (e.g., `ΑΠΛ-Α-2448299`) and clicks "Αναζήτηση".
  - Only one result card is ever displayed visually. If multiple records are returned, the card indicates the ambiguity and the Fix button is disabled.
- Validation and Fix
  - Server evaluates tri‑state checkpoints via `check.evaluate_checkpoints(df)`:
    1. Checkpoint 1: Exactly one row returned.
    2. Checkpoint 2: `StatusText` ends with the phrase `has already been sent to ECOS.` (δηλ. έχει ανέβει στο ECOS).
    3. Checkpoint 3: Η εγγραφή μπορεί να ενημερωθεί (`Status == 0`).
  - The header under «Αποτέλεσμα» shows a compact summary: `Checkpoint 1 • Checkpoint 2 • Checkpoint 3` as pass/fail badges. Ο λόγος για κάθε checkpoint εμφανίζεται σε tooltip κατά το hover/focus (compact παρουσίαση, επαγγελματική). Για προσβασιμότητα χρησιμοποιούμε και `aria-label` στο badge.
  - The Fix button is enabled only if all three checkpoints pass. Σε αντίθετη περίπτωση είναι απενεργοποιημένο και εμφανίζεται ο πρώτος λόγος αποτυχίας.
  - On Fix, server runs update SQL; success/failure message appears in alert area and the card refreshes.
- Messaging
  - Greek language strings for end-user clarity.
  - Examples:
    - Not found: "Δεν βρέθηκαν εγγραφές για το έγγραφο που δώσατε."
    - Multiple: "Βρέθηκαν περισσότερες από μία εγγραφές. Παρακαλώ ελέγξτε την αναζήτηση."
    - Healthy: "Η εγγραφή είναι υγιής και δεν απαιτείται διόρθωση."
    - Update OK: "Η ενημέρωση ολοκληρώθηκε επιτυχώς (Επηρεάστηκαν: N)."

#### Accessibility
- Sufficient contrast on dark background.
- Focus styles on inputs.
- Heart element includes `aria-label` and is decorative only.

#### Assets
- Logo: `images/SOFTONE-EINVOICING.svg` used in header and footer.

#### Pages & Routes
- `/` GET: Form page.
- `/search` POST: Runs query and renders card with validation state.
- `/fix` POST: Re-validates and applies update when permitted; shows result message.

#### Future Extensions (Guidelines)
- Add loading state for async actions.
- Show more friendly status labels (e.g., 0 → «Προς διόρθωση», 1 → «Υγιής»).
- Include audit log panel for performed fixes.
- Internationalization with message catalogs if needed.

#### Data Presentation: Result Card (Groups & Formatting)
- Grouping pattern
  - "Βασικές Πληροφορίες":
    - Έγγραφο (input echo)
    - Κατάσταση (raw Status value for now)
    - UID (fDocumentGID)
  - "Πληροφορίες Χρήστη":
    - Χρήστης (ESUCreated)
    - Ημερομηνία (ESDCreated) formatted as `dd.mm.yyyy • hh:mm:ss`
  - "Πληροφορίες Παρόχου":
    - Πάροχος (ProviderName)
    - Σύνδεσμος Παραστατικού (InvoiceURL) shown as a clickable link; if missing protocol it is normalized to https://
    - QR Code (if available) rendered as an image
  - "Πληροφορίες Τιμών":
    - Καθαρή Αξία (NetValue)
    - Αξία ΦΠΑ (VATValue)
    - Σύνολο (ADTotalValue)
- Formatting rules
  - Dates: ESDCreated accepts strings, pandas Timestamps, or datetimes; output is always `dd.mm.yyyy • hh:mm:ss`. If parsing fails, the original value is shown.
  - Numbers: monetary values are formatted with two decimals and European separators (e.g., 12.345,67) and the UI appends the `€` symbol after the value.
  - Links: InvoiceURL is normalized to include a scheme if missing; opens in a new tab with `rel="noopener noreferrer"`.
- Layout & styling
  - Each group uses a titled container (.kv-group) with an accent title (.kv-title) and a two-column responsive grid (.kv-grid → 1 column on small screens).
  - Keys are semi-bold and muted; values are bold. Rows are left-aligned using a grid (label column auto, value column 1fr). Dividers are subtle dashed lines using the theme divider token.
  - QR Code is rendered within the Provider group with a fixed-size thumbnail and border.
- Robustness
  - Empty or null values are omitted from rendering to keep presentation clean.
  - The "Περισσότερες Πληροφορίες" section excludes keys already shown in the groups to avoid duplication.

#### Theme System (Light / Dark / Auto)
- Mechanism: CSS variables scoped by `data-theme` attribute on the `<html>` element.
  - Dark: `:root[data-theme="dark"]`
  - Light: `:root[data-theme="light"]`
  - Auto: resolves to the system `prefers-color-scheme`, dynamically updates on OS theme changes.
- Persistence & defaults:
  - Preference key: `localStorage.themePref` with values `"light" | "dark" | "auto"`.
  - First paint resolver runs inline in `<head>` to avoid FOUC; migrates legacy `localStorage.theme` if present.
  - When set to `auto`, a `matchMedia('(prefers-color-scheme: dark)')` listener updates the resolved theme live.
- UI Control:
  - Header segmented control (radiogroup) with three options: Light, Dark, Auto.
  - Markup example:
    ```html
    <div class="color-scheme-toggle" role="radiogroup" tabindex="0">
      <div class="toggle-thumb" aria-hidden="true"></div>
      <label data-color-scheme-option="light"><input type="radio" name="color-scheme" value="light"><div class="text">Light</div></label>
      <label data-color-scheme-option="dark"><input type="radio" name="color-scheme" value="dark"><div class="text">Dark</div></label>
      <label data-color-scheme-option="auto"><input type="radio" name="color-scheme" value="auto"><div class="text">Auto</div></label>
    </div>
    ```
  - Controller API: `window.setPreferredColorScheme(value)` persists preference and updates the UI.
  - Accessibility: `role="radiogroup"`, keyboard arrows cycle options, focus-visible ring on labels.
- CSS Tokens (selected):
  - `--bg`, `--bg2`, `--text`, `--muted`, `--border`, `--divider`, `--card`, `--header-bg`, `--footer-bg`, `--field-bg`, alert vars (`--alert-bg`, `--alert-border`, `--alert-text`).
  - Actions: `--accent`, `--primary`, `--primary-600`; statuses `--ok`, `--warn`, `--info`, `--danger`.

Pages/components automatically inherit the active theme via variables; no per-component overrides are required.
