# OpenSearch Logger for Python

<p>
    <a href="https://github.com/vduseev/opensearch-logger/actions/workflows/test.yml"><img alt="Tests (main branch)" src="https://img.shields.io/github/actions/workflow/status/vduseev/opensearch-logger/test.yml?logo=github"></a>
    <a href="https://codecov.io/gh/vduseev/opensearch-logger"><img alt="Code coverage" src="https://img.shields.io/codecov/c/github/vduseev/opensearch-logger?logo=codecov&logoColor=white"></a>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="Package version" src="https://img.shields.io/pypi/v/opensearch-logger?logo=python&logoColor=white&color=blue"></a>
    <a href="https://pypi.org/pypi/opensearch-logger"><img alt="Supported python versions" src="https://img.shields.io/pypi/pyversions/opensearch-logger?logo=python&logoColor=white"></a>
    <a href="https://pypistats.org/packages/opensearch-logger"><img alt="PyPI Downloads" src="https://img.shields.io/pypi/dm/opensearch-logger?logo=python&logoColor=white&color=blue"></a>
</p>

This library provides a standard Python [logging][logging] handler compatible with [OpenSearch][opensearch] suite.

The **goals** of this project are

* to provide a **simple** and direct logging from Python to OpenSearch without *fluentd*, *logstash* or other middleware;
* keep it up to date with the growing difference between OpenSearch and Elasticsearch projects;
* keep the library easy to use, robust, and simple.

The library has been open-sourced from an internal project where it has been successfully used in production
since the release of OpenSearch 1.0.

Generated log records follow the [Elastic Common Schema (ECS)][ecs] field naming convention.
For better performance, it is recommended to set up a proper mapping for your logging indices.
However, everything will work fine without it.
A ready to use [compatible JSON mapping][ecs-mapping] can be found [in the repository][ecs-mapping].

## Installation

```shell
pip install opensearch-logger
```

## Usage

Just add the OpenSearch handler to your Python logger

```python
import logging
from opensearch_logger import OpenSearchHandler

handler = OpenSearchHandler(
    index_name="my-logs",
    hosts=["https://localhost:9200"],
    http_auth=("admin", "admin"),
    http_compress=True,
    use_ssl=True,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
```

To send logs to OpenSearch simply use the same regular logging commands

```python
# Logging a simple text message
logger.info("This message will be indexed in OpenSearch")

# Now, as an example, let's measure how long some operation takes
start_time = time.perf_counter()

heavy_database_operation()

elapsed_time = time.perf_counter() - start_time

# Let's send elapsed_time as an exatra parameter to the log record below.
# This will make the `elapsed_time` field searchable and aggregatable.
logger.info(
    f"Database operation took {elapsed_time:.3f} seconds",
    extra={"elapsed_time": elapsed_time},
)
```

## Configuration

The `OpenSearchHandler` constructor takes several arguments described in the table below.
These parameters specify the name of the index, buffering settings, and some general behavior.
None of this parameters are mandatory.

All other keyword arguments are passed directly "as is" to the underlying `OpenSearch` python client.
Full list of connection parameters can be found in [`opensearch-py`][opensearch-py] docs.
At least one connection parameter **must** be provided, otherwise a `TypeError` will be thrown.

## Logging parameters

| Parameter | Default | Description |
| - | - | - |
| `index_name` | `"python-logs"` | Base name of the OpenSearch index name that will be created. Or name of the data stream if `is_data_stream` is set to `True`.  |
| `index_rotate` | `DAILY` | Frequency that controls what date is appended to index name during its creation. `OpenSearchHandler.DAILY`. |
| `index_date_format` | `"%Y.%m.%d"` | Format of the date that gets appended to the base index name. |
| `index_name_sep` | `"-"` | Separator string between `index_name` and the date, appended to the index name. |
| `is_data_stream` | `False` | A flag to indicate that the documents will get indexed into a data stream. If `True`, index rotation settings are ignored. |
| `buffer_size` | `1000` | Number of log records which when reached on the internal buffer results in a flush to OpenSearch. |
| `flush_frequency` | `1` | Float representing how often the buffer will be flushed (in seconds). |
| `extra_fields` | `{}` | Nested dictionary with extra fields that will be added to every log record. |
| `raise_on_index_exc` | `False` | Raise exception if indexing the log record in OpenSearch fails. |

## Connection parameters

Here are a few examples of the connection parameters supported by the OpenSearch client.
For more details please check the [`opensearch-py`][opensearch-py] documentation.

| Parameter | Example | Description |
| - | - | - |
| `hosts` | `["https://localhost:9200"]` | The list of hosts to connect to. Multiple hosts are allowed. |
| `http_auth` | `("admin", "admin")` | Username and password to authenticate against the OpenSearch servers. |
| `http_compress` | `True` | Enables gzip compression for request bodies. |
| `use_ssl` | `True` | Whether communications should be SSL encrypted. |
| `verify_certs` | `False` | Whether the SSL certificates are validated or not. |
| `ssl_assert_hostname` | `False` | Verify authenticity of host for encrypted connections. |
| `ssl_show_warn` | `False` | Enable warning for SSL connections. |
| `ca_certs` | `"/var/lib/root-ca.pem"` | CA bundle path for using intermediate CAs with your root CA. |

## Configuration with logging.config or in Django

Similarly to other log handlers, `opensearch-logger` supports configuration via `logging.config` facility.
Just specify the `opensearch_logger.OpenSearchHandler` as one of the handlers and provide it with parameters.

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
            "class": "opensearch_logger.OpenSearchHandler",
            "index_name": "my-logs",
            "extra_fields": {"App": "test", "Environment": "dev"},
            "hosts": [{"host": "localhost", "port": 9200}],
            "http_auth": ("admin", "admin"),
            "http_compress": True,
            "use_ssl": True,
            "verify_certs": False,
            "ssl_assert_hostname": False,
            "ssl_show_warn": False,
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

## Using AWS OpenSearch

Package `requests_aws4auth` is required to connect to the AWS OpenSearch service.

```python
import boto3
from opensearch_logger import OpenSearchHandler
from requests_aws4auth import AWS4Auth
from opensearchpy import RequestsHttpConnection

host = ""  # The OpenSearch domain endpoint starting with https://
region = "us-east-1"  # AWS Region
service = "es"
creds = boto3.Session().get_credentials()

handler = OpenSearchHandler(
    index_name="my-logs",
    hosts=[host],
    http_auth=AWS4Auth(creds.access_key, creds.secret_key, region, service, session_token=creds.token),
    use_ssl=True,
    verify_certs=True,
    ssl_assert_hostname=True,
    ssl_show_warn=True,
    connection_class=RequestsHttpConnection,
)
```

## Using Kerberos Authentication

Package `requests_kerberos` is required to authenticate using Kerberos.

```python
from opensearch_logger import OpenSearchHandler
from requests_kerberos import HTTPKerberosAuth, DISABLED

handler = OpenSearchHandler(
    index_name="my-logs",
    hosts=["https://localhost:9200"],
    http_auth=HTTPKerberosAuth(mutual_authentication=DISABLED),
    use_ssl=True,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)
```

## Using Data Streams

Indexing documents into data streams is supported by just setting the `is_data_stream` parameter to `True`.

In this configuration however, It is OpenSearch that solely manages the rollover of the data stream's write index.
The logging handler's rollover functionality and index rotation settings (e.g. `index_rotate`) are disabled.

The following is an example configuration to send documents to a data stream.

```python
handler = OpenSearchHandler(
    index_name="logs-myapp-development",
    is_data_stream=True,
    hosts=["https://localhost:9200"],
    http_auth=("admin", "admin")
)
```

## Dependencies

This library depends on the following packages

* [`opensearch-py`][opensearch-py]

## Building from source & Developing

This package uses [`uv`][uv] for fast dependency management and [`pyenv`][pyenv] (optional) for Python version management.
It also uses Docker to run OpenSearch container for integration testing during development.

### Requirements
- Python 3.9 or later
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for running OpenSearch during testing)

### Setup

1. Clone the repo.
1. Install uv if you haven't already:

   ```shell
   # On macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Or with pip
   pip install uv
   ```

1. Set up the development environment:

   ```shell
   # Install dependencies and create virtual environment
   uv sync
   
   # This automatically:
   # - Creates a virtual environment
   # - Installs all dependencies from uv.lock
   # - Installs the package in development mode
   ```

### Development Workflow

1. **Running Tests**

   Tests require OpenSearch running on `https://localhost:9200` (local dev) or `http://localhost:9200` (CI).
   The tests automatically adapt based on the URL scheme to handle authentication and SSL settings.

   ```shell
   # Start OpenSearch with Docker (for local development)
   tests/start-opensearch-docker.sh
   
   # Wait 5-10 seconds, then run tests
   uv run pytest
   
   # Run with coverage
   uv run pytest --cov --cov-report=html
   
   # Stop OpenSearch
   tests/stop-opensearch-docker.sh
   ```

1. **Code Quality**

   ```shell
   # Format code
   uv run ruff format .
   
   # Check linting
   uv run ruff check .
   
   # Type checking
   uv run mypy opensearch_logger --strict
   ```

1. **Dependency Management**

   ```shell
   # Add a new dependency to pyproject.toml, then:
   uv sync
   
   # Update all dependencies to latest versions
   uv lock --upgrade
   uv sync
   ```

### Release Process

1. **Version Management**

   ```shell
   # Bump version (patch/minor/major)
   uv run bump2version patch
   ```

1. **Building and Publishing**

   ```shell
   # Build package
   uv build
   
   # Publish to PyPI (requires proper authentication)
   uv publish
   ```

**Note**: The CI/CD pipeline automatically handles building and publishing when version tags are pushed to the repository.

### Cheat Sheet for working with OpenSearch

1. List all created indices, including count of documents

   ```shell
   $ curl -k -XGET "https://admin:admin@localhost:9200/_cat/indices/test*?v&s=index"
   health status index                             uuid                   pri rep docs.count docs.deleted store.size pri.store.size
   yellow open   test-opensearch-logger-2021.11.08 N0BEEnG2RIuPP0l8RZE0Dg   1   1          7            0     29.7kb         29.7kb
   ```

1. Count documents in all indexes that start with `test`

   ```shell
   $ curl -k -XGET "https://admin:admin@localhost:9200/test*/_count"
   {"count":109,"_shards":{"total":1,"successful":1,"skipped":0,"failed":0}}
   ```

1. Retrieve all documents from indexes that start with `test`

   ```shell
   $ curl -k -XGET "https://admin:admin@localhost:9200/test*/_search" -H 'Content-Type: application/json' -d '{"query":{"match_all":{}}}'
   {
     "took": 1,
     "timed_out": false,
     "hits": {
       "total": {
       "value": 109,
       "relation": "eq"
     }
     ...
   ```

1. Same, but limit the number of returned documents to 10

   ```shell
   $ curl -k -XGET "https://admin:admin@localhost:9200/test*/_search?size=10" -H 'Content-Type: application/json' -d '{"query":{"match_all":{}}}'
   {
     "took": 1,
     "timed_out": false,
     "hits": {
       "total": {
       "value": 109,
       "relation": "eq"
     }
     ...
   ```

## Contributions

Contributions are welcome! 👏  🎉

Please create a GitHub issue and a Pull Request that references that issue as well as your proposed changes.
Your Pull Request will be automatically tested using GitHub actions.

After your pull request will be accepted, it will be merged and the version of the library will be bumped
and released to PyPI by project maintainers.

## History

This is a fork of [Python Elasticsearch ECS Log handler][python-elasticsearch-ecs-logger] project
which was in turn forked from [Python Elasticsearch Logger][python-elasticsearch-logger] project.
While original is perfectly suitable for logging to Elasticsearch, due to the split between
OpenSearch and Elasticsearch it makes sense to make a fork entirely tailored to work with OpenSearch
and based on the official [`opensearch-py`][opensearch-py] Python library.

The API between `python-elasticsearch-ecs-logger` and this project has slightly changed for better
compatibility with OpenSearch and for the purposes of simplification.

## Featured on

The `opensearch-logger` project is featured on the official
[OpenSearch Community Projects page][community-projects] 🚀.

![OpenSearch Community Featured Project](docs/images/community-projects.png)

## License

Distributed under the terms of [Apache 2.0][apache-2.0] license, opensearch-logger is free and open source software.

[opensearch]: https://opensearch.org/
[opensearch-py]: https://pypi.org/project/opensearch-py/
[logging]: https://docs.python.org/3/library/logging.html
[ecs]: https://www.elastic.co/guide/en/ecs/current/index.html
[logging-config]: https://docs.python.org/3/library/logging.config.html
[pyenv]: https://github.com/pyenv/pyenv
[ecs-mapping]: https://github.com/vduseev/opensearch-logger/blob/main/mappings/ecs1.4.0_compatible_minimal.json
[apache-2.0]: https://github.com/vduseev/opensearch-logger/blob/main/LICENSE.md
[python-elasticsearch-ecs-logger]: https://github.com/IMInterne/python-elasticsearch-ecs-logger
[python-elasticsearch-logger]: https://github.com/cmanaha/python-elasticsearch-logger
[community-projects]: https://opensearch.org/community_projects
[uv]: https://docs.astral.sh/uv/
