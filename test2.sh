#!/bin/bash

env_name="test"
#url="gitops-demo.virtualcomputing.cz"
#env_name=$ENV_NAME

json=$(cat cdk/cdk.json)
# Get the deployments object for the given environment
deployments=$(echo $json | jq -r --arg env "$env_name" '.context.config.env[$env].deployments')
url=$(echo $json | jq -r '.context.config.r53_zone_name')

# Loop over the deployments and make a curl request for each one
echo "Checking deployment versions for $env_name environment:"
echo "$deployments" | jq -r '.[] | .name' | while read name; do
  # Build the URL using the deployment name
  deployment_url="https://$name-$env_name.$url"
  
  # Make the curl request and extract the version from the response
  resp=$(curl -s $deployment_url)
  version=$(echo $resp | grep -Po '(?<=version = )[0-9\.]+')

  # Get the expected version from the deployments object
  expected_version=$(echo "$deployments" | jq -r --arg name "$name" '.[] | select(.name == $name) | .version')

  # Check if the response version matches the expected version
  if [ "$version" = "$expected_version" ]; then
    echo "$name: OK! Expected $expected_version and got $version"
  else
    echo "$name: Mismatch! Expected $expected_version but got $version"
  fi
done