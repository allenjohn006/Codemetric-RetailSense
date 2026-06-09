"""
RetailSense PDF Report Generator
Produces a professional, branded analytics report using ReportLab.
"""
import os
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# Brand colors
BRAND_PRIMARY = colors.HexColor("#6C63FF")
BRAND_DARK = colors.HexColor("#1A1A2E")
BRAND_ACCENT = colors.HexColor("#00D2FF")
BRAND_SUCCESS = colors.HexColor("#00C853")
BRAND_WARNING = colors.HexColor("#FF6D00")
BRAND_LIGHT_BG = colors.HexColor("#F5F5FA")


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "BrandTitle",
        parent=styles["Title"],
        fontSize=28,
        textColor=BRAND_PRIMARY,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "BrandSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=16,
        textColor=BRAND_DARK,
        spaceBefore=16,
        spaceAfter=8,
        borderPadding=(0, 0, 4, 0),
    ))
    styles.add(ParagraphStyle(
        "InsightText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=BRAND_DARK,
    ))
    styles.add(ParagraphStyle(
        "KPIValue",
        parent=styles["Normal"],
        fontSize=20,
        textColor=BRAND_PRIMARY,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "KPILabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
    ))
    return styles


def generate_pdf(
    summary_stats: dict,
    eda_data: dict,
    forecast_data: dict,
    seasonality_data: dict,
    category_data: dict,
    insights: dict,
    output_path: str,
) -> str:
    """Generate a full analytics PDF report."""
    styles = _build_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    elements = []

    # ─── Cover Section ────────────────────────────────────
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("RetailSense", styles["BrandTitle"]))
    elements.append(Paragraph("AI-Powered Retail Analytics Report", styles["BrandSubtitle"]))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["BrandSubtitle"]
    ))
    elements.append(HRFlowable(
        width="100%", thickness=2, color=BRAND_PRIMARY,
        spaceBefore=10, spaceAfter=20
    ))

    # ─── Executive Summary KPIs ───────────────────────────
    elements.append(Paragraph("Executive Summary", styles["SectionHeader"]))

    kpi_data = [
        ["Total Records", "Total Sales", "Categories", "YoY Growth"],
        [
            f"{summary_stats.get('total_rows', 'N/A'):,}" if isinstance(summary_stats.get('total_rows'), (int, float)) else "N/A",
            f"${summary_stats.get('total_sales', 0):,.0f}",
            str(summary_stats.get('num_categories', 'N/A')),
            f"{summary_stats.get('yoy_growth', 'N/A')}%" if summary_stats.get('yoy_growth') is not None else "N/A",
        ],
    ]

    kpi_table = Table(kpi_data, colWidths=[120, 120, 120, 120])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_LIGHT_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.grey),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("TEXTCOLOR", (0, 1), (-1, 1), BRAND_PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 16))

    # Date range
    date_range = summary_stats.get("date_range", {})
    if date_range:
        elements.append(Paragraph(
            f"<b>Analysis Period:</b> {date_range.get('start', 'N/A')[:10]} to {date_range.get('end', 'N/A')[:10]}",
            styles["InsightText"]
        ))
    elements.append(Spacer(1, 12))

    # ─── Seasonality Section ──────────────────────────────
    if seasonality_data:
        elements.append(Paragraph("Seasonality Analysis", styles["SectionHeader"]))
        elements.append(Paragraph(
            seasonality_data.get("insight", "No seasonal pattern detected."),
            styles["InsightText"]
        ))
        elements.append(Spacer(1, 8))

        # Monthly seasonality table
        monthly = seasonality_data.get("monthly", [])
        if monthly:
            header = ["Month", "Avg Sales"]
            rows = [[m["period"], f"${m['value']:,.0f}"] for m in monthly]
            all_rows = [header] + rows

            season_table = Table(all_rows, colWidths=[160, 160])
            season_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT_BG]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(season_table)

    elements.append(Spacer(1, 12))

    # ─── Category Breakdown ───────────────────────────────
    if category_data and category_data.get("top_5"):
        elements.append(Paragraph("Top Performing Categories", styles["SectionHeader"]))

        header = ["Category", "Total Sales", "Growth Rate"]
        rows = [
            [
                c["name"],
                f"${c['total_sales']:,.0f}",
                f"{c['growth_rate']}%" if c.get("growth_rate") is not None else "N/A",
            ]
            for c in category_data["top_5"]
        ]
        all_rows = [header] + rows

        cat_table = Table(all_rows, colWidths=[160, 120, 100])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT_BG]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(cat_table)

    elements.append(Spacer(1, 12))

    # ─── Forecast Section ─────────────────────────────────
    if forecast_data and forecast_data.get("forecast"):
        elements.append(Paragraph("Demand Forecast", styles["SectionHeader"]))
        elements.append(Paragraph(
            forecast_data.get("description", ""),
            styles["InsightText"]
        ))
        elements.append(Spacer(1, 8))

        header = ["Period", "Forecast", "Lower Bound", "Upper Bound"]
        rows = [
            [
                f["date"][:7],
                f"${f['forecast']:,.0f}",
                f"${f.get('lower_bound', 0):,.0f}",
                f"${f.get('upper_bound', 0):,.0f}",
            ]
            for f in forecast_data["forecast"][:12]
        ]
        all_rows = [header] + rows

        fc_table = Table(all_rows, colWidths=[100, 110, 110, 110])
        fc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT_BG]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(fc_table)

    # ─── Actionable Insights ──────────────────────────────
    if insights and insights.get("items"):
        elements.append(PageBreak())
        elements.append(Paragraph("Actionable Insights & Recommendations", styles["SectionHeader"]))

        for i, item in enumerate(insights["items"], 1):
            severity_color = {
                "success": BRAND_SUCCESS,
                "warning": BRAND_WARNING,
                "info": BRAND_PRIMARY,
            }.get(item.get("severity", "info"), BRAND_PRIMARY)

            elements.append(Paragraph(
                f"<font color='{severity_color}'><b>{i}. {item['title']}</b></font>",
                styles["InsightText"]
            ))
            elements.append(Paragraph(item["description"], styles["InsightText"]))
            elements.append(Spacer(1, 8))

    # ─── Footer ───────────────────────────────────────────
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(
        width="100%", thickness=1, color=colors.HexColor("#E0E0E0"),
        spaceBefore=10, spaceAfter=10
    ))
    elements.append(Paragraph(
        "Generated by RetailSense AI Analytics Platform • Confidential",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    # Build
    doc.build(elements)
    return output_path
