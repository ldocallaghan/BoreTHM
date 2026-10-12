"""Export docs/summary.md to a two-page PDF, with clickable repository links.

Requires reportlab and pypdf (available in the bundled document runtime).
Run: python tools/render_summary.py
"""
from html import escape
from pathlib import Path
import re
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output/pdf/summary-v135.pdf'
BASE = 'https://github.com/ldocallaghan/geothermal-thermo-hydraulic-model/blob/codex/v1.3.5/'


def font_files():
    windows = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    if (windows / 'arial.ttf').exists():
        return windows, ('arial.ttf', 'arialbd.ttf', 'ariali.ttf', 'arialbi.ttf')
    linux = Path('/usr/share/fonts/truetype/dejavu')
    return linux, ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSans-Oblique.ttf', 'DejaVuSans-BoldOblique.ttf')


def markup(text):
    text = escape(text)
    def link(match):
        label, href = match.groups()
        if '://' not in href:
            path, sep, anchor = href.partition('#')
            target = (ROOT / 'docs' / path).resolve().relative_to(ROOT).as_posix()
            href = BASE + target + (sep + anchor if sep else '')
        return f'<a href="{href}" color="#155b7a"><u>{label}</u></a>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    return text


def render():
    font_dir, files = font_files()
    for name, file in zip(('Reader', 'Reader-Bold', 'Reader-Italic', 'Reader-BoldItalic'), files):
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    pdfmetrics.registerFontFamily('Reader', normal='Reader', bold='Reader-Bold',
                                  italic='Reader-Italic', boldItalic='Reader-BoldItalic')
    body = ParagraphStyle('body', fontName='Reader', fontSize=10.2, leading=13.0,
                          spaceAfter=6, textColor=colors.HexColor('#202b34'))
    h1 = ParagraphStyle('title', parent=body, fontName='Reader-Bold', fontSize=17,
                        leading=20, spaceAfter=8)
    h2 = ParagraphStyle('heading', parent=body, fontName='Reader-Bold', fontSize=11.5,
                        leading=14, spaceBefore=4, spaceAfter=5, keepWithNext=True)
    cell = ParagraphStyle('cell', parent=body, fontSize=9.2, leading=11.0, spaceAfter=0)
    story = []
    lines = (ROOT / 'docs/summary.md').read_text(encoding='utf-8').splitlines()
    i = 0
    width = A4[0] - 76
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line == '<!-- PAGEBREAK -->':
            story.append(PageBreak())
            i += 1
        elif line.startswith('# '):
            story.append(Paragraph(markup(line[2:]), h1))
            i += 1
        elif line.startswith('## '):
            story.append(Paragraph(markup(line[3:]), h2))
            i += 1
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                entries = [t.strip() for t in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[-:]+', e) for e in entries):
                    rows.append([Paragraph(markup(e), cell) for e in entries])
                i += 1
            widths = [width * p for p in ([.43, .095, .245, .23] if len(rows[0]) == 4 else [.40, .39, .21])]
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0f3')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7f8')]),
                ('LINEBELOW', (0, 0), (-1, 0), .6, colors.HexColor('#9baeb6')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.extend([table, Spacer(1, 6)])
        else:
            parts = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '|', '<!--')) and not re.match(r'\d+\. ', lines[i]):
                parts.append(lines[i])
                i += 1
            story.append(Paragraph(markup(' '.join(parts)), body))

    def footer(canvas, doc):
        canvas.setFont('Reader', 8)
        canvas.setFillColor(colors.HexColor('#586a75'))
        canvas.drawString(38, 24, 'BoreTHM | reader draft | retained v1.3.4 calculation')
        canvas.drawRightString(A4[0] - 38, 24, str(doc.page))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=38, rightMargin=38,
                            topMargin=32, bottomMargin=38, title='BoreTHM v1.3.5: a summary for readers',
                            author="Liam O'Callaghan")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    pages = len(PdfReader(OUTPUT).pages)
    print(f'{OUTPUT}: {pages} pages')
    assert pages == 2, f'Edit the summary to fit two readable pages; found {pages}'


if __name__ == '__main__':
    render()
