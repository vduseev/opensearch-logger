import logging
import datetime
import sys
import decimal

import pytest

from opensearch_logger.serializers import OpensearchLoggerSerializer


@pytest.fixture
def logger():
    return logging.getLogger("serializer_test")


@pytest.fixture
def formatter():
    return logging.Formatter("%(asctime)s")


def test_dumps_classic_log(logger: logging.Logger, formatter: logging.Formatter):
    """Test classic log serialization."""
    serializer = OpensearchLoggerSerializer()
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn=__name__,
        lno=58,
        msg="dump_classic_log",
        args=None,
        exc_info=None,
        func=None,
        extra=None,
    )

    formatter.format(record)
    for value in record.__dict__.values():
        serializer.dumps(value)


def test_dumps_exception_log(logger: logging.Logger, formatter: logging.Formatter):
    """Test the exception log serialization with the exc_info field."""
    serializer = OpensearchLoggerSerializer()
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        record = logger.makeRecord(
            name=logger.name,
            level=logging.ERROR,
            fn=__name__,
            lno=58,
            msg="dump_exception_log",
            args=None,
            exc_info=sys.exc_info(),
            func=None,
            extra=None,
        )

        formatter.format(record)
        for value in record.__dict__.values():
            serializer.dumps(value)


def test_dumps_log_with_extras_and_args(logger: logging.Logger, formatter: logging.Formatter):
    """Test log serialization with arguments and extras."""
    serializer = OpensearchLoggerSerializer()
    record = logger.makeRecord(
        name=logger.name,
        level=logging.ERROR,
        fn=__name__,
        lno=58,
        msg="dump_%s_log",
        args="args",
        exc_info=None,
        func=None,
        extra={
            "extra_value_one": datetime.date.today(),
            "extra_value_two": decimal.Decimal("3.0"),
        },
    )

    formatter.format(record)
    for value in record.__dict__.values():
        serializer.dumps(value)
