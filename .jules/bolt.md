## 2026-08-20 - Loop Fusion in Lead Metrics
**Learning:** This codebase relies entirely on JSON lists loaded directly into memory rather than DB queries, causing severe CPU load loops when analyzing large datasets. Running many list comprehensions side-by-side acts like `O(10N)` behavior.
**Action:** Always practice loop fusion when aggregating over flat files/JSON lists — consolidate multiple passes into a single `for item in items:` loop.
