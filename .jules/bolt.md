## 2024-08-14 - Time Series Optimization with Hash Maps
**Learning:** In python backend, calculating time series statistics by nesting a date loop over an array of logs results in O(N * days) time complexity, which is highly inefficient for large logs.
**Action:** Always map log entries into a fast O(1) hash map lookup table (grouping by date) in a single pass O(N) before constructing the time series data. This avoids iterating over the same datasets repeatedly and improves the speed of analytical reporting significantly.
