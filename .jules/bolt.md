## 2024-08-19 - [O(N*R) Disk I/O Bottleneck Avoidance]
**Learning:** Calling file-reading functions (`json.load(f)`) inside a processing loop (like matching replies to leads) results in repetitive, expensive disk I/O, converting an operation into an O(N*R) bottleneck where N is leads and R is replies.
**Action:** When searching or filtering datasets inside a loop, load the entire dataset into memory once before the loop begins, and pass the loaded array/dictionary into lookup functions.
