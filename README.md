# Opensearch Logger for Python

<p>
    <a href="https://pypi.python.org/pypi/opensearch-logger"><img alt="Supported python versions" src="https://img.shields.io/pypi/pyversions/opensearch-logger.svg"></a>
    <a href="https://pypi.python.org/pypi/opensearch-logger"><img alt="Package stability" src="https://img.shields.io/pypi/status/opensearch-logger.svg"></a>
    <a href="https://pypi.python.org/pypi/opensearch-logger"><img alt="License" src="https://img.shields.io/pypi/l/opensearch-logger.svg"></a>
</p>

This library provides a logging handler compatible with Opensearch and standard Python `logging` module.

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
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "admin"),
    use_ssl=True,
    verify_certs=False,
    index_prefix="my-logs",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
```

To log to Opensearch, simply use the regular logging commands:

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
| `index_prefix` | - | A string with the prefix of the elasticsearch index that will be created. |
| `index_rotate` | `OpensearchHandler.DAILY` | The period which is used to generate actual index names and rotate them. |
| `buffer_size` | 1000 | An integer that defines size which when reached on the internal buffer results in a flush to Opensearch. |
| `flush_frequency` | 1 | A float representing how often and when the buffer will be flushed (in seconds). |
| `extra_fields` | A nested dictionary with all the additional fields that you would like to add to the logs. |

All other keyword arguments are passed directly to the underlying Opensearch python client.
Full list of connection parameters can be found in [`opensearch-py`] docs. Here are few examples:

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
            "handlers": ["file","elasticsearch"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

logging.config.dictConfig(LOGGING)
```

## Dependencies

This library uses the following packages

* opensearch-py
* requests

## Building from source & Developing

This package uses Poetry for development purposes.

[opensearch-py](https://github.com/opensearch-project/opensearch-py)
