---
name: Klyptra Studio
colors:
  surface: '#fbf8ff'
  surface-dim: '#dad9e3'
  surface-bright: '#fbf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f2fd'
  surface-container: '#eeedf7'
  surface-container-high: '#e8e7f1'
  surface-container-highest: '#e3e1ec'
  on-surface: '#1a1b22'
  on-surface-variant: '#464555'
  inverse-surface: '#2f3038'
  inverse-on-surface: '#f1effa'
  outline: '#777587'
  outline-variant: '#c7c4d8'
  surface-tint: '#4c42e9'
  primary: '#493ee5'
  on-primary: '#ffffff'
  primary-container: '#635bff'
  on-primary-container: '#fefaff'
  inverse-primary: '#c3c0ff'
  secondary: '#6b38d4'
  on-secondary: '#ffffff'
  secondary-container: '#8455ef'
  on-secondary-container: '#fffbff'
  tertiary: '#006285'
  on-tertiary: '#ffffff'
  tertiary-container: '#007ca8'
  on-tertiary-container: '#f8fbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#321ed2'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#c4e7ff'
  tertiary-fixed-dim: '#7bd0ff'
  on-tertiary-fixed: '#001e2c'
  on-tertiary-fixed-variant: '#004c69'
  background: '#fbf8ff'
  on-background: '#1a1b22'
  surface-variant: '#e3e1ec'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.03em
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.015em
  title-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-xs:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: -0.01em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-desktop: 1rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system delivers an ultra-refined, professional creative canvas engineered for video editors, streamers, and high-velocity digital creators. Balancing the precision-density of modern workflow tools (such as Linear and Figma) with pristine, breathable elegance, it prioritizes content fidelity above all else. 

The aesthetic marries **Minimalism** with structural **Low-Contrast Precision**. Interface chrome recedes into soft zinc surfaces and hairline dividers, allowing high-resolution video streams, waveform timelines, and AI extraction nodes to command attention. Accent interactions introduce restrained, ethereal tints of lavender and periwinkle, signaling intelligent automation without sensory fatigue. The overall impression is effortless velocity, calculated focus, and studio-grade craftsmanship.

## Colors

The palette operates on a calibrated spectrum of neutral zinc paired with luminous violet-lavender accents:

- **Canvas & Chrome:** Base canvas sits at `#FAFAFC` with raised container panels at `#FFFFFF`. Inactive surfaces transition downward to `#F4F4F7`.
- **Primary (`#635BFF`) & Secondary (`#8B5CF6`):** Precision periwinkle and soft lavender serve as the active engine—used strictly for playhead markers, AI generation boundaries, selected clip brackets, and primary action triggers.
- **Tertiary Accent (`#38BDF8`):** Sky blue reserved for speech-to-text anchors, audio waveform peaks, and automated transcription highlights.
- **Neutrals & Borders:** Hairline structural borders use `#E4E4E9` (resting) and `#D1D1DB` (interactive). Primary labels use rich zinc `#18181B`, body copy rests at `#52525B`, and utility metadata relies on `#71717A`.
- **Pastel Washes:** Ambient AI highlight fills leverage ultra-diluted gradients blending `#635BFF0D` (5%) to `#8B5CF608` (3%) over white surfaces.

## Typography

The typography system relies on a dual-engine architecture:
- **Plus Jakarta Sans** governs expressive display titles, panel headers, and onboarding flows, lending an architectural, modern feel without geometric rigidity.
- **Inter** handles dense data grids, timeline scrub labels, property inspectors, and long-form AI transcripts, optimized for micro-legibility at 11px to 13px.
- **JetBrains Mono** is utilized strictly for numeric timecodes (`00:14:32:08`), video bitrate meters, and export aspect ratio metrics.

Headlines employ tight negative letter-spacing for structural authority. Labels and button text use strict medium weights (`500`) to guarantee high-contrast legibility against pale surface backdrops.

## Layout & Spacing

The studio workspace adheres to a strict docked, multi-pane layout model inspired by professional digital audio and video workstations. 

- **Studio Canvas:** Utilizes non-overlapping edge-to-edge docked panes (Collapsible Media Browser, Central Viewport/Stage, Right-hand Inspector, Bottom Multi-track Timeline). Panes flex fluidly with fixed minimum widths (Left: 260px, Right: 300px, Bottom: 220px).
- **Global Grids:** Modals, project dashboards, and settings pages leverage a 12-column grid constrained to a maximum width of 1440px with `margin-desktop: 1.5rem` and `gutter-desktop: 1rem`.
- **Micro Rhythms:** Internal panel padding adheres strictly to `space-sm` (8px) for compact control clusters and `space-md` (12px) for inspector sections, minimizing unnecessary pointer travel during editing tasks.
- **Responsive Adaptations:** On displays under 1024px, the inspector collapses into a sliding bottom drawer, and secondary timeline lanes group into tabbed sheets.

## Elevation & Depth

Visual hierarchy is maintained through crisp hairline framing, nuanced surface tiering, and soft diffused shadows rather than heavy drop shadows:

- **Surface Tiers:**
  - Base Workspace (Floor): `#F4F4F7`
  - Floating Panes & Inspectors: Pure `#FFFFFF` bordered by a 1px continuous stroke of `#E4E4E9`.
  - Nested Toolbars & Inset Cavities: `#F8F8FA` with internal recessed borders.
- **Shadow System:**
  - **Flat / Structural:** 0px blur with `1px solid #E4E4E9` for permanent sidebars and timeline tracks.
  - **Elevated (Clip Drag / Popovers):** `0 4px 16px -2px rgba(24, 24, 27, 0.04), 0 2px 6px -1px rgba(24, 24, 27, 0.02)`.
  - **Overlay / Modal:** `0 12px 32px -4px rgba(24, 24, 27, 0.08), 0 4px 12px -2px rgba(24, 24, 27, 0.03)`.
- **Focus & Selection:** Active video layers and focused timeline tracks never rely on thick strokes; they employ a 1.5px `#635BFF` perimeter with a subtle `0 0 0 3px rgba(99, 91, 255, 0.12)` ambient periwinkle halo.

## Shapes

The design system enforces a precise, disciplined shape language (`roundedness: 1`):

- **Micro Controls & Inputs:** 4px (`rounded-sm` / `0.25rem`) for toolbar buttons, scrubber thumbs, tags, and text inputs to maintain geometric cohesion in dense spaces.
- **Cards & Panes:** 8px (`rounded-lg` / `0.5rem`) for timeline clips, floating menus, dialog containers, and asset previews.
- **Modals & Master Windows:** 12px (`rounded-xl` / `0.75rem`) for modal sheets and full-canvas export overlays.
- **Pill Exceptions:** Rounded-full tokens are strictly limited to active recording indicators, AI status tags, and timecode scrubber capsules.

## Components

### Buttons
- **Primary:** Background `#635BFF`, foreground `#FFFFFF`, micro-radius (`4px`). On hover, shifts to `#534AEF` with a soft lavender border highlight.
- **Secondary / Ghost:** White background, 1px border `#E4E4E9`, text `#18181B`. Hover initiates background `#F4F4F7` and border `#D1D1DB`.
- **Studio Action (Icon Buttons):** 28x28px or 32x32px square footprints with centered vector glyphs at 16px. Background is transparent; shifts to `#E4E4E9` on active press.

### Inputs & Scrubbers
- **Text & Numeric Inputs:** Minimalist boxes with white fill, 1px `#E4E4E9` stroke, 32px height, and monospaced alignment for timeline parameters. On focus: border shifts to `#635BFF` without layout jump.
- **Numeric Drag Scrubbers:** Integrated label-value pairs where dragging over the value changes the parameter horizontally, marked by a subtle cursor shift.

### Timeline Clips & Handles
- Base video clips appear as structured capsules with white or neutral backing, bordered by `#E4E4E9`, displaying mini SVG waveform/filmstrip ribbons inside.
- Clip handles are 6px vertical bars on clip edges tinted `#635BFF` only on cursor hover or active multi-selection.

### Chips & Badges
- **AI Status Chips:** Compact capsules with 2px horizontal padding, `#F5F3FF` lavender tint, `#7C3AED` text, and an animated 6px pulse dot indicating active transcription or clip synthesis.
- **Metadata Badges:** Subdued `#F4F4F7` background with `#71717A` typography at 11px.

### Checkboxes & Switches
- **Checkboxes:** 14x14px rounded squares (radius: 3px) with 1px stroke. Checked state is solid `#635BFF` with white check icon.
- **Switches:** Clean 28x16px track in neutral gray `#E4E4E9` with an 12px white circular thumb. Active state fills with `#635BFF`.

### Empty States & Drop Zones
- Constructed with light dashed hairline borders (`1.5px dashed #D1D1DB`) surrounding pure white islands. Subtle periwinkle wash highlights the interior when a media file is dragged over the canvas. Typography is centered with clear primary action triggers.