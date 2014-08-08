#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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


import logging
import os
import sys

import utils

COMPUTE_IMAGE_PACKAGES_GIT_URL = (
    'https://github.com/GoogleCloudPlatform/compute-image-packages.git')
IMAGE_FILE='disk.raw'
SETUP_PACKAGES_ESSENTIAL = 'grep file'.split()
SETUP_PACKAGES = 'pacman wget gcc make parted git setconf libaio sudo'.split()
IMAGE_PACKAGES = ('base tar wget '
                  'curl sudo mkinitcpio syslinux dhcp ethtool irqbalance '
                  'ntp psmisc openssh udev less bash-completion zip unzip '
                  'python2 python3').split()


def main():
  args = utils.DecodeArgs(sys.argv[1])
  utils.SetupLogging(quiet=args['quiet'], verbose=args['verbose'])
  logging.info('Setup Bootstrapper Environment')
  utils.SetupArchLocale()
  InstallPackagesForStagingEnvironment()
  image_path = os.path.join(os.getcwd(), IMAGE_FILE)
  CreateImage(image_path, size_gb=int(args['size_gb']))
  mount_path = utils.CreateTempDirectory(base_dir='/')
  image_mapping = utils.ImageMapper(image_path, mount_path)
  try:
    image_mapping.Map()
    primary_mapping = image_mapping.GetFirstMapping()
    image_mapping_path = primary_mapping['path']
    FormatImage(image_mapping_path)
    try:
      image_mapping.Mount()
      utils.CreateDirectory('/run/shm')
      utils.CreateDirectory(os.path.join(mount_path, 'run', 'shm'))
      InstallArchLinux(mount_path)
      disk_uuid = SetupFileSystem(mount_path, image_mapping_path)
      ConfigureArchInstall(
          args, mount_path, primary_mapping['parent'], disk_uuid)
      utils.DeleteDirectory(os.path.join(mount_path, 'run', 'shm'))
      PurgeDisk(mount_path)
    finally:
      image_mapping.Unmount()
    ShrinkDisk(image_mapping_path)
  finally:
    image_mapping.Unmap()
  utils.Run(['parted', image_path, 'set', '1', 'boot', 'on'])
  utils.Sync()


def ConfigureArchInstall(args, mount_path, parent_path, disk_uuid):
  relative_builder_path = utils.CopyBuilder(mount_path)
  utils.LogStep('Download compute-image-packages')
  packages_dir = utils.CreateTempDirectory(mount_path)
  utils.Run(['git', 'clone', COMPUTE_IMAGE_PACKAGES_GIT_URL, packages_dir])
  utils.CreateDirectory(os.path.join(mount_path, ''))
  packages_dir = os.path.relpath(packages_dir, mount_path)
  params = {
    'packages_dir': '/%s' % packages_dir,
    'device': parent_path,
    'disk_uuid': disk_uuid,
    'accounts': args['accounts'],
    'debugmode': args['debugmode'],
  }
  params.update(args)
  config_arch_py = os.path.join(
      '/', relative_builder_path, 'arch-image.py')
  utils.RunChroot(mount_path,
                  '%s "%s"' % (config_arch_py, utils.EncodeArgs(params)),
                  use_custom_path=False)
  utils.DeleteDirectory(os.path.join(mount_path, relative_builder_path))


def InstallPackagesForStagingEnvironment():
  utils.InstallPackages(SETUP_PACKAGES_ESSENTIAL)
  utils.InstallPackages(SETUP_PACKAGES)
  utils.SetupArchLocale()
  utils.AurInstall(name='multipath-tools-git')
  utils.AurInstall(name='zerofree')


def CreateImage(image_path, size_gb=10, fs_type='ext4'):
  utils.LogStep('Create Image')
  utils.Run(['rm', '-f', image_path])
  utils.Run(['truncate', image_path, '--size=%sG' % size_gb])
  utils.Run(['parted', image_path, 'mklabel', 'msdos'])
  utils.Run(['parted', image_path, 'mkpart', 'primary',
             fs_type, '1', str(int(size_gb) * 1024)])


def FormatImage(image_mapping_path):
  utils.LogStep('Format Image')
  utils.Run(['mkfs', image_mapping_path])
  utils.Sync()


def InstallArchLinux(base_dir):
  utils.LogStep('Install Arch Linux')
  utils.Pacstrap(base_dir, IMAGE_PACKAGES)


def SetupFileSystem(base_dir, image_mapping_path):
  utils.LogStep('File Systems')
  _, fstab_contents, _ = utils.Run(['genfstab', '-p', base_dir],
                                   capture_output=True)
  utils.WriteFile(os.path.join(base_dir, 'etc', 'fstab'), fstab_contents)
  _, disk_uuid, _ = utils.Run(['blkid', '-s', 'UUID',
                               '-o', 'value',
                               image_mapping_path],
                              capture_output=True)
  disk_uuid = disk_uuid.strip()
  utils.WriteFile(os.path.join(base_dir, 'etc', 'fstab'),
                  'UUID=%s   /   ext4   defaults   0   1' % disk_uuid)
  utils.Run(['tune2fs', '-i', '1', '-U', disk_uuid, image_mapping_path])
  return disk_uuid


def PurgeDisk(mount_path):
  paths = ['/var/cache', '/var/log', '/var/lib/pacman/sync']
  for path in paths:
    utils.DeleteDirectory(os.path.join(mount_path, path))


def ShrinkDisk(image_mapping_path):
  utils.LogStep('Shrink Disk')
  utils.Run(['zerofree', image_mapping_path])


main()
