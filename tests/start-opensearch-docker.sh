#!/bin/bash

docker pull opensearchproject/opensearch:latest
docker run -d --rm \
  --name test-opensearch-logger \
  -e "cluster.name=opensearch-cluster" \
  -e "node.name=opensearch" \
  -e "discovery.type=single-node" \
  -e "bootstrap.memory_lock=true" \
  -p "9200:9200" \
  opensearchproject/opensearch:latest
