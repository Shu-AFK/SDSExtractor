import argparse
from src.gui import App
from src.cli import run_cli

def main():
    parser = argparse.ArgumentParser(description="Run the application in GUI or CLI mode.")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in command-line mode instead of starting the GUI."
    )
    parser.add_argument(
        "--path"
        "-p",
        type=str,
        help="Path to the root of the pdf folder."
    )
    parser.add_argument(
        "--excel-file"
        "-e",
        type=str,
        help="Path to the excel file to be created."
    )

    args = parser.parse_args()

    if args.cli:
        if args.path == "" or args.path is None or args.excel_file == "" or args.excel_file is None:
            print("No path and/or excel file specified. Exiting.")
            return

        run_cli(args.path, args.excel_file)
    else:
        App().mainloop()

if __name__ == "__main__":
    main()
