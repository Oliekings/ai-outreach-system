🎯 **What:** The code health issue addressed
The `audit_all_leads` function in `intelligence/general_auditor.py` was overly long and complex, handling loading previous audits, stealth browser context setup, and the complete audit logic for each lead all in one place.

💡 **Why:** How this improves maintainability
By extracting sub-phases into `_load_existing_audits`, `_setup_stealth_context`, and `_audit_single_lead` helper functions, the main `audit_all_leads` function becomes much shorter, easier to read, and easier to modify in the future without unintended side effects.

✅ **Verification:** How you confirmed the change is safe
- Formatted with `black` to ensure consistent code styling.
- Compiled with `python3 -m py_compile`.
- Ran the full test suite via `pytest tests/`, and all tests passed.
- Manually reviewed the diff to confirm all original logic and behavior remain intact.

✨ **Result:** The improvement achieved
A drastically simplified `audit_all_leads` function and clearly separated components for lead auditing.
