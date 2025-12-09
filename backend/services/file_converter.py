"""
File Converter Service - конвертация PDF/DOC в изображения для OCR.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
import fitz  # PyMuPDF
from PIL import Image
from backend.config import get_settings

settings = get_settings()


class FileConverter:
    """Service for converting documents to images."""

    def __init__(self):
        self.dpi = 200  # Качество для OCR
        self.temp_dir = tempfile.gettempdir()

    def is_image(self, file_path: str) -> bool:
        """Check if file is already an image."""
        ext = Path(file_path).suffix.lower()
        return ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']

    def is_pdf(self, file_path: str) -> bool:
        """Check if file is PDF."""
        ext = Path(file_path).suffix.lower()
        return ext == '.pdf'

    def is_doc(self, file_path: str) -> bool:
        """Check if file is DOC/DOCX."""
        ext = Path(file_path).suffix.lower()
        return ext in ['.doc', '.docx']

    def convert_pdf_to_images(self, pdf_path: str) -> List[str]:
        """
        Convert PDF to list of image paths.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of paths to generated images
        """
        image_paths = []

        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Render page to image
            zoom = self.dpi / 72  # 72 is default PDF DPI
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)

            # Save as PNG
            output_path = os.path.join(
                self.temp_dir,
                f"{Path(pdf_path).stem}_page_{page_num + 1}.png"
            )
            pix.save(output_path)
            image_paths.append(output_path)

        doc.close()
        return image_paths

    def convert_doc_to_pdf(self, doc_path: str) -> str:
        """
        Convert DOC/DOCX to PDF using LibreOffice.

        Args:
            doc_path: Path to DOC/DOCX file

        Returns:
            Path to generated PDF
        """
        output_dir = self.temp_dir

        # Use LibreOffice to convert to PDF
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            doc_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

        # Find the output PDF
        pdf_path = os.path.join(output_dir, f"{Path(doc_path).stem}.pdf")

        if not os.path.exists(pdf_path):
            raise RuntimeError(f"PDF not created at {pdf_path}")

        return pdf_path

    def convert_doc_to_images(self, doc_path: str) -> List[str]:
        """
        Convert DOC/DOCX to images via PDF.

        Args:
            doc_path: Path to DOC/DOCX file

        Returns:
            List of image paths
        """
        # First convert to PDF
        pdf_path = self.convert_doc_to_pdf(doc_path)

        try:
            # Then convert PDF to images
            return self.convert_pdf_to_images(pdf_path)
        finally:
            # Cleanup intermediate PDF
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    def convert_to_images(self, file_path: str) -> List[str]:
        """
        Convert any supported file to images.

        Args:
            file_path: Path to file

        Returns:
            List of image paths (single item for images, multiple for PDFs/DOCs)
        """
        if self.is_image(file_path):
            return [file_path]

        if self.is_pdf(file_path):
            return self.convert_pdf_to_images(file_path)

        if self.is_doc(file_path):
            return self.convert_doc_to_images(file_path)

        ext = Path(file_path).suffix.lower()
        raise ValueError(f"Unsupported file type: {ext}. Supported: images, PDF, DOC, DOCX.")

    def cleanup_temp_images(self, image_paths: List[str], original_path: str):
        """Remove temporary images created during conversion."""
        for path in image_paths:
            if path != original_path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


# Singleton instance
file_converter = FileConverter()
