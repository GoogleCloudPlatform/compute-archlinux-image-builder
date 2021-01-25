# Maintainers Guide

Note that this document is intended for the owners of this repository who are
maintaining the common images (in the `arch` family), and the gce Pacman repo.
If you're just looking to build your own image, follow the instructions at the
end of README.md.

## Deploying Public Images

```console
$ DATE=$(date --utc +%Y%m%d)

$ sudo pacman -S --needed arch-install-scripts e2fsprogs

$ sudo ./build-arch-gce

$ gcloud auth login

$ gcloud config set project arch-linux-gce

$ gsutil cp "arch-v${DATE}.tar.gz" gs://arch-linux-gce-work

$ gcloud compute images create "arch-v${DATE}" \
    --source-uri="gs://arch-linux-gce-work/arch-v${DATE}.tar.gz" \
    --guest-os-features=VIRTIO_SCSI_MULTIQUEUE \
    --description="Arch Linux built on ${DATE}." \
    --family=arch

$ gsutil rm "gs://arch-linux-gce-work/arch-v${DATE}.tar.gz"

$ gcloud compute instances create "arch-v${DATE}-test" --image="arch-v${DATE}"

$ gcloud compute ssh "arch-v${DATE}-test"

$ gcloud compute instances delete "arch-v${DATE}-test"

$ gcloud compute images add-iam-policy-binding "arch-v${DATE}" \
    --member='allAuthenticatedUsers' \
    --role='roles/compute.imageUser'
```

## Managing the Pacman repo

See also
https://wiki.archlinux.org/index.php/Pacman/Tips_and_tricks#Custom_local_repository.

1.  Sync the repo to your device

    ```console
    $ mkdir -p repo
    $ gsutil rsync gs://arch-linux-gce/repo repo/
    ```

2.  Build packages and copy into the repo

    ```console
    $ cd path/to/package
    $ PKGEXT=".pkg.tar.zst" makepkg
    $ cp PACKAGE_NAME.pkg.tar.zst path/to/repo
    ```

3.  Update repo database

    ```console
    $ cd path/to/repo
    $ repo-add gce.db.tar.gz PACKAGE_NAME.pkg.tar.zst
    ```

4.  Upload the repo to GCS

    ```console
    $ cd ..
    $ gsutil rsync repo/ gs://arch-linux-gce/repo
    ```

Note that if deleting packages (use `repo-remove gce.db.tar.gz PACKAGE_NAME`),
`gsutil rsync` will not delete the old package files. Use `gsutil rm` if
required.
