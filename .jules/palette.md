## 2024-05-15 - Icon-only buttons accessibility requirements
**Learning:** Icon-only buttons (like ✕, ▶, 🔍, 🚀, or SVG menus) in Vue templates lack context for screen readers and miss visual hover hints for sighted users if left alone.
**Action:** Always include an `aria-label` attribute to provide context to screen readers, and a `title` attribute to show a native hover tooltip on desktop devices. Both are required for complete accessibility of icon-only buttons.
