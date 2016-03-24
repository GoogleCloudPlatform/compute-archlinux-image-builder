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


ETC_MOTD = '''Arch Linux for Compute Engine
'''

ETC_HOSTS = '''127.0.0.1 localhost
169.254.169.254 metadata.google.internal metadata
'''

ETC_SSH_SSH_CONFIG = '''
Host *
Protocol 2
ForwardAgent no
ForwardX11 no
HostbasedAuthentication no
StrictHostKeyChecking no
Ciphers aes128-ctr,aes192-ctr,aes256-ctr,arcfour256,arcfour128,aes128-cbc,3des-cbc
Tunnel no

# Google Compute Engine times out connections after 10 minutes of inactivity.
# Keep alive ssh connections by sending a packet every 7 minutes.
ServerAliveInterval 420
'''

ETC_SSH_SSHD_CONFIG = '''
# Disable PasswordAuthentication as ssh keys are more secure.
PasswordAuthentication no

# Disable root login, using sudo provides better auditing.
PermitRootLogin no

PermitTunnel no
AllowTcpForwarding yes
X11Forwarding no

# Compute times out connections after 10 minutes of inactivity.  Keep alive
# ssh connections by sending a packet every 7 minutes.
ClientAliveInterval 420

# Restrict sshd to just IPv4 for now as sshd gets confused for things
# like X11 forwarding.

Port 22
Protocol 2

UsePrivilegeSeparation yes

# Lifetime and size of ephemeral version 1 server key
KeyRegenerationInterval 3600
ServerKeyBits 768

SyslogFacility AUTH
LogLevel INFO

LoginGraceTime 120
StrictModes yes

RSAAuthentication yes
PubkeyAuthentication yes

IgnoreRhosts yes
RhostsRSAAuthentication no
HostbasedAuthentication no

PermitEmptyPasswords no
ChallengeResponseAuthentication no

PasswordAuthentication no
PrintMotd no
PrintLastLog yes

TCPKeepAlive yes

Subsystem sftp /usr/lib/openssh/sftp-server

UsePAM yes
UseDNS no
'''

ETC_SYSCTL_D_70_DISABLE_IPV6_CONF = '''
net.ipv6.conf.all.disable_ipv6 = 1
'''

ETC_SYSCTL_D_70_GCE_SECURITY_STRONGLY_RECOMMENDED_CONF = '''
# enables syn flood protection
net.ipv4.tcp_syncookies = 1

# ignores source-routed packets
net.ipv4.conf.all.accept_source_route = 0

# ignores source-routed packets
net.ipv4.conf.default.accept_source_route = 0

# ignores ICMP redirects
net.ipv4.conf.all.accept_redirects = 0

# ignores ICMP redirects
net.ipv4.conf.default.accept_redirects = 0

# ignores ICMP redirects from non-GW hosts
net.ipv4.conf.all.secure_redirects = 1

# ignores ICMP redirects from non-GW hosts
net.ipv4.conf.default.secure_redirects = 1

# don't allow traffic between networks or act as a router
net.ipv4.ip_forward = 0

# don't allow traffic between networks or act as a router
net.ipv4.conf.all.send_redirects = 0

# don't allow traffic between networks or act as a router
net.ipv4.conf.default.send_redirects = 0

# reverse path filtering - IP spoofing protection
net.ipv4.conf.all.rp_filter = 1

# reverse path filtering - IP spoofing protection
net.ipv4.conf.default.rp_filter = 1

# reverse path filtering - IP spoofing protection
net.ipv4.conf.default.rp_filter = 1

# ignores ICMP broadcasts to avoid participating in Smurf attacks
net.ipv4.icmp_echo_ignore_broadcasts = 1

# ignores bad ICMP errors
net.ipv4.icmp_ignore_bogus_error_responses = 1

# logs spoofed, source-routed, and redirect packets
net.ipv4.conf.all.log_martians = 1

# log spoofed, source-routed, and redirect packets
net.ipv4.conf.default.log_martians = 1

# implements RFC 1337 fix
net.ipv4.tcp_rfc1337 = 1

# randomizes addresses of mmap base, heap, stack and VDSO page
kernel.randomize_va_space = 2
'''

ETC_SYSCTL_D_70_GCE_SECURITY_RECOMMENDED_CONF = '''
# provides protection from ToCToU races
fs.protected_hardlinks=1

# provides protection from ToCToU races
fs.protected_symlinks=1

# makes locating kernel addresses more difficult
kernel.kptr_restrict=1

# set ptrace protections
kernel.yama.ptrace_scope=1

# set perf only available to root
kernel.perf_event_paranoid=2
'''

ETC_PAM_D_PASSWD = '''
#%PAM-1.0
password  required pam_cracklib.so difok=2 minlen=8 dcredit=2 ocredit=2 retry=3
password  required pam_unix.so sha512 shadow nullok
password  required pam_tally.so even_deny_root_account deny=3 lock_time=5 unlock_time=3600
'''

ETC_SUDOERS_D_ADD_GROUP_ADM = '''
%adm ALL=(ALL) ALL
'''

ETC_FAIL2BAN_JAIL_LOCAL = '''
[DEFAULT]
backend = systemd
loglevel = WARNING
'''

ETC_FAIL2BAN_JAIL_D_SSHD_CONF = '''
# fail2ban SSH
# block ssh after 3 unsuccessful login attempts for 10 minutes
[sshd]
enabled  = true
action   = iptables[chain=INPUT, protocol=tcp, port=22, name=sshd]
maxRetry = 3
findtime = 600
bantime  = 600
port     = 22
'''

GCIMAGEBUNDLE_ARCH_PY = '''
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


"""Arch Linux specific platform info."""


import os

from gcimagebundlelib import linux


class Arch(linux.LinuxPlatform):
  """Arch Linux specific information."""

  @staticmethod
  def IsThisPlatform(root='/'):
    return os.path.isfile('/etc/arch-release')

  def __init__(self):
    super(Arch, self).__init__()
'''

def main():
  args = utils.DecodeArgs(sys.argv[1])
  utils.SetupLogging(quiet=args['quiet'], verbose=args['verbose'])
  logging.info('Setup Bootstrapper Environment')
  SetupLocale()
  ConfigureTimeZone()
  ConfigureKernel()
  InstallBootloader(args['device'], args['disk_uuid'], args['debugmode'])
  ForwardSystemdToConsole()
  SetupNtpServer()
  SetupNetwork()
  SetupSsh()
  #SetupFail2ban()
  SetupAccounts(args)
  #InstallImportedPackages(args['packages_dir'])
  InstallGcePackages(args['packages_dir'])
  ConfigMessageOfTheDay()
  ConfigureSecurity()
  ConfigureSerialPortOutput()
  DisableUnusedServices()
  OptimizePackages()


def SetupAccounts(args):
  accounts = args['accounts']
  if accounts:
    utils.LogStep('Add Accounts')
    for account in accounts:
      username, password = account.split(':')
      logging.info(' - %s', username)
      utils.Run(['useradd', username, '-m', '-s', '/bin/bash',
                 '-G', 'adm,video'])
      utils.Run('echo %s:%s | chpasswd' % (username, password), shell=True)


def OptimizePackages():
  utils.LogStep('Cleanup Cached Package Data')
  utils.Pacman(['-Syu'])
  utils.Pacman(['-Sc'])
  utils.Run(['pacman-optimize'])


def SetupLocale():
  utils.LogStep('Set Locale to US English (UTF-8)')
  utils.SetupArchLocale()


def ConfigureTimeZone():
  utils.LogStep('Set Timezone to UTC')
  utils.Run(['ln', '-sf', '/usr/share/zoneinfo/UTC', '/etc/localtime'])


def ConfigureKernel():
  utils.LogStep('Configure Kernel')
  utils.Replace('/etc/mkinitcpio.conf',
                'MODULES=""',
                'MODULES="virtio virtio_blk virtio_pci virtio_scsi virtio_net"')
  utils.Replace('/etc/mkinitcpio.conf', 'autodetect ', '')
  utils.Run(['mkinitcpio',
             '-g', '/boot/initramfs-linux.img',
             '-k', '/boot/vmlinuz-linux',
             '-c', '/etc/mkinitcpio.conf'])


def InstallBootloader(device, uuid, debugmode):
  utils.LogStep('Install Syslinux bootloader')
  utils.Run(['blkid', '-s', 'PTTYPE', '-o', 'value', device])
  utils.CreateDirectory('/boot/syslinux')
  utils.CopyFiles('/usr/lib/syslinux/bios/*.c32', '/boot/syslinux/')
  utils.Run(['extlinux', '--install', '/boot/syslinux'])
  utils.Replace('/boot/syslinux/syslinux.cfg', 'sda3', 'sda1')
  utils.Run(['fdisk', '-l', device])
  utils.Run(['dd', 'bs=440', 'count=1', 'conv=notrunc',
             'if=/usr/lib/syslinux/bios/mbr.bin', 'of=%s' % device])
  
  boot_params = [
      'console=ttyS0,38400',
      'CONFIG_KVM_GUEST=y',
      'CONFIG_KVM_CLOCK=y',
      'CONFIG_VIRTIO_PCI=y',
      'CONFIG_SCSI_VIRTIO=y',
      'CONFIG_VIRTIO_NET=y',
      'CONFIG_STRICT_DEVMEM=y',
      'CONFIG_DEVKMEM=n',
      'CONFIG_DEFAULT_MMAP_MIN_ADDR=65536',
      'CONFIG_DEBUG_RODATA=y',
      'CONFIG_DEBUG_SET_MODULE_RONX=y',
      'CONFIG_CC_STACKPROTECTOR=y',
      'CONFIG_COMPAT_VDSO=n',
      'CONFIG_COMPAT_BRK=n',
      'CONFIG_X86_PAE=y',
      'CONFIG_SYN_COOKIES=y',
      'CONFIG_SECURITY_YAMA=y',
      'CONFIG_SECURITY_YAMA_STACKED=y',
  ]
  if debugmode:
    boot_params += [
      'systemd.log_level=debug',
      'systemd.log_target=console',
      'systemd.journald.forward_to_syslog=yes',
      'systemd.journald.forward_to_kmsg=yes',
      'systemd.journald.forward_to_console=yes',]
  boot_params = ' '.join(boot_params)
  boot_spec = '    APPEND root=UUID=%s rw append %s' % (uuid, boot_params)
  utils.ReplaceLine('/boot/syslinux/syslinux.cfg',
                    'APPEND root=',
                    boot_spec)

def DisableUnusedServices():
  utils.DisableService('getty@tty1.service')
  utils.DisableService('graphical.target')
  
def ForwardSystemdToConsole():
  utils.LogStep('Installing syslinux bootloader')
  utils.AppendFile('/etc/systemd/journald.conf', 'ForwardToConsole=yes')


def SetupNtpServer():
  utils.LogStep('Configure NTP')
  utils.WriteFile('/etc/ntp.conf', 'server metadata.google.internal iburst')


def SetupNetwork():
  utils.LogStep('Setup Networking')
  utils.SecureDeleteFile('/etc/hostname')
  utils.WriteFile('/etc/hosts', ETC_HOSTS)
  utils.WriteFile('/etc/sysctl.d/70-disable-ipv6.conf',
                  ETC_SYSCTL_D_70_DISABLE_IPV6_CONF)
  # https://wiki.archlinux.org/index.php/Network_configuration#Reverting_to_traditional_device_names
  utils.Symlink('/dev/null', '/etc/udev/rules.d/80-net-setup-link.rules')
  utils.EnableService('dhcpcd.service')
  utils.EnableService('systemd-networkd.service')
  utils.EnableService('systemd-networkd-wait-online.service')


def SetupSsh():
  utils.LogStep('Configure SSH')
  utils.WriteFile('/etc/ssh/sshd_not_to_be_run', 'GOOGLE')
  utils.SecureDeleteFile('/etc/ssh/ssh_host_key')
  utils.SecureDeleteFile('/etc/ssh/ssh_host_rsa_key*')
  utils.SecureDeleteFile('/etc/ssh/ssh_host_dsa_key*')
  utils.SecureDeleteFile('/etc/ssh/ssh_host_ecdsa_key*')
  utils.WriteFile('/etc/ssh/ssh_config', ETC_SSH_SSH_CONFIG)
  utils.Chmod('/etc/ssh/ssh_config', 644)
  utils.WriteFile('/etc/ssh/sshd_config', ETC_SSH_SSHD_CONFIG)
  utils.Chmod('/etc/ssh/sshd_config', 644)
  utils.EnableService('sshd.service')


def SetupFail2ban():
  utils.LogStep('Configure fail2ban')
  # http://flexion.org/posts/2012-11-ssh-brute-force-defence.html
  utils.Pacman(['-S', 'fail2ban'])
  utils.WriteFile('/etc/fail2ban/jail.local', ETC_FAIL2BAN_JAIL_LOCAL)
  utils.WriteFile('/etc/fail2ban/jail.d/sshd.conf',
                  ETC_FAIL2BAN_JAIL_D_SSHD_CONF)
  utils.EnableService('syslog-ng')
  utils.EnableService('fail2ban.service')


def ConfigureSecurity():
  utils.LogStep('Compute Engine Security Recommendations')
  utils.WriteFile('/etc/sysctl.d/70-gce-security-strongly-recommended.conf',
                  ETC_SYSCTL_D_70_GCE_SECURITY_STRONGLY_RECOMMENDED_CONF)
  utils.WriteFile('/etc/sysctl.d/70-gce-security-recommended.conf',
                  ETC_SYSCTL_D_70_GCE_SECURITY_RECOMMENDED_CONF)
  utils.LogStep('Lock Root User Account')
  utils.Run(['usermod', '-L', 'root'])
  utils.LogStep('PAM Security Settings')
  utils.WriteFile('/etc/pam.d/passwd', ETC_PAM_D_PASSWD)

  utils.LogStep('Disable CAP_SYS_MODULE')
  utils.WriteFile('/proc/sys/kernel/modules_disabled', '1')

  utils.LogStep('Remove the kernel symbol table')
  utils.SecureDeleteFile('/boot/System.map')

  utils.LogStep('Sudo Access')
  utils.WriteFile('/etc/sudoers.d/add-group-adm', ETC_SUDOERS_D_ADD_GROUP_ADM)
  utils.Run(['chown', 'root:root', '/etc/sudoers.d/add-group-adm'])
  utils.Run(['chmod', '0440', '/etc/sudoers.d/add-group-adm'])


def ConfigureSerialPortOutput():
  # https://wiki.archlinux.org/index.php/working_with_the_serial_console
  # Try this: http://wiki.alpinelinux.org/wiki/Enable_Serial_Console_on_Boot
  utils.LogStep('Configure Serial Port Output')

  utils.Sed('/boot/syslinux/syslinux.cfg', '/DEFAULT/aserial 0 38400')
  utils.ReplaceLine('/boot/syslinux/syslinux.cfg', 'TIMEOUT', 'TIMEOUT 1')


def InstallImportedPackages(packages_dir):
  aur_packages_dir = os.path.join(packages_dir, 'aur')
  for aur_package in os.listdir(aur_packages_dir):
    utils.Pacman('-U', aur_package, cwd=aur_packages_dir)


def InstallGcePackages(packages_dir):
  try:
    InstallGoogleCloudSdk()
  except:
    pass
  try:
    InstallComputeImagePackages(packages_dir)
  except:
    pass


def InstallComputeImagePackages(packages_dir):
  utils.LogStep('Install compute-image-packages')
  utils.Run(["egrep -lRZ 'python' %s | "
             "xargs -0 -l sed -i -e '/#!.*python/c\#!/usr/bin/env python2'" %
             packages_dir],
            shell=True)
  utils.CopyFiles(os.path.join(packages_dir, 'google-daemon', '*'), '/')
  utils.CopyFiles(os.path.join(packages_dir, 'google-startup-scripts', '*'),
                  '/')
  utils.SecureDeleteFile('/README.md')
  # TODO: Fix gcimagebundle does not work with Arch yet.
  #InstallGcimagebundle(packages_dir)
  
  # Patch Google services to run after the network is actually available.
  PatchGoogleSystemdService(
      '/usr/lib/systemd/system/google-startup-scripts.service')
  PatchGoogleSystemdService(
      '/usr/lib/systemd/system/google-accounts-manager.service')
  PatchGoogleSystemdService(
      '/usr/lib/systemd/system/google-address-manager.service')
  PatchGoogleSystemdService(
      '/usr/lib/systemd/system/google.service')
  utils.EnableService('google-accounts-manager.service')
  utils.EnableService('google-address-manager.service')
  utils.EnableService('google.service')
  utils.EnableService('google-startup-scripts.service')
  utils.DeleteDirectory(packages_dir)


def InstallGcimagebundle(packages_dir):
  utils.WriteFile(
      os.path.join(packages_dir, 'gcimagebundle/gcimagebundlelib/arch.py'),
      GCIMAGEBUNDLE_ARCH_PY)
  utils.Run(['python2', 'setup.py', 'install'],
            cwd=os.path.join(packages_dir, 'gcimagebundle'))


def PatchGoogleSystemdService(file_path):
  utils.ReplaceLine(file_path,
                    'After=network.target', 'After=network-online.target')
  utils.ReplaceLine(file_path,
                    'Requires=network.target', 'Requires=network-online.target')


def InstallGoogleCloudSdk():
  # TODO: There's a google-cloud-sdk in AUR which should be used
  # but it's not optimal for cloud use. The image is too large.
  utils.LogStep('Install Google Cloud SDK')
  usr_share_google = '/usr/share/google'
  archive = os.path.join(usr_share_google, 'google-cloud-sdk.zip')
  unzip_dir = os.path.join(usr_share_google, 'google-cloud-sdk')
  utils.CreateDirectory(usr_share_google)
  utils.DownloadFile(
      'https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.zip', archive)
  utils.Run(['unzip', archive, '-d', usr_share_google])
  utils.AppendFile('/etc/bash.bashrc',
                   'export CLOUDSDK_PYTHON=/usr/bin/python2')
  utils.Run([os.path.join(unzip_dir, 'install.sh'),
             '--usage-reporting', 'false',
             '--bash-completion', 'true',
             '--disable-installation-options',
             '--rc-path', '/etc/bash.bashrc',
             '--path-update', 'true'],
            cwd=unzip_dir,
            env={'CLOUDSDK_PYTHON': '/usr/bin/python2'})
  utils.Symlink(os.path.join(unzip_dir, 'bin/gcloud'), '/usr/bin/gcloud')
  utils.Symlink(os.path.join(unzip_dir, 'bin/gcutil'), '/usr/bin/gcutil')
  utils.Symlink(os.path.join(unzip_dir, 'bin/gsutil'), '/usr/bin/gsutil')
  utils.SecureDeleteFile(archive)


def ConfigMessageOfTheDay():
  utils.LogStep('Configure Message of the Day')
  utils.WriteFile('/etc/motd', ETC_MOTD)


if __name__ == '__main__':
  main()
