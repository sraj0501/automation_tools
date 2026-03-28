"""Tests for the Task Manager API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from utils import validate_task_input, ValidationError


def test_valid_task():
    result = validate_task_input("Fix login bug", "high")
    assert result["title"] == "Fix login bug"
    assert result["priority"] == "high"


def test_empty_title_raises():
    with pytest.raises(ValidationError, match="empty"):
        validate_task_input("", "medium")


def test_invalid_priority_raises():
    with pytest.raises(ValidationError, match="Priority"):
        validate_task_input("Some task", "urgent")


def test_title_too_long_raises():
    with pytest.raises(ValidationError, match="200"):
        validate_task_input("x" * 201, "low")


def test_past_due_date_raises():
    with pytest.raises(ValidationError, match="past"):
        validate_task_input("Old task", "low", due_date="2020-01-01")


def test_valid_due_date():
    result = validate_task_input("Future task", "medium", due_date="2099-12-31")
    assert result["due_date"] == "2099-12-31"
