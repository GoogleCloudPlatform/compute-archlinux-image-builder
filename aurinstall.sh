#!/bin/bash

InstallFromAur() {
  local package_url="https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=$1"
  local working_dir=${PWD}
  local temp_dir=`mktemp -d`
  cd ${temp_dir}
  wget -O ${temp_dir}/PKGBUILD ${package_url} -nv
  makepkg
  sudo pacman -U `ls *.tar*`
  rm ${temp_dir} -rf
  cd ${working_dir}
}

for package in "$@"
do
  InstallFromAur "${package}"
done
