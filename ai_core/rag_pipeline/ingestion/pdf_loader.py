import pdfplumber


def load_pdf(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages)

