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


import argparse
import os
import logging
import sys
from datetime import date

import utils

COMPUTE_IMAGE_PACKAGES_GIT_URL = (
    'https://github.com/GoogleCloudPlatform/compute-image-packages.git')
IMAGE_FILE='disk.raw'
SETUP_PACKAGES_ESSENTIAL = 'grep file'.split()
SETUP_PACKAGES = ('pacman wget gcc make parted git setconf libaio sudo '
                 'fakeroot arch-install-scripts').split()
IMAGE_PACKAGES = ('base tar wget '
                  'curl sudo mkinitcpio syslinux dhcp ethtool irqbalance '
                  'ntp psmisc openssh udev less bash-completion zip unzip '
                  'python2 python3').split()


def main():
  args = ParseArgs()
  utils.SetupLogging(quiet=args.quiet, verbose=args.verbose)
  logging.info('Arch Linux Image Builder')
  logging.info('========================')
  
  workspace_dir = None
  image_file = None
  try:
    aur_packages = InstallPackagesOnHostMachine()
    image_path = CreateArchImage(args, aur_packages)
    image_name, image_filename, image_description = GetImageNameAndDescription(
        args.outfile)
    image_file = SaveImage(image_path, image_filename)
    if args.upload and image_file:
      UploadImage(image_file, args.upload, make_public=args.public)
      if args.register:
        AddImageToComputeEngineProject(
            image_name, args.upload, image_description)
  finally:
    if not args.nocleanup and workspace_dir:
      utils.DeleteDirectory(workspace_dir)


def CreateArchImage(args, aur_packages):
  image_path = os.path.join(os.getcwd(), IMAGE_FILE)
  CreateBlankImage(image_path, size_gb=int(args.size_gb), fs_type=args.fs_type)
  mount_path = utils.CreateTempDirectory(base_dir='/')
  image_mapping = utils.ImageMapper(image_path, mount_path)
  try:
    image_mapping.InstallLoopback()
    image_mapping.Map()
    primary_mapping = image_mapping.GetFirstMapping()
    image_mapping_path = primary_mapping['path']
    FormatImage(image_mapping_path)
    try:
      image_mapping.Mount()
      utils.CreateDirectory('/run/shm')
      utils.CreateDirectory(os.path.join(mount_path, 'run', 'shm'))
      InstallArchLinux(mount_path)
      disk_uuid = SetupFileSystem(mount_path, image_mapping_path, args.fs_type)
      ConfigureArchInstall(
          args, mount_path, primary_mapping['parent'], disk_uuid, aur_packages)
      utils.DeleteDirectory(os.path.join(mount_path, 'run', 'shm'))
      PurgeDisk(mount_path)
    finally:
      image_mapping.Unmount()
    ShrinkDisk(image_mapping_path)
  finally:
    image_mapping.Unmap()
  utils.Run(['parted', image_path, 'set', '1', 'boot', 'on'])
  utils.Sync()
  return image_path


def ConfigureArchInstall(args, mount_path, parent_path, disk_uuid, aur_packages):
  relative_builder_path = utils.CopyBuilder(mount_path)
  packages_dir = utils.CreateTempDirectory(mount_path)
  utils.Run(['git', 'clone', COMPUTE_IMAGE_PACKAGES_GIT_URL, packages_dir])
  utils.CreateDirectory(os.path.join(mount_path, ''))
  aur_packages_dir = os.path.join(packages_dir, 'aur')
  for aur_package in aur_packages:
    utils.CopyFiles(aur_package, aur_packages_dir + '/')
  packages_dir = os.path.relpath(packages_dir, mount_path)
  params = {
    'packages_dir': '/%s' % packages_dir,
    'device': parent_path,
    'disk_uuid': disk_uuid,
    'accounts': args.accounts,
    'debugmode': args.debug,
    'quiet': args.quiet,
    'verbose': args.verbose,
    'packages': args.packages,
    'size_gb': args.size_gb
  }
  config_arch_py = os.path.join(
      '/', relative_builder_path, 'arch-image.py')
  utils.RunChroot(mount_path,
                  '%s "%s"' % (config_arch_py, utils.EncodeArgs(params)),
                  use_custom_path=False)
  utils.DeleteDirectory(os.path.join(mount_path, relative_builder_path))


def InstallPackagesOnHostMachine():
  aur_packages = []
  utils.UpdatePacmanDatabase()
  utils.InstallPackages(SETUP_PACKAGES_ESSENTIAL)
  utils.InstallPackages(SETUP_PACKAGES)
  utils.UpdateAllPackages()
  aur_packages.append(utils.AurInstall(name='multipath-tools-git'))
  aur_packages.append(utils.AurInstall(name='zerofree'))
  aur_packages.append(utils.AurInstall(name='python2-crcmod'))
  return aur_packages


def CreateBlankImage(image_path, size_gb=10, fs_type='ext4'):
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


def SetupFileSystem(base_dir, image_mapping_path, fs_type):
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
                  'UUID=%s   /   %s   defaults   0   1' % (disk_uuid, fs_type))
  utils.Run(['tune2fs', '-i', '1', '-U', disk_uuid, image_mapping_path])
  return disk_uuid


def PurgeDisk(mount_path):
  paths = ['/var/cache', '/var/log', '/var/lib/pacman/sync']
  for path in paths:
    utils.DeleteDirectory(os.path.join(mount_path, path))


def ShrinkDisk(image_mapping_path):
  utils.LogStep('Shrink Disk')
  utils.Run(['zerofree', image_mapping_path])


def SaveImage(disk_image_file, image_filename):
  utils.LogStep('Save Arch Linux Image in GCE format')
  image_raw = os.path.join(os.getcwd(), IMAGE_FILE)
  gce_image_file = os.path.join(os.getcwd(), image_filename)
  utils.Run(['tar', '-Szcf', image_filename, IMAGE_FILE])
  return gce_image_file


def UploadImage(image_path, gs_path, make_public=False):
  utils.LogStep('Upload Image to Cloud Storage')
  utils.SecureDeleteFile('~/.gsutil/*.url')
  utils.Run(['gsutil', 'rm', gs_path],
      env={'CLOUDSDK_PYTHON': '/usr/bin/python2'})
  utils.Run(['gsutil', 'cp', image_path, gs_path],
      env={'CLOUDSDK_PYTHON': '/usr/bin/python2'})
  if make_public:
    utils.Run(['gsutil', 'acl', 'set', 'public-read', gs_path],
        env={'CLOUDSDK_PYTHON': '/usr/bin/python2'})


def AddImageToComputeEngineProject(image_name, gs_path, description):
  utils.LogStep('Add image to project')
  utils.Run(
      ['gcloud', 'compute', 'images', 'delete', image_name, '-q'],
      env={'CLOUDSDK_PYTHON': '/usr/bin/python2'})
  utils.Run(
      ['gcloud', 'compute', 'images', 'create', image_name, '-q',
       '--source-uri', gs_path,
       '--description', description],
      env={'CLOUDSDK_PYTHON': '/usr/bin/python2'})


def GetImageNameAndDescription(outfile_name):
  today = date.today()
  isodate = today.strftime("%Y-%m-%d")
  yyyymmdd = today.strftime("%Y%m%d")
  image_name = 'arch-v%s' % yyyymmdd
  if outfile_name:
    image_filename = outfile_name
  else:
    image_filename = '%s.tar.gz' % image_name
  description = 'Arch Linux x86-64 built on %s' % isodate
  return image_name, image_filename, description


def ParseArgs():
  parser = argparse.ArgumentParser(
      description='Arch Linux Image Builder for Compute Engine')
  parser.add_argument('-p', '--packages',
                      dest='packages',
                      nargs='+',
                      help='Additional packages to install via Pacman.')
  parser.add_argument('-v', '--verbose',
                      dest='verbose',
                      default=False,
                      help='Verbose console output.',
                      action='store_true')
  parser.add_argument('-q', '--quiet',
                      dest='quiet',
                      default=False,
                      help='Suppress all console output.',
                      action='store_true')
  parser.add_argument('--upload',
                      dest='upload',
                      default=None,
                      help='Google Cloud Storage path to upload to.')
  parser.add_argument('--size_gb',
                      dest='size_gb',
                      default=10,
                      help='Volume size of image (in GiB).')
  parser.add_argument('--accounts',
                      dest='accounts',
                      nargs='+',
                      help='Space delimited list of user accounts to create on '
                      'the image. Format: username:password')
  parser.add_argument('--nocleanup',
                      dest='nocleanup',
                      default=False,
                      help='Prevent cleaning up the image build workspace '
                           'after image has been created.',
                      action='store_true')
  parser.add_argument('--outfile',
                      dest='outfile',
                      default=None,
                      help='Name of the output image file.')
  parser.add_argument('--debug',
                      dest='debug',
                      default=False,
                      help='Configure the image for debugging.',
                      action='store_true')
  parser.add_argument('--public',
                      dest='public',
                      default=False,
                      help='Make image file uploaded to Cloud Storage '
                           'available for everyone.',
                      action='store_true')
  parser.add_argument('--register',
                      dest='register',
                      default=False,
                      help='Add the image to Compute Engine project. '
                           '(Upload to Cloud Storage required.)',
                      action='store_true')
  parser.add_argument('--nopacmankeys',
                      dest='nopacmankeys',
                      default=False,
                      help='Disables signature checking for pacman packages.',
                      action='store_true')
  parser.add_argument('--fs_type',
                      dest='fs_type',
                      default='ext4',
                      help='Verbose console output.',
                      action='store_true')
  return parser.parse_args()


if __name__ == '__main__':
  main()
