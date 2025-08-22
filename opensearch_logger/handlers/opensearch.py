"""OpenSearch logging Handler facility."""

from typing import Any, List, Optional

from opensearchpy import OpenSearch, helpers

from ..serializers import OpenSearchLoggerSerializer
from .base import BaseSearchHandler


class OpenSearchHandler(BaseSearchHandler):
    """OpenSearch logging handler.

    Allows to log to OpenSearch in json format.
    All LogRecord fields are serialised and inserted
    """

    def __init__(
        self,
        **kwargs: Any,
    ):
        """Initialize OpenSearch logging handler.

        All of the parameters have default values except for connection
        parameters. Connection parameters are read from kwargs and passed
        directly to OpenSearch client. See opensearch-py documentation for the
        full list of
        accepted parameters.

        By default, the corresponsing date will be appended to the index_name.
        Consider a week between Nov 8, 2021 (Monday) and Nov 14, 2021
        (Sunday).
        In case It Is Wednesday, my dudes, then, depending on the index_rotate
        parameter, the index name for that day will be:

        * python-logs-2021.11.10 for DAILY
        * python-logs-2021.11.08 for WEEKLY (first day of the week)
        * python-logs-2021.11.01 for MONTHLY (first day of the month)
        * python-logs-2021.01.01 for YEARLY (first day of the year)
        * python-logs for NEVER (no date gets appended)

        Examples:
            The configuration below is suitable for connection to an
            OpenSearch docker container running locally.

            >>> import logging
            >>> from opensearch_logger import OpenSearchHandler
            >>> handler = OpenSearchHandler
            >>> handler = OpenSearchHandler(
            >>>     index_name="my-logs",
            >>>     hosts=["https://localhost:9200"],
            >>>     http_auth=("admin", "admin"),
            >>>     use_ssl=True,
            >>>     verify_certs=False,
            >>>     ssl_assert_hostname=False,
            >>>     ssl_show_warn=False,
            >>> )
            >>> logger = logging.getLogger(__name__)
            >>> logger.setLevel(logging.INFO)
            >>> logger.addHandler(handler)
            >>> logger.info("This message will be indexed in OpenSearch")
            >>> logger.info(
            ...     f"This one will have extra fields", extra={"topic": "dev"}
            ... )
        """
        super().__init__(**kwargs)

        self.client_kwargs = kwargs
        self._client: Optional[OpenSearch] = None
        self.serializer = OpenSearchLoggerSerializer()

    def bulk(self, actions: List[Any]) -> None:
        """Wraps calling of bulk submission."""
        helpers.bulk(
            client=self._get_client(),
            actions=actions,
            stats_only=True,
        )

    def _get_client(self) -> OpenSearch:
        if self._client is None:
            self._client = OpenSearch(**self.client_kwargs)
        return self._client
