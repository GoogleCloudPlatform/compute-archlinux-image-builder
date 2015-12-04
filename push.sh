#!/bin/bash

VM_USER="${USER}"
PACKAGE_FILE="archbuilder.tar.gz"
INSTANCE_NAME="instance-1"
ZONE="us-east1-d"
ARCH_DATE="20151203"
SSH_TARGET=${VM_USER}@${INSTANCE_NAME}

rm -f ${PACKAGE_FILE}
tar czf ${PACKAGE_FILE} *
gcloud compute ssh ${SSH_TARGET} --command "rm -fr *" --zone=${ZONE}
gcloud compute copy-files ${PACKAGE_FILE} ${SSH_TARGET}:/home/${VM_USER} --zone=${ZONE}

gcloud compute ssh ${SSH_TARGET} --command "tar xvzf ${PACKAGE_FILE}; rm ${PACKAGE_FILE}; chmod +x *.sh" --zone=${ZONE}
gcloud compute ssh ${SSH_TARGET} --command "sudo ./build-gce-arch.py --verbose --size_gb=100 --debug --public --upload gs://gce-arch-images/unverified/arch-v${ARCH_DATE}.tar.gz --register" --zone=${ZONE}
