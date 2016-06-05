## Arch Linux Image Builder for GCE

This project is a collection of scripts that create an Arch Linux OS image that
can run on [Google Compute Engine](https://cloud.google.com/compute/).

The image is configured close to the recommendations listed on
[Building an image from scratch](https://developers.google.com/compute/docs/images#buildingimage).

These scripts are written in Python3.

## Prebuilt Images
 * arch-v20160502 - [gs://gce-arch-images/arch-v20160502.tar.gz](https://storage.googleapis.com/gce-arch-images/arch-v20160502.tar.gz)
 * arch-v20151203 - [gs://gce-arch-images/arch-v20151203.tar.gz](https://storage.googleapis.com/gce-arch-images/arch-v20151203.tar.gz)
 * arch-v20151103 - [gs://gce-arch-images/arch-v20151103.tar.gz](https://storage.googleapis.com/gce-arch-images/arch-v20151103.tar.gz)
 * arch-v20151023 - [gs://gce-arch-images/arch-v20151023.tar.gz](https://storage.googleapis.com/gce-arch-images/arch-v20151023.tar.gz)
 * arch-v20150903 - [gs://gce-arch-images/arch-v20150903.tar.gz](https://storage.googleapis.com/gce-arch-images/arch-v20150903.tar.gz)

You can add these images using the
[Developers Console](https://console.developers.google.com/compute/imagesAdd).

You can use [Cloud SDK](https://cloud.google.com/sdk/) to add the prebuilt
images to your project. To do that run the following command.

```
gcloud compute images create arch-v20160502 \
  --source-uri gs://gce-arch-images/arch-v20160502.tar.gz \
  --description "Arch Linux built on 2016-05-02"
  --family "arch"
```

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

## Contributing Changes

* See [CONTRIB.md](CONTRIB.md)


## Licensing
All files in this repository are under the
[Apache License, Version 2.0](LICENSE) unless noted otherwise.


## Support
Google Inc. does not provide any support, guarantees, or warranty for this
project or the images provided.
