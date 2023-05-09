#!/bin/bash

# Load the JSON object from a file
json=$(cat cdk/cdk.json)

# Parse the JSON object to get the environment variables
names=$(echo $json | jq -r '.context.config.env.test.deployments[].name')


# Loop through the names and create the URLs
i=0
for n in $names; do
  url="https://$n-test.gitops-demo.virtualcomputing.cz"
  echo "Fetching version from $url..."
  resp=$(curl -s $url)
  version=$(echo $json | jq -r ".context.config.env.test.deployments[$i].version")
  v=$(echo $resp | grep -Po '(?<=version = )[0-9\.]+')
  echo "Version: $v"
  if [[ "$v" != "$version" ]]; then
    echo "Version mismatch for $n: expected $version, actual $v"
  fi
  i=$i+1
done