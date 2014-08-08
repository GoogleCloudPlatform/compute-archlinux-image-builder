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


"""Arch Linux Image Builder for GCE.

This script creates a clean Arch Linux image that can be used in Google Compute
Engine.

Usage: ./build-gce-arch.py -> archlinux-***.tar.gz
       ./build-gce-arch.py --packages docker
       ./build-gce-arch.py --help -> Detailed help.
"""
import argparse
import os
import logging
from datetime import date

import utils


DEFAULT_MIRROR = 'http://mirrors.kernel.org/archlinux/$repo/os/$arch'
#DEFAULT_MIRROR = 'http://mirror.us.leaseweb.net/archlinux/$repo/os/$arch'
TARGET_ARCH = 'x86_64'


def main():
  args = ParseArgs()
  utils.SetupLogging(quiet=args.quiet, verbose=args.verbose)
  workspace_dir = None
  image_file = None
  try:
    workspace_dir = utils.CreateTempDirectory()
    bootstrap_file = DownloadArchBootstrap(args.bootstrap)
    utils.Untar(bootstrap_file, workspace_dir)
    arch_root = PrepareBootstrap(workspace_dir, args.mirror, not args.nopacmankeys)
    relative_builder_path = utils.CopyBuilder(arch_root)
    ChrootIntoArchAndBuild(arch_root, relative_builder_path, args)
    image_name, image_filename, image_description = GetImageNameAndDescription(
        args.outfile)
    image_file = SaveImage(arch_root, image_filename)
    if args.upload and image_file:
      UploadImage(image_file, args.upload, make_public=args.public)
      if args.register:
        AddImageToComputeEngineProject(
            image_name, args.upload, image_description)
  finally:
    if not args.nocleanup and workspace_dir:
      utils.DeleteDirectory(workspace_dir)

  
def ParseArgs():
  parser = argparse.ArgumentParser(
      description='Arch Linux Image Builder for Compute Engine')
  parser.add_argument('-p', '--packages',
                      dest='packages',
                      nargs='+',
                      help='Additional packages to install via Pacman.')
  parser.add_argument('--mirror',
                      dest='mirror',
                      default=DEFAULT_MIRROR,
                      help='Mirror to download packages from.')
  parser.add_argument('--bootstrap',
                      dest='bootstrap',
                      help='Arch Linux Bootstrap tarball. '
                           '(default: Download latest version)')
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
  return parser.parse_args()


def DownloadArchBootstrap(bootstrap_tarball):
  utils.LogStep('Download Arch Linux Bootstrap')
  if bootstrap_tarball:
    url = bootstrap_tarball
    sha1sum = None
  else:
    url, sha1sum = GetLatestBootstrapUrl()
  logging.debug('Downloading %s', url)
  local_bootstrap = os.path.join(os.getcwd(), os.path.basename(url))
  if os.path.isfile(local_bootstrap):
    logging.debug('Using local file instead.')
    if sha1sum and utils.Sha1Sum(local_bootstrap) == sha1sum:
      return local_bootstrap
  utils.DownloadFile(url, local_bootstrap)
  if not sha1sum or utils.Sha1Sum(local_bootstrap) != sha1sum:
      raise ValueError('Bad checksum')
  return local_bootstrap


def ChrootIntoArchAndBuild(arch_root, relative_builder_path, args):
  params = {
    'quiet': args.quiet,
    'verbose': args.verbose,
    'packages': args.packages,
    'mirror': args.mirror,
    'accounts': args.accounts,
    'debugmode': args.debug,
    'size_gb': args.size_gb
  }
  chroot_archenv_script = os.path.join('/', relative_builder_path,
                                       'arch-staging.py')
  utils.RunChroot(arch_root,
                  '%s "%s"' % (chroot_archenv_script, utils.EncodeArgs(params)))
  logging.debug('Bootstrap Chroot: sudo %s/bin/arch-chroot %s/',
                arch_root, arch_root)


def SaveImage(arch_root, image_filename):
  utils.LogStep('Save Arch Linux Image in GCE format')
  source_image_raw = os.path.join(arch_root, 'disk.raw')
  image_raw = os.path.join(os.getcwd(), 'disk.raw')
  image_file = os.path.join(os.getcwd(), image_filename)
  utils.Run(['cp', '--sparse=always', source_image_raw, image_raw])
  utils.Run(['tar', '-Szcf', image_file, 'disk.raw'])
  return image_file


def UploadImage(image_path, gs_path, make_public=False):
  utils.LogStep('Upload Image to Cloud Storage')
  utils.SecureDeleteFile('~/.gsutil/*.url')
  utils.Run(['gsutil', 'rm', gs_path])
  utils.Run(['gsutil', 'cp', image_path, gs_path])
  if make_public:
    utils.Run(['gsutil', 'acl', 'set', 'public-read', gs_path])


def AddImageToComputeEngineProject(image_name, gs_path, description):
  utils.LogStep('Add image to project')
  utils.Run(['gcloud', 'compute', 'images', 'delete', image_name, '-q'])
  utils.Run(['gcloud', 'compute', 'images', 'create', image_name, '-q',
             '--source-uri', gs_path,
             '--description', description])

def PrepareBootstrap(workspace_dir, mirror_server, use_pacman_keys):
  utils.LogStep('Setting up Bootstrap Environment')
  arch_root = os.path.join(workspace_dir, os.listdir(workspace_dir)[0])
  mirrorlist = 'Server = {MIRROR_SERVER}'.format(MIRROR_SERVER=mirror_server)
  utils.AppendFile(os.path.join(arch_root, 'etc/pacman.d/mirrorlist'),
                   mirrorlist)
  utils.CreateDirectory(os.path.join(arch_root, 'run/shm'))
  if use_pacman_keys:
    utils.RunChroot(arch_root, 'pacman-key --init')
    utils.RunChroot(arch_root, 'pacman-key --populate archlinux')
  else:
    utils.ReplaceLine(os.path.join(arch_root, 'etc/pacman.conf'), 'SigLevel', 'SigLevel = Never')
  # Install the most basic utilities for the bootstrapper.
  utils.RunChroot(arch_root,
                  'pacman --noconfirm -Sy python3')

  return arch_root


def GetLatestBootstrapUrl():
  base_url = 'http://mirrors.kernel.org/archlinux/iso/latest/'
  sha1sums = utils.HttpGet(base_url + 'sha1sums.txt')
  items = sha1sums.splitlines()
  for item in items:
    if TARGET_ARCH in item and 'bootstrap' in item:
      entries = item.split()
      return base_url + entries[1], entries[0]
  raise RuntimeError('Cannot find Arch bootstrap url')


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


main()
