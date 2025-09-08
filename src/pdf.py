import re
import pdfplumber

H_TO_GHS = {
    "H200": ["GHS01"], "H201": ["GHS01"], "H202": ["GHS01"], "H203": ["GHS01"],
    "H220": ["GHS02"], "H221": ["GHS02"], "H222": ["GHS02"], "H225": ["GHS02"], "H226": ["GHS02"],
    "H228": ["GHS02"],
    "H301": ["GHS06"], "H311": ["GHS06"], "H331": ["GHS06"],
    "H302": ["GHS07"], "H312": ["GHS07"], "H315": ["GHS07"], "H319": ["GHS07"], "H335": ["GHS07"], "H336": ["GHS07"],
    "H317": ["GHS07", "GHS08"],  # sensitizer, may overlap with health hazard
    "H314": ["GHS05"], "H318": ["GHS05"],
    "H350": ["GHS08"], "H360": ["GHS08"], "H370": ["GHS08"], "H372": ["GHS08"],
    "H400": ["GHS09"], "H410": ["GHS09"], "H411": ["GHS09"], "H412": ["GHS09"]
}

def extract_text_chain(pdf_path: str) -> str:
    """Extract and normalize text from SDS PDF."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text(layout=True) or "")
    raw_text = "\n".join(text_parts)

    # Clean text
    text = re.sub(r"-\n", "", raw_text)  # fix split words
    text = re.sub(r"\n+", "\n", text)  # collapse newlines
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


def split_sections_fallback(text: str) -> dict:
    """Split SDS into sections by 'ABSCHNITT x:' headers."""
    sections = {}
    matches = list(re.finditer(r"\*?\s*ABSCHNITT\s+(\d+):", text, flags=re.I))
    for i, match in enumerate(matches):
        sec_num = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[sec_num] = text[start:end].strip()
    return sections


def parse_sds_fallback(text: str) -> dict:
    """Extract key SDS info by EU norm fields."""
    data = {
        "handelsname": None,
        "manufacturer": None,
        "h_statements": [],
        "un_number": None,
        "pictograms": [],
        "sds_date": None
    }

    # Datum global suchen (vor Abschnitt 1 möglich)
    date_match = re.search(
        r"(?:Überarbeitet am|Druckdatum|Bearbeitungsdatum|Erstelldatum|Stand|Revisionsdatum)\s*:?\s*([\d]{1,2}[.\-/][\d]{1,2}[.\-/][\d]{4})",
        text,
        flags=re.I
    )
    if date_match:
        data["sds_date"] = date_match.group(1).strip()

    sections = split_sections(text)

    # Abschnitt 1
    if "1" in sections:
        # Handelsname / Artikelname
        handels_match = re.search(r"(?:Handelsname|Artikelname):\s*(.*)", sections["1"], flags=re.I)
        if handels_match:
            data["handelsname"] = handels_match.group(1).strip()

        # Hersteller / Lieferant: alles nach "Lieferant:"
        manuf_match = re.search(r"Lieferant:\s*(.*?)\n", sections["1"], flags=re.I)
        if manuf_match:
            data["manufacturer"] = manuf_match.group(1).strip()

    # Abschnitt 2 – H-Sätze + Piktogramme
    if "2" in sections:
        # H-Sätze können als "H317" oder "(H317)" vorkommen
        h_matches = re.findall(r"\bH\d{3}\b", sections["2"])
        data["h_statements"] = sorted(set(h_matches))

        # Piktogramme GHSxx
        ghs_matches = re.findall(r"\bGHS\d{2}\b", sections["2"])
        data["pictograms"] = sorted(set(ghs_matches))

    # Abschnitt 14 – UN-Nummer
    if "14" in sections:
        un_match = re.search(r"\bUN\s*\d{1,4}\b", sections["14"], flags=re.I)
        if un_match:
            data["un_number"] = un_match.group(0).replace(" ", "")

    return data


def parse_sds_3m_format(pdf_path: str) -> dict:
    """Parse 3M/Meguiar's style SDS documents with different structure."""
    text = extract_text_chain(pdf_path)

    data = {
        "handelsname": None,
        "manufacturer": None,
        "h_statements": [],
        "un_number": None,
        "pictograms": [],
        "sds_date": None
    }

    # Extract date from header - look for "Überarbeitet am" pattern
    date_match = re.search(
        r"Überarbeitet am:\s*([\d]{1,2}[./][\d]{1,2}[./][\d]{4})",
        text,
        flags=re.I
    )
    if date_match:
        data["sds_date"] = date_match.group(1).strip()

    # Extract product name from document title (before the underscores)
    product_match = re.search(
        r"^([^\n_]+(?:Heavy Duty Cleaner|Remover|Cleaner)[^\n_]*)",
        text,
        flags=re.MULTILINE
    )
    if product_match:
        data["handelsname"] = re.sub(r'\s+', ' ', product_match.group(1).strip())

    # Split into sections
    sections = {}
    matches = list(re.finditer(r"ABSCHNITT\s+(\d+):\s*([^\n]*)", text, flags=re.I))

    for i, match in enumerate(matches):
        sec_num = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[sec_num] = text[start:end].strip()

    # Section 1 - Product identification
    if "1" in sections:
        section1 = sections["1"]

        # Look for manufacturer/supplier info - 3M format uses "Anschrift:"
        manuf_match = re.search(
            r"Anschrift:\s*([^,\n]+)",
            section1,
            flags=re.I
        )
        if manuf_match:
            data["manufacturer"] = manuf_match.group(1).strip()

    # Section 2 - Hazards
    if "2" in sections:
        section2 = sections["2"]

        # Look for H-statements in various formats
        h_matches = re.findall(r"\bH\d{3}\b", section2)
        data["h_statements"] = sorted(set(h_matches))

        # Look for GHS pictograms
        ghs_matches = re.findall(r"\bGHS\d{2}\b", section2)
        data["pictograms"] = sorted(set(ghs_matches))

    # Section 14 - Transport information
    if "14" in sections:
        section14 = sections["14"]

        # Check if it explicitly states "Kein Gefahrgut" or similar
        if re.search(r"Kein Gefahrgut|Not dangerous for transport", section14, flags=re.I):
            data["un_number"] = "Not classified"
        else:
            # Look for UN number
            un_match = re.search(r"\bUN\s*(\d{1,4})\b", section14, flags=re.I)
            if un_match:
                data["un_number"] = f"UN{un_match.group(1)}"

    return data

def parse_sds_basf_format(pdf_path: str) -> dict:
    """Parse BASF-style SDS (with EU 2020/878 format)."""
    text = extract_text_chain(pdf_path)

    data = {
        "handelsname": None,
        "manufacturer": None,
        "h_statements": [],
        "un_number": None,
        "pictograms": [],
        "sds_date": None
    }

    # Extract revision date
    date_match = re.search(r"Überarbeitet am:\s*([\d]{1,2}[./-][\d]{1,2}[./-][\d]{4})", text, flags=re.I)
    if date_match:
        data["sds_date"] = date_match.group(1).strip()

    # Split sections
    sections = split_sections(text)

    # Abschnitt 1 – Product and company identification
    if "1" in sections:
        section1 = sections["1"]

        handels_match = re.search(r"Handelsname\s*:?\s*(.+)", section1, flags=re.I)
        if handels_match:
            data["handelsname"] = re.sub(r"\s+", " ", handels_match.group(1).strip())

        manuf_match = re.search(r"Firma:\s*([^\n\r]+)", section1, flags=re.I)
        if manuf_match:
            data["manufacturer"] = manuf_match.group(1).strip()

    # Abschnitt 2 – Hazards
    if "2" in sections:
        section2 = sections["2"]

        # H-statements
        h_matches = re.findall(r"\bH\d{3}\b", section2)
        data["h_statements"] = sorted(set(h_matches))

        # Try to find explicit pictograms first
        ghs_matches = re.findall(r"\bGHS\d{2}\b", section2)
        if ghs_matches:
            data["pictograms"] = sorted(set(ghs_matches))
        else:
            # Derive pictograms from H-statements
            pictos = []
            for h in data["h_statements"]:
                pictos.extend(H_TO_GHS.get(h, []))
            data["pictograms"] = sorted(set(pictos))

    # Abschnitt 14 – Transport
    if "14" in sections:
        section14 = sections["14"]
        un_match = re.search(r"\bUN\s*(\d{1,4})\b", section14, flags=re.I)
        if un_match:
            data["un_number"] = f"UN{un_match.group(1)}"

    return data