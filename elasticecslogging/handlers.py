""" Elasticsearch logging handler
"""

import collections
import copy
import datetime
import logging
import os
import socket
import traceback
import uuid
from threading import Timer, Lock

from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch import helpers as eshelpers
from enum import Enum

try:
    from requests_kerberos import HTTPKerberosAuth, DISABLED
    CMR_KERBEROS_SUPPORTED = True
except ImportError:
    CMR_KERBEROS_SUPPORTED = False

try:
    from requests_aws4auth import AWS4Auth
    AWS4AUTH_SUPPORTED = True
except ImportError:
    AWS4AUTH_SUPPORTED = False

from elasticecslogging.serializers import ElasticECSSerializer


class ElasticECSHandler(logging.Handler):
    """ Elasticsearch log handler

    Allows to log to elasticsearch into json format.
    All LogRecord fields are serialised and inserted
    """

    class AuthType(Enum):
        """ Authentication types supported

        The handler supports
         - No authentication
         - Basic authentication
         - Kerberos or SSO authentication (on windows and linux)
        """
        NO_AUTH = 0
        BASIC_AUTH = 1
        KERBEROS_AUTH = 2
        AWS_SIGNED_AUTH = 3

    class IndexNameFrequency(Enum):
        """ Index type supported
        the handler supports
        - Daily indices
        - Weekly indices
        - Monthly indices
        - Year indices
        - Never expiring indices
        """
        DAILY = 0
        WEEKLY = 1
        MONTHLY = 2
        YEARLY = 3
        NEVER = 4

    # Defaults for the class
    __DEFAULT_ELASTICSEARCH_HOST = [{'host': 'localhost', 'port': 9200}]
    __DEFAULT_AUTH_USER = ''
    __DEFAULT_AUTH_PASSWD = ''
    __DEFAULT_AWS_ACCESS_KEY = ''
    __DEFAULT_AWS_SECRET_KEY = ''
    __DEFAULT_AWS_REGION = ''
    __DEFAULT_USE_SSL = False
    __DEFAULT_VERIFY_SSL = True
    __DEFAULT_AUTH_TYPE = AuthType.NO_AUTH
    __DEFAULT_INDEX_FREQUENCY = IndexNameFrequency.DAILY
    __DEFAULT_BUFFER_SIZE = 1000
    __DEFAULT_FLUSH_FREQ_INSEC = 1
    __DEFAULT_ADDITIONAL_FIELDS = {}
    __DEFAULT_ADDITIONAL_FIELDS_IN_ENV = {}
    __DEFAULT_ES_INDEX_NAME = 'python_logger'
    __DEFAULT_RAISE_ON_EXCEPTION = False

    __LOGGING_FILTER_FIELDS = ['msecs',
                               'relativeCreated',
                               'levelno',
                               'exc_text',
                               'msg']

    __AGENT_TYPE = 'python-elasticsearch-ecs-logger'
    __AGENT_VERSION = '1.0.3'
    __ECS_VERSION = "1.4.0"

    @staticmethod
    def _get_daily_index_name(es_index_name):
        """ Returns elasticearch index name
        :param: index_name the prefix to be used in the index
        :return: A srting containing the elasticsearch indexname used which should include the date.
        """
        return "{0!s}-{1!s}".format(es_index_name, datetime.datetime.now().strftime('%Y.%m.%d'))

    @staticmethod
    def _get_weekly_index_name(es_index_name):
        """ Return elasticsearch index name
        :param: index_name the prefix to be used in the index
        :return: A srting containing the elasticsearch indexname used which should include the date and specific week
        """
        current_date = datetime.datetime.now()
        start_of_the_week = current_date - datetime.timedelta(days=current_date.weekday())
        return "{0!s}-{1!s}".format(es_index_name, start_of_the_week.strftime('%Y.%m.%d'))

    @staticmethod
    def _get_monthly_index_name(es_index_name):
        """ Return elasticsearch index name
        :param: index_name the prefix to be used in the index
        :return: A srting containing the elasticsearch indexname used which should include the date and specific moth
        """
        return "{0!s}-{1!s}".format(es_index_name, datetime.datetime.now().strftime('%Y.%m'))

    @staticmethod
    def _get_yearly_index_name(es_index_name):
        """ Return elasticsearch index name
        :param: index_name the prefix to be used in the index
        :return: A srting containing the elasticsearch indexname used which should include the date and specific year
        """
        return "{0!s}-{1!s}".format(es_index_name, datetime.datetime.now().strftime('%Y'))

    @staticmethod
    def _get_never_index_name(es_index_name):
        """ Return elasticsearch index name
        :param: index_name the prefix to be used in the index
        :return: A srting containing the elasticsearch indexname used which should include just the index name
        """
        return "{0!s}".format(es_index_name)

    _INDEX_FREQUENCY_FUNCION_DICT = {
        IndexNameFrequency.DAILY: _get_daily_index_name,
        IndexNameFrequency.WEEKLY: _get_weekly_index_name,
        IndexNameFrequency.MONTHLY: _get_monthly_index_name,
        IndexNameFrequency.YEARLY: _get_yearly_index_name,
        IndexNameFrequency.NEVER: _get_never_index_name
    }

    def __init__(self,
                 hosts=__DEFAULT_ELASTICSEARCH_HOST,
                 auth_details=(__DEFAULT_AUTH_USER, __DEFAULT_AUTH_PASSWD),
                 aws_access_key=__DEFAULT_AWS_ACCESS_KEY,
                 aws_secret_key=__DEFAULT_AWS_SECRET_KEY,
                 aws_region=__DEFAULT_AWS_REGION,
                 auth_type=__DEFAULT_AUTH_TYPE,
                 use_ssl=__DEFAULT_USE_SSL,
                 verify_ssl=__DEFAULT_VERIFY_SSL,
                 buffer_size=__DEFAULT_BUFFER_SIZE,
                 flush_frequency_in_sec=__DEFAULT_FLUSH_FREQ_INSEC,
                 es_index_name=__DEFAULT_ES_INDEX_NAME,
                 index_name_frequency=__DEFAULT_INDEX_FREQUENCY,
                 es_additional_fields=__DEFAULT_ADDITIONAL_FIELDS,
                 es_additional_fields_in_env=__DEFAULT_ADDITIONAL_FIELDS_IN_ENV,
                 raise_on_indexing_exceptions=__DEFAULT_RAISE_ON_EXCEPTION):
        """ Handler constructor

        :param hosts: The list of hosts that elasticsearch clients will connect. The list can be provided
                    in the format ```[{'host':'host1','port':9200}, {'host':'host2','port':9200}]``` to
                    make sure the client supports failover of one of the instertion nodes
        :param auth_details: When ```ElasticECSHandler.AuthType.BASIC_AUTH``` is used this argument must contain
                    a tuple of string with the user and password that will be used to authenticate against
                    the Elasticsearch servers, for example```('User','Password')
        :param aws_access_key: When ```ElasticECSHandler.AuthType.AWS_SIGNED_AUTH``` is used this argument must contain
                    the AWS key id of the  the AWS IAM user
        :param aws_secret_key: When ```ElasticECSHandler.AuthType.AWS_SIGNED_AUTH``` is used this argument must contain
                    the AWS secret key of the  the AWS IAM user
        :param aws_region: When ```ElasticECSHandler.AuthType.AWS_SIGNED_AUTH``` is used this argument must contain
                    the AWS region of the  the AWS Elasticsearch servers, for example```'us-east'
        :param auth_type: The authentication type to be used in the connection ```ElasticECSHandler.AuthType```
                    Currently, NO_AUTH, BASIC_AUTH, KERBEROS_AUTH are supported
                    You can pass a str instead of the enum value. It is useful if you are using a config file for
                    configuring the logging module.
        :param use_ssl: A boolean that defines if the communications should use SSL encrypted communication
        :param verify_ssl: A boolean that defines if the SSL certificates are validated or not
        :param buffer_size: An int, Once this size is reached on the internal buffer results are flushed into ES
        :param flush_frequency_in_sec: A float representing how often and when the buffer will be flushed, even
                    if the buffer_size has not been reached yet
        :param es_index_name: A string with the prefix of the elasticsearch index that will be created. Note a
                    date with YYYY.MM.dd, ```python_logger``` used by default
        :param index_name_frequency: Defines what the date used in the postfix of the name would be. available values
                    are selected from the IndexNameFrequency class (IndexNameFrequency.DAILY,
                    IndexNameFrequency.WEEKLY, IndexNameFrequency.MONTHLY, IndexNameFrequency.YEARLY,
                    IndexNameFrequency.NEVER). By default it uses daily indices.
                    You can pass a str instead of the enum value. It is useful if you are using a config file for
                    configuring the logging module.
        :param es_additional_fields: A dictionary with all the additional fields that you would like to add
                    to the logs, such the application, environment, etc. You can nest dicts to follow ecs convention.
        :param es_additional_fields_in_env: A dictionary with all the additional fields that you would like to add
                    to the logs, such the application, environment, etc. You can nest dicts to follow ecs convention.
                    The values are environment variables keys. At each elastic document created, the values of these
                    environment variables will be read. If an environment variable for a field doesn't exists, the value
                    of the same field in es_additional_fields will be taken if it exists. In last resort, there will be
                    no value for the field.
        :param raise_on_indexing_exceptions: A boolean, True only for debugging purposes to raise exceptions
                    caused when
        :return: A ready to be used ElasticECSHandler.
        """
        logging.Handler.__init__(self)

        self.hosts = hosts
        self.auth_details = auth_details
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region
        if isinstance(auth_type, str):
            self.auth_type = ElasticECSHandler.AuthType[auth_type]
        else:
            self.auth_type = auth_type
        self.use_ssl = use_ssl
        self.verify_certs = verify_ssl
        self.buffer_size = buffer_size
        self.flush_frequency_in_sec = flush_frequency_in_sec
        self.es_index_name = es_index_name
        if isinstance(index_name_frequency, str):
            self.index_name_frequency = ElasticECSHandler.IndexNameFrequency[index_name_frequency]
        else:
            self.index_name_frequency = index_name_frequency

        self.es_additional_fields = copy.deepcopy(es_additional_fields.copy())
        self.es_additional_fields.setdefault('ecs', {})['version'] = ElasticECSHandler.__ECS_VERSION

        agent_dict = self.es_additional_fields.setdefault('agent', {})
        agent_dict['ephemeral_id'] = uuid.uuid4()
        agent_dict['type'] = ElasticECSHandler.__AGENT_TYPE
        agent_dict['version'] = ElasticECSHandler.__AGENT_VERSION

        host_dict = self.es_additional_fields.setdefault('host', {})
        host_name = socket.gethostname()
        host_dict['hostname'] = host_name
        host_dict['name'] = host_name
        host_dict['id'] = host_name
        host_dict['ip'] = socket.gethostbyname(socket.gethostname())

        self.es_additional_fields_in_env = copy.deepcopy(es_additional_fields_in_env.copy())

        self.raise_on_indexing_exceptions = raise_on_indexing_exceptions

        self._client = None
        self._buffer = []
        self._buffer_lock = Lock()
        self._timer = None
        self._index_name_func = ElasticECSHandler._INDEX_FREQUENCY_FUNCION_DICT[self.index_name_frequency]
        self.serializer = ElasticECSSerializer()

    def __schedule_flush(self):
        if self._timer is None:
            self._timer = Timer(self.flush_frequency_in_sec, self.flush)
            self._timer.setDaemon(True)
            self._timer.start()

    def __get_es_client(self):
        if self.auth_type == ElasticECSHandler.AuthType.NO_AUTH:
            if self._client is None:
                self._client = Elasticsearch(hosts=self.hosts,
                                             use_ssl=self.use_ssl,
                                             verify_certs=self.verify_certs,
                                             connection_class=RequestsHttpConnection,
                                             serializer=self.serializer)
            return self._client

        if self.auth_type == ElasticECSHandler.AuthType.BASIC_AUTH:
            if self._client is None:
                return Elasticsearch(hosts=self.hosts,
                                     http_auth=self.auth_details,
                                     use_ssl=self.use_ssl,
                                     verify_certs=self.verify_certs,
                                     connection_class=RequestsHttpConnection,
                                     serializer=self.serializer)
            return self._client

        if self.auth_type == ElasticECSHandler.AuthType.KERBEROS_AUTH:
            if not CMR_KERBEROS_SUPPORTED:
                raise EnvironmentError("Kerberos module not available. Please install \"requests-kerberos\"")
            # For kerberos we return a new client each time to make sure the tokens are up to date
            return Elasticsearch(hosts=self.hosts,
                                 use_ssl=self.use_ssl,
                                 verify_certs=self.verify_certs,
                                 connection_class=RequestsHttpConnection,
                                 http_auth=HTTPKerberosAuth(mutual_authentication=DISABLED),
                                 serializer=self.serializer)

        if self.auth_type == ElasticECSHandler.AuthType.AWS_SIGNED_AUTH:
            if not AWS4AUTH_SUPPORTED:
                raise EnvironmentError("AWS4Auth not available. Please install \"requests-aws4auth\"")
            if self._client is None:
                awsauth = AWS4Auth(self.aws_access_key, self.aws_secret_key, self.aws_region, 'es')
                self._client = Elasticsearch(
                    hosts=self.hosts,
                    http_auth=awsauth,
                    use_ssl=self.use_ssl,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection,
                    serializer=self.serializer
                )
            return self._client

        raise ValueError("Authentication method not supported")

    def test_es_source(self):
        """ Returns True if the handler can ping the Elasticsearch servers

        Can be used to confirm the setup of a handler has been properly done and confirm
        that things like the authentication is working properly

        :return: A boolean, True if the connection against elasticserach host was successful
        """
        return self.__get_es_client().ping()

    @staticmethod
    def __get_es_datetime_str(timestamp):
        """ Returns elasticsearch utc formatted time for an epoch timestamp

        :param timestamp: epoch, including milliseconds
        :return: A string valid for elasticsearch time record
        """
        current_date = datetime.datetime.utcfromtimestamp(timestamp)
        return "{0!s}.{1:03d}Z".format(current_date.strftime('%Y-%m-%dT%H:%M:%S'), int(current_date.microsecond / 1000))

    def flush(self):
        """ Flushes the buffer into ES
        :return: None
        """
        if self._timer is not None and self._timer.is_alive():
            self._timer.cancel()
        self._timer = None

        if self._buffer:
            try:
                with self._buffer_lock:
                    logs_buffer = self._buffer
                    self._buffer = []
                actions = (
                    {
                        '_index': self._index_name_func.__func__(self.es_index_name),
                        '_source': log_record
                    }
                    for log_record in logs_buffer
                )
                eshelpers.bulk(
                    client=self.__get_es_client(),
                    actions=actions,
                    stats_only=True
                )
            except Exception as exception:
                if self.raise_on_indexing_exceptions:
                    raise exception

    def close(self):
        """ Flushes the buffer and release any outstanding resource

        :return: None
        """
        if self._timer is not None:
            self.flush()
        self._timer = None

    def emit(self, record):
        """ Emit overrides the abstract logging.Handler logRecord emit method

        Format and records the log

        :param record: A class of type ```logging.LogRecord```
        :return: None
        """
        self.format(record)
        es_record = self._log_record_to_ecs_fields(record)
        with self._buffer_lock:
            self._buffer.append(es_record)

        if len(self._buffer) >= self.buffer_size:
            self.flush()
        else:
            self.__schedule_flush()

    def _log_record_to_ecs_fields(self, log_record):
        """
        This function take the original logging.LogRecord and map its attributes to ecs fields.

        :param log_record: The original logging.LogRecord.
        :return The elasticsearch document that will be sent.
        """
        log_record_dict = log_record.__dict__.copy()
        es_record = copy.deepcopy(self.es_additional_fields)
        self._add_additional_fields_in_env(es_record)

        if 'created' in log_record_dict:
            es_record['@timestamp'] = self.__get_es_datetime_str(log_record_dict.pop('created'))

        if 'message' in log_record_dict:
            message = log_record_dict.pop('message')
            es_record['message'] = message
            es_record.setdefault('log', {})['original'] = message

        if 'levelname' in log_record_dict:
            es_record.setdefault('log', {})['level'] = log_record_dict.pop('levelname')

        if 'name' in log_record_dict:
            es_record.setdefault('log', {})['logger'] = log_record_dict.pop('name')

        if 'lineno' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('origin', {}).setdefault('file', {})[
                'line'] = log_record_dict.pop('lineno')

        if 'filename' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('origin', {}).setdefault('file', {})[
                'name'] = log_record_dict.pop('filename')

        if 'pathname' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('origin', {}).setdefault('file', {})[
                'path'] = log_record_dict.pop('pathname')

        if 'funcName' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('origin', {})['function'] = log_record_dict.pop('funcName')

        if 'module' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('origin', {})['module'] = log_record_dict.pop('module')

        if 'processName' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('process', {})['name'] = log_record_dict.pop('processName')

        if 'process' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('process', {})['pid'] = log_record_dict.pop('process')

        if 'threadName' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('thread', {})['name'] = log_record_dict.pop('threadName')

        if 'thread' in log_record_dict:
            es_record.setdefault('log', {}).setdefault('thread', {})['id'] = log_record_dict.pop('thread')

        if 'exc_info' in log_record_dict:
            exc_info = log_record_dict.pop('exc_info')
            if exc_info:
                exc_type, exc_value, traceback_object = exc_info
                es_record['error'] = {
                    'code': exc_type.__name__,
                    'id': uuid.uuid4(),
                    'type': exc_type.__name__,
                    'message': str(exc_value),
                    'stack_trace': "".join(traceback.format_exception(exc_type, exc_value, traceback_object))
                }

        # Copy unknown attributes of the log_record object.
        for key, value in log_record_dict.items():
            if key not in ElasticECSHandler.__LOGGING_FILTER_FIELDS:
                if key == "args":
                    value = tuple(str(arg) for arg in value)
                es_record[key] = "" if value is None else value

        return es_record

    def _add_additional_fields_in_env(self, es_record):
        """
        Add the additional fields with their values in environment variables.
        :param es_record: The record where the additional fields with
                          their values fetched in environment variables will be added or overridden.
        """
        additional_fields_in_env_values = _fetch_additional_fields_in_env(self.es_additional_fields_in_env)
        _update_nested_dict(es_record, additional_fields_in_env_values)


def _fetch_additional_fields_in_env(additional_fields_env_keys):
    """
    Walk the additional_fields_env_keys and fetch the values from the environment variables.
    :param additional_fields_env_keys: A dictionnary with the additional_fields_in_env with their keys.
    :return: A dictionary with the additional_fields_in_env with their values fetched instead of their keys.
    """
    additional_fields_env_values = {}
    for dict_key, dict_value in additional_fields_env_keys.items():
        if isinstance(dict_value, collections.Mapping):
            nested_dict_env_keys = dict_value
            additional_fields_env_values[dict_key] = _fetch_additional_fields_in_env(nested_dict_env_keys)
        else:
            if dict_value in os.environ:
                additional_fields_env_values[dict_key] = os.environ[dict_value]
    return additional_fields_env_values


def _update_nested_dict(source, override):
    """
    Update the source dictionary with the override dictionary.

    :param source: The dictionary to update.
    :param override: The dictionary that will update the source dictionary.
    """
    for key, value in override.items():
        if isinstance(value, collections.Mapping):
            _update_nested_dict(source.setdefault(key, {}), value)
        else:
            source[key] = value
