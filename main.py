import argparse
from src.gui import App
from src.cli import run_cli

def main():
    parser = argparse.ArgumentParser(
        description="Run the application in GUI or CLI mode. "
                    "When not specifying any arguments, the application will start in GUI mode."
    )

    parser.add_argument(
        "--cli", "-c",
        dest="cli",
        action="store_true",
        help="Run in command-line mode instead of starting the GUI."
    )
    parser.add_argument(
        "--gui", "-g",
        dest="gui",
        action="store_true",
        help="Run in GUI mode explicitly."
    )

    # Shared options
    parser.add_argument(
        "--path", "-p",
        dest="path",
        type=str,
        help="Path to the root of the pdf folder."
    )
    parser.add_argument(
        "--excel-path", "-e",
        dest="excel_path",
        type=str,
        help="Path to the excel file to be created."
    )
    parser.add_argument(
        "--insert-row", "-r",
        dest="insert_row",
        type=int,
        help="Row number in the Excel file where data should be inserted (1-based index)."
    )
    parser.add_argument(
        "--use-fallback", "-f",
        dest="use_fallback",
        action="store_true",
        help="Use fallback method for extracting sds fields."
    )
    parser.add_argument(
        "--use-3mf", "-3",
        dest="use_3mf",
        action="store_true",
        help="Use 3M method for extracting sds fields."
    )
    parser.add_argument(
        "--use-basf", "-b",
        dest="use_basf",
        action="store_true",
        help="Use BASF method for extracting sds fields."
    )
    parser.add_argument(
        "--use-lechler", "-l",
        dest="use_lechler",
        action="store_true",
        help="Use Lechler method for extracting sds fields."
    )

    parser.set_defaults(cli=False, gui=False,
                        use_fallback=False, use_3mf=False,
                        use_basf=False, use_lechler=False,
                        insert_row=None)

    args = parser.parse_args()

    if args.cli:
        if not args.path or not args.excel_path:
            print("No path and/or excel file specified. Exiting.")
            return

        run_cli(
            args.path,
            args.excel_path,
            args.use_fallback,
            args.use_3mf,
            args.use_basf,
            args.use_lechler,
            insert_row=args.insert_row,
        )
    else:
        app = App(
            path=args.path,
            excel_path=args.excel_path,
            insert_row=args.insert_row,
        )

        if args.use_fallback:
            app.parse_mode_var.set("Fallback")
        elif args.use_3mf:
            app.parse_mode_var.set("3M")
        elif args.use_basf:
            app.parse_mode_var.set("BASF")
        elif args.use_lechler:
            app.parse_mode_var.set("Lechler")

        app.mainloop()


if __name__ == "__main__":
    main()
