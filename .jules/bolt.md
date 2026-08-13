## 2024-08-13 - Dashboard Logs Performance
**Learning:** `get_detailed_logs` in `dashboard_server.py` processes thousands of log entries repeatedly, parsing the date string for every single one.
**Action:** Added lexical string comparison (`date_str[:10] >= cutoff_iso`) to skip full datetime parsing for logs older than the 12-day cutoff. Also optimized `parse_date` to favor `datetime.fromisoformat` fast paths.
