"""ElasticSearch logging Handler facility."""

from typing import Any, List, Optional

from ecs_logging import StdlibFormatter
from elasticsearch import Elasticsearch, helpers

from .base import BaseSearchHandler


class ElasticSearchHandler(BaseSearchHandler):
    """ElasticSearch logging handler.

    Allows to log to ElasticSearch cloud in json format
    """

    def __init__(
        self,
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
        super().__init__(**kwargs)

        self.client_kwargs = kwargs
        self._client: Optional[Elasticsearch] = None
        self.serializer = StdlibFormatter()

    def bulk(self, actions: List[Any]) -> None:
        """Wraps calling of bulk submission."""
        helpers.bulk(
            client=self._get_client(),
            actions=actions,
            stats_only=True,
        )

    def _get_client(self) -> Elasticsearch:
        if self._client is None:
            self._client = Elasticsearch(
                self.client_kwargs["host"],
                api_key=self.client_kwargs.get("api_key"),
            )
        return self._client
