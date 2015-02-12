#!/bin/bash
# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Build an Arch Linux image from within a GCE Debian VM.

BUILDER_ROOT=/mnt/archongce/source
INSTANCE_NAME=$(/usr/share/google/get_metadata_value attributes/instance-name)
ZONE_NAME=$(/usr/share/google/get_metadata_value attributes/instance-zone)
SCRIPT_PARAMS=$(/usr/share/google/get_metadata_value attributes/script-params)
SCRIPT_PARAMS="--verbose --register ${SCRIPT_PARAMS}"
GIT_SOURCE_URI=$(/usr/share/google/get_metadata_value attributes/git-source-uri)
REMOTE_IMAGE=$(echo "i = '${SCRIPT_PARAMS}'.split(); print i[i.index('--upload') + 1]" | python)

echo "Builder Root: ${BUILDER_ROOT}"
echo "Instance Name: ${INSTANCE_NAME}"
echo "Instance Zone: ${ZONE_NAME}"
echo "Source Git Repository: ${GIT_SOURCE_URI}"
echo "Remote Image: ${REMOTE_IMAGE}"
echo "Running script as:"
echo "  ./build-gce-arch.py ${SCRIPT_PARAMS}"

echo "Setup Builder Environment"
mkdir -p ${BUILDER_ROOT}

echo "Updating Cloud SDK"
yes | gcloud components update

function InstallDependenciesForDebian {
  echo "Installing Dependencies (Debian)"
  apt-get update
  apt-get install -y -qq python3 haveged git
}

function InstallDependenciesForRedhat {
  echo "Installing Dependencies (Redhat)"
  rpm -Uvh http://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
  yum install -y python3 haveged git
}
if [ -f /etc/redhat-release ]
then
  InstallDependenciesForRedhat
else
  InstallDependenciesForDebian
fi

echo "Getting source code..."
git clone ${GIT_SOURCE_URI} ${BUILDER_ROOT}

cd ${BUILDER_ROOT}
haveged -w 1024
gsutil rm ${REMOTE_IMAGE}
./build-gce-arch.py ${SCRIPT_PARAMS}

function SaveLogForRedhat {
  journalctl > builder.log
}

function SaveLogForDebian {
  cat /var/log/syslog | grep -o "startupscript.*" > builder.log
}

if [ -f /etc/redhat-release ]
then
  SaveLogForRedhat
else
  SaveLogForDebian
fi

gsutil cp builder.log ${REMOTE_IMAGE}.log
gcloud compute -q instances delete ${INSTANCE_NAME} --zone ${ZONE_NAME}
