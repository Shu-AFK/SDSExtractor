from openpyxl import Workbook, load_workbook
import os

def open_and_write_excel(filepath: str, row_data: list, sheet_name="Gefahrstoffkataster"):
    """
    Append a row to an Excel file. Creates file if it does not exist.
    :param filepath: path to the .xlsx file
    :param row_data: list of values to append
    :param sheet_name: name of the sheet
    """

    if os.path.exists(filepath):
        wb = load_workbook(filepath)
        if sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
        else:
            ws = wb.create_sheet(sheet_name)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        ws.append(["Produktname / Handelsname", "Hersteller", "UN-Nr.", "Gefahren (H-Sätze)", "Piktogramme", "Lagerort", "Menge im Lager", "Besonderheiten", "Stand"])


    ws.append(row_data)
    wb.save(filepath)

def convert_data_to_list(data: dict) -> list:
    """
    Converts the SDS data to a list for writing to Excel.
    :param data: the dict of SDS data
    :return: list of values
    """

    return [
        data["handelsname"],
        data["manufacturer"],
        data["un_number"],
        ", ".join(data["h_statements"]),
        ", ".join(data["pictograms"]),
        "",
        "",
        "",
        data["sds_date"],
    ]