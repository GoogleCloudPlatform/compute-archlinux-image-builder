# Copyright 2018 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Maintainer: Lorenzo Castelli <lcastelli@google.com>
# Maintainer: Samuel Littley <samuellittley@google.com>

pkgname='build-arch-gce'
pkgver=0.1
pkgrel=1
pkgdesc='Builds a Arch image for Google Compute Engine'
arch=('any')
url=''
license=('Apache')
depends=('arch-install-scripts' 'e2fsprogs')
source=('build-arch-gce')
sha256sums=('7630868a98e3713bdf12fcfecd8733796b113296336c99e5827cb7b97e191a37')

package() {
	install -m755 -Dt "$pkgdir/usr/bin/" build-arch-gce
}
