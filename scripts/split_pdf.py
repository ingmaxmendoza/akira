"""Split a PDF into page-range chunks that fit the Read tool's limits
(20MB per file, 20 pages per request for large PDFs).

Usage:
    python scripts/split_pdf.py "path/to/big.pdf"
    python scripts/split_pdf.py "path/to/big.pdf" --max-pages 15 --max-mb 18 --out-dir some/dir

Writes chunks next to the source PDF by default, named
"<stem>_part01-of-03.pdf" etc., and prints each chunk's path and page
range so they can be fed to the Read tool one at a time.
"""
import argparse
from pathlib import Path

from pypdf import PdfReader, PdfWriter

DEFAULT_MAX_MB = 19  # stay under the tool's 20MB cap
DEFAULT_MAX_PAGES = 20  # the tool's per-request page cap for large PDFs


def split_pdf(src: Path, out_dir: Path, max_pages: int, max_mb: float) -> list[Path]:
    max_bytes = max_mb * 1024 * 1024
    reader = PdfReader(src)
    n = len(reader.pages)

    chunks: list[tuple[int, int]] = []  # (start, end) inclusive, 0-indexed
    start = 0
    while start < n:
        end = min(start + max_pages - 1, n - 1)
        # Shrink the page range until the serialized chunk fits max_bytes.
        while end > start:
            writer = PdfWriter()
            for p in range(start, end + 1):
                writer.add_page(reader.pages[p])
            size = _writer_size(writer)
            if size <= max_bytes:
                break
            end -= 1
        chunks.append((start, end))
        start = end + 1

    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(chunks)
    paths = []
    for i, (start, end) in enumerate(chunks, 1):
        writer = PdfWriter()
        for p in range(start, end + 1):
            writer.add_page(reader.pages[p])
        out_path = out_dir / f"{src.stem}_part{i:02d}-of-{total:02d}.pdf"
        with out_path.open("wb") as f:
            writer.write(f)
        paths.append(out_path)
        print(f"{out_path}  (pages {start + 1}-{end + 1}, {out_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return paths


def _writer_size(writer: PdfWriter) -> int:
    import io
    buf = io.BytesIO()
    writer.write(buf)
    return buf.tell()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path, help="Path to the source PDF")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help=f"Max pages per chunk (default {DEFAULT_MAX_PAGES})")
    ap.add_argument("--max-mb", type=float, default=DEFAULT_MAX_MB, help=f"Max size per chunk in MB (default {DEFAULT_MAX_MB})")
    ap.add_argument("--out-dir", type=Path, default=None, help="Output directory (default: same folder as source PDF)")
    args = ap.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"No such file: {args.pdf}")

    out_dir = args.out_dir or args.pdf.parent
    split_pdf(args.pdf, out_dir, args.max_pages, args.max_mb)


if __name__ == "__main__":
    main()
