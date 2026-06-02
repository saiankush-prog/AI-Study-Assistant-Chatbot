import os
import fitz  # PyMuPDF
import gradio as gr
from google import genai 

# =========================
# GEMINI CONFIGURATION
# =========================

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    API_KEY = "YOUR_NEW_REVOKED_REPLACEMENT_KEY_HERE"

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"❌ Initialization Error: Failed to create client wrapper. Details: {e}")

def ask_gemini_stream(prompt):
    try:
        response = client.models.generate_content_stream(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        
        text_accumulator = ""
        for chunk in response:
            if chunk.text:
                text_accumulator += chunk.text
                yield text_accumulator
                
    except Exception as e:
        yield f"❌ Gemini API Error: {e}"
# =========================
# PDF TEXT EXTRACTION
# =========================

def extract_text(pdf_path):
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        return f"Error reading PDF: {e}"
    return text

# =========================
# MAIN STUDY ASSISTANT
# =========================

def study_assistant(pdf_file, question):
    if pdf_file is None:
        yield "❌ Please upload a PDF."
        return

    if not question.strip():
        yield "❌ Please enter a question."
        return

    try:
        yield "🔄 Reading PDF file..."
        pdf_text = extract_text(pdf_file)

        if not pdf_text.strip() or pdf_text.startswith("Error reading PDF"):
            yield "❌ Could not extract text from this PDF. It might be scanned or empty."
            return

        pdf_text = pdf_text[:150000] 
        question_lower = question.lower()

        if "summary" in question_lower:
            task_prompt = f"Summarize this material:\n{pdf_text}"
        elif "quiz" in question_lower:
            task_prompt = f"Create a 5-question quiz with answers at the end:\n{pdf_text}"
        else:
            task_prompt = f"System: Answer using this material.\nMaterial:\n{pdf_text}\nQuestion: {question}"

        yield "🧠 Gemini is thinking and writing..."
        
        for partial_response in ask_gemini_stream(task_prompt):
            yield partial_response

    except Exception as e:
        yield f"❌ System Error: {e}"

        # --------------------------------
        # SPECIAL TASK DETECTION
        # --------------------------------
        if "summary" in question_lower:
            task_prompt = f"""
            Summarize the following study material.
            Requirements:
            - Use bullet points.
            - Keep it concise.
            - Highlight key concepts.

            Material:
            {pdf_text}
            """
        elif "quiz" in question_lower:
            task_prompt = f"""
            Create a quiz from the study material.
            Requirements:
            - 5 questions
            - Include answers at the end

            Material:
            {pdf_text}
            """
        elif "mcq" in question_lower:
            task_prompt = f"""
            Generate 5 MCQs from the study material.
            Requirements:
            - Four options each
            - Mention correct answer

            Material:
            {pdf_text}
            """
        elif "flashcard" in question_lower:
            task_prompt = f"""
            Generate 10 flashcards from the material.
            Format:
            Q: Question
            A: Answer

            Material:
            {pdf_text}
            """
        elif "study plan" in question_lower:
            task_prompt = f"""
            Create a 7-day study plan using the study material.
            Requirements:
            - Day-wise schedule
            - Revision day
            - Practice day

            Material:
            {pdf_text}
            """
        else:
            task_prompt = f"""
            You are an expert AI Study Assistant.
            Study Material:
            {pdf_text}

            Student Question:
            {question}

            Rules:
            - Answer accurately using the provided material.
            - Use simple language and clear examples when possible.
            - Use bullet points when appropriate.
            - If information is explicitly unavailable in the text, let the student know.
            """

        return ask_gemini(task_prompt)

    except Exception as e:
        return f"❌ System Error: {e}"

# =========================
# GRADIO INTERFACE
# =========================

interface = gr.Interface(
    fn=study_assistant,
    inputs=[
        gr.File(type="filepath", label="📄 Upload Study PDF"),
        gr.Textbox(
            lines=3,
            label="Ask a Question",
            placeholder="Examples:\nExplain Chapter 1\nGenerate Quiz\nGenerate MCQs\nGenerate Flashcards\nGenerate Summary\nCreate Study Plan"
        )
    ],
    outputs=gr.Textbox(
        lines=25,
        label="📚 AI Response",
        show_copy_button=True
    ),
    title="🎓 AI Study Assistant",
    description="Upload a document and query specific study milestones automatically.",
    theme=gr.themes.Soft()
)

if __name__ == "__main__":
    interface.launch(share=False, inbrowser=True)