"""
PDF Text Extraction Module

Extracts text from PDF files with paragraph preservation and metadata tracking.
Designed to work seamlessly with the text transformation pipeline.
"""

import io
import logging
from typing import NamedTuple

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logger = logging.getLogger(__name__)


class PDFExtractionResult(NamedTuple):
    """Result from PDF text extraction."""

    text: str  # Full extracted text
    page_count: int  # Number of pages in PDF
    paragraph_count: int  # Number of paragraphs detected
    word_count: int  # Approximate word count
    success: bool  # Whether extraction was successful
    error: str | None = None  # Error message if extraction failed


def extract_text_from_pdf(pdf_bytes: bytes) -> PDFExtractionResult:
    """
    Extract text from a PDF file.

    Args:
        pdf_bytes: Raw PDF file bytes (from file upload)

    Returns:
        PDFExtractionResult with extracted text and metadata

    Raises:
        ValueError: If PDF is invalid or cannot be read
    """
    if not pdfplumber:
        raise ImportError(
            "pdfplumber is not installed. Install with: pip install pdfplumber"
        )

    if not pdf_bytes:
        return PDFExtractionResult(
            text="",
            page_count=0,
            paragraph_count=0,
            word_count=0,
            success=False,
            error="Empty PDF file",
        )

    try:
        # Open PDF from bytes
        pdf_file = io.BytesIO(pdf_bytes)
        pdf = pdfplumber.open(pdf_file)

        page_count = len(pdf.pages)
        if page_count == 0:
            return PDFExtractionResult(
                text="",
                page_count=0,
                paragraph_count=0,
                word_count=0,
                success=False,
                error="PDF has no pages",
            )

        logger.info(f"Extracting text from PDF with {page_count} pages")

        # Extract text page-by-page, preserving paragraph structure
        pages_text = []
        for page_num, page in enumerate(pdf.pages, 1):
            try:
                # Extract text with layout preservation where possible
                page_text = page.extract_text()

                if page_text and page_text.strip():
                    pages_text.append(page_text)
                    logger.debug(f"Page {page_num}: {len(page_text)} chars extracted")
                else:
                    logger.warning(f"Page {page_num}: No extractable text found")

            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {e}")
                continue

        pdf.close()

        # Combine pages with paragraph-like spacing
        combined_text = "\n\n".join(pages_text)

        if not combined_text.strip():
            return PDFExtractionResult(
                text="",
                page_count=page_count,
                paragraph_count=0,
                word_count=0,
                success=False,
                error="No extractable text found in PDF",
            )

        # Count paragraphs (separated by double newlines)
        paragraph_count = len([p for p in combined_text.split("\n\n") if p.strip()])

        # Estimate word count
        word_count = len(combined_text.split())

        logger.info(
            f"PDF extraction successful: {page_count} pages, {paragraph_count} paragraphs, {word_count} words"
        )

        return PDFExtractionResult(
            text=combined_text,
            page_count=page_count,
            paragraph_count=paragraph_count,
            word_count=word_count,
            success=True,
            error=None,
        )

    except Exception as e:
        error_msg = f"PDF extraction failed: {str(e)}"
        logger.error(error_msg)
        return PDFExtractionResult(
            text="",
            page_count=0,
            paragraph_count=0,
            word_count=0,
            success=False,
            error=error_msg,
        )


def validate_pdf_file(filename: str) -> bool:
    """
    Validate that a file is a PDF.

    Args:
        filename: Name of the file

    Returns:
        True if file has .pdf extension, False otherwise
    """
    return filename.lower().endswith(".pdf")
