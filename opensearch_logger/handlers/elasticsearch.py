"""ElasticSearch logging Handler facility."""

from typing import Any, Optional

from ecs_logging import StdlibFormatter
from elasticsearch import Elasticsearch, helpers

from .base import BaseSearchHandler


class ElasticSearchHandler(BaseSearchHandler):
    """ElasticSearch logging handler.

    Allows to log to ElasticSearch cloud in json format
    """

    def __init__(
        self,
        host: str,
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize ElasticSearch logging handler.

        Just pass arguments into parent class constructor, later overwriting
        to use elasticsearch module to construct the client and submit logs.

        Notice that arguments needed to instantiate the Elasticsearch client
        differ from those used by OpenSearch, so a "host" (single one) and
        "api_key" (b64 string)
        must be given.

        Examples:
            The configuration below is suitable for connection to an
            elasticsearch docker container running locally.

            >>> import logging
            >>> from opensearch_logger import ElasticSearchHandler
            >>> handler = OpenSearchHandler
            >>> handler = ElasticSearchHandler(
            >>>     index_name="my-logs",
            >>>     host="https://localhost:9200"],
            >>>     api_key="YWRtaW46YWRtaW4="
            >>> )
            >>> logger = logging.getLogger(__name__)
            >>> logger.setLevel(logging.INFO)
            >>> logger.addHandler(handler)
            >>> logger.info("This message will be indexed in ElasticSearch")
            >>> logger.info(
            ...     f"This one will have extra fields", extra={"topic": "dev"}
            ... )
        """
        # Throw an exception if connection arguments for Elasticsearch client
        # are empty
        if not kwargs:
            raise TypeError("Missing connection parameters.")

        BaseSearchHandler.__init__(self, *args)

        self.host = host
        self.client_kwargs = kwargs
        self._client: Optional[Elasticsearch] = None
        self.serializer = StdlibFormatter()
        self.bulk = helpers.bulk

    def _get_opensearch_client(self) -> Elasticsearch:
        if self._client is None:
            self._client = Elasticsearch(
                self.host,
                api_key=self.client_kwargs.get("api_key"),
            )
        return self._client
