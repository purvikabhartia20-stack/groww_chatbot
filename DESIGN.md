---
name: Groww Brand Identity
colors:
  surface: '#f3fbf5'
  surface-dim: '#d4dcd6'
  surface-bright: '#f3fbf5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#edf6ef'
  surface-container: '#e8f0e9'
  surface-container-high: '#e2eae4'
  surface-container-highest: '#dce5de'
  on-surface: '#161d19'
  on-surface-variant: '#3c4a43'
  inverse-surface: '#2a322e'
  inverse-on-surface: '#eaf3ec'
  outline: '#6b7b72'
  outline-variant: '#bacac1'
  surface-tint: '#006c4f'
  primary: '#006c4f'
  on-primary: '#ffffff'
  primary-container: '#00d09c'
  on-primary-container: '#00533c'
  inverse-primary: '#2fe0aa'
  secondary: '#3247e2'
  on-secondary: '#ffffff'
  secondary-container: '#4f63fb'
  on-secondary-container: '#fffbff'
  tertiary: '#934b07'
  on-tertiary: '#ffffff'
  tertiary-container: '#ffa15b'
  on-tertiary-container: '#733800'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#59fdc5'
  primary-fixed-dim: '#2fe0aa'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#dfe0ff'
  secondary-fixed-dim: '#bcc2ff'
  on-secondary-fixed: '#000b62'
  on-secondary-fixed-variant: '#102bcd'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb785'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#713700'
  background: '#f3fbf5'
  on-background: '#161d19'
  surface-variant: '#dce5de'
typography:
  display-lg:
    fontFamily: DM Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: DM Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-md:
    fontFamily: DM Sans
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  body-lg:
    fontFamily: DM Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: DM Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: DM Sans
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: DM Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  container-margin-mobile: 16px
  container-margin-desktop: 48px
  gutter: 16px
---

## Brand & Style
The design system is engineered to evoke a sense of financial empowerment through a "Growth-First" aesthetic. The primary objective is to balance high-tech efficiency with approachable simplicity, catering to both novice investors and seasoned traders. 

The visual narrative relies on extreme clarity, generous whitespace, and purposeful use of the signature green to signify positive momentum and "active" states. By blending **Minimalism** with **Corporate Modern** standards, the UI maintains a professional demeanor while the pill-shaped elements and vibrant accents ensure it feels contemporary and accessible.

## Colors
This design system utilizes a dual-mode color strategy focused on readability and action-oriented signaling.

- **Primary Green (#00D09C):** Reserved exclusively for high-intent actions (CTAs), success states, and active navigation indicators. It represents growth and "go."
- **Secondary Purple (#5367FF):** Used for informational hierarchy, including text links, citations, and secondary data visualizations.
- **Backgrounds:**
  - **Light Mode:** Uses `#FFFFFF` for primary surfaces and `#F7F8FA` for grouping sections or inset backgrounds.
  - **Dark Mode:** Employs a deep navy `#1A1A2E` for the base layer, with `#16213E` used for cards and elevated components to maintain depth without pure black.
- **Borders:** Extremely subtle strokes (`#E8E8E8` / `#2A2A3E`) are used to define structure without introducing visual noise.

## Typography
The design system leverages **DM Sans** for its low-contrast, geometric precision which ensures legibility in data-heavy environments. 

- **Headlines:** Use Medium (500) or Bold (700) weights to establish clear content hierarchy.
- **Body Text:** Standardized at 16px for optimal readability. 
- **Labels:** Used for micro-copy, button labels, and captions.
- **Scaling:** On mobile devices, `display-lg` and `headline-lg` should scale down by 20% (e.g., 32px and 26px respectively) to ensure headlines do not wrap excessively on narrow viewports.

## Layout & Spacing
The layout follows a **fluid grid** system based on an 8px rhythmic scale. 

- **Mobile:** 4-column grid with 16px side margins and 16px gutters.
- **Desktop:** 12-column grid with a max-width of 1200px. Content should be centered with variable margins.
- **Vertical Spacing:** Elements are stacked using the 8px scale. Use `lg` (24px) for spacing between unrelated sections and `md` (16px) for spacing between related components within a section.

## Elevation & Depth
Elevation in this design system is achieved through **low-contrast outlines** supplemented by **ambient shadows**.

- **Level 0 (Base):** Flat background color.
- **Level 1 (Cards):** Uses a 1px border (`#E8E8E8` / `#2A2A3E`). On hover or interaction, apply a very soft, diffused shadow (0px 4px 20px rgba(0, 0, 0, 0.04)) to indicate lift.
- **Level 2 (Modals/Overlays):** Significant shadow diffusion (0px 12px 32px rgba(0, 0, 0, 0.08)) to separate from the background. 
- **Dark Mode Elevation:** Depth is communicated primarily through color stepping (moving from `#1A1A2E` to `#16213E`) rather than heavy shadows, ensuring the interface remains crisp.

## Shapes
The shape language is defined by the **Pill-shape (Rounded-full)** philosophy for interactive elements, contrasted by moderately rounded containers.

- **Interactive Elements:** Buttons, Chips, and Tags must use `rounded-full` (pill shape).
- **Structural Elements:** Cards, input fields, and modals use `rounded-lg` (1rem / 16px) to maintain a modern, friendly structure without becoming overly playful.
- **Iconography:** Use rounded terminals and consistent stroke weights (1.5px or 2px) to match the typography's softness.

## Components
- **Buttons:** Primary buttons are pill-shaped with `#00D09C` background and white text. Secondary buttons use a transparent background with a 1px border of the Primary Green.
- **Cards:** White or dark navy background with subtle 1px borders. Padding should be generous (`24px`).
- **Input Fields:** 1px border, `rounded-lg` corners. On focus, the border transitions to the Primary Green with a subtle 2px outer glow.
- **Chips/Filters:** Pill-shaped. Unselected states use the secondary background color; selected states use a light tint of Primary Green with dark green text.
- **Lists:** Clean rows separated by thin horizontal rules. Active items are indicated by a vertical bar of Primary Green on the far left.
- **Navigation:** Bottom navigation (mobile) or top navigation (desktop) uses Primary Green for active icons and text labels to indicate the current view.