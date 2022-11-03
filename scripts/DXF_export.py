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

    # create empty lists
    xValues = []
    leadingEdge = []
    trailingeEge = []
    #hingeLine = []
    #quarterChordLine = []

    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    grid = wingData.planform.grid
    for element in grid:
        # build up list of x-values
        xValues.append(element.y)

        # build up lists of y-values
        leadingEdge.append(element.leadingEdge)
        #quarterChordLine.append(element.quarterChordLine)
        #hingeLine.append(element.hingeLine)
        trailingeEge.append(element.trailingEdge)

    # setup root- and tip-joint
    trailingeEge[0] = leadingEdge[0]
    trailingeEge[-1] = leadingEdge[-1]

    num = len(xValues) -1
    for idx in range(num):
        # add leading edge
        msp.add_line((xValues[idx], leadingEdge[idx]), ((xValues[idx+1], leadingEdge[idx+1])))
        # add trailing edge
        msp.add_line((xValues[idx], trailingeEge[idx]), ((xValues[idx+1], trailingeEge[idx+1])))

    # save to file
    doc.saveas(FileName)
    NoteMsg("DXF data was successfully written.")
    return 0
