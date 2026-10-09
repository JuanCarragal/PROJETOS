import argparse
from pathlib import Path
from data_processor import DataProcessor
from report_engine import ReportEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process an Excel file and generate PDF, PPTX, and HTML reports."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the Excel file to process.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "reports",
        help="Directory where generated reports will be saved.",
    )
    args = parser.parse_args()

    if not args.input_file.exists():
        raise SystemExit(f"Input file not found: {args.input_file}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    processor = DataProcessor(str(args.input_file))
    if not processor.load_data():
        raise SystemExit("Failed to load the Excel file. Check the file format and columns.")

    engine = ReportEngine(processor.get_all_analysis())
    stem = args.input_file.stem

    pdf_path = args.output_dir / f"{stem}.pdf"
    pptx_path = args.output_dir / f"{stem}.pptx"
    html_path = args.output_dir / f"{stem}.html"

    engine.generate_pdf(str(pdf_path))
    engine.generate_pptx(str(pptx_path))
    engine.generate_html(str(html_path))

    print("Reports generated successfully:")
    print(f"  PDF:  {pdf_path}")
    print(f"  PPTX: {pptx_path}")
    print(f"  HTML: {html_path}")


if __name__ == "__main__":
    main()
