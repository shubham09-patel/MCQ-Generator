import os

import spacy
import random
import streamlit as st
import fitz  # PyMuPDF for PDF extraction
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    with st.spinner("Downloading SpaCy model..."):
        spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
    
# Load SpaCy model
nlp = spacy.load('en_core_web_sm')

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text += page.get_text()
    return text

# Function to generate MCQs
def generate_mcqs(text, num_questions=5):
    doc = nlp(text)
    sentences = [sentence.text for sentence in doc.sents]
    selected_sentences = random.sample(sentences, min(num_questions, len(sentences)))

    mcqs = []
    for sentence in selected_sentences:
        sent_doc = nlp(sentence)
        nouns = [token.text for token in sent_doc if token.pos_ == "NOUN"]
        if not nouns:  # Handle cases with no nouns
            continue

        subject = nouns[0]
        question_stem = sentence.replace(subject, "_______")
        answer_choices = [subject]

        all_tokens = [token.text for token in doc if token.pos_ in ["NOUN", "PROPN", "ADJ"] and token.text != subject]
        distractors = list(set(all_tokens) - set(answer_choices))

        while len(distractors) < 3:
            distractors.append("[Distractor]")

        random.shuffle(distractors)
        distractors = distractors[:3]

        answer_choices.extend(distractors)
        random.shuffle(answer_choices)

        correct_answer = chr(65 + answer_choices.index(subject))
        mcqs.append((question_stem, answer_choices, correct_answer))

    return mcqs

# Function to create a text file from MCQs
def create_text(mcqs):
    text_content = ""
    for idx, (question, choices, correct_answer) in enumerate(mcqs):
        text_content += f"Q{idx+1}: {question}\n"
        for i, choice in enumerate(choices):
            text_content += f"    {chr(65+i)}. {choice}\n"
        text_content += f"Correct Answer: {correct_answer}\n\n"
    return text_content

# Initialize Session State for tracking user answers
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}

if "check_clicked" not in st.session_state:
    st.session_state.check_clicked = False

if "mcqs" not in st.session_state:
    st.session_state.mcqs = []

# Sidebar for navigation
st.sidebar.title("Navigation")
st.sidebar.header("Instructions")
st.sidebar.write("1. Upload a PDF file to extract text.")
st.sidebar.write("2. Select the difficulty level and the number of questions.")
st.sidebar.write("3. Generate MCQs and check your answers.")
st.sidebar.write("4. Download the MCQs as a PDF or text file.")

# Sidebar options for settings
st.sidebar.header("Settings")
difficulty = st.sidebar.selectbox("Select difficulty level", options=["Easy", "Medium", "Hard"])
num_questions = st.sidebar.selectbox("Select number of questions", options=list(range(1, 11)), index=4)

# Streamlit UI for PDF upload
st.title("Enhanced PDF to MCQ Generator")
uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file is not None:
    with st.spinner("Extracting text from PDF..."):
        pdf_text = extract_text_from_pdf(uploaded_file)

    st.subheader("Extracted Text")
    st.write(pdf_text[:2000])  # Display the first 2000 characters

    # Generate MCQs Button
    if st.button("Generate MCQs"):
        with st.spinner("Generating MCQs..."):
            mcqs = generate_mcqs(pdf_text, num_questions)
            st.session_state.mcqs = mcqs
            st.session_state.user_answers = {idx: None for idx in range(len(mcqs))}
            st.session_state.check_clicked = False  # Reset check flag


    # MCQ Display
    if "mcqs" in st.session_state:
        mcqs = st.session_state.mcqs
        st.subheader("Generated MCQs")

        for idx, (question, choices, correct_answer) in enumerate(mcqs):
            st.write(f"**Q{idx + 1}.** {question}")

            # Add a placeholder to the choices
            choices_with_placeholder = ["Select an answer"] + choices

            # Store the user's selected answer in session state
            user_answer = st.radio(
                f"Choose an option for Q{idx + 1}:",
                choices_with_placeholder,
                index=0 if st.session_state.user_answers[idx] is None else choices_with_placeholder.index(
                    st.session_state.user_answers[idx]),
                key=f"radio_{idx}"
            )

            # Update user answers directly after radio selection
            st.session_state.user_answers[idx] = user_answer

        # Check Answers Button
        if st.button("Check Answers"):
            st.session_state.check_clicked = True

        # Show Results
        if st.session_state.check_clicked:
            st.subheader("Results")
            correct_count = 0
            for idx, (question, choices, correct_answer) in enumerate(mcqs):
                st.write(f"**Q{idx + 1}.** {question}")
                selected_answer = st.session_state.user_answers[idx]

                if selected_answer == "Select an answer" or selected_answer is None:
                    st.write(f"⚠️ **No option selected for this question!**")
                else:
                    correct_answer_text = \
                    [choice for choice in choices if chr(65 + choices.index(choice)) == correct_answer][0]
                    if selected_answer == correct_answer_text:
                        st.write("✅ **Correct!**")
                        correct_count += 1
                    else:
                        st.write(f"❌ **Wrong!** The correct answer is **{correct_answer_text}**.")
                st.write("---")
            st.write(f"Your score: {correct_count}/{len(mcqs)}")

        # Download MCQs as Text
        st.subheader("Download MCQs")
        text_content = create_text(st.session_state.mcqs)
        st.download_button(
            label="Download as Text",
            data=text_content,
            file_name="mcqs.txt",
            mime="text/plain"
        )
        
        