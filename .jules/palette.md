## 2024-03-24 - Icon-Only Button Accessibility Pattern
**Learning:** Found a recurring pattern in the design system where icon-only action buttons (e.g., ▶ Run task, ✕ Close modal, 🔍 Dry run, 🚀 Launch) were missing `aria-label` and `title` attributes. This prevented screen readers from parsing their purpose and deprived mouse users of hover tooltips explaining the action.
**Action:** Always verify that every icon-only `<button>` includes both `aria-label` (for a11y) and `title` (for tooltips) before submitting UX enhancements involving interactive elements.
