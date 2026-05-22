import io
import logging

logger = logging.getLogger(__name__)

EXCEL_MIMETYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
PDF_MIMETYPES = {"application/pdf"}


def ler_excel(file_bytes: bytes, filename: str = "") -> str:
    import pandas as pd

    try:
        buf = io.BytesIO(file_bytes)
        xl = pd.ExcelFile(buf, engine="openpyxl")
        parts = []
        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name).dropna(how="all").fillna("")
            sheet_text = df.to_string(index=False)
            if len(xl.sheet_names) > 1:
                parts.append(f"[Aba: {sheet_name}]\n{sheet_text}")
            else:
                parts.append(sheet_text)
        return "\n\n".join(parts)
    except Exception as e:
        logger.error("excel_read_error", extra={"filename": filename, "error": str(e)})
        return f"[Erro ao ler Excel: {e}]"


def ler_pdf(file_bytes: bytes, filename: str = "") -> str:
    import pypdf

    try:
        buf = io.BytesIO(file_bytes)
        reader = pypdf.PdfReader(buf)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p for p in pages if p.strip())
    except Exception as e:
        logger.error("pdf_read_error", extra={"filename": filename, "error": str(e)})
        return f"[Erro ao ler PDF: {e}]"


def extrair_texto(file_bytes: bytes, mimetype: str, filename: str = "") -> str | None:
    fname = filename.lower()
    is_generic_mime = mimetype in ("application/octet-stream", "")

    if mimetype in EXCEL_MIMETYPES or (is_generic_mime and fname.endswith((".xlsx", ".xls"))):
        return ler_excel(file_bytes, filename)
    if mimetype in PDF_MIMETYPES or (is_generic_mime and fname.endswith(".pdf")):
        return ler_pdf(file_bytes, filename)
    return None
