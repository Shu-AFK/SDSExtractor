import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image, ImageTk

from src.pdf import extract_text_chain, parse_sds
from src.excel import open_and_write_excel
import src.image


class RowWidget:
    def __init__(self, parent, row_index, all_rows):
        self.parent = parent
        self.row_index = row_index
        self.all_rows = all_rows

        self.data = {
            "handelsname": "",
            "manufacturer": "",
            "h_statements": [],
            "un_number": "",
            "pictograms": [],
            "sds_date": "",
        }

        self.frame = tk.Frame(parent, padx=6, pady=4, borderwidth=1, relief="groove")
        tk.Label(self.frame, text=f"Zeile {row_index + 1}:").grid(row=0, column=0, padx=(2, 8), sticky="w")

        tk.Label(self.frame, text="Handelsname:").grid(row=0, column=1, sticky="e")
        self.handelsname_var = tk.StringVar()
        self.handelsname_entry = tk.Entry(self.frame, textvariable=self.handelsname_var, width=40, state="disabled")
        self.handelsname_entry.grid(row=0, column=2, padx=6, sticky="we")

        self.load_btn = tk.Button(self.frame, text="PDF(s) laden", command=self.load_pdfs)
        self.load_btn.grid(row=0, column=3, padx=4, sticky="w")

        self.frame.grid_columnconfigure(2, weight=1)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def load_pdfs(self):
        file_paths = filedialog.askopenfilenames(
            title="Sicherheitsdatenblatt PDF(s) auswählen",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not file_paths:
            return

        parsed_list = []
        for pdf_path in file_paths:
            try:
                text = extract_text_chain(pdf_path)
                parsed = parse_sds(text)
                parsed_list.append(parsed)
            except Exception as e:
                messagebox.showerror("Fehler beim Lesen", f"Fehler beim Verarbeiten von:\n{pdf_path}\n\n{e}")

        # Gruppieren nach einzigartiger Kombination von H-Sätzen + Piktogrammen
        unique_groups = {}
        for parsed in parsed_list:
            key = (tuple(sorted(parsed.get("h_statements", []))),
                   tuple(sorted(parsed.get("pictograms", []))))
            if key not in unique_groups:
                unique_groups[key] = parsed

        rows_to_create = []
        for parsed in unique_groups.values():
            data = {
                "handelsname": parsed.get("handelsname") or "",
                "manufacturer": parsed.get("manufacturer") or "",
                "h_statements": sorted(parsed.get("h_statements", [])),
                "un_number": sorted(parsed.get("un_number", [])),
                "pictograms": sorted(parsed.get("pictograms", [])),
                "sds_date": parsed.get("sds_date") or "",
            }
            rows_to_create.append(data)

        # Erste Zeile befüllen
        first = rows_to_create.pop(0)
        self.data.update(first)
        self.handelsname_var.set(self.data["handelsname"])
        self.handelsname_entry.config(state="normal")
        self.handelsname_entry.focus_set()

        # Weitere Zeilen hinzufügen, wenn es unterschiedliche Gruppen gibt
        for data in rows_to_create:
            new_row = RowWidget(self.parent, len(self.all_rows), self.all_rows)
            new_row.data.update(data)
            new_row.handelsname_var.set(data["handelsname"])
            new_row.handelsname_entry.config(state="normal")
            new_row.grid(row=len(self.all_rows), column=0, sticky="we", pady=3)
            self.all_rows.append(new_row)

    def get_row_for_excel(self):
        self.data["handelsname"] = self.handelsname_var.get().strip()
        return [
            self.data["handelsname"],
            self.data["manufacturer"] or "",
            ", ".join(self.data["un_number"]) or "",
            "; ".join(self.data["h_statements"]) or "",
            ", ".join(self.data["pictograms"]) or "",
            "",  # Lagerort
            "",  # Menge im Lager
            "",  # Besonderheiten
            self.data["sds_date"] or "",
        ]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SDS → Excel")
        self.geometry("800x420")

        icon_data = base64.b64decode(src.image.icon_base64)
        img = Image.open(BytesIO(icon_data))
        icon = ImageTk.PhotoImage(img)

        self.iconphoto(False, icon)

        top = tk.Frame(self, padx=10, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="Excel-Datei:").pack(side="left")
        self.excel_path_var = tk.StringVar()
        self.excel_entry = tk.Entry(top, textvariable=self.excel_path_var)
        self.excel_entry.pack(side="left", expand=True, fill="x", padx=6)
        tk.Button(top, text="Durchsuchen...", command=self.choose_excel).pack(side="left")

        mid = tk.Frame(self, padx=10, pady=4)
        mid.pack(fill="both", expand=True)

        ctrl_bar = tk.Frame(mid)
        ctrl_bar.pack(fill="x", pady=(0, 6))
        tk.Button(ctrl_bar, text="Zeile hinzufügen", command=self.add_row).pack(side="left")

        self.rows_container = ScrollableFrame(mid)
        self.rows_container.pack(fill="both", expand=True)

        self.rows = []

        bottom = tk.Frame(self, padx=10, pady=10)
        bottom.pack(fill="x")
        self.submit_btn = tk.Button(bottom, text="Zu Excel hinzufügen", command=self.submit_to_excel)
        self.submit_btn.pack(side="right")

    def choose_excel(self):
        path = filedialog.askopenfilename(
            title="Excel-Datei auswählen",
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if path:
            self.excel_path_var.set(path)

    def add_row(self):
        row = RowWidget(self.rows_container.content, len(self.rows), self.rows)
        row.grid(row=len(self.rows), column=0, sticky="we", pady=3)
        self.rows_container.content.grid_columnconfigure(0, weight=1)
        self.rows.append(row)

    def submit_to_excel(self):
        excel_path = self.excel_path_var.get().strip()
        if not excel_path:
            messagebox.showwarning("Fehlende Excel-Datei", "Bitte wählen Sie oben eine Excel-Datei aus.")
            return
        if not self.rows:
            messagebox.showwarning("Keine Zeilen", "Bitte fügen Sie mindestens eine Zeile hinzu.")
            return

        to_write = []
        for r in self.rows:
            row_data = r.get_row_for_excel()
            if not row_data[0]:
                messagebox.showwarning(
                    "Fehlender Handelsname",
                    "Bitte laden Sie PDF(s) für jede Zeile und/oder tragen Sie den Handelsnamen ein."
                )
                return
            to_write.append(row_data)

        try:
            Path(excel_path).parent.mkdir(parents=True, exist_ok=True)
            for row_data in to_write:
                open_and_write_excel(excel_path, row_data)

            messagebox.showinfo("Erfolg", f"{len(to_write)} Zeile(n) wurden in die Excel-Datei geschrieben.")

            for row in self.rows:
                row.frame.destroy()
            self.rows.clear()

        except Exception as e:
            messagebox.showerror("Fehler beim Schreiben", f"Konnte nicht in Excel schreiben:\n{e}")


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, height=260, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        canvas = tk.Canvas(self, height=height)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.content = tk.Frame(canvas)

        self.content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")