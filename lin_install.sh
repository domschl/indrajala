#!/bin/bash

sudo mkdir /var/lib/indrajala
sudo mkdir /var/lib/indrajala/tasks
sudo cp -v target/release/indrajala /usr/bin
sudo cp -rv python_indrajala/sub_tasks/* /var/lib/indrajala/tasks
sudo cp -rv python_indrajala/indralib /var/lib/indrajala/tasks
sudo chown -R indrajala:indrajala /var/lib/indrajala
