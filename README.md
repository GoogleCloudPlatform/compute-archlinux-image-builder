## Arch Linux Image Builder for GCE

Creates an Arch Linux image that can run on Google Compute Engine.

The image is configured close to the recommendations listed on [Building an image from scratch](https://developers.google.com/compute/docs/images#buildingimage).

These scripts are written in Python3.

## Usage

### Install and Configure Cloud SDK (one time setup)
```
# Install Cloud SDK (https://developers.google.com/cloud/sdk/)
# For linux:
curl https://sdk.cloud.google.com | bash

gcloud auth login
gcloud config set project <project>
# Your project ID in Cloud Console, https://console.developers.google.com/
```

### On a Compute Engine VM (recommended)
```
./build-arch-on-gce.sh --upload gs://${BUCKET}/archlinux.tar.gz

# You will need a Cloud Storage bucket.
# List buckets owned by your project.
gsutil ls gs://
# Create a new bucket
gsutil mb gs://${BUCKET}
```

### Locally
```
# Install Required Packages
# Arch Linux
sudo pacman -S python haveged
# Debian
sudo apt-get -y install python3 haveged
# Redhat
sudo yum install -y python3 haveged

./build-gce-arch.py --verbose
# Upload to Cloud Storage
gsutil cp archlinux-gce.tar.gz gs://${BUCKET}/archlinux.tar.gz

# Add image to project
gcloud compute images insert archlinux \
  --source-uri gs://${BUCKET}/archlinux.tar.gz \
  --description "Arch Linux for Compute Engine"
```


## Contributing changes

* See [CONTRIB.md](CONTRIB.md)


## Licensing
All files in this repository are under the [Apache License, Version 2.0](LICENSE) unless noted otherwise.
