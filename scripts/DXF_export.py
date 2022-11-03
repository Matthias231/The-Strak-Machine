#!/usr/bin/env python

#  This file is part of "The Strak Machine".

#  "The Strak Machine" is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  "The Strak Machine" is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with "The Strak Machine".  If not, see <http://www.gnu.org/licenses/>.

#  Copyright (C) 2020-2022 Matthias Boese

import os, re
import ezdxf
from copy import deepcopy
from strak_machine import (ErrorMsg, WarningMsg, NoteMsg, DoneMsg, bs)


def export_toDXF(wingData, FileName):
    params = wingData.params

    # create empty list (outline of planform)
    outline = []

    # create new dxf
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    grid = wingData.planform.grid

    # setup root joint (trailing edge --> leading edge)
    outline.append((grid[0].y, grid[0].trailingEdge))

    num = len(grid)

    # add points of leading edge to outline from root --> tip
    for idx in range(num):
        outline.append((grid[idx].y, grid[idx].leadingEdge))

    # setup tip joint (leading edge --> trailing edge)
    outline.append((grid[-1].y, grid[-1].trailingEdge))

    # add points of trailing edge to outline from tip --> root
    for idx in reversed(range(num)):
        outline.append((grid[idx].y, grid[idx].trailingEdge))

    # add leightweight polyline
    msp.add_lwpolyline(outline)

    # save to file
    doc.saveas(FileName)
    NoteMsg("DXF data was successfully written.")
    return 0
