import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from rag.embeddings import get_chat_model
from rag.pdf_loader import load_pdf_text, split_text
from rag.vector_store import build_vector_store, retrieve_relevant_docs


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}
MAX_CONTENT_LENGTH = 24 * 1024 * 1024
MIN_RETRIEVAL_SCORE = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.12"))

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

CHAT_SESSIONS = {}


def api_error(message, status=400):
    return jsonify({"ok": False, "error": message}), status


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def create_session_state(filename, vector_store, chunk_count):
    session_id = uuid.uuid4().hex
    CHAT_SESSIONS[session_id] = {
        "filename": filename,
        "vector_store": vector_store,
        "chunk_count": chunk_count,
        "created_at": time.time(),
        "messages": [],
    }
    return session_id


def build_prompt(context, question):
    return f"""
You are DATAGPT AI, a PDF-grounded assistant.
Answer the user's question using only the PDF context below.
If the answer is not clearly present in the context, reply exactly:
The question does not match the uploaded PDF.

PDF context:
{context}

Question:
{question}
""".strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "pdf" not in request.files:
        return api_error("Please choose a PDF file.")

    file = request.files["pdf"]
    if not file or not file.filename:
        return api_error("Please choose a PDF file.")

    if not allowed_file(file.filename):
        return api_error("Only PDF files are supported.")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return api_error("Groq API key is missing. Add GROQ_API_KEY to your .env file.", 500)

    original_name = secure_filename(file.filename)
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    filepath = UPLOAD_DIR / stored_name
    file.save(filepath)

    try:
        text = load_pdf_text(filepath)
        chunks = split_text(text)
        if not chunks:
            return api_error("No readable text was found in this PDF.", 422)

        vector_store = build_vector_store(chunks)
        session_id = create_session_state(original_name, vector_store, len(chunks))

        return jsonify(
            {
                "ok": True,
                "session_id": session_id,
                "filename": original_name,
                "chunks": len(chunks),
                "message": "PDF uploaded and indexed successfully.",
            }
        )
    except Exception as exc:
        return api_error(f"Could not process this PDF: {exc}", 500)
    finally:
        try:
            filepath.unlink(missing_ok=True)
        except OSError:
            pass


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    question = (data.get("message") or "").strip()

    if not session_id or session_id not in CHAT_SESSIONS:
        return api_error("Upload a PDF before asking questions.", 404)

    if not question:
        return api_error("Type a question first.")

    session = CHAT_SESSIONS[session_id]

    try:
        docs, confidence = retrieve_relevant_docs(session["vector_store"], question)
        if not docs or confidence < MIN_RETRIEVAL_SCORE:
            answer = "The question does not match the uploaded PDF."
        else:
            context = "\n\n".join(doc.page_content for doc in docs)
            response = get_chat_model().invoke(build_prompt(context, question))
            answer = (getattr(response, "content", None) or str(response)).strip()
            if not answer:
                answer = "The question does not match the uploaded PDF."

        message_pair = {
            "question": question,
            "answer": answer,
            "confidence": round(confidence, 3),
            "timestamp": int(time.time()),
        }
        session["messages"].append(message_pair)

        return jsonify({"ok": True, **message_pair})
    except Exception as exc:
        return api_error(f"Could not answer right now: {exc}", 500)


@app.errorhandler(413)
def file_too_large(_):
    return api_error("The PDF is too large. Upload a file under 24 MB.", 413)


if __name__ == "__main__":
    app.run(debug=True)
