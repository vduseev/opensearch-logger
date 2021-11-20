"""JSON serializer for OpenSearch."""
from typing import Any

from opensearchpy.serializer import JSONSerializer


class OpenSearchLoggerSerializer(JSONSerializer):
    """JSON serializer inherited from the OpenSearch JSON serializer.

    Allows to serialize logs for OpenSearch.
    Manage the record.exc_info containing an exception type.
    """

    def default(self, data: Any) -> Any:
        """Transform unknown types into strings.

        Args:
            data: The data to serialize before sending it to elastic search.
        """
        try:
            return super(OpenSearchLoggerSerializer, self).default(data)
        except TypeError:
            return str(data)
