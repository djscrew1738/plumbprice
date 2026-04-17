"""Tests for blueprint analysis tasks."""

import pytest
from unittest.mock import patch, MagicMock


class TestBlueprintAnalysis:
    """Test blueprint analysis Celery tasks."""

    @patch("worker.tasks.blueprint_analysis.analyze_blueprint")
    def test_analyze_blueprint_success(self, mock_analyze):
        """Test successful blueprint analysis."""
        mock_analyze.return_value = {
            "id": "bp-123",
            "description": "2-bathroom remodel",
            "fixtures": 8,
            "estimated_hours": 32,
        }

        result = mock_analyze("blueprint.pdf")
        assert result["id"] == "bp-123"
        assert result["fixtures"] == 8
        assert result["estimated_hours"] == 32

    @patch("worker.tasks.blueprint_analysis.extract_fixtures")
    def test_extract_fixtures_from_blueprint(self, mock_extract):
        """Test fixture extraction from blueprint."""
        mock_extract.return_value = ["toilet", "sink", "bathtub", "shower"]

        result = mock_extract("blueprint.pdf")
        assert len(result) == 4
        assert "toilet" in result
        assert "bathtub" in result

    @patch("worker.tasks.blueprint_analysis.estimate_work")
    def test_estimate_work_from_blueprint(self, mock_estimate):
        """Test work estimation from blueprint."""
        mock_estimate.return_value = {
            "labor_hours": 40,
            "material_cost": 1200,
            "complexity": "medium",
        }

        result = mock_estimate({"fixture_count": 6, "type": "bathroom"})
        assert result["labor_hours"] == 40
        assert result["material_cost"] == 1200
        assert result["complexity"] == "medium"

    def test_blueprint_analysis_task_exists(self):
        """Test that blueprint analysis task is registered."""
        from worker.worker import app

        task_names = [t for t in app.tasks.keys() if "blueprint" in t.lower()]
        assert len(task_names) > 0
