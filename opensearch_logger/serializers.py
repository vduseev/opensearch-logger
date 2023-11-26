"""JSON serializer for OpenSearch."""

# Copyright 2021-2023 Vagiz Duseev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
