"""
summary_pdf.py – Generates an executive-ready Summary PDF
with embedded clickable hyperlinks, formatted data tables, KPI metric cards,
and bulleted strategic insights in clean, simple English.
"""

import sys
from pathlib import Path
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib import colors


def _esc(text):
    """Escape XML special characters for ReportLab Paragraphs."""
    if not text:
        return ''
    text = str(text)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return text


def generate_summary_pdf(jobs_data: list, output_dir: Path, failed_jobs: list = None, low_score_jobs: list = None, strategic_insights: list = None) -> str:
    """
    Generate an executive-grade Summary.pdf report.
    
    Args:
        jobs_data: List of dicts for shortlisted/generated jobs (score >= 60%) with keys:
            - company: str
            - role: str
            - fit_score / score: int
            - fit_label: str
            - ats_score: int
            - recruiter_score: int
            - filename: str
            - apply_link: str
            - notes: str (optional)
        output_dir: Destination Path
        failed_jobs: List of dicts for failed/inaccessible links with keys:
            - company / title: str
            - apply_link: str
            - error_reason: str
            - suggested_action: str
        low_score_jobs: List of dicts for jobs scoring < 60% with keys:
            - company: str
            - role: str
            - score: int
            - reason: str
            - apply_link: str
        strategic_insights: Optional list of bullet strings in English.
    
    Returns:
        str: Path to the generated Summary.pdf
    """
    failed_jobs = failed_jobs or []
    low_score_jobs = low_score_jobs or []
    strategic_insights = strategic_insights or []
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "Summary.pdf"

    # Color Palette (Modern Executive Theme)
    c_primary = colors.HexColor("#1A365D")      # Deep Navy
    c_secondary = colors.HexColor("#2B6CB0")    # Slate Blue
    c_accent = colors.HexColor("#0D9488")       # Teal / Emerald
    c_bg_light = colors.HexColor("#F8FAFC")     # Soft Off-White
    c_card_border = colors.HexColor("#E2E8F0")  # Soft Gray
    c_text_dark = colors.HexColor("#1E293B")    # Charcoal
    c_text_muted = colors.HexColor("#64748B")   # Muted Slate
    c_warn_bg = colors.HexColor("#FFFBEB")      # Soft Amber
    c_gray_bg = colors.HexColor("#F1F5F9")      # Light Slate

    # Document Setup
    margin = 0.5 * inch
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin
    )

    story = []

    # Styles
    s_title = ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=c_primary)
    s_subtitle = ParagraphStyle('DocSubtitle', fontName='Helvetica', fontSize=9.5, leading=13.5, textColor=c_text_muted)
    s_sec_heading = ParagraphStyle('SecHeading', fontName='Helvetica-Bold', fontSize=11.5, leading=15.5, textColor=c_primary, spaceBefore=8, spaceAfter=4)
    s_bullet = ParagraphStyle('BulletText', fontName='Helvetica', fontSize=8.5, leading=12.5, textColor=c_text_dark, leftIndent=12, spaceAfter=3)
    s_th = ParagraphStyle('TableHeader', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.white, alignment=TA_CENTER)
    s_td = ParagraphStyle('TableCell', fontName='Helvetica', fontSize=8, leading=11, textColor=c_text_dark)
    s_td_center = ParagraphStyle('TableCellCenter', fontName='Helvetica', fontSize=8, leading=11, textColor=c_text_dark, alignment=TA_CENTER)
    s_link = ParagraphStyle('LinkStyle', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=c_secondary, alignment=TA_CENTER)

    # 1. Header Banner
    today_str = date.today().strftime("%B %d, %Y")
    story.append(Paragraph("🎯 Batch Job Application &amp; Resume Intelligence Report", s_title))
    story.append(Paragraph(f"<b>Date:</b> {today_str} &nbsp;|&nbsp; <b>Candidate:</b> Kaustubh Kale &nbsp;|&nbsp; <b>Threshold:</b> &ge;60% Match Required for Resume Generation", s_subtitle))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_secondary, spaceAfter=8))

    # 2. KPI Metrics Summary Cards
    total_processed = len(jobs_data) + len(low_score_jobs) + len(failed_jobs)
    ready_count = len(jobs_data)
    low_count = len(low_score_jobs)
    attention_count = len(failed_jobs)
    avg_ats = round(sum(j.get('ats_score', j.get('score', 0)) for j in jobs_data) / max(len(jobs_data), 1)) if jobs_data else 0

    card_data = [
        [
            Paragraph(f"<font size=14 color='{c_primary.hexval()}'><b>{total_processed}</b></font><br/><font size=7.5 color='{c_text_muted.hexval()}'>LINKS ANALYZED</font>", s_td_center),
            Paragraph(f"<font size=14 color='{c_accent.hexval()}'><b>{ready_count}</b></font><br/><font size=7.5 color='{c_text_muted.hexval()}'>RESUMES GENERATED (&ge;60%)</font>", s_td_center),
            Paragraph(f"<font size=14 color='{c_secondary.hexval()}'><b>{avg_ats}%</b></font><br/><font size=7.5 color='{c_text_muted.hexval()}'>AVG SHORTLIST ATS</font>", s_td_center),
            Paragraph(f"<font size=14 color='{'#D97706' if attention_count else c_text_muted.hexval()}'><b>{attention_count}</b></font><br/><font size=7.5 color='{c_text_muted.hexval()}'>FAILED / MANUAL REVIEW</font>", s_td_center),
        ]
    ]
    card_table = Table(card_data, colWidths=[1.85 * inch, 1.85 * inch, 1.85 * inch, 1.85 * inch])
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_light),
        ('BOX', (0, 0), (-1, -1), 1, c_card_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_card_border),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 10))

    # 3. Comprehensive Application Status Table (Shortlisted: Score >= 60%)
    story.append(Paragraph("📋 Shortlisted Opportunities &amp; Tailored Resumes (Score &ge; 60%)", s_sec_heading))
    if jobs_data:
        table_data = [
            [
                Paragraph("<b>#</b>", s_th),
                Paragraph("<b>Company &amp; Position</b>", s_th),
                Paragraph("<b>Match Score</b>", s_th),
                Paragraph("<b>Tailored PDF Resume</b>", s_th),
                Paragraph("<b>Direct Apply Link</b>", s_th),
            ]
        ]

        for idx, job in enumerate(jobs_data, 1):
            comp = _esc(job.get('company', 'Unknown'))
            role = _esc(job.get('role', job.get('title', 'Unknown')))
            score_val = job.get('ats_score', job.get('score', 0))
            fname = _esc(job.get('filename', 'Resume.pdf'))
            apply_url = job.get('apply_link', job.get('url', ''))

            comp_cell = Paragraph(f"<b>{comp}</b><br/><font color='{c_text_muted.hexval()}'>{role}</font>", s_td)
            score_cell = Paragraph(f"<font color='{c_accent.hexval()}'><b>{score_val}%</b></font>", s_td_center)
            resume_cell = Paragraph(f"📄 <font size=7.5>{fname}</font>", s_td)

            if apply_url:
                link_cell = Paragraph(f'<a href="{apply_url}"><font color="#2B6CB0"><b><u>Apply Now &rarr;</u></b></font></a>', s_link)
            else:
                link_cell = Paragraph("<font color='#94A3B8'>Direct Link N/A</font>", s_td_center)

            table_data.append([
                Paragraph(str(idx), s_td_center),
                comp_cell,
                score_cell,
                resume_cell,
                link_cell
            ])

        main_table = Table(table_data, colWidths=[0.35 * inch, 2.7 * inch, 1.0 * inch, 2.35 * inch, 1.0 * inch])
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_primary),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, c_card_border),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_light]),
        ]))
        story.append(main_table)
    else:
        story.append(Paragraph("<i>No jobs scored 60% or higher in this batch.</i>", s_td))
    story.append(Spacer(1, 10))

    # 4. Low Score Roles Table (< 60% - No Resumes Generated)
    if low_score_jobs:
        story.append(Paragraph("🔍 Low Relevance / Filtered Roles (&lt; 60% – No Resume Generated)", s_sec_heading))
        low_table_data = [
            [
                Paragraph("<b>#</b>", s_th),
                Paragraph("<b>Company &amp; Role</b>", s_th),
                Paragraph("<b>Score</b>", s_th),
                Paragraph("<b>Reason / Stack Mismatch</b>", s_th),
                Paragraph("<b>Apply Link</b>", s_th),
            ]
        ]
        for idx, lj in enumerate(low_score_jobs, 1):
            comp = _esc(str(lj.get('company', 'Unknown'))[:60])
            role = _esc(str(lj.get('role', lj.get('title', 'Unknown')))[:80])
            sc = lj.get('score', 0)
            reason = _esc(str(lj.get('reason', 'Score below required 60% threshold'))[:250])
            apply_u = lj.get('apply_link', lj.get('url', ''))

            comp_c = Paragraph(f"<b>{comp}</b><br/><font color='{c_text_muted.hexval()}'>{role}</font>", s_td)
            score_c = Paragraph(f"<font color='#D97706'><b>{sc}%</b></font>", s_td_center)
            reason_c = Paragraph(f"<font size=7.5 color='{c_text_muted.hexval()}'>{reason}</font>", s_td)
            if apply_u:
                link_c = Paragraph(f'<a href="{apply_u}"><font color="#2B6CB0"><u>View &rarr;</u></font></a>', s_link)
            else:
                link_c = Paragraph("—", s_td_center)

            low_table_data.append([
                Paragraph(str(idx), s_td_center),
                comp_c,
                score_c,
                reason_c,
                link_c
            ])

        low_table = Table(low_table_data, colWidths=[0.35 * inch, 2.35 * inch, 0.75 * inch, 3.05 * inch, 0.9 * inch])
        low_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#475569")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, c_card_border),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_gray_bg]),
        ]))
        story.append(low_table)
        story.append(Spacer(1, 10))

    # 5. Attention Required: Failed or Inaccessible Links
    if failed_jobs:
        story.append(Paragraph("⚠️ Attention Required: Failed / Inaccessible Links", s_sec_heading))
        warn_data = []
        for fj in failed_jobs:
            c = _esc(str(fj.get('company', fj.get('title', 'Unknown Link')))[:80])
            u = fj.get('apply_link', fj.get('url', ''))
            reason = _esc(str(fj.get('error_reason', 'Could not parse job description.'))[:200])
            act = _esc(str(fj.get('suggested_action', 'Open URL directly and paste JD into Manual Tailor if interested.'))[:200])
            warn_data.append([
                Paragraph(f"<b>{c}</b><br/><font color='#B45309'><b>Reason:</b> {reason}</font><br/><font color='#1E293B'><b>Action:</b> {act}</font><br/><a href='{u}'><font color='#2563EB'><u>{u}</u></font></a>", s_td)
            ])
        warn_table = Table(warn_data, colWidths=[7.4 * inch])
        warn_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), c_warn_bg),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#FCD34D")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(warn_table)
        story.append(Spacer(1, 10))

    # 6. Strategic Tailoring Analysis & Insights
    if strategic_insights:
        story.append(Paragraph("💡 Strategic Analysis &amp; Tailoring Insights", s_sec_heading))
        for item in strategic_insights:
            story.append(Paragraph(item, s_bullet))
            story.append(Spacer(1, 2))

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_card_border, spaceAfter=5))
    story.append(Paragraph("🔒 <i>All generated resumes strictly maintain 1-page ATS compliance without fabricating experience. Direct apply links open candidate career portals.</i>", s_subtitle))

    # Build Document
    doc.build(story)
    return str(pdf_path)
