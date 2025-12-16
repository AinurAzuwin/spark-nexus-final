import streamlit as st
from streamlit_option_menu import option_menu
from database.children import get_children_by_therapist
from database.reports import get_reports_by_child, approve_report, create_report, update_report_text
from database.sessions import get_sessions_by_child, get_session_by_id
from database.nlp import get_nlp_result, save_nlp_result, get_previous_nlp_result
from database.users import get_user_by_id
from nlp.llm_report_generator import generate_report_text
from nlp.nlp import run_full_analysis, get_focus_summary, get_emotion_profile
from utils.session_state import clear_cookies
from utils.ui_components import render_footer
import uuid
import os
import re
import json

def strip_markdown(text):
    """Strip basic markdown formatting to display as plain text with bold preserved."""
    # Remove italic
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Remove headers
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Remove links
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    return text

def format_report_text(text):
    """Convert markdown report to plain text format as specified."""
    # Strip markdown formatting
    text = strip_markdown(text)
    # Remove any remaining **
    text = re.sub(r'\*\*', '', text)
    # Replace A – Assessment (Screening Interpretation) with A – Assessment
    text = re.sub(r'A – Assessment \(Screening Interpretation\)', r'A – Assessment', text)
    # Add colons to S, O, and A sections if not already present
    text = re.sub(r'(S – Subjective)(?!:)', r'\1:', text)
    text = re.sub(r'(O – Objective)(?!:)', r'\1:', text)
    text = re.sub(r'(A – Assessment)(?!:)', r'\1:', text)
    # Remove extra spaces and normalize
    text = re.sub(r'\n\s*\n', '\n', text)
    # Ensure double newline before major sections
    text = re.sub(r'(\n[A-Z] – [A-Za-z]+.*?:)', r'\n\n\1', text)
    # Add extra newlines before Age: and Summary: for separation
    text = re.sub(r'\nAge:', r'\n\nAge:', text)
    text = re.sub(r'\nSummary:', r'\n\nSummary:', text)
    # Handle Analysis Results section
    text = re.sub(r'(Analysis Results:)', r'\n\n\1', text)
    # Handle numbered items
    text = re.sub(r'(\n\d+\.)', r'\n\1', text)
    # Clean up extra newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Add bold formatting to specific sections
    bold_phrases = [
        r'Therapy Session Report \(SOAP Format\)',
        r'Child Name:',
        r'Age:',
        r'2\. Emotion Summary:',
        r'2\. Emotion:',
        r'Summary:',
        r'S – Subjective:',
        r'O – Objective:',
        r'Analysis Results:',
        r'1\. Focus Percent:',
        r'3\. Vocabulary:',
        r'4\. Syntax:',
        r'5\. MLU \(Mean Length of Utterance\):',
        r'6\. Conversational Skills:',
        r'7\. Semantic Pairs:',
        r'A – Assessment:',
        r'P – Plan:'
    ]
    for phrase in bold_phrases:
        text = re.sub(rf'({phrase})', r'**\1**', text)
    return text.strip()
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
        "Summary": r"\*\*Summary:\*\*\n(.*?)(?=\n\*\*S – Subjective|$)",
        "S": r"\*\*S – Subjective:?\*\*\n(.*?)(?=\n\*\*O – Objective|$)",
        "O": r"\*\*O – Objective:?\*\*\n(.*?)(?=\n\*\*Analysis Results:|$)",
        "A": r"\*\*A – Assessment.*?:?\*\*\n(.*?)(?=\n\*\*P – Plan|$)",
        "P": r"\*\*P – Plan:?\*\*\n(.*?)$",
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
        match = re.search(rf"\*\*{re.escape(search_key)}:\*\*\n(.*?)(?=\n\*\*\d+\.|\n\*\*A – Assessment|\n\*\*Diagnosis|$)", nlp_text, re.DOTALL)
        if match:
            value = match.group(1).strip()
            content[content_key] = value

    # Retrieve actual Focus Percentage, MLU, and Emotion data from database if session_id is provided
    if session_id:
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

    # S – Subjective
    story.append(Paragraph("S – SUBJECTIVE", styles["SectionHeader"]))
    story.append(Paragraph(content.get("S", "-"), styles['BodyText']))
    story.append(Spacer(1, 0.08 * inch))

    # O – Objective
    story.append(Paragraph("O – OBJECTIVE", styles["SectionHeader"]))
    story.append(Paragraph(content.get("O", "-"), styles['BodyText']))
    story.append(Spacer(1, 0.08 * inch))

    # A – Assessment
    story.append(Paragraph("A – ASSESSMENT", styles["SectionHeader"]))
    story.append(Paragraph(content.get("A", "-"), styles['BodyText']))
    story.append(Spacer(1, 0.08 * inch))

    # P – Plan
    story.append(Paragraph("P – PLAN", styles["SectionHeader"]))
    story.append(Paragraph(content.get("P", "-"), styles['BodyText']))
    story.append(Spacer(1, 0.08 * inch))

    # Page break before Detailed Analysis
    story.append(PageBreak())

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

    # Signature
    signature_box = Paragraph("This is computer generated invoice no signature required*", ParagraphStyle(
        name="SignatureBox",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=colors.red,
        leading=12,
        spaceBefore=6,
        spaceAfter=6,
    ))
    story.append(signature_box)

    # Build the document to the in-memory buffer
    doc.build(story, onFirstPage=footer_and_page_number, onLaterPages=footer_and_page_number)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes

def display_preliminary_report(nlp_data):
    """Display the preliminary NLP report in a readable format."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Child Information")
        st.write(f"**Name:** {nlp_data.get('child_name', 'Unknown')}")
        st.write(f"**Age:** {nlp_data.get('child_age', 'Unknown')}")

        st.markdown("### Focus & Attention")
        focus_pct = nlp_data.get('focus_percent', 0.0)
        st.write(f"**Focus Percentage:** {focus_pct * 100:.1f}%")
        st.progress(focus_pct)

    with col2:
        st.markdown("### Emotion Analysis")
        emotion = nlp_data.get('emotion_summary', {})
        st.write(f"**Dominant Emotion:** {emotion.get('dominant', 'Unknown')}")
        st.write(f"**Consistency:** {emotion.get('consistency', 0.0) * 100:.1f}%")

        if emotion.get('counts'):
            st.markdown("**Emotion Distribution:**")
            for emo, count in emotion['counts'].items():
                st.write(f"- {emo}: {count}")

    st.markdown("### Language Development")

    # Vocabulary metrics
    vocab = nlp_data.get('vocabulary', {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Type-Token Ratio", f"{vocab.get('ttr', 0.0):.2f}")
    with col2:
        st.metric("Total Words", vocab.get('total_words', 0))
    with col3:
        st.metric("Unique Words", vocab.get('unique_words', 0))

    # Syntax metrics
    syntax = nlp_data.get('syntax', {})
    st.markdown("**Syntax Analysis:**")
    st.write(f"- Number of Sentences: {syntax.get('num_sentences', 0)}")
    st.write(f"- Average Sentence Length: {syntax.get('avg_sentence_len_words', 0.0):.1f} words")
    st.write(f"- Complete Sentences: {syntax.get('complete_sentences', 0)}")
    st.write(f"- Incomplete Sentences: {syntax.get('incomplete_sentences', 0)}")

    # MLU and Conversational
    conv = nlp_data.get('conversational', {})
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Mean Length of Utterance (MLU)", f"{nlp_data.get('mlu', 0.0):.2f}")
    with col2:
        st.metric("Child Turn Ratio", f"{conv.get('turn_ratio_child_over_total', 0.0):.2f}")

    st.markdown("**Conversational Patterns:**")
    st.write(f"- Child Turns: {conv.get('child_turns', 0)}")
    st.write(f"- Assistant Turns: {conv.get('assistant_turns', 0)}")

    # Semantic pairs
    pairs = nlp_data.get('semantic_pairs', [])
    if pairs:
        st.markdown("### Semantic Analysis")
        st.write(f"**Average Pair Similarity:** {nlp_data.get('avg_pair_similarity', 0.0):.3f}")

        with st.expander("View Semantic Pairs"):
            for i, pair in enumerate(pairs[:10]):  # Show first 10 pairs
                st.write(f"**Pair {i+1}:** Similarity = {pair.get('similarity', 0.0):.3f}")
                st.write(f"- Assistant: {pair.get('assistant', '')[:100]}...")
                st.write(f"- Child: {pair.get('child', '')[:100]}...")
                st.divider()

    # Diagnosis
    diagnosis = nlp_data.get('diagnosis', [])
    if diagnosis:
        st.markdown("### Potential Diagnosis")
        for diag in diagnosis:
            st.info(f"**{diag.get('label', 'Unknown')}:** {diag.get('reason', '')}")



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
        .report-text {
            overflow-x: hidden;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="safe-header">
    <h2 style="margin: 0;">Report and Note Approval</h2>
    <p style="margin: 0;">Review and approve NLP reports.</p>
</div>
""", unsafe_allow_html=True)

therapist_id = st.session_state.get('user_id')
children = get_children_by_therapist(therapist_id)

selected = option_menu(
    menu_title=None,
    options=["Generate New Reports", "Reports Approval", "Approved Reports"],
    icons=["bi-file-earmark-plus", "bi-check-circle", "bi-check-circle-fill"],
    manual_select=st.session_state.get('selected_tab_index', 0),
    orientation="horizontal",
)



if selected == "Generate New Reports":

    if children:
        for child in children:
            with st.expander(f"Generate Report for {child['Name']}"):
                sessions = get_sessions_by_child(child['ChildID'])
                sessions = sorted(sessions, key=lambda s: int(s.get('session_number', 0)))
                if sessions:
                    session_options = {session['session_id']: f"Session {session.get('session_number', session['session_id'])}" for session in sessions}
                    selected_session = st.selectbox(
                        f"Select session for {child['Name']}:",
                        options=list(session_options.keys()),
                        format_func=lambda x: session_options[x],
                        key=f"session_{child['ChildID']}"
                    )

                    # Check if NLP analysis already exists for this session
                    existing_nlp = get_nlp_result(selected_session)

                    if existing_nlp:
                        # Show preliminary report
                        st.subheader(f"Preliminary NLP Report for {child['Name']}")
                        display_preliminary_report(existing_nlp)

                        # Check if a summary report already exists for this session
                        reports = get_reports_by_child(child['ChildID'])
                        report_exists = any(report['SessionID'] == selected_session for report in reports)

                        if not report_exists:
                            # Button to generate LLM summary
                            st.divider()
                            if st.button(f"Generate Summary Report for {child['Name']}", key=f"summary_{child['ChildID']}", type="primary", use_container_width=True):
                                with st.spinner("Generating summary report..."):
                                    # Get previous NLP data for comparison if available
                                    previous_nlp = get_previous_nlp_result(selected_session)
                                    # Generate report text using LLM
                                    report_text = generate_report_text(existing_nlp, previous_nlp)

                                    # Create report in database
                                    report_id = str(uuid.uuid4())
                                    create_report(
                                        report_id=report_id,
                                        child_id=child['ChildID'],
                                        therapist_id=therapist_id,
                                        session_id=selected_session,
                                        nlp_text=report_text
                                    )

                                st.success(f"Summary report generated successfully for {child['Name']}!")
                                st.rerun()
                    else:
                        # Generate preliminary report
                        if st.button(f"Generate Preliminary Report for {child['Name']}", key=f"generate_{child['ChildID']}", type="primary", use_container_width=True):
                            with st.spinner("Running NLP analysis..."):
                                # First run NLP analysis on the session
                                nlp_data = run_full_analysis(selected_session)

                                # Save NLP results to database
                                save_nlp_result(selected_session, nlp_data)

                            st.success(f"Preliminary report generated successfully for {child['Name']}! Please refresh to view the report.")
                            st.rerun()
                else:
                    st.write(f"No sessions available for {child['Name']}.")
    else:
        st.write("No children assigned.")

elif selected == "Reports Approval":
    if children:
        for child in children:
            reports = get_reports_by_child(child['ChildID'])
            for report in reports:
                if not report.get('Approved', False):
                    session = get_session_by_id(report.get('SessionID'))
                    session_display = session.get('session_number', report.get('SessionID', 'Unknown')) if session else report.get('SessionID', 'Unknown')
                    with st.expander(f"Report for Session {session_display} - {child['Name']}"):
                        edit_key = f"edit_{report['ReportID']}"
                        is_editing = st.session_state.get(edit_key, False)

                        if is_editing:
                            edited_text = st.text_area(
                                "Edit Report Text:",
                                value=report['NLP_Text'],
                                height=300,
                                key=f"textarea_{report['ReportID']}"
                            )
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("Save Changes", key=f"save_{report['ReportID']}", type="primary", use_container_width=True):
                                    update_report_text(report['ReportID'], edited_text)
                                    st.success("Report updated successfully!")
                                    st.session_state[edit_key] = False
                                    st.rerun()
                            with col2:
                                if st.button("Cancel Edit", key=f"cancel_{report['ReportID']}", use_container_width=True):
                                    st.session_state[edit_key] = False
                                    st.rerun()
                            with col3:
                                if st.button(f"Approve Report", key=f"approve_{report['ReportID']}", type="secondary", use_container_width=True):
                                    approve_report(report['ReportID'])
                                    st.success("Report approved successfully!")
                                    st.session_state['selected_tab_index'] = 2
                                    st.rerun()
                        else:
                            formatted = format_report_text(report["NLP_Text"])
                            lines = formatted.split('\n', 1)
                            st.markdown('<b>' + lines[0] + '</b>', unsafe_allow_html=True)
                            if len(lines) > 1:
                                st.markdown(lines[1], unsafe_allow_html=True)
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"Edit Report", key=f"edit_btn_{report['ReportID']}", use_container_width=True):
                                    st.session_state[edit_key] = True
                                    st.rerun()
                            with col2:
                                if st.button(f"Approve Report", key=f"approve_{report['ReportID']}", type="primary", use_container_width=True):
                                    approve_report(report['ReportID'])
                                    st.success("Report approved successfully!")
                                    st.session_state['selected_tab_index'] = 2
                                    st.rerun()
    else:
        st.write("No children assigned.")

elif selected == "Approved Reports":
    if children:
        # Get unique parents from children assigned to therapist
        parent_ids = list(set(child['ParentID'] for child in children))
        parents = []
        for pid in parent_ids:
            parent = get_user_by_id(pid)
            if parent:
                parents.append(parent)

        if parents:
            # Select parent
            parent_options = {p['UserID']: p['FullName'] for p in parents}
            selected_parent_id = st.selectbox(
                "Select Parent:",
                options=list(parent_options.keys()),
                format_func=lambda x: parent_options[x],
                key="approved_parent_select"
            )

            # Get children of selected parent that are assigned to this therapist
            parent_children = [child for child in children if child['ParentID'] == selected_parent_id]

            if parent_children:
                # Select child
                child_options = {c['ChildID']: c['Name'] for c in parent_children}
                selected_child_id = st.selectbox(
                    "Select Child:",
                    options=list(child_options.keys()),
                    format_func=lambda x: child_options[x],
                    key="approved_child_select"
                )

                # Get approved reports for selected child
                reports = get_reports_by_child(selected_child_id)
                approved_reports = [report for report in reports if report.get('Approved', False)]

                if approved_reports:
                    # Sort approved reports by session number
                    def get_session_number(report):
                        session = get_session_by_id(report.get('SessionID'))
                        return int(session.get('session_number', 0)) if session else 0

                    approved_reports_sorted = sorted(approved_reports, key=get_session_number)

                    # Select report by session
                    report_options = {}
                    for report in approved_reports_sorted:
                        session = get_session_by_id(report.get('SessionID'))
                        session_display = session.get('session_number', report.get('SessionID', 'Unknown')) if session else report.get('SessionID', 'Unknown')
                        report_options[report['ReportID']] = f"Session {session_display}"

                    selected_report_id = st.selectbox(
                        "Select Report:",
                        options=list(report_options.keys()),
                        format_func=lambda x: report_options[x],
                        key="approved_report_select"
                    )

                    # Display selected report
                    selected_report = next(r for r in approved_reports if r['ReportID'] == selected_report_id)
                    with st.expander(f"Approved Report for {child_options[selected_child_id]} - {report_options[selected_report_id]}"):
                        st.markdown(format_report_text(selected_report['NLP_Text']))

                        # Generate PDF for download
                        content = parse_nlp_text_to_content(selected_report['NLP_Text'], selected_report['SessionID'])
                        child_name = content['CHILD_NAME']
                        child_age = content['CHILD_AGE']
                        pdf_bytes = generate_report_pdf(content, child_name, child_age, selected_report['SessionID'], therapist_id)
                        # Get session date for filename
                        session = get_session_by_id(selected_report['SessionID'])
                        session_date = session['date'] if session and 'date' in session else "YYYY-MM-DD"
                        filename = OUTPUT_FILENAME_TEMPLATE.format(
                            CHILD_NAME=child_name.replace(" ", "_"),
                            SESSION_DATE=session_date
                        )
                        st.divider()
                        st.download_button(
                            label="Download as PDF",
                            data=pdf_bytes,
                            file_name=filename,
                            mime="application/pdf",
                            key=f"download_{selected_report_id}",
                            type="primary",
                            use_container_width=True
                        )
                else:
                    st.write(f"No approved reports for {child_options[selected_child_id]}.")
            else:
                st.write("No children assigned to this therapist for the selected parent.")
        else:
            st.write("No parents found.")
    else:
        st.write("No children assigned.")

render_footer()

