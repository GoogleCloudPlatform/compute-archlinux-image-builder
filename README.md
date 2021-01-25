## Arch Linux Image Builder for Google Compute Engine

This project provides a script that creates an [Arch
Linux](https://www.archlinux.org/) image that can run on [Google Compute
Engine](https://cloud.google.com/compute/).

The image is configured to be as close as possible to a base Arch Linux
installation, while still allowing it to be fully functional and optimized for
Compute Engine.  Notable choices made and differences compared to a standard
Arch Linux installation are the following:

- GRUB is used with BIOS-based boot and a GPT partition table.
- Serial console logging is enabled from kernel command line and journald is
  configured to forward to it.
- Block multiqueue and elevator noop are configured from kernel command line to
  optimize Compute Engine disk performance.
- A minimal initcpio is configured for booting on Compute Engine virtual
  machines.
- Root filesystem is ext4.
- Locale is set to en_US.UTF-8 and timezone is set to UTC.
- Network is configured through dhclient.
- Systemd-timesyncd is enabled and configured to use the Compute Engine metadata
  server.
- Pacman keyring is configured to be built and initialized on first boot.
- Pacman mirror list is taken fresh from Arch Linux servers at the time the
  image is built.
- [Linux Guest Environment for Google Compute
  Engine](https://github.com/GoogleCloudPlatform/compute-image-packages) is
  installed and enabled.
- An OpenSSH server is installed and enabled, with root login and password
  authentication forbidden.  User SSH keys are deployed and managed
  automatically by the Linux Guest Environment as described in the
  [corresponding
  documentation](https://cloud.google.com/compute/docs/instances/connecting-to-instance).
- Sudo is installed.  Permission to use sudo is managed automatically by Linux
  Guest Environment.
- Root partition and filesystem are automatically extended at boot using
  [growpart](https://launchpad.net/cloud-utils), to support dynamic disk
  resizing.
- An additional Pacman repository is used to install and keep the [Linux Guest
  Environment](https://aur.archlinux.org/packages/google-compute-engine/) and
  [growpartfs](https://aur.archlinux.org/packages/growpartfs/) packages up to date.

## Prebuilt Images

You can use [Cloud SDK](https://cloud.google.com/sdk/docs/) to create instances
with the latest prebuilt Arch Linux image.  To do that follow the SDK
installation procedure, and then run the [following
command](https://cloud.google.com/sdk/gcloud/reference/compute/instances/create):

```console
$ gcloud compute instances create INSTANCE_NAME \
      --image-project=arch-linux-gce --image-family=arch
```

## Build Your Own Image

You can build the Arch Linux image yourself with the following procedure:

1.  Install the required dependencies and build the image

    ```console
    $ sudo pacman -S --needed arch-install-scripts e2fsprogs
    $ git clone https://github.com/GoogleCloudPlatform/compute-archlinux-image-builder.git
    $ cd compute-archlinux-image-builder
    $ sudo ./build-arch-gce
    ```

    You can also use the `build-arch-gce` package from the AUR, and run
    `sudo /usr/bin/build-arch-gce`

    If the build is successful, this will create an image file named
    arch-vDATE.tar.gz in the current directory, where DATE is the current date.

2.  Install and configure the [Cloud SDK](https://cloud.google.com/sdk/docs/).

3.  Copy the image file to Google Cloud Storage:

    ```console
    $ gsutil mb gs://BUCKET_NAME
    $ gsutil cp arch-vDATE.tar.gz gs://BUCKET_NAME
    ```

4.  Import the image file to Google Cloud Engine as a new custom image:

    ```console
    $ gcloud compute images create IMAGE_NAME \
          --source-uri=gs://BUCKET_NAME/arch-vDATE.tar.gz \
          --guest-os-features=VIRTIO_SCSI_MULTIQUEUE
    ```

You can now create new instances with your custom image:

```console
$ gcloud compute instances create INSTANCE_NAME --image=IMAGE_NAME
```

The Google Cloud Storage file is no longer needed, so you can delete it if you
want:

```console
$ gsutil rm gs://BUCKET_NAME/arch-vDATE.tar.gz
```

## Contributing Changes

* See [CONTRIB.md](CONTRIB.md)

## Licensing

All files in this repository are under the [Apache License, Version
2.0](LICENSE) unless noted otherwise.

## Support

Google Inc. does not provide any support, guarantees, or warranty for this
project or the images provided.
