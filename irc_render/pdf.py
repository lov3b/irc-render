"""PDF rendering primitives for IRC logs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .colors import nick_to_rgb
from .fonts import safe_register_mono_font
from .formatting import ParsedLine
from .images import URL_RE, download_image_bytes, load_image_reader, looks_like_image_url


def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size):
    """Draw text within max_width using simple word wrapping."""
    words = text.split()
    line = ""
    while words:
        w = words.pop(0)
        candidate = w if not line else line + " " + w
        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
            line = candidate
        else:
            if line:
                c.drawString(x, y, line)
                y -= font_size * 1.4
            line = w
    if line:
        c.drawString(x, y, line)
        y -= font_size * 1.4
    return y


@dataclass
class RenderConfig:
    title: str
    page_size_name: str
    font_size: int
    margin: int
    max_image_width_pt: int
    max_image_height_pt: int


class PDFRenderer:
    """Handle ReportLab drawing concerns for the IRC log output."""

    def __init__(self, output_path: str, config: RenderConfig):
        self.config = config
        self.page = letter if config.page_size_name.lower() == "letter" else A4
        self.width, self.height = self.page
        self.font_name, _ = safe_register_mono_font()
        self.canvas = canvas.Canvas(output_path, pagesize=self.page)
        self.canvas.setTitle(config.title)

        # Layout metrics
        self.left = config.margin
        self.right = self.width - config.margin
        self.top = self.height - config.margin
        self.bottom = config.margin
        self.y = self.top

        self.ts_width = (
            pdfmetrics.stringWidth("[00:00] ", self.font_name, config.font_size) * 1.1
        )
        self.max_nick_width = pdfmetrics.stringWidth(
            "<nick> ", self.font_name, config.font_size
        )

        self.page_num = 1
        self._draw_page_header()

    def render(self, lines: Iterable[ParsedLine]) -> None:
        for pl in lines:
            self._update_nick_width(pl)
            self._maybe_new_page()
            self._render_line(pl)
        self._finish_page_footer()
        self.canvas.save()

    def _draw_page_header(self) -> None:
        self.canvas.setFont(self.font_name, self.config.font_size + 3)
        self.canvas.setFillColor(colors.black)
        self.canvas.drawString(self.left, self.y, self.config.title)
        self.y -= (self.config.font_size + 8) * 1.6
        self.canvas.setFont(self.font_name, self.config.font_size)

    def _finish_page_footer(self) -> None:
        self.canvas.setFont(self.font_name, self.config.font_size - 2)
        self.canvas.setFillColor(colors.grey)
        self.canvas.drawRightString(self.right, self.bottom / 2, f"Page {self.page_num}")
        self.canvas.setFont(self.font_name, self.config.font_size)

    def _new_page(self) -> None:
        self.canvas.showPage()
        self.page_num += 1
        self.y = self.top
        self.canvas.setFont(self.font_name, self.config.font_size + 3)
        self.canvas.setFillColor(colors.black)
        self.canvas.drawString(self.left, self.y, self.config.title)
        self.y -= (self.config.font_size + 8) * 1.6
        self.canvas.setFont(self.font_name, self.config.font_size)

    def _maybe_new_page(self) -> None:
        if self.y < self.bottom + 2 * self.config.font_size:
            self._finish_page_footer()
            self._new_page()

    def _ensure_space(self, h_needed: float) -> None:
        if self.y < self.bottom + h_needed:
            self._finish_page_footer()
            self._new_page()

    def _update_nick_width(self, pl: ParsedLine) -> None:
        if pl.nick:
            w = pdfmetrics.stringWidth(
                f"<{pl.nick}> ", self.font_name, self.config.font_size
            )
            if w > self.max_nick_width:
                max_possible = self.right - self.left - self.ts_width - 50
                self.max_nick_width = min(w, max_possible)

    def _render_line(self, pl: ParsedLine) -> None:
        x = self.left
        font_size = self.config.font_size

        # Timestamp
        if pl.timestamp:
            ts_text = f"[{pl.timestamp}] "
            self.canvas.setFillColor(colors.HexColor("#666666"))
            self.canvas.drawString(x, self.y, ts_text)
            x += pdfmetrics.stringWidth(ts_text, self.font_name, font_size)
        else:
            x += self.ts_width * 0.4

        # Nick / markers
        if pl.kind == "message" and pl.nick:
            nick_text = f"<{pl.nick}> "
            r, g, b = nick_to_rgb(pl.nick)
            self.canvas.setFillColorRGB(r, g, b)
            self.canvas.drawString(x, self.y, nick_text)
            x += self.max_nick_width
        elif pl.kind == "action" and pl.nick:
            star = "* "
            self.canvas.setFillColor(colors.HexColor("#444444"))
            self.canvas.drawString(x, self.y, star)
            x += pdfmetrics.stringWidth(star, self.font_name, font_size)

            r, g, b = nick_to_rgb(pl.nick)
            self.canvas.setFillColorRGB(r, g, b)
            nick_text = f"{pl.nick} "
            self.canvas.drawString(x, self.y, nick_text)
            x += self.max_nick_width
        else:
            marker = "— "
            self.canvas.setFillColor(colors.HexColor("#888888"))
            self.canvas.drawString(x, self.y, marker)
            x += pdfmetrics.stringWidth(marker, self.font_name, font_size)

        # Text color by line type
        if pl.kind == "system":
            self.canvas.setFillColor(colors.HexColor("#666666"))
        elif pl.kind == "action":
            self.canvas.setFillColor(colors.HexColor("#444444"))
        else:
            self.canvas.setFillColor(colors.black)

        msg_width = self.right - x
        self.y = self._render_text_with_inline_images(pl.text, x, self.y, msg_width)

    def _render_text_with_inline_images(
        self, text: str, x_start: float, y_cur: float, msg_w: float
    ) -> float:
        tokens = URL_RE.split(text)
        pending_text = ""
        font_size = self.config.font_size

        for tok in tokens:
            if not URL_RE.fullmatch(tok) or not looks_like_image_url(tok):
                pending_text += (
                    ("" if pending_text == "" else " ") + tok.strip()
                    if tok.strip()
                    else tok
                )
                continue

            if pending_text.strip():
                y_cur = draw_wrapped_text(
                    self.canvas,
                    pending_text,
                    x_start,
                    y_cur,
                    msg_w,
                    self.font_name,
                    font_size,
                )
                pending_text = ""

            maybe_y = self._render_inline_image(tok, x_start, y_cur, msg_w)
            if maybe_y is None:
                pending_text += (" " if pending_text else "") + tok
            else:
                y_cur = maybe_y

        if pending_text.strip():
            y_cur = draw_wrapped_text(
                self.canvas,
                pending_text,
                x_start,
                y_cur,
                msg_w,
                self.font_name,
                font_size,
            )

        return y_cur

    def _render_inline_image(
        self, url: str, x_start: float, y_cur: float, msg_w: float
    ) -> Optional[float]:
        """Download and render an inline image. Returns the updated y or None on failure."""
        data = download_image_bytes(url)
        if not data:
            return None

        font_size = self.config.font_size
        try:
            img, (iw, ih) = load_image_reader(data)
            target_w = min(msg_w, self.config.max_image_width_pt)
            scale = min(target_w / iw, self.config.max_image_height_pt / ih, 1.0)
            disp_w = iw * scale
            disp_h = ih * scale

            top_adjust = font_size * 0.3
            self._ensure_space(disp_h + font_size + top_adjust)

            y_cur -= disp_h
            img_bottom = y_cur + top_adjust
            self.canvas.drawImage(
                img,
                x_start,
                img_bottom,
                width=disp_w,
                height=disp_h,
                preserveAspectRatio=True,
                mask="auto",
            )
            self.canvas.linkURL(
                url,
                (x_start, img_bottom, x_start + disp_w, img_bottom + disp_h),
                relative=0,
            )
            return img_bottom - font_size * 1.0
        except Exception:
            return None


def render_pdf(
    input_path: str,
    output_path: str,
    title: str,
    page_size_name: str,
    font_size: int,
    margin: int,
    max_image_width_pt: int,
    max_image_height_pt: int,
) -> None:
    config = RenderConfig(
        title=title,
        page_size_name=page_size_name,
        font_size=font_size,
        margin=margin,
        max_image_width_pt=max_image_width_pt,
        max_image_height_pt=max_image_height_pt,
    )
    from .parser import IRCLogParser  # local import to avoid cycle

    parser = IRCLogParser()
    renderer = PDFRenderer(output_path, config)
    renderer.render(parser.parse_file(input_path))
