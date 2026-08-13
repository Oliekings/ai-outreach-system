## 2024-05-18 - Missing ARIA Labels on Icon-only Buttons
**Learning:** Found multiple icon-only buttons (`▶`, `✕`, `🔍`, `🚀`) missing `aria-label` and `title` attributes across the Vue application. This is a common inaccessible pattern that prevents screen readers from understanding button intent and deprives sighted users of helpful tooltips.
**Action:** When creating or reviewing UI code, especially for icon-heavy dashboards, always enforce that any button without visible text must have an `aria-label` attribute (for screen readers) and a `title` attribute (for tooltips on hover).
