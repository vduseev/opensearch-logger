"""Module for Open/Elastic Search handlers."""

from .elasticsearch import ElasticSearchHandler
from .opensearch import OpenSearchHandler

__all__ = ["OpenSearchHandler", "ElasticSearchHandler"]
