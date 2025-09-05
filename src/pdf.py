import re
import pdfplumber

def extract_text_chain(pdf_path: str) -> str:
    """Extract and normalize text from SDS PDF."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text(layout=True) or "")
    raw_text = "\n".join(text_parts)

    # Clean text
    text = re.sub(r"-\n", "", raw_text)  # fix split words
    text = re.sub(r"\n+", "\n", text)    # collapse newlines
    text = re.sub(r"[ \t]+", " ", text)  # normalize spaces
    return text.strip()


def split_sections(text: str) -> dict:
    """Split SDS into sections by 'ABSCHNITT x:' headers."""
    sections = {}
    matches = list(re.finditer(r"\*?\s*ABSCHNITT\s+(\d+):\s*(.*)", text, flags=re.I))
    for i, match in enumerate(matches):
        sec_num = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[sec_num] = text[start:end].strip()
    return sections


def parse_sds(text: str) -> dict:
    """Extract key SDS info by EU norm fields."""
    data = {
        "handelsname": None,
        "manufacturer": None,
        "h_statements": [],
        "un_number": None,
        "pictograms": [],
        "sds_date": None
    }

    # Datum aus dem gesamten Dokument suchen (vor Abschnitt 1)
    date_match = re.search(
        r"(?:Überarbeitet am|Druckdatum|Bearbeitungsdatum|Erstelldatum|Stand|Revisionsdatum)\s*:?\s*([\d]{1,2}[.\-/][\d]{1,2}[.\-/][\d]{4})",
        text,
        flags=re.I
    )
    if date_match:
        data["sds_date"] = date_match.group(1).strip()

    # Abschnitte extrahieren
    sections = split_sections(text)

    # Abschnitt 1
    if "1" in sections:
        # Abschnitt 1.1 – Handelsname (accepts "Handelsname" or "Artikelname")
        handels_match = re.search(r"(?:Handelsname|Artikelname):\s*(.*)", sections["1"], flags=re.I)
        data["handelsname"] = handels_match.group(1).strip() if handels_match else None

        # Abschnitt 1.3 – Hersteller
        manuf_match = re.search(r"Hersteller/Lieferant:\s*([^\n\r]+)", sections["1"], flags=re.I)
        data["manufacturer"] = manuf_match.group(1).strip() if manuf_match else None

    # Abschnitt 2.1/2.2 – H-Sätze + Piktogramme
    if "2" in sections:
        h_matches = re.findall(r"\bH\d{3}", sections["2"])
        data["h_statements"] = sorted(set(h_matches))

        ghs_matches = re.findall(r"\bGHS\d{2}", sections["2"])
        data["pictograms"] = sorted(set(ghs_matches))

    # Abschnitt 14 – UN-Nummern
    if "14" in sections:
        un_match = re.search(r"(\bUN\s*\d{1,4})", sections["14"], flags=re.I)
        data["un_number"] = un_match.group(1).strip().replace(" ", "") if un_match else None


    return data
