import fitz  # PyMuPDF
import re

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extracts text from a PDF file using PyMuPDF.
    Handles both file paths and file-like objects (e.g., from Streamlit).
    """
    text = ""
    try:
        if isinstance(pdf_file, str):
            doc = fitz.open(pdf_file)
        else:
            # Revert to beginning if it was read before
            if hasattr(pdf_file, 'seek'):
                pdf_file.seek(0)
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            
        for page in doc:
            text += page.get_text()
            
        return clean_text(text)
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return ""

def clean_text(text: str) -> str:
    """
    Cleans the extracted text by removing unwanted newline characters,
    excessive whitespace, and potentially headers/footers.
    """
    if not text:
        return ""
        
    # Remove multiple newlines
    text = re.sub(r'\n+', '\n', text)
    # Remove excessive spaces
    text = re.sub(r' +', ' ', text)
    # Could add more rules for headers/footers
    
    return text.strip()
