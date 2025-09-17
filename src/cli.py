from pathlib import Path
import os
import re

import src.pdf
import src.excel


def _extract_h_set(sds):
    if not isinstance(sds, dict):
        return set()

    values = sds.get("h_statements", [])

    if isinstance(values, (list, set, tuple)) and not values:
        return set()

    if isinstance(values, (list, set, tuple)):
        return {str(x).strip() for x in values if x is not None and str(x).strip()}

    if isinstance(values, str):
        parts = [p.strip() for p in re.split(r"[;,]", values)]
        return {p for p in parts if p}

    return set()


def _set_handels_name(sds, name: str):
    if isinstance(sds, dict):
        sds["handelsname"] = name


def _build_handelsname_with_first_dir(root: Path, child_dir: Path, leaf_name: str) -> str:
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
    return val is None or (isinstance(val, str) and val.strip() == "")


def _report_none_fields(sds: dict, file_path: Path) -> None:
    expected_keys = ["handelsname", "manufacturer", "h_statements", "un_number", "pictograms", "sds_date"]
    none_fields = [k for k in expected_keys if is_missing(k, sds.get(k))]

    if len(none_fields) == len(expected_keys):
        print(f"[WARN] All SDS fields are missing for: {file_path}")
    elif none_fields:
        print(f"[WARN] Some SDS fields are missing for: {file_path} -> {', '.join(none_fields)}")


def _should_write_sds(sds: dict, file_path: Path) -> bool:
    expected_keys = ["handelsname", "manufacturer", "h_statements", "un_number", "pictograms", "sds_date"]
    none_fields = [k for k in expected_keys if is_missing(k, sds.get(k))]

    if not none_fields:
        return True

    allowed_missing = {"un_number", "handelsname", "pictograms", "sds_date"}
    if set(none_fields).issubset(allowed_missing):
        return True

    print(f"[SKIP] Not writing '{file_path}' due to missing fields (None): {', '.join(none_fields)}")
    return False


def run_cli(path: str, excel_path: str, use_fallback: bool, use_3mf: bool, use_basf: bool, use_lechler: bool,
            insert_row: int | None = None):
    """
    Main CLI runner. Walks directories, parses SDS PDFs, and writes them into Excel.

    Args:
        path: Root folder with PDFs
        excel_path: Path to Excel file
        use_fallback: Use fallback parser
        use_3mf: Use 3M parser
        use_basf: Use BASF parser
        insert_row: If given, insert into this row instead of appending
    """
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
                        if use_3mf:
                            sds = src.pdf.parse_sds_3m_format(entry.as_posix())
                        elif use_basf:
                            sds = src.pdf.parse_sds_basf_format(entry.as_posix())
                        elif use_lechler:
                            sds = src.pdf.parse_sds_lechler_format(entry.as_posix())
                            sds["manufacturer"] = "Lechler Coatings GmbH"
                        elif use_fallback:
                            text = src.pdf.extract_text_chain(entry.as_posix())
                            sds = src.pdf.parse_sds_fallback(text)
                        else:
                            text = src.pdf.extract_text_chain(entry.as_posix())
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
                        src.excel.open_and_write_excel(
                            excel_path, sds_excel_list, insert_row=insert_row
                        )

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
                            src.excel.open_and_write_excel(
                                excel_path, sds_excel_list, insert_row=insert_row
                            )

            except PermissionError:
                print(f"Permission denied: {parent_name}")
                continue
