import argparse
from src.gui import App
from src.cli import run_cli

def main():
    parser = argparse.ArgumentParser(description="Run the application in GUI or CLI mode.")
    parser.add_argument(
        "--cli",
        "-c",
        dest="cli",
        action="store_true",
        help="Run in command-line mode instead of starting the GUI."
    )
    parser.add_argument(
        "--path",
        "-p",
        dest="path",
        type=str,
        help="Path to the root of the pdf folder."
    )
    parser.add_argument(
        "--excel-path",
        "-e",
        dest="excel_path",
        type=str,
        help="Path to the excel file to be created."
    )
    parser.add_argument(
        "--use-fallback",
        "-f",
        dest="use_fallback",
        action="store_true",
        help="Use fallback method for extracting sds fields."
    )
    parser.add_argument(
        "--use-3mf",
        "-3",
        dest="use_3mf",
        action="store_true",
        help="Use 3MF method for extracting sds fields."
    )
    parser.add_argument(
        "--use-basf"
        "-b",
        dest="use_basf",
        action="store_true",
        help="Use BASF method for extracting sds fields."
    )

    parser.set_defaults(cli=False)
    parser.set_defaults(use_fallback=False)
    parser.set_defaults(use_3mf=False)
    parser.set_defaults(use_basf=False)

    args = parser.parse_args()

    if args.cli:
        if not args.path or not args.excel_path:
            print("No path and/or excel file specified. Exiting.")
            return

        run_cli(args.path, args.excel_path, args.use_fallback, args.use_3mf, args.use_basf)
    else:
        App().mainloop()

if __name__ == "__main__":
    main()
