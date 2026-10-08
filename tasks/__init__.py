"""Celery tasks package for distributed anti-piracy verification."""
from .verification import verify_url_task

__all__ = ["verify_url_task"]
