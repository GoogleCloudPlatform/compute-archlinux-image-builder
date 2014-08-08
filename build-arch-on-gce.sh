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

# Creates a Debian VM to build an Arch Linux image.

INSTANCE_ID=${RANDOM}
INSTANCE_NAME=archbuilder${INSTANCE_ID}
ZONE_NAME=us-central1-f
MACHINE_TYPE=n1-standard-2
GIT_SOURCE_URI=https://github.com/GoogleCloudPlatform/compute-archlinux-image-builder.git
SCRIPT_PARAMS="$*"

function GcloudNotConfiguredHelp() {
  echo "gcloud is missing or project is not set."
  echo "Run these commands:"
  echo " gcloud auth login"
  echo " gcloud config set project <project>"
  echo ""
  echo "To install Cloud SDK go here: https://developers.google.com/cloud/sdk/"
}

function MissingRequiredFlagsHelp() {
  echo "--upload parameter is required to build on VM."
  echo "Example: --upload gs://cloud-storage-bucket/archlinux.tar.gz"
  echo ""
  echo "Cloud Storage Buckets already in your project:"
  gsutil ls gs://
}

function PrintHelp() {
  ./build-gce-arch.py --help
}

function DeployVm() {
  echo "Creating Instance, ${INSTANCE_NAME}"
  gcloud compute instances create ${INSTANCE_NAME} \
    --image debian-7-backports \
    --machine-type ${MACHINE_TYPE} \
    --zone ${ZONE_NAME} \
    --metadata-from-file startup-script=build-arch-on-gce-remote.sh \
    --metadata \
    script-params="${SCRIPT_PARAMS}" \
    instance-name="${INSTANCE_NAME}" \
    instance-zone="${ZONE_NAME}" \
    git-source-uri="${GIT_SOURCE_URI}" \
    --scopes compute-rw storage-full
  echo "You can monitor progress of the build via:"
  echo "  gcloud compute instances get-serial-port-output ${INSTANCE_NAME} --zone ${ZONE_NAME} | grep startupscript"
}


GCLOUD_PROJECT_CONFIGURED=$(gcloud config list --all | grep project)
if [ "${GCLOUD_PROJECT_CONFIGURED}" != "" ]; then
  if [[ "${SCRIPT_PARAMS}" == *--help* ]]; then
    PrintHelp
  elif [[ "${SCRIPT_PARAMS}" == *--upload* ]]; then
    echo "Creating VM to build Arch Linux"
    DeployVm
  else
    MissingRequiredFlagsHelp
  fi
else
  GcloudNotConfiguredHelp
fi
