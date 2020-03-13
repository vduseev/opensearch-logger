import logging
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath('.'))
from elasticecslogging.handlers import ElasticECSHandler


class ElasticECSHandlerTestCase(unittest.TestCase):
    DEFAULT_ES_SERVER = 'localhost'
    DEFAULT_ES_PORT = 9200

    def getESHost(self):
        return os.getenv('TEST_ES_SERVER', ElasticECSHandlerTestCase.DEFAULT_ES_SERVER)

    def getESPort(self):
        try:
            return int(os.getenv('TEST_ES_PORT', ElasticECSHandlerTestCase.DEFAULT_ES_PORT))
        except ValueError:
            return ElasticECSHandlerTestCase.DEFAULT_ES_PORT

    def setUp(self):
        self.log = logging.getLogger("MyTestCase")
        test_handler = logging.StreamHandler(stream=sys.stderr)
        self.log.addHandler(test_handler)

    def tearDown(self):
        del self.log

    def test_ping(self):
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name="pythontest",
                                    use_ssl=False,
                                    raise_on_indexing_exceptions=True)
        es_test_server_is_up = handler.test_es_source()
        self.assertEqual(True, es_test_server_is_up)

    def test_buffered_log_insertion_flushed_when_buffer_full(self):
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    use_ssl=False,
                                    buffer_size=2,
                                    flush_frequency_in_sec=1000,
                                    es_index_name="pythontest",
                                    raise_on_indexing_exceptions=True)

        es_test_server_is_up = handler.test_es_source()
        self.log.info("ES services status is:  {0!s}".format(es_test_server_is_up))
        self.assertEqual(True, es_test_server_is_up)

        log = logging.getLogger("PythonTest")
        log.setLevel(logging.DEBUG)
        log.addHandler(handler)
        log.warning("First Message")
        log.info("Seccond Message")
        self.assertEqual(0, len(handler._buffer))
        handler.close()

    def test_es_log_with_additional_env_fields(self):
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    use_ssl=False,
                                    es_index_name="pythontest",
                                    es_additional_fields={'App': 'Test', 'Nested': {'One': '1', 'Two': '2'}},
                                    es_additional_fields_in_env={'App': 'ENV_APP', 'Environment': 'ENV_ENV',
                                                                 'Nested': {'One': 'ENV_ONE'}},
                                    raise_on_indexing_exceptions=True)

        es_test_server_is_up = handler.test_es_source()
        self.log.info("ES services status is:  {0!s}".format(es_test_server_is_up))
        self.assertEqual(True, es_test_server_is_up)

        log = logging.getLogger("PythonTest")
        log.addHandler(handler)

        log.warning("Test1 without environment variables set.")
        self.assertEqual(1, len(handler._buffer))
        self.assertEqual('Test', handler._buffer[0]['App'])
        self.assertEqual('1', handler._buffer[0]['Nested']['One'])
        self.assertEqual('2', handler._buffer[0]['Nested']['Two'])
        self.assertNotIn('Environment', handler._buffer[0])

        handler.flush()
        self.assertEqual(0, len(handler._buffer))

        os.environ['ENV_APP'] = 'Test2'
        os.environ['ENV_ENV'] = 'Dev'
        os.environ['ENV_ONE'] = 'One'
        log.warning("Test2 with environment variables set.")
        self.assertEqual(1, len(handler._buffer))
        self.assertEqual('Test2', handler._buffer[0]['App'])
        self.assertEqual('Dev', handler._buffer[0]['Environment'])
        self.assertEqual('One', handler._buffer[0]['Nested']['One'])
        self.assertEqual('2', handler._buffer[0]['Nested']['Two'])

        del os.environ['ENV_APP']
        del os.environ['ENV_ENV']
        del os.environ['ENV_ONE']

        handler.flush()
        self.assertEqual(0, len(handler._buffer))

    def test_es_log_extra_argument_insertion(self):
        self.log.info("About to test elasticsearch insertion")
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    use_ssl=False,
                                    es_index_name="pythontest",
                                    es_additional_fields={'App': 'Test', 'Environment': 'Dev',
                                                          'Nested': {'One': '1', 'Two': '2'}},
                                    raise_on_indexing_exceptions=True)

        es_test_server_is_up = handler.test_es_source()
        self.log.info("ES services status is:  {0!s}".format(es_test_server_is_up))
        self.assertEqual(True, es_test_server_is_up)

        log = logging.getLogger("PythonTest")
        log.addHandler(handler)
        log.warning("Extra arguments Message", extra={"Arg1": 300, "Arg2": 400})
        log.warning("Another Log")
        self.assertEqual(2, len(handler._buffer))
        self.assertEqual(300, handler._buffer[0]['Arg1'])
        self.assertEqual(400, handler._buffer[0]['Arg2'])
        self.assertEqual('Test', handler._buffer[0]['App'])
        self.assertEqual('Dev', handler._buffer[0]['Environment'])
        self.assertEqual('1', handler._buffer[0]['Nested']['One'])
        self.assertEqual('2', handler._buffer[0]['Nested']['Two'])
        handler.flush()
        self.assertEqual(0, len(handler._buffer))

    def test_es_log_exception_insertion(self):
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    use_ssl=False,
                                    es_index_name="pythontest",
                                    raise_on_indexing_exceptions=True)

        es_test_server_is_up = handler.test_es_source()
        self.log.info("ES services status is:  {0!s}".format(es_test_server_is_up))
        self.assertEqual(True, es_test_server_is_up)

        log = logging.getLogger("PythonTest")
        log.addHandler(handler)

        try:
            _ = 21/0
        except ZeroDivisionError:
            log.exception('Division Error')

        self.assertEqual(1, len(handler._buffer))
        handler.flush()
        self.assertEqual(0, len(handler._buffer))

    def test_buffered_log_insertion_after_interval_expired(self):
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    use_ssl=False,
                                    flush_frequency_in_sec=0.1,
                                    es_index_name="pythontest",
                                    raise_on_indexing_exceptions=True)

        es_test_server_is_up = handler.test_es_source()
        self.log.info("ES services status is:  {0!s}".format(es_test_server_is_up))
        self.assertEqual(True, es_test_server_is_up)

        log = logging.getLogger("PythonTest")
        log.addHandler(handler)
        log.warning("Warning Message")
        self.assertEqual(1, len(handler._buffer))
        time.sleep(1)
        self.assertEqual(0, len(handler._buffer))

    def test_fast_insertion_of_hundred_logs(self):
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    use_ssl=False,
                                    buffer_size=500,
                                    flush_frequency_in_sec=0.5,
                                    es_index_name="pythontest",
                                    raise_on_indexing_exceptions=True)
        log = logging.getLogger("PythonTest")
        log.setLevel(logging.DEBUG)
        log.addHandler(handler)
        for i in range(100):
            log.info("Logging line {0:d}".format(i), extra={'LineNum': i})
        handler.flush()
        self.assertEqual(0, len(handler._buffer))

    def test_index_name_frequency_functions(self):
        index_name = "pythontest"
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name=index_name,
                                    use_ssl=False,
                                    index_name_frequency=ElasticECSHandler.IndexNameFrequency.DAILY,
                                    raise_on_indexing_exceptions=True)
        self.assertEqual(
            ElasticECSHandler._get_daily_index_name(index_name),
            handler._index_name_func.__func__(index_name)
        )

        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name=index_name,
                                    use_ssl=False,
                                    index_name_frequency=ElasticECSHandler.IndexNameFrequency.WEEKLY,
                                    raise_on_indexing_exceptions=True)
        self.assertEqual(
            ElasticECSHandler._get_weekly_index_name(index_name),
            handler._index_name_func.__func__(index_name)
        )

        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name=index_name,
                                    use_ssl=False,
                                    index_name_frequency=ElasticECSHandler.IndexNameFrequency.MONTHLY,
                                    raise_on_indexing_exceptions=True)
        self.assertEqual(
            ElasticECSHandler._get_monthly_index_name(index_name),
            handler._index_name_func.__func__(index_name)
        )

        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name=index_name,
                                    use_ssl=False,
                                    index_name_frequency=ElasticECSHandler.IndexNameFrequency.YEARLY,
                                    raise_on_indexing_exceptions=True)
        self.assertEqual(
            ElasticECSHandler._get_yearly_index_name(index_name),
            handler._index_name_func.__func__(index_name)
        )

        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name=index_name,
                                    use_ssl=False,
                                    index_name_frequency=ElasticECSHandler.IndexNameFrequency.NEVER,
                                    raise_on_indexing_exceptions=True)
        self.assertEqual(
            ElasticECSHandler._get_never_index_name(index_name),
            handler._index_name_func.__func__(index_name)
        )


if __name__ == '__main__':
    unittest.main()
