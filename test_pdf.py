import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pages.therapist.report_note_approval import parse_nlp_text_to_content, generate_report_pdf

# Sample NLP_Text for testing
sample_nlp_text = """
**Child Name:** John Doe
**Age:** 5

**Summary:**
John showed good engagement during the session. He participated actively in the conversation.

**Analysis Results:**
1. Focus Percent: 0.75
2. MLU (Mean Length of Utterance): 4.2
3. Vocabulary: TTR=0.65, Words=150
4. Syntax: Good sentence structure observed.
5. Conversational Skills: Turn-taking was appropriate.
6. Emotion Summary: Child was consistently happy with 0.8 consistency.
7. Semantic Pairs: 5 pairs analyzed.

**Diagnosis:**
John appears to be developing normally for his age with no significant concerns.

**Recommendations:**
Continue with current therapy approach. Focus on expanding vocabulary.

**Future Goals:**
1. Improve vocabulary by 20%
2. Enhance conversational skills
3. Increase focus duration
"""

def test_pdf_generation():
    print("Testing PDF generation...")

    # Parse the content
    content = parse_nlp_text_to_content(sample_nlp_text)
    print("Parsed content keys:", list(content.keys()))

    # Generate PDF
    pdf_bytes = generate_report_pdf(content, "John Doe", "5", "2024-12-13")
    print(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")

    # Save to file for inspection
    with open("test_report.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("PDF saved as test_report.pdf")

    return True

if __name__ == "__main__":
    test_pdf_generation()
