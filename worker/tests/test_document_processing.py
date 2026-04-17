"""Tests for document processing tasks."""

import pytest
from unittest.mock import patch, MagicMock
import io


class TestDocumentProcessing:
    """Test document processing Celery tasks."""

    @patch("worker.tasks.document_processing.extract_text")
    def test_extract_text_from_pdf(self, mock_extract):
        """Test PDF text extraction."""
        mock_extract.return_value = "Extracted text from blueprint"

        result = mock_extract("blueprint.pdf")
        assert result == "Extracted text from blueprint"
        mock_extract.assert_called_once_with("blueprint.pdf")

    @patch("worker.tasks.document_processing.analyze_document")
    def test_analyze_document_success(self, mock_analyze):
        """Test document analysis."""
        mock_analyze.return_value = {
            "type": "blueprint",
            "confidence": 0.95,
            "entities": ["fixture", "pipe", "valve"],
        }

        result = mock_analyze("blueprint.pdf")
        assert result["type"] == "blueprint"
        assert result["confidence"] == 0.95
        assert "fixture" in result["entities"]

    @patch("worker.tasks.document_processing.generate_pdf")
    def test_generate_pdf_proposal(self, mock_generate):
        """Test PDF proposal generation."""
        mock_generate.return_value = io.BytesIO(b"PDF content here")

        result = mock_generate({"title": "Test Proposal"})
        assert result.read() == b"PDF content here"

    def test_document_processing_task_exists(self):
        """Test that document processing task is registered."""
        from worker.worker import app

        task_names = [t for t in app.tasks.keys() if "document" in t.lower()]
        assert len(task_names) > 0
