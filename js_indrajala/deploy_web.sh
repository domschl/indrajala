#!/bin/bash

# Check, if executable `tomlq` is available, else exit:
if ! command -v tomlq &> /dev/null; then
    echo "tomlq could not be found, 'pip install tomlq' or similar."
    exit 1
fi

data_directory=$(tomlq -r '.indrajala.data_directory' ../config/indrajala.toml)
# expand tilde:
data_directory="${data_directory/#\~/$HOME}"
echo "Using data_directory: >$data_directory<"

rsync -avh --exclude "deploy_web.sh" ./ $data_directory/web/ --delete

echo "Check if npm install in plot/scripts is up-to-date"
