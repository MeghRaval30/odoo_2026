"""
Payslip PDF generation (PRD-5.9.4).

Uses ReportLab, which ships as a pure wheel and needs no system libraries —
WeasyPrint would need GTK on Windows, which is not a fight worth having in a
24-hour build.
"""

import os
from decimal import Decimal
from functools import lru_cache
from io import BytesIO

from django.http import HttpResponse

RUPEE = "₹"

#: Fonts that carry U+20B9 INDIAN RUPEE SIGN, best first. ReportLab's built-in
#: Helvetica is a Type 1 face encoded WinAnsi, which has no rupee glyph at all —
#: printing the symbol with it silently emitted the wrong character on every
#: money figure of every payslip. So we embed a TrueType face when one is
#: available and degrade to the "INR" prefix when none is.
#: (regular, bold) TrueType pairs, best first.
_RUPEE_FONT_CANDIDATES = (
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
)

#: Layout-safe fallback when no rupee-capable face is installed.
REGULAR, BOLD = "Helvetica", "Helvetica-Bold"


@lru_cache(maxsize=1)
def _register_currency_font():
    """
    Register a rupee-capable TrueType face once per process.

    Returns (regular, bold, can_draw_rupee). Falling back to Helvetica is
    safe for layout but not for the symbol, so the caller switches to an
    ASCII "INR" prefix in that case rather than emitting a glyph the font
    does not have.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for regular_path, bold_path in _RUPEE_FONT_CANDIDATES:
        if not os.path.exists(regular_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont("PP360-Sans", regular_path))
            bold_name = "PP360-Sans"
            if os.path.exists(bold_path) and bold_path != regular_path:
                pdfmetrics.registerFont(TTFont("PP360-Sans-Bold", bold_path))
                bold_name = "PP360-Sans-Bold"
            return "PP360-Sans", bold_name, True
        except Exception:
            continue
    return REGULAR, BOLD, False


def _fonts():
    regular, bold, _ = _register_currency_font()
    return regular, bold


def _fmt(amount):
    """Money for the PDF, in a form the chosen font can actually draw."""
    *_, can_draw_rupee = _register_currency_font()
    symbol = RUPEE if can_draw_rupee else "INR"
    return f"{symbol} {Decimal(amount):,.2f}"


def build_payslip_pdf(payslip) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    regular, bold = _fonts()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Payslip {payslip.number}")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16,
                        spaceAfter=2, fontName=bold,
                        textColor=colors.HexColor("#1a1a1a"))
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9,
                         fontName=regular,
                         textColor=colors.HexColor("#666666"))
    section = ParagraphStyle("section", parent=styles["Heading2"], fontSize=11,
                             spaceBefore=10, spaceAfter=4, fontName=bold)

    employee = payslip.employee
    company = employee.company
    story = []

    story.append(Paragraph(company.name, h1))
    story.append(Paragraph(
        f"Payslip {payslip.number} &nbsp;|&nbsp; "
        f"{payslip.period_start:%d %b %Y} &ndash; {payslip.period_end:%d %b %Y}",
        sub))
    story.append(Spacer(1, 10))

    # -- employee block -----------------------------------------------------
    meta = [
        ["Employee", employee.full_name, "Employee Code", employee.employee_code],
        ["Department", employee.department.name if employee.department else "-",
         "Job Position", employee.job_position.name if employee.job_position else "-"],
        ["Contract", payslip.contract.reference if payslip.contract else "-",
         "Monthly Wage", _fmt(payslip.contract.wage) if payslip.contract else "-"],
        ["Worked Days", f"{payslip.worked_days} / {payslip.expected_days}",
         "Loss of Pay", f"{payslip.lop_days} days"],
        ["Overtime", f"{payslip.overtime_hours} hrs",
         "Bank A/C", employee.bank_account_number or "NOT ON FILE"],
    ]
    meta_table = Table(meta, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), bold),
        ("FONTNAME", (2, 0), (2, -1), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#555555")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#eeeeee")),
    ]))
    story.append(meta_table)

    # -- salary computation -------------------------------------------------
    story.append(Paragraph("Salary Computation", section))

    employee_lines = list(payslip.lines.filter(
        appears_on_payslip=True, is_employer_cost=False).order_by("sequence"))
    employer_lines = list(payslip.lines.filter(
        appears_on_payslip=True, is_employer_cost=True).order_by("sequence"))

    rows = [["Rule", "Code", "Category", "Amount"]]
    for line in employee_lines:
        rows.append([line.name, line.code, line.get_category_display(),
                     _fmt(line.amount)])

    calc = Table(rows, colWidths=[70 * mm, 25 * mm, 35 * mm, 40 * mm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f7f7f7")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Emphasise the subtotal rows so the calculation reads at a glance
    for idx, line in enumerate(employee_lines, start=1):
        if line.category in ("GROSS", "NET"):
            style.append(("FONTNAME", (0, idx), (-1, idx), bold))
            style.append(("BACKGROUND", (0, idx), (-1, idx),
                          colors.HexColor("#eef2f7")))
    calc.setStyle(TableStyle(style))
    story.append(calc)

    # -- employer contributions --------------------------------------------
    # Shown separately and never inside the deductions above: these are paid
    # by the company on the employee's behalf, so they raise cost to company
    # without reducing take-home pay.
    if employer_lines:
        story.append(Paragraph("Employer Contributions", section))
        er_rows = [["Rule", "Code", "Amount"]]
        for line in employer_lines:
            er_rows.append([line.name, line.code, _fmt(line.amount)])
        er_rows.append(["Total employer cost", "", _fmt(payslip.employer_cost)])
        er = Table(er_rows, colWidths=[95 * mm, 35 * mm, 40 * mm])
        er.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a5568")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), bold),
            ("FONTNAME", (0, -1), (-1, -1), bold),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(er)
        story.append(Paragraph(
            "Employer contributions are paid by the company and do not reduce "
            "net pay.", sub))

    # -- totals -------------------------------------------------------------
    story.append(Spacer(1, 8))
    totals = Table([
        ["Gross Salary", _fmt(payslip.gross)],
        ["Total Deductions", _fmt(payslip.deductions)],
        ["Net Salary", _fmt(payslip.net)],
        ["Cost to Company", _fmt(payslip.ctc)],
    ], colWidths=[130 * mm, 40 * mm])
    totals.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), bold),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#2d3748")),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(totals)

    warnings = list(payslip.warnings.all())
    if warnings:
        story.append(Paragraph("Warnings", section))
        for w in warnings:
            story.append(Paragraph(f"&bull; {w.message}", sub))

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "This is a computer-generated payslip and does not require a signature.",
        sub))

    doc.build(story)
    return buffer.getvalue()


def render_payslip_pdf(payslip) -> HttpResponse:
    pdf = build_payslip_pdf(payslip)
    filename = f"payslip-{payslip.number.replace('/', '-')}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
