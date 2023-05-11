#!/bin/bash

#env_name="dev"
env_name=$ENV

response_code=0

json=$(cat config/config.json)
#get URL from the config
url=$(echo $json | jq -r '.r53_zone_name')
# Get the deployments object for the given environment
deployments=$(echo $json | jq -r --arg env "$env_name" '.env[$env].deployments')

# Loop over the deployments and make a curl request for each one
echo "Checking deployment versions for $env_name environment:"
echo "$deployments" | jq -r '.[] | .name' | while read name; do
  # Build the URL using the deployment name
  deployment_url="https://$name-$env_name.$url"
  echo $deployment_url
  
  # Make the curl request and extract the version from the response
  resp=$(curl -s $deployment_url)
  version=$(echo $resp | grep -oP 'Version:\s*\K\d+\.\d+')

  # Get the expected version from the deployments object
  expected_version=$(echo "$deployments" | jq -r --arg name "$name" '.[] | select(.name == $name) | .version')

  # Check if the response version matches the expected version
  if [ "$version" = "$expected_version" ]; then
    echo "$name: OK! Expected $expected_version and got $version"
  else
    echo "$name: Mismatch! Expected $expected_version but got $version"
    response_code=1
  fi
done

exit $response_code