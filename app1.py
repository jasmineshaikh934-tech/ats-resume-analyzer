import streamlit as st
import PyPDF2
import re
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    ListFlowable, ListItem, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import tempfile
from datetime import datetime

# -------------------------------
# TEXT EXTRACTION
# -------------------------------

def extract_text(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text.lower()

def clean_text(text):
    return re.sub(r'[^a-zA-Z0-9\s%]', '', text).lower()

# -------------------------------
# GRADE BADGE
# -------------------------------

def get_grade(score):
    if score >= 85:
        return "🏆 Excellent"
    elif score >= 70:
        return "✅ Good"
    elif score >= 50:
        return "⚠ Average"
    else:
        return "❌ Poor"

# -------------------------------
# ATS CALCULATION
# -------------------------------

def calculate_ats(resume_text, jd_text=""):

    score = 0
    suggestions = []
    keyword_gap = []
    jd_match_percent = 0

    word_count = len(resume_text.split())

    # Resume Length (15)
    if 400 <= word_count <= 900:
        score += 15
    else:
        suggestions.append("Keep resume length between 400-900 words.")

    # Section Detection (20)
    sections = ["skills", "experience", "education", "project"]
    detected_sections = {}

    for sec in sections:
        if sec in resume_text:
            score += 5
            detected_sections[sec] = True
        else:
            detected_sections[sec] = False
            suggestions.append(f"Add '{sec}' section.")

    # Contact Info (15)
    if "@" in resume_text:
        score += 8
    else:
        suggestions.append("Email not detected.")

    if re.search(r'\d{10}', resume_text):
        score += 7
    else:
        suggestions.append("Phone number not detected properly.")

    # Action Verbs (10)
    action_verbs = [
        "developed","created","analyzed","built",
        "designed","implemented","managed","led","optimized"
    ]

    verb_count = sum(1 for v in action_verbs if v in resume_text)

    if verb_count >= 4:
        score += 10
    else:
        suggestions.append("Use more strong action verbs.")

    # Measurable Achievements (10)
    if "%" in resume_text:
        score += 10
    else:
        suggestions.append("Add measurable achievements using % or numbers.")

    # JD Matching (20)
    if jd_text.strip():
        resume_words = set(resume_text.split())
        jd_words = set(clean_text(jd_text).split())

        matched = resume_words.intersection(jd_words)
        missing = jd_words - resume_words

        jd_score = (len(matched) / len(jd_words)) * 20 if jd_words else 0
        score += jd_score

        jd_match_percent = round((len(matched) / len(jd_words)) * 100, 2) if jd_words else 0
        keyword_gap = list(missing)[:20]

        if keyword_gap:
            suggestions.append("Some job description keywords are missing.")

    return round(score,2), suggestions, detected_sections, keyword_gap, jd_match_percent

# -------------------------------
# AI REWRITE
# -------------------------------

def ai_rewrite(suggestions, keyword_gap):

    rewrite_text = []

    for s in suggestions:
        if "skills" in s.lower():
            rewrite_text.append("Example Skills: Python, SQL, Data Analysis, Power BI, Machine Learning.")
        if "experience" in s.lower():
            rewrite_text.append("Example Experience Bullet: Developed data pipeline improving efficiency by 25%.")
        if "education" in s.lower():
            rewrite_text.append("Example Education: B.Tech in Computer Science | 2024 | CGPA: 8.5")
        if "project" in s.lower():
            rewrite_text.append("Example Project: Built ATS Resume Analyzer using Python & Streamlit.")
        if "action verbs" in s.lower():
            rewrite_text.append("Use verbs like Developed, Led, Implemented, Optimized.")

    if keyword_gap:
        rewrite_text.append("Add these missing JD keywords naturally:")
        rewrite_text.append(", ".join(keyword_gap))

    if not rewrite_text:
        rewrite_text.append("Resume looks strong. Only minor improvements suggested.")

    return rewrite_text

# -------------------------------
# PDF GENERATOR
# -------------------------------

def generate_pdf(name, score, grade, suggestions, sections, keyword_gap, jd_match_percent):

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(temp.name, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>ATS Resume Analysis Report</b>", styles["Title"]))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph(f"<b>Candidate:</b> {name}", styles["Normal"]))
    elements.append(Paragraph(f"<b>ATS Score:</b> {score}%", styles["Normal"]))
    elements.append(Paragraph(f"<b>Grade:</b> {grade}", styles["Normal"]))
    elements.append(Paragraph(f"<b>JD Match:</b> {jd_match_percent}%", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Section Table
    elements.append(Paragraph("<b>Section Detection</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    section_data = [["Section", "Status"]]
    for sec, status in sections.items():
        section_data.append([sec.title(), "Present" if status else "Missing"])

    table = Table(section_data, colWidths=[220, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('ALIGN', (1,1), (-1,-1), 'CENTER')
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Keyword Gap
    if keyword_gap:
        elements.append(Paragraph("<b>Missing JD Keywords</b>", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        keyword_list = [ListItem(Paragraph(word, styles["Normal"])) for word in keyword_gap]
        elements.append(ListFlowable(keyword_list, bulletType='bullet'))
        elements.append(Spacer(1, 20))

    # Suggestions
    elements.append(Paragraph("<b>Improvement Suggestions</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    suggestion_list = [ListItem(Paragraph(s, styles["Normal"])) for s in suggestions]
    elements.append(ListFlowable(suggestion_list, bulletType='bullet'))

    doc.build(elements)
    return temp.name

# -------------------------------
# STREAMLIT UI
# -------------------------------

st.title("🚀 Pro Universal ATS Resume Analyzer")

if "history" not in st.session_state:
    st.session_state.history = []

name = st.text_input("Enter Your Name")
uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
jd_input = st.text_area("Paste Job Description (Optional Advanced Analysis)")

if uploaded_file and name:

    resume_text = clean_text(extract_text(uploaded_file))

    score, suggestions, sections, keyword_gap, jd_match_percent = calculate_ats(resume_text, jd_input)
    grade = get_grade(score)

    # Save History
    st.session_state.history.append({
        "Name": name,
        "Score": score,
        "Grade": grade,
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    st.subheader(f"🎯 ATS Score: {score}%")
    st.markdown(f"### {grade}")

    fig, ax = plt.subplots()
    ax.bar(["ATS Score"], [score])
    ax.set_ylim(0,100)
    st.pyplot(fig)

    st.write("### 📂 Section Detection")
    for sec, status in sections.items():
        st.write(f"{sec.title()}: {'✅ Present' if status else '❌ Missing'}")

    if keyword_gap:
        st.write("### ❌ Keyword Gap Analysis")
        st.write(keyword_gap)

    st.write("### 💡 Improvement Suggestions")
    for s in suggestions:
        st.write("-", s)

    if st.button("🤖 Generate AI Rewrite Suggestions"):
        rewrite_output = ai_rewrite(suggestions, keyword_gap)
        st.write("### ✨ AI Resume Rewrite Suggestions")
        for line in rewrite_output:
            st.write(line)

    pdf_path = generate_pdf(
        name, score, grade,
        suggestions, sections,
        keyword_gap, jd_match_percent
    )

    with open(pdf_path, "rb") as f:
        st.download_button("📥 Download Detailed ATS Report", f, "ATS_Report.pdf")

# -------------------------------
# HISTORY TABLE
# -------------------------------

if st.session_state.history:
    st.write("## 📜 Resume Analysis History")
    df = pd.DataFrame(st.session_state.history)
    st.dataframe(df)