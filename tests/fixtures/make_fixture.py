"""Generate tests/fixtures/mini.pdf - a 3-page synthetic PDF used by test_parse.

Contains: running header/footer, numbered section headings at 3 depths, body
paragraphs, and one Markdown-renderable table. Synthetic content only.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FIXTURE = Path(__file__).parent / "mini.pdf"


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.75 * inch, 10.5 * inch, "MiniCorp Security Policy v1 - RUNNING HEADER")
    canvas.drawRightString(7.75 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(path: Path = FIXTURE) -> Path:
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=8)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceAfter=6)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=11, spaceAfter=4)
    body = styles["BodyText"]

    doc = SimpleDocTemplate(str(path), pagesize=LETTER, topMargin=1.0 * inch)
    story = []

    story.append(Paragraph("MiniCorp Security Policy", h1))
    story.append(Paragraph("1 Purpose", h1))
    story.append(
        Paragraph(
            "This policy defines how MiniCorp protects its fictional assets. It is a synthetic "
            "fixture document for unit tests only. Passwords must be at least twelve characters "
            "long and stored in the approved vault.",
            body,
        )
    )
    story.append(Paragraph("1.1 Scope", h2))
    story.append(
        Paragraph(
            "The policy applies to all synthetic employees and contractors of MiniCorp. "
            "Third-party vendors must sign the fictional vendor agreement before access is granted.",
            body,
        )
    )
    story.append(Paragraph("1.1.1 Exclusions", h3))
    story.append(
        Paragraph(
            "Test fixtures are excluded from real compliance scope. This sentence exists so a "
            "third-level heading appears in the parse output.",
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("2 Access Control", h1))
    story.append(
        Paragraph(
            "Access is granted by role. Administrators may approve access requests within one "
            "business day. All access reviews occur quarterly.",
            body,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("Table 1 - Role permissions", body))
    data = [
        ["Role", "Read docs", "Admin console", "Approve requests"],
        ["Employee", "Yes", "No", "No"],
        ["Contractor", "Yes", "No", "No"],
        ["Administrator", "Yes", "Yes", "Yes"],
    ]
    t = Table(data, colWidths=[1.6 * inch, 1.3 * inch, 1.4 * inch, 1.6 * inch])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Privileged accounts require multi-factor authentication. Session tokens expire "
            "after thirty minutes of inactivity.",
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("3 Incident Reporting", h1))
    story.append(
        Paragraph(
            "Suspected incidents must be reported to security@minicorp.example within one hour "
            "of discovery. The security team triages every report.",
            body,
        )
    )
    story.append(Paragraph("3.1 Severity levels", h2))
    story.append(
        Paragraph(
            "Severity one is reserved for active data breaches. Severity two covers contained "
            "malware. Severity three covers policy violations without data loss.",
            body,
        )
    )

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return path


if __name__ == "__main__":
    p = build()
    print(f"wrote {p}")
