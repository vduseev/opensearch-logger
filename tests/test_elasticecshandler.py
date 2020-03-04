import unittest
import logging
import time
import os
import sys
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

    def test_es_log_extra_argument_insertion(self):
        self.log.info("About to test elasticsearch insertion")
        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    use_ssl=False,
                                    es_index_name="pythontest",
                                    es_additional_fields={'App': 'Test', 'Environment': 'Dev',
                                                          'Nested': {'One': 1, 'Two': 2}},
                                    raise_on_indexing_exceptions=True)

        es_test_server_is_up = handler.test_es_source()
        self.log.info("ES services status is:  {0!s}".format(es_test_server_is_up))
        self.assertEqual(True, es_test_server_is_up)

        log = logging.getLogger("PythonTest")
        log.addHandler(handler)
        log.warning("Extra arguments Message", extra={"Arg1": 300, "Arg2": 400})
        log.warning("Another Log")
        self.assertEqual(2, len(handler._buffer))
        self.assertEqual(handler._buffer[0]['Arg1'], 300)
        self.assertEqual(handler._buffer[0]['Arg2'], 400)
        self.assertEqual(handler._buffer[0]['App'], 'Test')
        self.assertEqual(handler._buffer[0]['Environment'], 'Dev')
        self.assertEqual(handler._buffer[0]['Nested']['One'], 1)
        self.assertEqual(handler._buffer[0]['Nested']['Two'], 2)
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
            handler._index_name_func.__func__(index_name),
            ElasticECSHandler._get_daily_index_name(index_name)
        )

        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name=index_name,
                                    use_ssl=False,
                                    index_name_frequency=ElasticECSHandler.IndexNameFrequency.WEEKLY,
                                    raise_on_indexing_exceptions=True)
        self.assertEqual(
            handler._index_name_func.__func__(index_name),
            ElasticECSHandler._get_weekly_index_name(index_name)
        )

        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name=index_name,
                                    use_ssl=False,
                                    index_name_frequency=ElasticECSHandler.IndexNameFrequency.MONTHLY,
                                    raise_on_indexing_exceptions=True)
        self.assertEqual(
            handler._index_name_func.__func__(index_name),
            ElasticECSHandler._get_monthly_index_name(index_name)
        )

        handler = ElasticECSHandler(hosts=[{'host': self.getESHost(), 'port': self.getESPort()}],
                                    auth_type=ElasticECSHandler.AuthType.NO_AUTH,
                                    es_index_name=index_name,
                                    use_ssl=False,
                                    index_name_frequency=ElasticECSHandler.IndexNameFrequency.YEARLY,
                                    raise_on_indexing_exceptions=True)
        self.assertEqual(
            handler._index_name_func.__func__(index_name),
            ElasticECSHandler._get_yearly_index_name(index_name)
        )


if __name__ == '__main__':
    unittest.main()
