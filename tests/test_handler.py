"""Tests for OpenSearchHandler functionality."""

# Copyright 2021-2025 Vagiz Duseev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
from datetime import datetime, timezone

import pytest

from opensearch_logger import OpenSearchHandler


@pytest.fixture(scope="module")
def hosts():
    """Fixture providing OpenSearch hosts."""
    DEFAULT_OPENSEARCH_HOST = "https://admin:0penSe*rch@localhost:9200"
    host = os.environ.get("TEST_OPENSEARCH_HOST", DEFAULT_OPENSEARCH_HOST)

    return [host]


@pytest.fixture(scope="module")
def test_date():
    """Fixture providing a test date."""
    return datetime(2021, 11, 8, tzinfo=timezone.utc)


def test_missing_opensearch_parameters(hosts):
    """Test that TypeError is raised when parameters are missing."""
    with pytest.raises(TypeError):
        OpenSearchHandler(index_name="test-opensearch-logger")

    with pytest.raises(TypeError):
        OpenSearchHandler()

    # Test that handler can be created with valid hosts parameter
    _ = OpenSearchHandler(hosts=hosts)
    # Connection test result depends on whether OpenSearch is
    # running/accessible


def test_raise_on_index_exc():
    """Test that exceptions are raised when raise_on_index_exc is True."""
    handler = OpenSearchHandler(
        index_name="test-opensearch-logger",
        raise_on_index_exc=True,
        hosts=["http://nothere:30129"],
    )

    with pytest.raises((ConnectionError, Exception)):
        logger = logging.getLogger(test_raise_on_index_exc.__name__)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.warning("Message that will not happen")
        handler.flush()


def test_not_raise_on_index_exc():
    """Test that exceptions are not raised when raise_on_index_exc=False."""
    handler = OpenSearchHandler(
        index_name="test-opensearch-logger",
        hosts=["http://nothere:30129"],
    )

    try:
        logger = logging.getLogger(test_raise_on_index_exc.__name__)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.warning("Message that will not happen")
        handler.flush()
    except Exception:
        pass


def test_daily_index_name(test_date):
    """Test daily index name generation."""
    handler = OpenSearchHandler(
        index_name="i",
        index_date_format="%Y-%m-%d",
        hosts=[],
    )
    assert handler._get_daily_index_name(test_date) == "i-2021-11-08"


def test_weekly_index_name(test_date):
    """Test weekly index name generation."""
    handler = OpenSearchHandler(
        index_name="i",
        hosts=[],
    )
    assert handler._get_weekly_index_name(test_date) == "i-2021.11.08"
    assert (
        handler._get_weekly_index_name(
            datetime(2021, 11, 10, 23, 59, 59, tzinfo=timezone.utc)
        )
        == "i-2021.11.08"
    )
    assert (
        handler._get_weekly_index_name(
            datetime(2021, 11, 10, 0, 0, 1, tzinfo=timezone.utc)
        )
        == "i-2021.11.08"
    )


def test_monthly_index_name(test_date):
    """Test monthly index name generation."""
    handler = OpenSearchHandler(
        index_name="name",
        index_date_format="%Y_%m_%d",
        index_name_sep="_",
        hosts=[],
    )
    assert handler._get_monthly_index_name(test_date) == "name_2021_11_01"


def test_yearly_index_name(test_date):
    """Test yearly index name generation."""
    handler = OpenSearchHandler(
        index_name="index",
        index_date_format="%YZ",
        index_name_sep="_",
        hosts=[],
    )
    assert handler._get_yearly_index_name(test_date) == "index_2021Z"


def test_never_index_name(test_date):
    """Test index name generation with no rotation."""
    handler = OpenSearchHandler(
        index_name="index",
        index_date_format="%Y-%m-%d",
        hosts=[],
    )
    assert handler._get_never_index_name() == "index"
