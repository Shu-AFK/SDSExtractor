from pathlib import Path
import os
import re

import src.pdf
import src.excel

def _extract_h_set(sds):
    """
    Extract H-Sätze as a set from the parsed SDS object.
    If h_statements is an empty list (or empty iterable), return an empty set.
    """
    if not isinstance(sds, dict):
        return set()

    values = sds.get("h_statements", [])

    # If it's explicitly an empty list (or any empty iterable), exclude by returning an empty set
    if isinstance(values, (list, set, tuple)) and not values:
        return set()

    if isinstance(values, (list, set, tuple)):
        return {str(x).strip() for x in values if x is not None and str(x).strip()}

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

def _build_handelsname_with_first_dir(root: Path, child_dir: Path, leaf_name: str) -> str:
    """
    Build '{firstname} {sub} {leaf}' where:
      - firstname: the first directory under root (e.g., 'Auto-K')
      - sub: the immediate parent of 'leaf' under that first directory (if present)
      - leaf: the provided leaf_name (e.g., current child dir)
    """
    rel_parts = child_dir.relative_to(root).parts
    firstname = rel_parts[0] if rel_parts else leaf_name
    sub = rel_parts[-2] if len(rel_parts) >= 2 else ""

    parts = [firstname]
    if sub and sub != firstname and sub != leaf_name:
        parts.append(sub)
    parts.append(leaf_name)
    return " ".join(parts)


def is_missing(key, val):
    if key in ("h_statements", "pictograms"):
        return val is None or (isinstance(val, (list, tuple, set)) and len(val) == 0)
        # string-like fields
    return val is None or (isinstance(val, str) and val.strip() == "")


def _report_none_fields(sds: dict, file_path: Path) -> None:
    """
    Print a warning if some or all expected fields in the SDS are missing.
    Missing means:
      - None
      - empty string (after strip)
      - empty iterable for list-like fields
    """
    expected_keys = ["handelsname", "manufacturer", "h_statements", "un_number", "pictograms", "sds_date"]
    none_fields = [k for k in expected_keys if is_missing(k, sds.get(k))]

    if len(none_fields) == len(expected_keys):
        print(f"[WARN] All SDS fields are missing for: {file_path}")
    elif none_fields:
        print(f"[WARN] Some SDS fields are missing for: {file_path} -> {', '.join(none_fields)}")

def _should_write_sds(sds: dict, file_path: Path) -> bool:
    """
    Allow writing if:
      - all required fields are present, OR
      - the only missing (None) fields are 'un_number' and/or 'handelsname'.
    """
    expected_keys = ["handelsname", "manufacturer", "h_statements", "un_number", "pictograms", "sds_date"]
    none_fields = [k for k in expected_keys if is_missing(k, sds.get(k))]

    if not none_fields:
        return True

    allowed_missing = {"un_number", "handelsname"}
    if set(none_fields).issubset(allowed_missing):
        # Only UN number and/or handelsname missing -> still write
        return True

    # Otherwise, skip and notify
    print(f"[SKIP] Not writing '{file_path}' due to missing fields (None): {', '.join(none_fields)}")
    return False

def run_cli(path: str, excel_path: str, use_fallback: bool):
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
                        text = src.pdf.extract_text_chain(entry.as_posix())

                        # --- Parser auswählen ---
                        if use_fallback:
                            sds = src.pdf.parse_sds_fallback(text)
                        else:
                            sds = src.pdf.parse_sds(text)

                        _report_none_fields(sds, entry)
                        h_set = _extract_h_set(sds)

                        all_entries.append((entry.name, h_set, sds))

                if not all_entries:
                    continue

                unique_h_sets = {frozenset(h) for _, h, _ in all_entries}

                if len(unique_h_sets) == 1:
                    first_sds = all_entries[0][2]
                    handelsname = _build_handelsname_with_first_dir(root, child_path, child_name)
                    _set_handels_name(first_sds, handelsname)

                    if _should_write_sds(first_sds, child_path):
                        sds_excel_list = src.excel.convert_data_to_list(first_sds)
                        src.excel.open_and_write_excel(excel_path, sds_excel_list)

                else:
                    counts = {}
                    for _, h, _ in all_entries:
                        key = frozenset(h)
                        counts[key] = counts.get(key, 0) + 1
                    sds_list = [s for _, h, s in all_entries if counts[frozenset(h)] == 1]

                    handelsname = _build_handelsname_with_first_dir(root, child_path, child_name)
                    for sds_obj in sds_list:
                        _set_handels_name(sds_obj, handelsname)
                        if _should_write_sds(sds_obj, child_path):
                            sds_excel_list = src.excel.convert_data_to_list(sds_obj)
                            src.excel.open_and_write_excel(excel_path, sds_excel_list)

            except PermissionError:
                print(f"Permission denied: {parent_name}")
                continue