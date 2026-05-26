from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def load_pdf_text(path):
    reader = PdfReader(str(Path(path)))
    pages = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(f"[Page {index}]\n{text}")

    return "\n\n".join(pages).strip()


def split_text(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=220,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.create_documents([text])
