"""Integration tests for opensearch-logger."""

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
import time

import pytest

from opensearch_logger import ElasticSearchHandler


@pytest.fixture(scope="module")
def hosts():
    """Fixture providing OpenSearch hosts."""
    DEFAULT_OPENSEARCH_HOST = "https://admin:0penSe*rch@localhost:9200"
    host = os.environ.get("TEST_OPENSEARCH_HOST", DEFAULT_OPENSEARCH_HOST)

    return [host]


@pytest.fixture(scope="module")
def elasticsearch_config():
    """Generate ElasticSearch connection config based on host URL."""

    return {
        "host": "http://localhost:9201",
    }


def test_ping(elasticsearch_config):
    """Test OpenSearch connection ping."""
    handler = ElasticSearchHandler(
        index_name="test-elasticsearch-logger",
        **elasticsearch_config,
    )

    assert handler.test_opensearch_connection()

    logger = logging.getLogger(test_ping.__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.warning("Message zero")
    handler.flush()

    time.sleep(1)
    assert len(handler._buffer) == 0

    handler.close()


def test_buffered_log_flushed_when_buffer_full(elasticsearch_config):
    """Test that buffered logs are flushed when buffer is full."""
    handler = ElasticSearchHandler(
        index_name="test-elasticsearch-logger",
        index_rotate="DAILY",
        buffer_size=2,
        flush_frequency=1000,
        **elasticsearch_config,
    )

    assert handler.test_opensearch_connection()

    index = handler._get_index()
    start_count = handler._get_client().count(index=index)

    logger = logging.getLogger(
        test_buffered_log_flushed_when_buffer_full.__name__
    )
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.warning("Message one")
    logger.info("Message two")

    assert len(handler._buffer) == 0
    handler.close()

    time.sleep(5)
    end_count = handler._get_client().count(index=index)

    assert end_count["count"] - start_count["count"] == 2


def test_log_with_extra_fields(elasticsearch_config):
    """Test logging with extra fields."""
    handler = ElasticSearchHandler(
        index_name="test-elasticsearch-logger",
        flush_frequency=1000,
        extra_fields={"App": "test", "Nested": {"One": 1, "Two": 2}},
        **elasticsearch_config,
    )

    assert handler.test_opensearch_connection()

    index = handler._get_index()
    start_count = handler._get_client().count(index=index)

    logger = logging.getLogger(test_log_with_extra_fields.__name__)
    logger.addHandler(handler)
    logger.warning("Extra fields")

    assert len(handler._buffer) == 1
    assert handler._buffer[0]["App"] == "test"
    assert handler._buffer[0]["Nested"]["One"] == 1
    assert handler._buffer[0]["Nested"]["Two"] == 2
    assert "Environment" not in handler._buffer[0]

    handler.flush()
    assert len(handler._buffer) == 0
    handler.close()

    time.sleep(5)
    end_count = handler._get_client().count(index=index)
    assert end_count["count"] - start_count["count"] == 1


def test_log_extra_arguments(elasticsearch_config):
    """Test logging with extra arguments."""
    handler = ElasticSearchHandler(
        index_name="test-elasticsearch-logger",
        flush_frequency=1000,
        extra_fields={"App": "test", "Nested": {"One": 1, "Two": 2}},
        **elasticsearch_config,
    )

    assert handler.test_opensearch_connection()

    index = handler._get_index()
    start_count = handler._get_client().count(index=index)

    logger = logging.getLogger(test_log_extra_arguments.__name__)
    logger.addHandler(handler)

    logger.warning("Extra arguments", extra={"Arg1": True, "Arg2": 400.0})
    logger.warning("Extra arguments - another message")

    assert len(handler._buffer) == 2
    assert handler._buffer[0]["Arg1"] is True
    assert handler._buffer[0]["Arg2"] == 400
    assert handler._buffer[0]["App"] == "test"

    handler.flush()
    assert len(handler._buffer) == 0
    handler.close()

    time.sleep(5)
    end_count = handler._get_client().count(index=index)
    assert end_count["count"] - start_count["count"] == 2


def test_log_exception(elasticsearch_config):
    """Test logging exceptions."""
    handler = ElasticSearchHandler(
        index_name="test-elasticsearch-logger",
        flush_frequency=1000,
        **elasticsearch_config,
    )

    assert handler.test_opensearch_connection()

    index = handler._get_index()
    start_count = handler._get_client().count(index=index)

    logger = logging.getLogger(test_log_exception.__name__)
    logger.addHandler(handler)

    try:
        _ = 42 / 0
    except ZeroDivisionError:
        logger.exception("Division error")

    assert len(handler._buffer) == 1
    handler.flush()
    assert len(handler._buffer) == 0
    handler.close()

    time.sleep(5)
    end_count = handler._get_client().count(index=index)
    assert end_count["count"] - start_count["count"] == 1


def test_buffered_log_when_flush_frequency_reached(elasticsearch_config):
    """Test that logs are flushed when flush frequency is reached."""
    handler = ElasticSearchHandler(
        index_name="test-elasticsearch-logger",
        flush_frequency=0.1,
        **elasticsearch_config,
    )

    assert handler.test_opensearch_connection()

    index = handler._get_index()
    start_count = handler._get_client().count(index=index)
    handler.close()

    logger = logging.getLogger(
        test_buffered_log_when_flush_frequency_reached.__name__
    )
    logger.addHandler(handler)

    logger.warning("Frequency timeout reached")
    assert len(handler._buffer) == 1

    time.sleep(1)
    assert len(handler._buffer) == 0

    time.sleep(5)
    end_count = handler._get_client().count(index=index)
    assert end_count["count"] - start_count["count"] == 1


def test_fast_processing_of_many_logs(elasticsearch_config):
    """Test fast processing of many log messages."""
    handler = ElasticSearchHandler(
        index_name="test-elasticsearch-logger",
        flush_frequency=1000,
        **elasticsearch_config,
    )

    assert handler.test_opensearch_connection()

    index = handler._get_index()
    start_count = handler._get_client().count(index=index)

    logger = logging.getLogger(test_fast_processing_of_many_logs.__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    start_time = time.perf_counter()
    for i in range(100):
        logger.info(f"Fast processing of line {i}", extra={"line_number": i})
    handler.flush()

    assert len(handler._buffer) == 0
    handler.close()

    end_time = time.perf_counter()
    time.sleep(5)
    assert end_time - start_time < 5

    end_count = handler._get_client().count(index=index)
    assert end_count["count"] - start_count["count"] == 100


def test_logging_config(hosts, elasticsearch_config):
    """Test logging configuration."""
    import logging
    import logging.config

    # Build handler config from elasticsearch_config
    handler_config = {
        "level": "INFO",
        "class": "opensearch_logger.ElasticSearchHandler",
        "index_name": "test-elasticsearch-logger",
        "flush_frequency": 0.1,
        **elasticsearch_config,
    }

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"opensearch": handler_config},
        "loggers": {
            "foo": {
                "handlers": ["opensearch"],
                "level": "INFO",
                "propogate": False,
            }
        },
    }

    logging.config.dictConfig(LOGGING)

    handler = ElasticSearchHandler(
        index_name="test-elasticsearch-logger",
        flush_frequency=1000,
        **elasticsearch_config,
    )

    assert handler.test_opensearch_connection()

    index = handler._get_index()
    start_count = handler._get_client().count(index=index)

    logger = logging.getLogger("foo")
    logger.info("Logging based on dictConfig")

    time.sleep(5)

    end_count = handler._get_client().count(index=index)
    assert end_count["count"] - start_count["count"] == 1
