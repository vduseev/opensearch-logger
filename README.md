# Opensearch Logger for Python

<p>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="Package version" src="https://img.shields.io/pypi/v/opensearch-logger?logo=python&logoColor=white&color=blue"></a>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="Supported python versions" src="https://img.shields.io/pypi/pyversions/opensearch-logger?logo=python&logoColor=white"></a>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="Package stability" src="https://img.shields.io/pypi/status/opensearch-logger?logo=python&logoColor=white&color=blue"></a>
    <a href="https://codecov.io/gh/vduseev/opensearch-logger"><img alt="Code coverage" src="https://img.shields.io/codecov/c/github/vduseev/opensearch-logger?logo=codecov&logoColor=white&color=white"></a>
    <a href="https://github.com/vduseev/opensearch-logger/actions/workflows/test.yml"><img alt="Tests (main branch)" src="https://img.shields.io/github/workflow/status/vduseev/opensearch-logger/Test/main?logo=github"></a>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="License" src="https://img.shields.io/pypi/l/opensearch-logger"></a>
</p>

This library provides a standard Python logging handler compatible with [Opensearch][opensearch] suite.

The **goals** of this project are

* to provide a **simple** and direct logging from Python to Opensearch without *fluentd*, *logstash* or other middleware;
* keep it up to date with the growing difference between Opensearch and Elasticsearch projects;
* keep the library easy to use, robust, and simple.

The library has been open-sourced from an internal project where it has been successfully used in production
since the release of Opensearch 1.0.

Generated log records follow the [Elastic Common Schema (ECS)][ecs] field naming convention.
For better performance it is recommended to set up a proper mapping for you logging indices but everything will
work even without it. You can find a ready to use [compatible JSON mapping][ecs-mapping] in the repository.

## Installation

```shell
pip install opensearch-logger
```

## Usage

Just add the handler to your logger as follows

```python
import logging
from opensearch_logger import OpensearchHandler

handler = OpensearchHandler(
    index_name="my-logs",
    hosts=["https://localhost:9200"],
    http_auth=("admin", "admin"),
    use_ssl=True,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
```

To log into Opensearch, simply use the regular logging commands:

```python
logger.info("This message will be indexed in Opensearch")

# Report extra fields
start_time = time.perf_counter()
heavy_database_operation()
elapsed_time = time.perf_counter() - start_time

logger.info(f"Database operation took {elapsed_time:.3f} seconds", extra={"elapsed_time": elapsed_time})
```

## Configuration

The `OpensearchHandler` constructor several parameters from the first table below to control name of the index,
buffering, and some general behavior. None of this parameters are mandatory.

All other keyword arguments are passed directly to the underlying Opensearch python client.
Full list of connection parameters can be found in [`opensearch-py`][opensearch-py] docs.
At least one connection parameter **must** be provided, otherwise a `TypeError` will be thrown.

## Logging parameters

| Parameter | Default | Description |
| - | - | - |
| `index_name` | `"python-logs"` | Base name of the Opensearch index name that will be created. |
| `index_rotate` | `DAILY` | Frequency that controls what date is appended to index name during its creation. `OpensearchHandler.DAILY`. |
| `index_date_format` | `"%Y.%m.%d"` | Format of the date that gets appended to the base index name. |
| `index_name_sep` | `"-"` | Separator string between `index_name` and the date, appended to the index name. |
| `buffer_size` | `1000` | Number of log records which when reached on the internal buffer results in a flush to Opensearch. |
| `flush_frequency` | `1` | Float representing how often the buffer will be flushed (in seconds). |
| `extra_fields` | `{}` | Nested dictionary with all the additional fields that you would like to add to all logs. |
| `raise_on_index_exc` | `False` | Raise exception if indexing to Opensearch fails. |

## Connection parameters

Here are few examples of the connection parameters supported by the Opensearch client.

| Parameter | Example | Description |
| - | - | - |
| `hosts` | `["https://localhost:9200"]` | The list of hosts to connect to. Multiple hosts are allowed. |
| `http_auth` | `("admin", "admin")` | Username and password to authenticate against the Opensearch servers. |
| `http_compress` | `True` | Enables gzip compression for request bodies. |
| `use_ssl` | `True` | Whether communications should be SSL encrypted. |
| `verify_certs` | `False` | Whether the SSL certificates are validated or not. |
| `ssl_assert_hostname` | `False` | Verify authenticity of host for encrypted connections. |
| `ssl_show_warn` | `False` | Enable warning for SSL connections. |
| `ca_carts` | `"/var/lib/root-ca.pem"` | CA bundle path for using intermediate CAs with your root CA. |

## Configuring using logging.config or in Django

As most other log handlers, `opensearch-logger` support configuration via `logging.config` facility.
Just specify the `opensearch_logger.OpensearchHandler` as one of the handlers and provide parameters to it.

Full guide on tweaking `logging.config` can be found in the [official python documentation][logging-config].

```python
import logging.config

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "./debug.log",
            "maxBytes": 102400,
            "backupCount": 5,
        },
        "opensearch": {
            "level": "INFO",
            "class": "opensearch_logger.OpensearchHandler",
            "hosts": [{"host": "localhost", "port": 9200}],
            "index_name": "my-logs",
            "extra_fields": {"App": "test", "Environment": "dev"},
            "use_ssl": True,
            "verify_certs": False,
        },
    },
    "loggers": {
        "root": {
            "handlers": ["file", "opensearch"],
            "level": "INFO",
            "propogate": False,
        },
        "django": {
            "handlers": ["file","opensearch"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

logging.config.dictConfig(LOGGING)
```

## Dependencies

This library uses the following packages

* [`opensearch-py`][opensearch-py]

## Building from source & Developing

This package uses [`pyenv`][pyenv] (optional) and [Poetry][poetry] for development purposes.
It also uses Docker to run Opensearch container for integration testing during development.

1. Clone the repo.
1. Instruct poetry to use a proper Python version and install dependencies.

   ```shell
   poetry env use 3.8.12
   poetry install
   ```

1. Run tests

   **WARNING**: You need opensearch running on `https://localhost:9200` to run the tests.
   Part of the tests verifies that correct number of logs actually gets into Opensearch.
   Alternatively, you can specify the `TEST_OPENSEARCH_HOST` variable and set it to a different value pointing
   to the running Opensearch server.

   There are not many tests, but they run with **5 seconds cooldown each** to allow Opensearch to process the
   newly sent log records properly and verify their count.

   Small helper scripts are available in the `tests/` directory to start and stop Opensearch using Docker.

   ```shell
   # Give it 5-10 seconds to initialize before running tests
   tests/start-opensearch-docker.sh

   # Run tests
   poetry run pytest

   # Run coverage tests
   poetry run pytest --cov --cov-report=html

   # Run mypy typing verification
   poetry run pytest --mypy opensearch_logger --strict-markers

   # Run flake8 to make sure code style is correct
   poetry run flake8

   # Turn off Opensearch
   tests/stop-opensearch-docker.sh
   ```

   Before turning the Opensearch container off, it is possible to check that the records are actually there.

   ```shell
   # Verify index is in place and has required number of records
   $ curl -k -XGET "https://admin:admin@localhost:9200/_cat/indices/test*?v&s=index"
   health status index                             uuid                   pri rep docs.count docs.deleted store.size pri.store.size
   yellow open   test-opensearch-logger-2021.11.08 N0BEEnG2RIuPP0l8RZE0Dg   1   1          7            0     29.7kb         29.7kb
   ```

1. Build a package

   ```shell
   poetry build
   ```

## Contributions

Contributions are welcome! 👏  🎉

Please create a GitHub issue and a Pull Request that references that issue as well as your proposed changes.
Your Pull Request will be automatically tested using GitHub actions.

After your pull request will be accepted, it will be merged and the version of the library will be bumped
and released to PyPI.

## History

This is a fork of [Python Elasticsearch ECS Log handler][python-elasticsearch-ecs-logger] project
which was in turn forked from [Python Elasticsearch Logger][python-elasticsearch-logger] project.
While original is perfectly suitable for logging to Elasticsearch, due to the split between
Opensearch and Elasticsearch it makes sense to make a fork entirely tailored to work with Opensearch
and based on the official [`opensearch-py`][opensearch-py] Python library.

The API between `python-elasticsearch-ecs-logger` and this project has slightly changed for better
compatibility with Opensearch and for the purposes of simplification.

## License

Distributed under the terms of [Apache 2.0][apache-2.0] license, opensearch-logger is free and open source software.

[opensearch]: https://opensearch.org/
[opensearch-py]: https://pypi.org/project/opensearch-py/
[logging]: https://docs.python.org/3/library/logging.html
[ecs]: https://www.elastic.co/guide/en/ecs/current/index.html
[logging-config]: https://docs.python.org/3/library/logging.config.html
[pyenv]: https://github.com/pyenv/pyenv
[poetry]: https://python-poetry.org/
[ecs-mapping]: https://github.com/vduseev/opensearch-logger/blob/main/mappings/ecs1.4.0_compatible_minimal.json
[apache-2.0]: https://github.com/vduseev/opensearch-logger/blob/main/LICENSE.md
[python-elasticsearch-ecs-logger]: https://github.com/IMInterne/python-elasticsearch-ecs-logger
[python-elasticsearch-logger]: https://github.com/cmanaha/python-elasticsearch-logger
