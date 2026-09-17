---
name: ScioBraille Light
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1c1b1b'
  on-surface-variant: '#474552'
  inverse-surface: '#313030'
  inverse-on-surface: '#f3f0ef'
  outline: '#787584'
  outline-variant: '#c8c4d4'
  surface-tint: '#584fb9'
  primary: '#584fb9'
  on-primary: '#ffffff'
  primary-container: '#7169d4'
  on-primary-container: '#030024'
  inverse-primary: '#c5c0ff'
  secondary: '#8b4f31'
  on-secondary: '#ffffff'
  secondary-container: '#fdaf8a'
  on-secondary-container: '#784023'
  tertiary: '#5d5c5a'
  on-tertiary: '#ffffff'
  tertiary-container: '#757472'
  on-tertiary-container: '#f9ffeb'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e3dfff'
  primary-fixed-dim: '#c5c0ff'
  on-primary-fixed: '#140067'
  on-primary-fixed-variant: '#4036a0'
  secondary-fixed: '#ffdbcc'
  secondary-fixed-dim: '#ffb693'
  on-secondary-fixed: '#351000'
  on-secondary-fixed-variant: '#6e381c'
  tertiary-fixed: '#e5e2df'
  tertiary-fixed-dim: '#c8c6c3'
  on-tertiary-fixed: '#1c1c1a'
  on-tertiary-fixed-variant: '#474745'
  background: '#fcf9f8'
  on-background: '#1c1b1b'
  surface-variant: '#e5e2e1'
typography:
  headline-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 48px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 32px
    fontWeight: '800'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.0'
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 8px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
  max-width: 1280px
---

## Brand & Style

The design system is engineered for a sophisticated educational and assistive technology environment. It prioritizes clarity, high legibility, and a sense of calm intelligence. The brand personality is "Empowering Clarity"—fusing the reliability of academic tools with the approachability of modern assistive software.

The aesthetic follows a **High-Contrast / Modern** direction. It utilizes generous whitespace, crisp structural lines, and purposeful color blocking to ensure that users with varying visual needs can navigate intuitively. The style avoids unnecessary decoration, focusing instead on "functional elegance" where depth is communicated through tonal shifts rather than complex skeuomorphic effects.

## Colors

The palette is anchored by a deep, authoritative purple (#7169D4) used for primary actions and brand presence. To add warmth and character, a muted terracotta (#D48C69) is introduced as the secondary accent. This color provides a sophisticated contrast to the purple, used specifically for highlighting key instructional containers, secondary interactive elements, and UI callouts.

A warm neutral (#F4F1EE) serves as the foundation for page surfaces, reducing the harshness of pure white while maintaining high contrast against the dark charcoal text (#1A1A1A). This combination ensures WCAG AAA compliance for text legibility while providing a distinct, rhythmic visual character.

## Typography

This design system utilizes **Atkinson Hyperlegible Next** as the core typeface across all levels. This font is specifically designed for low-vision users, focusing on character differentiation to increase readability. **JetBrains Mono** is utilized for technical labels and data-heavy strings to provide a clear, systematic contrast to the humanist body text.

Headlines should be set with tight leading and bold weights to create a strong visual hierarchy. Body text employs generous line-height (1.6) to prevent "crowding" and improve the reading experience for users with visual fatigue.

## Layout & Spacing

The design system employs a **fixed grid** approach on desktop and a **fluid grid** on mobile. The layout is structured around an 8px base unit to ensure consistent vertical rhythm.

- **Desktop:** 12-column grid with a 1280px max-width, 24px gutters, and 64px side margins.
- **Tablet:** 8-column grid with 24px gutters and 32px side margins.
- **Mobile:** 4-column fluid grid with 16px gutters and 16px side margins.

Containers should prioritize vertical stacking to maintain a clear reading path. Large instructional blocks should use the full width of the container to prevent eye-strain from excessive line-jumping.

## Elevation & Depth

Visual hierarchy is achieved through **Tonal Layers** and **Bold Outlines** rather than traditional shadows. 

The background surface is the lowest layer. Content is housed in containers with a slightly lighter or darker background than the base. Interactive elements use a 2px solid border in the Primary or Secondary color to define their hit area. 

Elevation is indicated by color intensity:
- **Level 0 (Surface):** #F4F1EE
- **Level 1 (Card):** #FFFFFF with a 1px #E0DBD6 border.
- **Level 2 (Active/Hover):** 2px solid border using #7169D4.
- **Level 3 (Highlight):** Background fill using the secondary terracotta at 10-15% opacity.

## Shapes

The shape language is **Soft** (Level 1). This choice provides a modern, friendly feel while maintaining the structural integrity required for an educational tool. 

- **Standard Buttons & Inputs:** 0.25rem (4px) corner radius.
- **Cards & Modals:** 0.75rem (12px) corner radius.
- **Highlight Badges:** 0.5rem (8px) corner radius.

This subtle rounding ensures that elements remain clearly defined as distinct units of information without appearing overly "bubbly" or informal.

## Components

### Buttons
- **Primary:** Solid #7169D4 background with white text. No shadow; use a 2px inset white border on focus.
- **Secondary:** Transparent background with #D48C69 2px solid border and #D48C69 text.
- **Ghost:** No border, #7169D4 text, becomes light gray on hover.

### Input Fields
- Use a 2px solid border in #E0DBD6. On focus, the border changes to #7169D4. 
- Labels are always persistent above the field in **label-mono** style for maximum clarity.

### Cards & Highlights
- **Instructional Containers:** Use the secondary terracotta (#D48C69) at 10% opacity for the background with a 4px left-accent border in solid terracotta.
- **Standard Cards:** White background with 1px neutral border.

### Interactive Controls
- **Checkboxes/Radios:** Large 24px x 24px touch targets. Use the primary purple for the "selected" state.
- **Chips:** Used for filtering; these use the secondary color at low opacity for an "unselected" state and solid for "selected."

### Braille Display Indicators
- Specific UI components representing Braille cells should use high-contrast circles with the primary purple representing "raised" dots and a light gray for "flat" dots.