import copy
from datetime import datetime, timedelta
import logging
import socket
from threading import Timer, Lock
import traceback
from typing import Any, Dict, List, Optional
from uuid import uuid4

from opensearchpy import OpenSearch
from opensearchpy import helpers
from enum import Enum

from .serializers import OpensearchLoggerSerializer
from .version import __version__


class RotateFrequency(Enum):
    DAILY = 0
    WEEKLY = 1
    MONTHLY = 2
    YEARLY = 3
    NEVER = 4


__DEFAULT_HOSTS = [{"host": "localhost", "port": 9200}]
__DEFAULT_HTTP_AUTH = ("admin", "admin")
__DEFAULT_USE_SSL = True
__DEFAULT_VERIFY_SSL = False

__DEFAULT_INDEX_PREFIX = "python-logs"
__DEFAULT_INDEX_ROTATE = RotateFrequency.DAILY
__DEFAULT_INDEX_DATE_FORMAT = "%Y-%m-%d"
__DEFAULT_BUFFER_SIZE = 1000
__DEFAULT_FLUSH_FREQUENCY = 1
__DEFAULT_EXTRA_FIELDS = {}
__DEFAULT_RAISE_ON_EXCEPTION = False

__LOGGING_FILTER_FIELDS = ['msecs', 'relativeCreated', 'levelno', 'exc_text', 'msg']

__AGENT_TYPE = 'opensearch-logger'
__AGENT_VERSION = __version__
__ECS_VERSION = "1.4.0"


class OpensearchHandler(logging.Handler):
    """Opensearch logging handler.

    Allows to log to Opensearch in json format.
    All LogRecord fields are serialised and inserted
    """

    DAILY = RotateFrequency.DAILY
    WEEKLY = RotateFrequency.WEEKLY
    MONTHLY = RotateFrequency.MONTHLY
    YEARLY = RotateFrequency.YEARLY
    NEVER = RotateFrequency.NEVER

    @staticmethod
    def _get_daily_index_name(index_prefix, date_format=__DEFAULT_INDEX_DATE_FORMAT):
        return f"{index_prefix}-{datetime.now().strftime(date_format)}"

    @staticmethod
    def _get_weekly_index_name(index_prefix, date_format=__DEFAULT_INDEX_DATE_FORMAT):
        current_date = datetime.now()
        start_of_the_week = current_date - timedelta(days=current_date.weekday())
        return f"{index_prefix}-{start_of_the_week.strftime(date_format)}"

    @staticmethod
    def _get_monthly_index_name(index_prefix, date_format=__DEFAULT_INDEX_DATE_FORMAT):
        current_date = datetime.now()
        first_date_of_month = datetime(current_date.year, current_date.month, 1)
        return f"{index_prefix}-{first_date_of_month.strftime(date_format)}"

    @staticmethod
    def _get_yearly_index_name(index_prefix, date_format=__DEFAULT_INDEX_DATE_FORMAT):
        current_date = datetime.now()
        first_date_of_year = datetime(current_date.year, 1, 1)
        return f"{index_prefix}-{first_date_of_year.strftime(date_format)}"

    @staticmethod
    def _get_never_index_name(index_prefix):
        return index_prefix

    _INDEX_NAME_FUNCTIONS = {
        RotateFrequency.DAILY: _get_daily_index_name,
        RotateFrequency.WEEKLY: _get_weekly_index_name,
        RotateFrequency.MONTHLY: _get_monthly_index_name,
        RotateFrequency.YEARLY: _get_yearly_index_name,
        RotateFrequency.NEVER: _get_never_index_name
    }

    def __init__(
        self,
        index_prefix: str = __DEFAULT_INDEX_PREFIX,
        index_rotate: RotateFrequency =__DEFAULT_INDEX_ROTATE,
        buffer_size: int = __DEFAULT_BUFFER_SIZE,
        flush_frequency: float = __DEFAULT_FLUSH_FREQUENCY,
        extra_fields: Dict = __DEFAULT_EXTRA_FIELDS,
        raise_on_exception: bool = __DEFAULT_RAISE_ON_EXCEPTION,
        **kwargs: Any,
    ):
        logging.Handler.__init__(self)

        # Arguments that will be passed to Opensearch client object
        self.opensearch_kwargs = kwargs

        # Bufferization and flush settings
        self.buffer_size = buffer_size
        self.flush_frequency = flush_frequency

        # Index name
        self.index_prefix = index_prefix
        if isinstance(index_rotate, str):
            self.index_rotate = RotateFrequency[index_rotate]
        else:
            self.index_rotate = index_rotate

        self.extra_fields = copy.deepcopy(extra_fields.copy())
        self.extra_fields.setdefault('ecs', {})['version'] = __ECS_VERSION

        agent_dict = self.extra_fields.setdefault('agent', {})
        agent_dict['ephemeral_id'] = uuid4()
        agent_dict['type'] = __AGENT_TYPE
        agent_dict['version'] = __AGENT_VERSION

        host_dict = self.extra_fields.setdefault('host', {})
        host_name = socket.gethostname()
        host_dict['hostname'] = host_name
        host_dict['name'] = host_name
        host_dict['id'] = host_name
        host_dict['ip'] = socket.gethostbyname(socket.gethostname())

        self._client: Optional[OpenSearch] = None
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_lock: Lock = Lock()
        self._timer: Optional[Timer] = None
        self._index_name_func = OpensearchHandler._INDEX_NAME_FUNCTIONS[self.index_rotate]
        self.serializer = OpensearchLoggerSerializer()

        self.raise_on_exception: bool = raise_on_exception

    def test_opensearch_connection(self) -> bool:
        """Returns True if the handler can ping the Opensearch servers.

        Can be used to confirm the setup of a handler has been properly done and confirm
        that things like the authentication are working properly.

        Returns:
            bool: True if the connection against elasticserach host was successful.
        """
        return self._get_opensearch_client().ping()

    def flush(self) -> None:
        """Flush the buffer into Opensearch."""
        if self._timer is not None and self._timer.is_alive():
            self._timer.cancel()
        self._timer = None

        if self._buffer:
            try:
                with self._buffer_lock:
                    logs_buffer = self._buffer
                    self._buffer = []

                actions = [
                    {
                        '_index': self._index_name_func.__func__(self.index_prefix),
                        '_source': log_record
                    }
                    for log_record in logs_buffer
                ]

                helpers.bulk(
                    client=self._get_opensearch_client(),
                    actions=actions,
                    stats_only=True,
                )

            except Exception as exception:
                if self.raise_on_exception:
                    raise exception

    def close(self) -> None:
        """Flush the buffer and release any outstanding resource."""
        if self._timer is not None:
            self.flush()
        self._timer = None

    def emit(self, record: logging.LogRecord) -> None:
        """Emit overrides the abstract logging.Handler logRecord emit method.

        Formats and emits the log record.

        Args:
            record: A record.
        """
        self.format(record)
        opensearch_doc = self._convert_log_record_to_doc(record)
        with self._buffer_lock:
            self._buffer.append(opensearch_doc)

        if len(self._buffer) >= self.buffer_size:
            self.flush()
        else:
            self._schedule_flush()

    def _schedule_flush(self) -> None:
        if self._timer is None:
            self._timer = Timer(self.flush_frequency, self.flush)
            self._timer.setDaemon(True)
            self._timer.start()

    def _get_opensearch_client(self) -> OpenSearch:
        if self._client is None:
            self._client = OpenSearch(**self.opensearch_kwargs)
        return self._client

    def _convert_log_record_to_doc(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Take the original logging.LogRecord and map its attributes to ecs fields.

        Args:
            record: The original LogRecord.

        Returns:
            Dict[str, Any]: Opensearch ECS compliant document with all the proper meta data fields.
        """
        log_record_dict = record.__dict__.copy()
        doc = copy.deepcopy(self.extra_fields)

        if 'created' in log_record_dict:
            doc['@timestamp'] = self._get_opensearch_datetime_str(log_record_dict.pop('created'))

        if 'message' in log_record_dict:
            message = log_record_dict.pop('message')
            doc['message'] = message
            doc.setdefault('log', {})['original'] = message

        if 'levelname' in log_record_dict:
            doc.setdefault('log', {})['level'] = log_record_dict.pop('levelname')

        if 'name' in log_record_dict:
            doc.setdefault('log', {})['logger'] = log_record_dict.pop('name')

        if 'lineno' in log_record_dict:
            doc.setdefault('log', {}).setdefault('origin', {}).setdefault('file', {})[
                'line'] = log_record_dict.pop('lineno')

        if 'filename' in log_record_dict:
            doc.setdefault('log', {}).setdefault('origin', {}).setdefault('file', {})[
                'name'] = log_record_dict.pop('filename')

        if 'pathname' in log_record_dict:
            doc.setdefault('log', {}).setdefault('origin', {}).setdefault('file', {})[
                'path'] = log_record_dict.pop('pathname')

        if 'funcName' in log_record_dict:
            doc.setdefault('log', {}).setdefault('origin', {})['function'] = log_record_dict.pop('funcName')

        if 'module' in log_record_dict:
            doc.setdefault('log', {}).setdefault('origin', {})['module'] = log_record_dict.pop('module')

        if 'processName' in log_record_dict:
            doc.setdefault('log', {}).setdefault('process', {})['name'] = log_record_dict.pop('processName')

        if 'process' in log_record_dict:
            doc.setdefault('log', {}).setdefault('process', {})['pid'] = log_record_dict.pop('process')

        if 'threadName' in log_record_dict:
            doc.setdefault('log', {}).setdefault('thread', {})['name'] = log_record_dict.pop('threadName')

        if 'thread' in log_record_dict:
            doc.setdefault('log', {}).setdefault('thread', {})['id'] = log_record_dict.pop('thread')

        if 'exc_info' in log_record_dict:
            exc_info = log_record_dict.pop('exc_info')
            if exc_info:
                exc_type, exc_value, traceback_object = exc_info
                doc['error'] = {
                    'code': exc_type.__name__,
                    'id': uuid4(),
                    'type': exc_type.__name__,
                    'message': str(exc_value),
                    'stack_trace': "".join(traceback.format_exception(exc_type, exc_value, traceback_object))
                }

        # Copy unknown attributes of the log_record object.
        for key, value in log_record_dict.items():
            if key not in __LOGGING_FILTER_FIELDS:
                if key == "args":
                    value = tuple(str(arg) for arg in value)
                doc[key] = "" if value is None else value

        return doc

    @staticmethod
    def _get_opensearch_datetime_str(timestamp: float) -> str:
        """Return Opensearch utc formatted time for an epoch timestamp.

        Args:
            timestamp (float): Timestamp, including milliseconds.

        Returns:
            str: A string valid for Opensearch record such "2021-11-08T10:04:06.122Z".
        """
        dt = datetime.utcfromtimestamp(timestamp)
        fmt = "%Y-%m-%dT%H:%M:%S"
        return f"{dt.strftime(fmt)}.{int(dt.microsecond / 1000):.03d}Z"
