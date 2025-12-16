import streamlit as st
from database.reports import get_reports_by_child
from database.sessions import get_sessions_by_child
from database.users import get_user_by_id
from utils.session_state import clear_cookies
from utils.ui_components import render_footer
import re
from reportlab.lib import colors
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.units import inch, mm

# --- Static Configuration ---
REPORT_TITLE = "THERAPY SESSION REPORT"
OUTPUT_FILENAME_TEMPLATE = "Therapy_Report_{CHILD_NAME}_{SESSION_DATE}.pdf"

def parse_nlp_text_to_content(nlp_text, session_id=None):
    """Parses the NLP_Text string into a dictionary suitable for PDF generation."""
    content = {}

    # 1. Extract Child Info
    child_name_match = re.search(r"\*\*Child Name:\*\* (.*?)\n", nlp_text)
    child_age_match = re.search(r"\*\*Age:\*\* (.*?)\n", nlp_text)

    content['CHILD_NAME'] = child_name_match.group(1).strip() if child_name_match else "N/A"
    content['CHILD_AGE'] = child_age_match.group(1).strip() if child_age_match else "N/A"

    # 2. Extract Key Sections
    sections = {
        "Summary": r"\*\*Summary:\*\*\n(.*?)\n\n\*\*Analysis Results:",
        "Diagnosis": r"\*\*Diagnosis:\*\*\n(.*?)\n\n\*\*Recommendations:",
        "Recommendations": r"\*\*Recommendations:\*\*\n(.*?)\n\n\*\*Future Goals:",
        "Future Goals": r"\*\*Future Goals:\*\*\n(.*?)$",
    }

    for key, pattern in sections.items():
        match = re.search(pattern, nlp_text, re.DOTALL)
        content[key] = match.group(1).strip() if match else f"No {key} provided."

    # *** FIX: Convert numbered list goals to HTML list structure for Paragraph ***
    goals_text = content.get("Future Goals", "")
    if goals_text:
        # Clean the text by replacing tabs with spaces and normalizing whitespace
        goals_text = re.sub(r'\t+', ' ', goals_text)  # Replace tabs with single space
        goals_text = re.sub(r'\s+', ' ', goals_text)  # Normalize multiple spaces to single space
        # 1. Split the text by number-period-space, keeping the goals only
        goals_list = [g.strip() for g in re.split(r'\s*\d+\.\s*', goals_text) if g.strip()]

        # 2. Reformat as an HTML unordered list (ReportLab renders this cleanly as a bullet list)
        html_goals = "".join([f"<li leftIndent='30'>{g}</li>" for g in goals_list])
        content["Future Goals_HTML"] = f"<ul>{html_goals}</ul>"
    else:
        content["Future Goals_HTML"] = "No future goals specified."

    # 3. Extract Analysis Results
    # Use individual searches for robustness, matching the LLM prompt format with numbers
    analysis_keys = {
        "1. Focus Percent": "Focus Percent",
        "2. Emotion Summary": "Emotion Summary",
        "3. Vocabulary": "Vocabulary (TTR/Words)",
        "4. Syntax": "Syntax",
        "5. MLU (Mean Length of Utterance)": "MLU (Mean Length of Utterance)",
        "6. Conversational Skills": "Conversational Skills",
        "7. Semantic Pairs": "Semantic Pairs"
    }

    for search_key, content_key in analysis_keys.items():
        match = re.search(rf"\*\*{re.escape(search_key)}:\*\*\n(.*?)(?=\n\*\*\d+\.|\n\*\*Diagnosis|$)", nlp_text, re.DOTALL)
        if match:
            value = match.group(1).strip()
            content[content_key] = value

    # Retrieve actual Focus Percentage, MLU, and Emotion data from database if session_id is provided
    if session_id:
        from database.nlp import get_nlp_result
        from nlp.nlp import get_focus_summary, get_emotion_profile
        actual_focus_pct = get_focus_summary(session_id)
        content["Focus Percent"] = f"{actual_focus_pct:.2f}"

        nlp_data = get_nlp_result(session_id)
        if nlp_data and 'mlu' in nlp_data:
            content["MLU (Mean Length of Utterance)"] = f"{nlp_data.get('mlu', 0.0):.2f}"

        # Always retrieve emotion data from database if available
        emotion_profile = get_emotion_profile(session_id)
        if emotion_profile and emotion_profile.get("dominant") != "Unknown":
            content["emotion_data"] = emotion_profile

    # Ensure all required keys for the PDF template are present
    content["Focus Percent"] = content.get("Focus Percent", "0.0")
    content["MLU (Mean Length of Utterance)"] = content.get("MLU (Mean Length of Utterance)", "-")
    content["Emotion Summary"] = content.get("Emotion Summary", "No emotion data available.")
    content["Syntax"] = content.get("Syntax", "-")
    content["Conversational Skills"] = content.get("Conversational Skills", "-")
    content["Semantic Pairs"] = content.get("Semantic Pairs", "-")

    return content

def footer_and_page_number(canvas, doc):
    canvas.saveState()
    styles = getSampleStyleSheet()
    footer_text = f"Generated by HolaChild AI – Confidential | Session Date: {doc.session_date}"
    canvas.setStrokeColor(colors.lightgrey)
    canvas.setLineWidth(0.5)
    left = doc.leftMargin
    right = letter[0] - doc.rightMargin
    canvas.line(left, 0.75 * inch, right, 0.75 * inch)
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.drawString(left, 0.55 * inch, footer_text)
    page_num = f"Page {canvas.getPageNumber()}"
    canvas.drawRightString(right, 0.55 * inch, page_num)
    canvas.restoreState()

def create_focus_bar_drawing(focus_percent_str):
    drawing = Drawing(260, 60)
    try:
        observed = float(focus_percent_str)
    except Exception:
        observed = 0.0
    target = 0.8
    bar_x = 10
    bar_y = 20
    bar_height = 14
    max_width = 220
    drawing.add(Rect(bar_x, bar_y, max_width, bar_height, strokeWidth=0.5, strokeColor=colors.lightgrey, fillColor=colors.whitesmoke))
    obs_width = max(0, min(1.0, observed)) * max_width
    obs_color = colors.red if observed < 0.2 else colors.green
    drawing.add(Rect(bar_x, bar_y, obs_width, bar_height, strokeWidth=0.5, strokeColor=obs_color, fillColor=obs_color))
    tgt_x = bar_x + target * max_width
    drawing.add(Line(tgt_x, bar_y - 3, tgt_x, bar_y + bar_height + 3, strokeWidth=1, strokeColor=colors.blue))
    drawing.add(String(bar_x, bar_y + bar_height + 6, f"Observed: {observed*100:.0f}%", fontSize=8))
    drawing.add(String(bar_x + max_width - 70, bar_y + bar_height + 6, f"Target: {target*100:.0f}%", fontSize=8))
    return drawing

def create_emotion_pie_chart(content):
    # Check if we have actual emotion data from database
    emotion_data = content.get("emotion_data")
    if emotion_data and emotion_data.get("counts"):
        counts = emotion_data["counts"]
        total = sum(counts.values())
        if total > 0:
            data = [count / total * 100 for count in counts.values()]
            labels = [f"{emo.capitalize()} ({count / total * 100:.0f}%)" for emo, count in counts.items()]
            dominant = emotion_data.get("dominant", "Neutral").capitalize()
            consistency = emotion_data.get("consistency", 0.0)
            drawing = Drawing(150, 110)
            pie = Pie()
            pie.x = 20
            pie.y = 10
            pie.width = 90
            pie.height = 90
            pie.data = data
            pie.labels = labels
            pie.slices.strokeWidth = 0.5
            # Highlight dominant emotion
            dominant_lower = dominant.lower()
            colors_list = [colors.HexColor("#FFD54F") if emo.lower() == dominant_lower else colors.lightgrey for emo in counts.keys()]
            for i, color in enumerate(colors_list):
                pie.slices[i].fillColor = color
            drawing.add(pie)
            drawing.add(String(115, 80, f"Dominant: {dominant}", fontSize=8))
            drawing.add(String(115, 68, f"Consistency: {consistency*100:.0f}%", fontSize=8))
            return drawing

    # Fallback to parsing text or default
    consistency = 0.0
    dominant = "Neutral"
    try:
        emotion_text = content.get("Emotion Summary", "")
        m = re.search(r"consistency of\s*([0-9]*\.?[0-9]+)", emotion_text, flags=re.IGNORECASE)
        if m:
            consistency = float(m.group(1))
        m2 = re.search(r"was\s+([a-zA-Z]+)", emotion_text)
        if m2:
            dominant = m2.group(1).capitalize()
        if consistency == 0.0 and 'consistently' in emotion_text:
             consistency = 1.0
    except Exception:
        pass

    other = max(0.0, 1.0 - consistency)
    drawing = Drawing(150, 110)
    pie = Pie()
    pie.x = 20
    pie.y = 10
    pie.width = 90
    pie.height = 90
    pie.data = [consistency * 100.0, other * 100.0]
    pie.labels = [f"{dominant} ({consistency*100:.0f}%)", f"Other ({other*100:.0f}%)"]
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = colors.HexColor("#FFD54F")
    pie.slices[1].fillColor = colors.lightgrey
    drawing.add(pie)
    drawing.add(String(115, 80, f"{dominant}: {consistency*100:.0f}%", fontSize=8))
    drawing.add(String(115, 68, f"Other: {other*100:.0f}%", fontSize=8))
    return drawing

def generate_report_pdf(content, child_name, child_age, session_id, therapist_id):
    """Generates the PDF content in memory and returns the binary data."""
    buffer = BytesIO()

    # Retrieve session date from the session or report
    from database.sessions import get_session_by_id
    session = get_session_by_id(session_id)
    if session and 'date' in session:
        session_date = session['date']
    else:
        # Fallback to current date if no date in session
        from datetime import datetime
        session_date = datetime.now().strftime("%Y-%m-%d")

    # Retrieve session number
    session_number = session.get('session_number', 'Unknown') if session else 'Unknown'

    # Retrieve therapist name
    therapist = get_user_by_id(therapist_id)
    therapist_name = therapist['FullName'] if therapist else "Dr. [Your Name/ID]"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.9 * inch
    )
    doc.session_date = session_date
    doc.child_name = child_name

    styles = getSampleStyleSheet()
    styles['BodyText'].fontName = 'Helvetica'
    styles['BodyText'].fontSize = 10
    styles['BodyText'].leading = 13
    styles['BodyText'].spaceAfter = 6
    styles.add(ParagraphStyle(name='ReportTitle', fontName='Helvetica-Bold', fontSize=18, textColor=colors.navy, leading=20, spaceAfter=0))
    styles.add(ParagraphStyle(name='SectionHeader', fontName='Helvetica-Bold', fontSize=14, spaceAfter=8, spaceBefore=12, textColor=colors.navy))
    styles.add(ParagraphStyle(name='SubTitle', fontName='Helvetica-Bold', fontSize=11, spaceAfter=4))
    styles.add(ParagraphStyle(name='UserInfo', fontName='Helvetica', fontSize=11, leading=14))
    styles.add(ParagraphStyle(name='TableValue', fontName='Helvetica', fontSize=10, leading=13))
    metric_style = ParagraphStyle('MetricLabel', fontName='Helvetica-Bold', fontSize=10, leading=13)
    metric_style1 = ParagraphStyle('MetricLabel', fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=colors.white)

    story = []

    # --- Header: Title with Logos ---
    # Create header table with title on left and logos on right
    header_data = [
        [
            Paragraph(REPORT_TITLE, styles['ReportTitle']),
            Table([
                [Image("assets/usm_logo.png", width=1.0*inch, height=0.6*inch),
                 Image("assets/advantech_logo.png", width=1.8*inch, height=0.8*inch)]
            ], colWidths=[1.0*inch, 1.8*inch], style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        ]
    ]
    header_table = Table(header_data, colWidths=[doc.width * 0.7, doc.width * 0.3])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.12 * inch))

    # Child Info
    info_table_data = [
        [Paragraph('<b>CHILD NAME:</b>', styles['UserInfo']), Paragraph(child_name, styles['UserInfo']),
         Paragraph('<b>SESSION DATE:</b>', styles['UserInfo']), Paragraph(session_date, styles['UserInfo'])],
        [Paragraph('<b>CHILD AGE:</b>', styles['UserInfo']), Paragraph(child_age, styles['UserInfo']),
         Paragraph('<b>CLINICIAN:</b>', styles['UserInfo']), Paragraph(therapist_name, styles['UserInfo'])]
    ]
    info_table = Table(info_table_data, colWidths=[1.25 * inch, 2.5 * inch, 1.25 * inch, 2.5 * inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7F9FB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.18 * inch))

    # Summary
    story.append(Paragraph(f"SUMMARY OF SESSION {session_number}", styles["SectionHeader"]))
    story.append(Paragraph(content.get("Summary", "-"), styles['BodyText']))
    story.append(Spacer(1, 0.08 * inch))

    # Detailed metrics table
    story.append(Paragraph("DETAILED ANALYSIS RESULTS", styles["SectionHeader"]))

    # *** FIX: Cleaned up metric_data definition. ***
    metric_data = [
        [Paragraph('METRIC', metric_style1), Paragraph('VALUE / OBSERVATION', metric_style1)],
        [Paragraph("Focus Percent:", metric_style), Paragraph(content.get("Focus Percent", "-"), styles['TableValue'])],
        [Paragraph("MLU (Mean Length of Utterance):", metric_style), Paragraph(content.get("MLU (Mean Length of Utterance)", "-"), styles['TableValue'])],
        [Paragraph("Vocabulary (TTR/Words):", metric_style), Paragraph(content.get("Vocabulary (TTR/Words)", "-"), styles['TableValue'])],
        [Paragraph("Syntax:", metric_style), Paragraph(content.get("Syntax", "-"), styles['TableValue'])],
        [Paragraph("Conversational Skills:", metric_style), Paragraph(content.get("Conversational Skills", "-"), styles['TableValue'])],
        [Paragraph("Emotion Summary:", metric_style), Paragraph(content.get("Emotion Summary", "-"), styles['TableValue'])],
        [Paragraph("Semantic Pairs:", metric_style), Paragraph(content.get("Semantic Pairs", "-"), styles['TableValue'])],
    ]
    metric_table = Table(metric_data, colWidths=[2.2 * inch, None], repeatRows=1)
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), # This makes the header text white
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 0.18 * inch))

    # Page break before Performance Visualizations
    story.append(PageBreak())

    # Charts
    story.append(Paragraph("PERFORMANCE VISUALIZATIONS", styles["SectionHeader"]))
    focus_drawing = create_focus_bar_drawing(content.get("Focus Percent", "0.0"))
    emotion_drawing = create_emotion_pie_chart(content)

    subtitle_row = Table([
        [Paragraph('<b>Focus Percentage (Observed vs. Target)</b>', styles['SubTitle']),
         Paragraph('<b>Emotion Consistency Breakdown</b>', styles['SubTitle'])]
    ], colWidths=[doc.width * 0.55, doc.width * 0.45])
    subtitle_row.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))

    charts_table = Table(
        [
            [focus_drawing, emotion_drawing]
        ],
        colWidths=[doc.width * 0.55, doc.width * 0.45]
    )
    charts_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(subtitle_row)
    story.append(charts_table)
    story.append(Spacer(1, 0.2 * inch))

    # Clinical Diagnosis
    story.append(Paragraph("CLINICAL DIAGNOSIS", styles["SectionHeader"]))
    diag_box = Paragraph(content.get("Diagnosis", "-"), ParagraphStyle(
        name="DiagBox",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.white,
        backColor=colors.darkred,
        leading=14,
        leftIndent=6,
        rightIndent=6,
        spaceBefore=6,
        spaceAfter=6,
    ))
    story.append(diag_box)
    story.append(Spacer(1, 0.12 * inch))

    # Recommendations and Future Goals
    story.append(Paragraph("RECOMMENDATIONS", styles["SectionHeader"]))
    story.append(Paragraph(content.get("Recommendations", "-"), styles['BodyText']))
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph("FUTURE GOALS", styles["SectionHeader"]))

    # *** FINAL FIX: Rendering HTML list structure ***
    html_goals = content.get("Future Goals_HTML", "No future goals specified.")

    goal_style = ParagraphStyle(
        name='GoalListStyle',
        parent=styles['BodyText']
    )
    story.append(Paragraph(html_goals, goal_style))

    story.append(Spacer(1, 0.4 * inch))

    # Signature
    story.append(Paragraph("___________________________________", styles["BodyText"]))
    story.append(Paragraph("Clinician Signature / Date", styles["BodyText"]))

    # Build the document to the in-memory buffer
    doc.build(story, onFirstPage=footer_and_page_number, onLaterPages=footer_and_page_number)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes

def logout():
    """Clears session state and cookies for logout and forces a rerun."""
    # Clear cookies
    clear_cookies(st.session_state.get('cookies'))
    # Clear session state keys related to the logged-in user
    if 'logged_in' in st.session_state:
        del st.session_state['logged_in']
    if 'user_id' in st.session_state:
        del st.session_state['user_id']
    if 'user_role' in st.session_state:
        del st.session_state['user_role']
    if 'full_name' in st.session_state:
        del st.session_state['full_name']
    if 'user_email' in st.session_state:
        del st.session_state['user_email']

    # Rerun the app to go back to the main login/home page
    st.rerun()

# Logout button in sidebar
with st.sidebar:
    if st.button("Logout", icon=":material/logout:", help="Click to securely log out", use_container_width=True):
        logout()

st.markdown("""
    <style>
        .safe-header {
            background-color: #004280;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="safe-header">
    <h2 style="margin: 0;">Reports</h2>
    <p style="margin: 0;">View approved session reports.</p>
</div>
""", unsafe_allow_html=True)

from database.children import get_children_by_parent

parent_id = st.session_state.get('user_id')
children = get_children_by_parent(parent_id)

if children:
    child_names = [child['Name'] for child in children]
    selected_child_name = st.selectbox("Select Child", child_names, key="child_select")

    # Find the selected child's ID
    selected_child = next((child for child in children if child['Name'] == selected_child_name), None)
    if selected_child:
        child_id = selected_child['ChildID']
        sessions = get_sessions_by_child(child_id)

        if sessions:
            # Sort sessions by session_number
            sessions_sorted = sorted(sessions, key=lambda s: s['session_number'])
            # Create display numbers starting from 1
            display_numbers = list(range(1, len(sessions_sorted) + 1))
            selected_display_number = st.selectbox("Select Session Number", display_numbers, key="session_select")

            # Find the selected session based on the display number (index in sorted list)
            selected_session = sessions_sorted[selected_display_number - 1]  # -1 because list is 0-indexed
            if selected_session:
                session_id = selected_session['session_id']

                # Fetch reports for the child and filter by session and approved
                reports = get_reports_by_child(child_id)
                approved_reports = [report for report in reports if report.get('Approved', False) and report.get('SessionID') == session_id]

                if approved_reports:
                    for report in approved_reports:
                        with st.expander(f"Report for {selected_child_name} - Session {selected_display_number}"):
                            st.write(report['NLP_Text'])
                            st.write("Therapist Notes:", report.get('Notes', 'None'))

                            # Generate PDF for download
                            content = parse_nlp_text_to_content(report['NLP_Text'], session_id)
                            child_name = content['CHILD_NAME']
                            child_age = content['CHILD_AGE']
                            pdf_bytes = generate_report_pdf(content, child_name, child_age, session_id, report.get('TherapistID'))
                            # Get session date for filename
                            session_date = selected_session['date'] if selected_session and 'date' in selected_session else "YYYY-MM-DD"
                            filename = OUTPUT_FILENAME_TEMPLATE.format(
                                CHILD_NAME=child_name.replace(" ", "_"),
                                SESSION_DATE=session_date
                            )
                            st.download_button(
                                label="Download as PDF",
                                data=pdf_bytes,
                                file_name=filename,
                                mime="application/pdf",
                                key=f"download_{report['ReportID']}",
                                type="primary",
                                use_container_width=True
                            )
                else:
                    st.write("No approved report yet.")
        else:
            st.write("No sessions available for this child.")
else:
    st.write("No children found.")

render_footer()
