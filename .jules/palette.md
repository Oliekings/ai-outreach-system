## 2024-05-20 - Icon-only buttons lacking ARIA labels
**Learning:** Icon-only buttons in the application UI (like close icons '✕', dry-run icons '🔍', and task run icons '▶') were frequently missing `aria-label` attributes for screen reader accessibility and `title` attributes for tooltips, relying solely on visual representation.
**Action:** Added explicit `aria-label` and `title` attributes to all icon-only buttons to conform to accessibility standards and improve UX.
