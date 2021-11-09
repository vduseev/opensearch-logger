from datetime import datetime, timezone
import logging
import os

import pytest
from opensearch_logger import handlers

from opensearch_logger.handlers import OpensearchHandler


@pytest.fixture(scope="module")
def hosts():
    DEFAULT_OPENSEARCH_HOST = "https://localhost:9200"
    host = os.environ.get("TEST_OPENSEARCH_HOST", DEFAULT_OPENSEARCH_HOST)

    return [host]


@pytest.fixture(scope="module")
def test_date():
    return datetime(2021, 11, 8, tzinfo=timezone.utc)


def test_missing_opensearch_parameters():
    with pytest.raises(TypeError):
        OpensearchHandler(index_name="test-opensearch-logger")

    with pytest.raises(TypeError):
        OpensearchHandler()

    handler = OpensearchHandler(hosts=["https://localhost:9200"])
    assert handler.test_opensearch_connection() is False


def test_raise_on_index_exc():
    handler = OpensearchHandler(
        index_name="test-opensearch-logger",
        raise_on_index_exc=True,
        hosts=["http://nothere:30129"],
    )

    with pytest.raises(Exception):
        logger = logging.getLogger(test_raise_on_index_exc.__name__)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.warning("Message that will not happen")
        handler.flush()


def test_not_raise_on_index_exc():
    handler = OpensearchHandler(
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
    handler = OpensearchHandler(
        index_name="i",
        index_date_format="%Y-%m-%d",
        hosts=[],
    )
    assert handler._get_daily_index_name(test_date) == "i-2021-11-08"


def test_weekly_index_name(test_date):
    handler = OpensearchHandler(
        index_name="i",
        hosts=[],
    )
    assert handler._get_weekly_index_name(test_date) == "i-2021.11.08"
    assert handler._get_weekly_index_name(datetime(2021, 11, 10, 23, 59, 59, tzinfo=timezone.utc)) == "i-2021.11.08"
    assert handler._get_weekly_index_name(datetime(2021, 11, 10, 0, 0, 1, tzinfo=timezone.utc)) == "i-2021.11.08"


def test_monthly_index_name(test_date):
    handler = OpensearchHandler(
        index_name="name",
        index_date_format="%Y_%m_%d",
        index_name_sep="_",
        hosts=[],
    )
    assert handler._get_monthly_index_name(test_date) == "name_2021_11_01"


def test_yearly_index_name(test_date):
    handler = OpensearchHandler(
        index_name="index",
        index_date_format="%YZ",
        index_name_sep="_",
        hosts=[],
    )
    assert handler._get_yearly_index_name(test_date) == "index_2021Z"


def test_never_index_name(test_date):
    handler = OpensearchHandler(
        index_name="index",
        index_date_format="%Y-%m-%d",
        hosts=[],
    )
    assert handler._get_never_index_name() == "index"