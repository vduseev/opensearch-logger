#!/bin/bash

# Copyright 2021-2025 Vagiz Duseev
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

docker pull opensearchproject/opensearch:latest
docker run -d --rm \
  --name test-opensearch-logger \
  -e "cluster.name=opensearch-cluster" \
  -e "cluster.routing.allocation.disk.threshold_enabled=false" \
  -e "node.name=opensearch" \
  -e "discovery.type=single-node" \
  -e "bootstrap.memory_lock=true" \
  -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
  -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=0penSe*rch" \
  -p "9200:9200" \
  -p "9600:9600" \
  opensearchproject/opensearch:latest
