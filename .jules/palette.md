## 2024-08-20 - [Add aria-label and title to icon-only buttons]
**Learning:** Found an accessibility issue pattern specific to this app's components, where multiple icon-only buttons (like those with emojis `▶`, `✕`, `🔍`, `🚀`, or SVGs like the hamburger menu) are missing both ARIA labels for screen readers and title attributes for visual tooltips.
**Action:** Ensure all new icon-only buttons include `aria-label` and `title` attributes.
