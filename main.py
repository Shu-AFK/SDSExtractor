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

    args = parser.parse_args()

    if args.cli:
        if not args.path or not args.excel_path:
            print("No path and/or excel file specified. Exiting.")
            return

        run_cli(args.path, args.excel_path, args.use_fallback)
    else:
        App().mainloop()

if __name__ == "__main__":
    main()
