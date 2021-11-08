# Opensearch Logger for Python

<p>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="Supported python versions" src="https://img.shields.io/pypi/pyversions/opensearch-logger?logo=python&logoColor=white"></a>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="Package stability" src="https://img.shields.io/pypi/status/opensearch-logger?logo=python&logoColor=white"></a>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="License" src="https://img.shields.io/pypi/l/opensearch-logger"></a>
    <a href="https://github.com/vduseev/opensearch-logger/actions/workflows/test.yml"><img alt="Tests (main branch)" src="https://img.shields.io/github/workflow/status/vduseev/opensearch-logger/Test/main?logo=github"></a>
</p>

This library provides a standard Python logging handler compatible with [Opensearch][opensearch] suite.

The **goals** of this project are

* to provide a **simple** and direct logging from Python to Opensearch without *fluentd*, *logstash* or other middleware;
* keep it up to date with the growing difference between Opensearch and Elasticsearch projects;
* keep the library easy to use, robust, and simple (entire source code is currently `~300` lines).

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
    hosts=["https://localhost:9200"],
    http_auth=("admin", "admin"),
    use_ssl=True,
    verify_certs=False,
    index_prefix="my-logs",
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

The constructor takes the following parameters

| Argument | Default | Description |
| - | - | - |
| `index_prefix` | `python-logs` | Prefix of the Opensearch index name that will be created. |
| `index_rotate` | `OpensearchHandler.DAILY` | The period which is used to generate actual index names and rotate them. |
| `buffer_size` | 1000 | Number of log records which when reached on the internal buffer results in a flush to Opensearch. |
| `flush_frequency` | 1 | Float representing how often the buffer will be flushed (in seconds). |
| `extra_fields` | `{}` | Nested dictionary with all the additional fields that you would like to add to all logs. |

All other keyword arguments are passed directly to the underlying Opensearch python client.
Full list of connection parameters can be found in [`opensearch-py`][opensearch-py] docs. Here are few examples:

* `hosts`:  The list of hosts that Opensearch client will connect, multiple hosts are allowed.

  ```python
  [{"host": "localhost", "port": 9200}, "https://admin:admin@opensearch:9200"]
  ```

* `http_auth`: Tuple with user name and password that will be used to authenticate against the Opensearch servers.

  ```python
  ("admin","admin")
  ```

* `use_ssl`: A boolean that defines if the communications should be SSL encrypted.
* `verify_certs`: A boolean that defines whether the SSL certificates are validated or not.

## Configuring using dictConfig or in Django

A complete configuration of logging is also supported.
Just specify the `opensearch_logger.OpensearchHandler` as one of the handlers.

Full guide on tweaking `logging.config` can be found in the official python documentation for [`dictConfig`][dictConfig].

```python
import logging.config

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {
            "format": "%(asctime)-15s | %(process)d | %(levelname)s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
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
            "index_prefix": "my-logs",
            "extra_fields": {"App": "test", "Environment": "dev"},
            "use_ssl": True,
            "verify_certs": False,
        },
    },
    "loggers": {
        "root": {
            "handlers": ["console", "file", "opensearch"],
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

In the example above following things are configured:

* 1 formatter named "standard" that will be used to output to the terminal.
* 3 different log handlers:
  * One named `console` for logging to terminal, through the `stderr` stream
  * One called `file` for logging into a rotated log file
  * And finally one for Opensearch
* 2 loggers are configured:
  * `root`, from which all other loggers are derived, will log all messages with level INFO or higher using all three handlers.
  * `django` handler log all messages with level DEBUG or higher using file and opensearch handlers.

## Dependencies

This library uses the following packages

* [`opensearch-py`][opensearch-py]

## Building from source & Developing

This package uses [`pyenv`][pyenv] (optional) and [Poetry][poetry] for development purposes.
It also uses Docker to run Opensearch container for integration testing during development.

1. Clone the repo
1. Instruct poetry to use a proper Python version for virtual environment creation.

   ```shell
   poetry env use 3.8.12
   ```

1. Create virtual environment and install dependencies

   ```shell
   poetry install
   ```

1. Test that the library works

   **WARNING**: You need Docker installed and available on the system to run the tests.
   Part of the tests verifies that logs actually get into Opensearch that runs in a docker container.

   ```shell
   poetry run pytest
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

[opensearch]: https://opensearch.org/
[opensearch-py]: https://github.com/opensearch-project/opensearch-py
[logging]: https://docs.python.org/3/library/logging.html
[ecs]: https://www.elastic.co/guide/en/ecs/current/index.html
[dictConfig]: https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig
[pyenv]: https://github.com/pyenv/pyenv
[poetry]: https://python-poetry.org/
[ecs-mapping]: https://github.com/vduseev/opensearch-logger/blob/master/mappings/ecs1.4.0_compatible_minimal.json
