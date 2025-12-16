from openai import OpenAI
from config.settings import OPENAI_API_KEY
from typing import Dict, Any, Optional

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_report_text(nlp_data: Dict[str, Any], previous_nlp_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a report text using OpenAI API based on NLP data.
    If previous_nlp_data is provided, include a comparison section.
    """
    previous_info = ""
    if previous_nlp_data:
        previous_info = f"""
        Previous Session Data for Comparison:
        - Focus Percent: {previous_nlp_data.get('focus_percent', 0.0)}
        - Emotion Summary: {previous_nlp_data.get('emotion_summary', {})}
        - Vocabulary: {previous_nlp_data.get('vocabulary', {})}
        - Syntax: {previous_nlp_data.get('syntax', {})}
        - MLU: {previous_nlp_data.get('mlu', 0.0)}
        - Conversational Skills: {previous_nlp_data.get('conversational', {})}
        - Semantic Pairs: {previous_nlp_data.get('semantic_pairs', [])}
        - Diagnosis: {previous_nlp_data.get('diagnosis', [])}

        Include a comparison in the Summary section, noting improvements or areas needing attention compared to the previous session.
        """

    # Prepare data for sections
    semantic_pairs_data = nlp_data.get('semantic_pairs', [])
    emotion_summary_data = nlp_data.get('emotion_summary', {})
    vocabulary_data = nlp_data.get('vocabulary', {})
    syntax_data = nlp_data.get('syntax', {})
    conversational_data = nlp_data.get('conversational', {})

    prompt = f"""
    You are a licensed speech therapist preparing an AI-assisted clinical screening report for parents.
    The purpose of this report is to SUPPORT understanding of the child's language and attention development.
    This is a SCREENING report, NOT a medical diagnosis.

    Write in a clear, supportive, parent-friendly tone.
    Avoid medical jargon or explain it simply.
    Do NOT use the word "diagnosis".
    Use terms such as "potential indicators", "risk level", or "patterns consistent with".

    Generate ONLY the report in the exact Markdown format below.
    Use ** for bold headings.
    Do NOT add extra text outside this format.
    IMPORTANT: Fill in ALL sections with appropriate content based on the NLP data provided. Do not leave any section empty or with placeholder text.

    NLP Data for Reference:
    - Focus Percent: {nlp_data.get('focus_percent', 0.0)}
    - Emotion Summary: {emotion_summary_data}
    - Vocabulary: {vocabulary_data}
    - Syntax: {syntax_data}
    - MLU: {nlp_data.get('mlu', 0.0)}
    - Conversational Skills: {conversational_data}
    - Semantic Pairs: {semantic_pairs_data}

    **Therapy Session Report (SOAP Format)**

    **Child Name:** {nlp_data.get('child_name', 'Unknown')}

    **Age:** {nlp_data.get('child_age', 'Unknown')}

    **Summary:**
    [Write a brief, parent-friendly summary of the child's performance in this session based on the provided NLP data. {'If previous data is provided, compare to the last session, highlighting progress or concerns.' if previous_nlp_data else 'This is the first session, so no comparison is available.'}]

    **S – Subjective:**
    [Summarize therapist observations, or child’s expressed difficulties in simple language in a paragraph based on the session data.]

    **O – Objective:**
    [Base this section strictly on the observed and measured session data from the NLP Data for Reference in a paragraph. Summarize the key metrics and findings.]

    **Analysis Results:**

    **1. Focus Percent:** {nlp_data.get('focus_percent', 0.0)}

    **2. Emotion Summary:**
    [Summarize the child's emotional expressions during the session in simple terms based on {emotion_summary_data}.]

    **3. Vocabulary:**
    [Describe the child's word usage and any notable vocabulary development based on {vocabulary_data}.]

    **4. Syntax:**
    [Explain the child's sentence structure and grammar in an accessible way based on {syntax_data}.]

    **5. MLU (Mean Length of Utterance):** {nlp_data.get('mlu', 0.0)}

    **6. Conversational Skills:**
    [Assess how well the child engaged in conversation, turn-taking, etc. based on {conversational_data}.]

    **7. Semantic Pairs:**
    [Describe the child's semantic understanding and word associations based on {semantic_pairs_data}.]

    IMPORTANT: The 'O – Objective' section must be a summary paragraph. Do not put the detailed list in 'O – Objective'. The detailed list belongs under 'Analysis Results:' with the numbered items.

    **A – Assessment (Screening Interpretation):**
    [Provide a professional screening interpretation based on S and O. Indicate ONE of the following patterns where appropriate:
    - Typical language development
    - Potential risk of language delay
    - Potential attention-related traits consistent with ADHD

    IMPORTANT RULES:
    - Do NOT state a medical diagnosis
    - Clearly mention that this is a preliminary screening interpretation
    - Use cautious and ethical wording]

    **P – Plan:**
    [Outline next steps for therapy support based on the assessment, including:
    - Focus areas for upcoming sessions
    - Home-based support suggestions
    - Monitoring or follow-up plans
    Do NOT include medical treatment or medication advice.]

    {previous_info}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional speech therapist generating reports based on NLP analysis."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating report: {str(e)}"
