from pathlib import Path
import os
import re

import src.pdf
import src.excel

def _extract_h_set(sds):
    """
    Extract H-Sätze as a set from the parsed SDS object.

    Expected schema:
    {
        "handelsname": str | None,
        "manufacturer": str | None,
        "h_statements": list[str],
        "un_number": str | None,
        "pictograms": list[str],
        "sds_date": str | None
    }
    """
    if not isinstance(sds, dict):
        return set()
    values = sds.get("h_statements", [])
    if isinstance(values, (list, set, tuple)):
        return {str(x).strip() for x in values if str(x).strip()}
    if isinstance(values, str):
        parts = [p.strip() for p in re.split(r"[;,]", values)]
        return {p for p in parts if p}
    return set()

def _set_handels_name(sds, name: str):
    """
    Set the product trade name on the SDS object using the 'handelsname' key.
    """
    if isinstance(sds, dict):
        sds["handelsname"] = name

# ... existing code ...
def run_cli(path: str, excel_path: str):
    root = Path(path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Path does not exist or is not a directory: {root}")

    for dirpath, dirnames, _ in os.walk(root):
        parent_name = Path(dirpath).name

        for child_name in dirnames:
            child_path = Path(dirpath) / child_name
            try:
                all_entries = []
                for entry in child_path.iterdir():
                    if entry.is_file() and entry.suffix.lower() == ".pdf":
                        sds = src.pdf.parse_sds(os.fspath(entry))
                        h_set = _extract_h_set(sds)
                        # keep (filename, h_set, sds) so we can modify or collect later
                        all_entries.append((entry.name, h_set, sds))

                # Only proceed if we found PDFs
                if not all_entries:
                    continue

                # Compare H-Sätze across entries in this child directory
                unique_h_sets = {frozenset(h) for _, h, _ in all_entries}

                # Case 1: every file has a different (unique) H-set within this child dir
                if len(unique_h_sets) == 1:
                    first_sds = all_entries[0][2]
                    _set_handels_name(first_sds, child_name)
                    print(f"Set handels_name of first SDS in '{parent_name}/{child_name}' to '{child_name}'.")

                    sds_excel_list = src.excel.convert_data_to_list(first_sds)
                    src.excel.open_and_write_excel(excel_path, sds_excel_list)

                # Case 2: otherwise, create a new list of SDS objects (they share some H-sets)
                else:
                    # Build a list that only contains SDS whose H-Sätze are unique within this child directory
                    counts = {}
                    for _, h, _ in all_entries:
                        key = frozenset(h)
                        counts[key] = counts.get(key, 0) + 1
                    sds_list = [s for _, h, s in all_entries if counts[frozenset(h)] == 1]

                    for entry in sds_list:
                        sds_excel_list = src.excel.convert_data_to_list(entry)
                        src.excel.open_and_write_excel(excel_path, sds_excel_list)


            except PermissionError:
                print(f"Permission denied: {parent_name})")
                continue
