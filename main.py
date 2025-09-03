from src.gui import App

"""
if __name__ == "__main__":
    pdf_path = "D:\\SDBREZ142_-_Aerosol_Zinkstaub_dunkel_DE.pdf"

    text = extract_text_chain(pdf_path)

    data = parse_sds(text)

    print("Handelsname:", data["handelsname"])
    print("Hersteller:", data["manufacturer"])
    print("H-Sätze:", data["h_statements"])
    print("CAS Nummern:", data["cas_numbers"])
    print("Pictogramme:", data["pictograms"])
"""

if __name__ == "__main__":
    App().mainloop()
