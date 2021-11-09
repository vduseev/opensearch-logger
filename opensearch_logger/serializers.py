"""JSON serializer for Opensearch."""
from typing import Any

from opensearchpy.serializer import JSONSerializer


class OpensearchLoggerSerializer(JSONSerializer):
    """JSON serializer inherited from the Opensearch JSON serializer.

    Allows to serialize logs for Opensearch.
    Manage the record.exc_info containing an exception type.
    """

    def default(self, data: Any) -> Any:
        """Transform unknown types into strings.

        Args:
            data: The data to serialize before sending it to elastic search.
        """
        try:
            return super(OpensearchLoggerSerializer, self).default(data)
        except TypeError:
            return str(data)
