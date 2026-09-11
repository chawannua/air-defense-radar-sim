# Third-Party Notices

AEGIS Radar is distributed under a [proprietary source-available licence](LICENSE).
That licence covers **only** the AEGIS Radar source code and assets authored by the
copyright holder.

The distributed Windows executable additionally bundles the third-party components
listed below. Each remains the property of its respective copyright holders and is
governed by its own licence, which is **not** affected by the AEGIS Radar licence.
Those licences are reproduced or referenced here to satisfy their attribution
requirements.

---

## Python runtime and libraries

### pygame — LGPL-2.1-or-later
Copyright (c) 2000-2024 pygame developers

pygame is licensed under the GNU Lesser General Public License, version 2.1 or
later. Full text: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html

> **Relinking notice (LGPL-2.1 §6).** The copyright holder will, on request,
> provide the object files required to relink AEGIS Radar against a modified
> version of pygame. Contact the copyright holder to obtain them. A directory-style
> build, in which `pygame` and its DLLs are replaceable in place, is also available
> on request.

### NumPy — BSD-3-Clause
Copyright (c) 2005-2025 NumPy Developers. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the above copyright notice, this list of conditions
and the following disclaimer are retained. Neither the name of the NumPy Developers
nor the names of its contributors may be used to endorse or promote products
derived from this software without specific prior written permission.

Full text: https://github.com/numpy/numpy/blob/main/LICENSE.txt

---

## Native libraries bundled with pygame

### SDL2, SDL2_image, SDL2_mixer, SDL2_ttf — zlib licence
Copyright (c) 1997-2024 Sam Lantinga and contributors

This software is provided "as-is", without any express or implied warranty. In no
event will the authors be held liable for any damages arising from the use of this
software. Altered source versions must be plainly marked as such, and must not be
misrepresented as being the original software. This notice may not be removed or
altered from any source distribution.

Full text: https://www.libsdl.org/license.php

### FreeType — FreeType Licence (FTL, BSD-style)
Portions of this software are copyright (c) 2006-2024 The FreeType Project
(www.freetype.org). All rights reserved.

Full text: https://gitlab.freedesktop.org/freetype/freetype/-/blob/master/LICENSE.TXT

### libpng — PNG Reference Library Licence v2
Copyright (c) 1995-2024 The PNG Reference Library Authors

Full text: http://www.libpng.org/pub/png/src/libpng-LICENSE.txt

### libjpeg — Independent JPEG Group licence
This software is based in part on the work of the Independent JPEG Group.

Full text: https://jpegclub.org/reference/libjpeg-license/

### libogg, libopus, libopusfile — BSD-3-Clause
Copyright (c) 1994-2024 Xiph.Org Foundation and contributors. All rights reserved.

Full text: https://gitlab.xiph.org/xiph/ogg/-/blob/master/COPYING

### libwebp — BSD-3-Clause
Copyright (c) 2010-2024 Google Inc. All rights reserved.

Full text: https://chromium.googlesource.com/webm/libwebp/+/HEAD/COPYING

### PortMidi — MIT
Copyright (c) 2009-2024 PortMidi authors

Full text: https://github.com/PortMidi/portmidi/blob/master/LICENSE

---

## Build tooling

### PyInstaller — GPL-2.0-or-later with bootloader exception
The PyInstaller bootloader is distributed with an explicit exception permitting its
use in, and distribution with, applications released under any licence, including
proprietary licences. AEGIS Radar relies on that exception.

Full text: https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

---

## Data

### Natural Earth — public domain
Country outline data (`*.json`) is derived from Natural Earth 1:10m Cultural
Vectors (admin-0 countries), which is in the **public domain**. No permission is
required to use it. Natural Earth requests, but does not require, credit:

> Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com

---

*Component list generated from the 78 native libraries present in the distributed
build. If a bundled component is missing from this file, that is an oversight
rather than an assertion of rights — please report it.*
