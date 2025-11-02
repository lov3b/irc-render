#!/usr/bin/env python3
"""CLI entry point for the IRC log renderer."""

import argparse
import os


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an IRC log (.txt) to a colored PDF with inline images."
    )
    parser.add_argument("input", help="Path to IRC log .txt file")
    parser.add_argument("output", help="Output PDF path", required=False, default=None)
    parser.add_argument(
        "--title",
        "-t",
        default=None,
        required=False,
        help="Title shown at the top of each page",
    )
    parser.add_argument(
        "--page-size",
        choices=["A4", "Letter"],
        default="A4",
        help="Page size",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=11,
        help="Base font size (points)",
    )
    parser.add_argument("--margin", type=int, default=36, help="Page margin (points)")
    parser.add_argument(
        "--max-image-width",
        type=int,
        default=360,
        help="Maximum inline image width (points)",
    )
    parser.add_argument(
        "--max-image-height",
        type=int,
        default=260,
        help="Maximum inline image height (points)",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("IRC_RENDER_LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO or IRC_RENDER_LOG_LEVEL env var)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    from irc_render.pdf import render_pdf  # Import after logging is configured
    import logging
    from pathlib import Path

    logging.basicConfig(
        level=args.log_level.upper(),
        format="[%(asctime)s] %(levelname)s(%(name)s): %(message)s",
        datefmt="%Y:%m:%D %H:%M.%S",
    )

    input_path = Path(args.input)

    render_pdf(
        input_path,
        args.output or str(input_path.parent / (input_path.stem + ".pdf")),
        args.title or input_path.stem,
        args.page_size,
        args.font_size,
        args.margin,
        args.max_image_width,
        args.max_image_height,
    )


if __name__ == "__main__":
    main()
