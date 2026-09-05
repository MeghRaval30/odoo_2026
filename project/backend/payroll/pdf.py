"""
Payslip PDF generation (PRD-5.9.4).

Uses ReportLab, which ships as a pure wheel and needs no system libraries —
WeasyPrint would need GTK on Windows, which is not a fight worth having in a
24-hour build.
"""

from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse

RUPEE = "₹"


def _fmt(amount):
    return f"{RUPEE} {Decimal(amount):,.2f}"


def build_payslip_pdf(payslip) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Payslip {payslip.number}")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16,
                        spaceAfter=2, textColor=colors.HexColor("#1a1a1a"))
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9,
                         textColor=colors.HexColor("#666666"))
    section = ParagraphStyle("section", parent=styles["Heading2"], fontSize=11,
                             spaceBefore=10, spaceAfter=4)

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
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
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

    rows = [["Rule", "Code", "Category", "Amount"]]
    for line in payslip.lines.order_by("sequence"):
        rows.append([line.name, line.code, line.get_category_display(),
                     _fmt(line.amount)])

    calc = Table(rows, colWidths=[70 * mm, 25 * mm, 35 * mm, 40 * mm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f7f7f7")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Emphasise the subtotal rows so the calculation reads at a glance
    for idx, line in enumerate(payslip.lines.order_by("sequence"), start=1):
        if line.category in ("GROSS", "NET"):
            style.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))
            style.append(("BACKGROUND", (0, idx), (-1, idx),
                          colors.HexColor("#eef2f7")))
    calc.setStyle(TableStyle(style))
    story.append(calc)

    # -- totals -------------------------------------------------------------
    story.append(Spacer(1, 8))
    totals = Table([
        ["Gross Salary", _fmt(payslip.gross)],
        ["Total Deductions", _fmt(payslip.deductions)],
        ["Net Salary", _fmt(payslip.net)],
    ], colWidths=[130 * mm, 40 * mm])
    totals.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
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
