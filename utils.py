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

import base64
import glob
import gzip
import hashlib
import json
import os
import logging
import pwd
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request, urllib.error, urllib.parse


APP_NAME = 'archbuilder'
BUILDER_USER = 'nobody'
ETC_LOCALE_GEN = '''
en_US.UTF-8 UTF-8
en_US ISO-8859-1
'''


def LogStep(msg):
  logging.info('- %s', msg)


def SetupLogging(quiet=False, verbose=False):
  if not quiet:
    root = logging.getLogger()
    stdout_logger = logging.StreamHandler(sys.stdout)
    if verbose:
      stdout_logger.setLevel(logging.DEBUG)
    else:
      stdout_logger.setLevel(logging.WARNING)
    stdout_logger.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    root.addHandler(stdout_logger)
    root.setLevel(logging.DEBUG)


def Sed(file_path, modification):
  Run(['sed', '-i', modification, file_path])


def Replace(file_path, pattern, replacement):
  Sed(file_path, 's/%s/%s/g' % (pattern, replacement))


def ReplaceLine(file_path, pattern, replacement):
  Sed(file_path, '/%s/c\%s' % (pattern, replacement))


def SudoRun(params, cwd=None, capture_output=False):
  if os.geteuid() != 0:
    params = ['sudo'] + params
  return Run(params, capture_output=capture_output)


def UserExists(username):
  try:
    pwd.getpwnam(username)
    return True
  except:
    return False


def Run(params, cwd=None, capture_output=False, shell=False, env=None, wait=True):
  try:
    logging.debug('Run: %s in %s', params, cwd)
    if env:
      new_env = os.environ.copy()
      new_env.update(env)
      env = new_env
    out_pipe = None
    if capture_output:
      out_pipe = subprocess.PIPE
    proc = subprocess.Popen(params, stdout=out_pipe, cwd=cwd, shell=shell, env=env)
    if not wait:
      return 0, '', ''
    out, err = proc.communicate()
    if capture_output:
      logging.debug(out)

    if out:
      out = out.decode(encoding='UTF-8')
    if err:
      err = err.decode(encoding='UTF-8')
  except KeyboardInterrupt:
    return 1, '', ''
  except:
    logging.error(sys.exc_info()[0])
    logging.error(sys.exc_info())
    Run(['/bin/bash'])
    return 1, '', ''

  return proc.returncode, out, err


def DownloadFile(url, file_path):
  Run(['wget', '-O', file_path, url, '-nv'])


def HttpGet(url):
  return str(urllib.request.urlopen(url).read(), encoding='utf8')


def Sha1Sum(file_path):
  with open(file_path, 'rb') as fp:
    return hashlib.sha1(fp.read()).hexdigest()


def Untar(file_path, dest_dir):
  Run(['tar', '-C', dest_dir, '-xzf', file_path])


def Chmod(fp, mode):
  Run(['chmod', str(mode), fp])


def CreateDirectory(dir_path):
  dir_path = ToAbsolute(dir_path)
  if not os.path.isdir(dir_path):
    os.makedirs(dir_path)


def ToAbsolute(path):
  if not path:
    return path
  return os.path.expandvars(os.path.expanduser(path))


def DeleteFile(file_pattern):
  DeleteFileFunc(file_pattern, lambda item: os.remove(item))


def SecureDeleteFile(file_pattern):
  DeleteFileFunc(file_pattern, lambda item: Run(['shred', '--remove', '--zero', item]))


def DeleteFileFunc(file_pattern, delete_func):
  items = glob.glob(ToAbsolute(file_pattern))
  for item in items:
    logging.warning('Deleting %s', item)
    delete_func(item)


def DirectoryExists(dir_path):
  return os.path.exists(dir_path)


def DeleteDirectory(dir_path):
  if DirectoryExists(dir_path):
    shutil.rmtree(dir_path)


def CreateTempDirectory(base_dir=None):
  return tempfile.mkdtemp(dir=ToAbsolute(base_dir), prefix='gcearch')


def WriteFile(path, content):
  with open(ToAbsolute(path), 'w') as fp:
    fp.write(content)


def AppendFile(path, content):
  with open(ToAbsolute(path), 'a') as fp:
    fp.write(content)


def RunChroot(base_dir, command, use_custom_path=True):
  base_dir = ToAbsolute(base_dir)
  if use_custom_path:
    chroot_file = os.path.join(base_dir, 'bin/arch-chroot')
  else:
    chroot_file = 'arch-chroot'
  SudoRun([chroot_file, base_dir, '/bin/bash', '-c', command])


def CopyFiles(source_pattern, dest):
  """Copies a set of files based on glob pattern to a directory.
     Avoiding shutil.copyfile because of bugs.python.org/issue10016."""
  items = glob.glob(ToAbsolute(source_pattern))
  for item in items:
    Run(['cp', '-Rf', item, dest])


def CopyBuilder(base_dir):
  script_dir = os.path.dirname(os.path.realpath(__file__))
  temp_dir = CreateTempDirectory(base_dir=base_dir)
  DeleteDirectory(temp_dir)
  relative_dir = os.path.relpath(temp_dir, base_dir)
  shutil.copytree(script_dir, temp_dir, ignore=shutil.ignore_patterns('*.tar.gz', '*.raw'))
  return relative_dir


def EncodeArgs(decoded_args):
  return base64.standard_b64encode(gzip.compress(bytes(json.dumps(decoded_args), 'utf-8'))).decode('utf-8')


def DecodeArgs(encoded_args):
  return json.loads(gzip.decompress(base64.standard_b64decode(encoded_args)).decode('utf-8'))


def DebugBash():
  Run(['/bin/bash'])


def DebugPrintFile(file_path):
  logging.info('==============================================================')
  logging.info('File: %s', file_path)
  logging.info('==============================================================')
  Run(['cat', file_path])


def Sync():
  Run(['sync'])


def EnableService(service_name):
  Run(['systemctl', 'enable', service_name])


def DisableService(service_name):
  Run(['systemctl', 'disable', service_name])


def Symlink(source_file, dest_file):
  Run(['ln', '-s', source_file, dest_file])


def ChangeDirectoryOwner(username, directory):
  SudoRun(['chown', '-R', username, directory])


def AurInstall(name=None, pkbuild_url=None):
  if name:
    pkbuild_url = 'https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=%s' % (name.lower())
  workspace_dir = CreateTempDirectory()
  DownloadFile(pkbuild_url, os.path.join(workspace_dir, 'PKGBUILD'))
  ChangeDirectoryOwner(BUILDER_USER, workspace_dir)
  Run(['runuser', '-m', BUILDER_USER, '-c', 'makepkg'], cwd=workspace_dir)
  tarball = glob.glob(os.path.join(workspace_dir, '*.tar*'))
  tarball = tarball[0]
  Pacman(['-U', tarball], cwd=workspace_dir)

  return tarball


def Pacstrap(base_dir, params):
  Run(['pacstrap', base_dir] + params)


def Pacman(params, cwd=None):
  Run(['pacman', '--noconfirm'] + params, cwd=cwd)


def UpdatePacmanDatabase():
  Pacman(['-Sy'])


def UpdateAllPackages():
  Pacman(['-Syyu'])

def InstallPackages(package_list):
  Pacman(['-S'] + package_list)


def SetupArchLocale():
  AppendFile('/etc/locale.gen', ETC_LOCALE_GEN)
  Run(['locale-gen'])
  Run(['localectl', 'set-locale', 'LANG="en_US.UTF-8"', 'LC_COLLATE="C"'])


class ImageMapper(object):
  """Interface for kpartx, mount, and umount."""
  def __init__(self, raw_disk, mount_path):
    self._raw_disk = raw_disk
    self._mount_path = mount_path
    self._device_map = None
    self._mount_points = None

  def _LoadPartitionsIfNeeded(self):
    if not self._device_map:
      self.LoadPartitions()

  def InstallLoopback(self):
    SudoRun(['modprobe', 'loop'])

  def LoadPartitions(self):
    return_code, out, err = SudoRun(['kpartx', '-l', self._raw_disk], capture_output=True)
    # Expected Format
    # loop2p1 : 0 10483712 /dev/loop2 2048
    # loop2p2 : 0 1 /dev/loop2 2047
    # loop deleted : /dev/loop2

    self._device_map = {}
    lines = out.splitlines()
    for line in lines:
      parts = str(line).split()
      if len(parts) == 6:
        mapping = {
            'name': parts[0],
            'size_blocks': parts[3],
            'parent': parts[4],
            'start_block': parts[5],
            'path': '/dev/mapper/%s' % str(parts[0])
          }
        logging.info('Mapping: %s', mapping)
        self._device_map[mapping['name']] = mapping
    if len(self._device_map) == 1:
      self._mount_points = [self._mount_path]
    else:
      self._mount_points = []
      for name in list(self._device_map.keys()):
        self._mount_points.append(os.path.join(self._mount_path, name))

  def ForEachDevice(self, func):
    for name in list(self._device_map.keys()):
      spec = self._device_map[name]
      func(spec)

  def ForEachDeviceWithIndex(self, func):
    i = 0
    for name in list(self._device_map.keys()):
      spec = self._device_map[name]
      func(i, spec)
      i += 1

  def GetFirstMapping(self):
    logging.info('DeviceMap: %s', self.GetDeviceMap())
    return next(iter(self.GetDeviceMap().values()))

  def GetDeviceMap(self):
    return self._device_map

  def Sync(self):
    Run(['sync'])

  def Map(self):
    SudoRun(['kpartx', '-a', '-v', '-s', self._raw_disk])
    self.LoadPartitions()

  def Unmap(self):
    self.Sync()
    time.sleep(2)
    SudoRun(['kpartx', '-d', '-v', '-s', self._raw_disk])
    self._device_map = None

  def Mount(self):
    self._LoadPartitionsIfNeeded()
    self._ThrowIfBadMountMap()
    def MountCmd(index, spec):
      mount_point = self._mount_points[index]
      CreateDirectory(mount_point)
      SudoRun(['mount', spec['path'], mount_point])
    self.ForEachDeviceWithIndex(MountCmd)

  def Unmount(self):
    self._LoadPartitionsIfNeeded()
    self._ThrowIfBadMountMap()
    for path in self._mount_points:
      SudoRun(['umount', path])
    self.Sync()
    time.sleep(2)

  def _ThrowIfBadMountMap(self):
    if not self._mount_points:
      raise IOError('Attempted to found {0} without a mount points.'.format(self._raw_disk))
    if len(self._mount_points) != len(list(self._device_map.keys())):
      raise IOError('Number of device maps ({0}) does not match mount points ({1}).'.format(
          len(list(self._device_map.keys())), len(self._mount_points)
      ))
