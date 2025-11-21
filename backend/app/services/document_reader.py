import os
from pathlib import Path
from urllib.parse import urlparse, unquote
import pdfplumber

def sanitize_file_path(file_path):
    if file_path.startswith("file://"):
        parsed_path = urlparse(file_path).path
        parsed_path = unquote(parsed_path)
        if os.name == "nt":
            parsed_path = parsed_path.lstrip("/")
        return parsed_path
    return file_path

def read_document(file_path):
    try:
        file_path = sanitize_file_path(file_path)
        if not os.path.exists(file_path):
            return None
        if file_path.lower().endswith(".pdf"):
            return read_pdf(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def read_pdf(file_path):
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text + "\n"
        return text.strip()
    except Exception:
        return None
