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
from ezdxf.addons import Importer
import numpy as np
from copy import deepcopy
from strak_machine import (ErrorMsg, WarningMsg, NoteMsg, DoneMsg, bs)

# Scale from mm --> m
scaleFactor = (1.0/1000.0)

################################################################################
#
# helper functions
#
################################################################################
def calculate_distance(x1, x2, y1, y2):
    '''calculates the distance between two given points'''
    dist = np.sqrt(np.square(x2-x1) + np.square(y2-y1))
    return dist

def norm_xy(xy, wingData):
    (x, y) = xy
    x_norm = x / wingData.params.halfwingspan
    y_norm = y / wingData.params.rootchord
    return (x_norm, y_norm)

def denorm_xy(xy_norm, wingData):
    (x_norm, y_norm) = xy_norm
    x = x_norm * wingData.params.halfwingspan * scaleFactor
    y = y_norm * wingData.params.rootchord * scaleFactor
    return (x, y)

################################################################################
#
# main function
#
################################################################################
def export_toDXF(wingData, FileName, num_points):
    params = wingData.params

    # create empty list (outline of planform)
    outline = []

    # create new dxf
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    grid = wingData.planform.grid

    # setup root joint (trailing edge --> leading edge)
    x, y = norm_xy((grid[0].y, grid[0].trailingEdge), wingData)
    outline.append((x, y))

    num = len(grid)

    # add points of leading edge to outline from root --> tip
    for idx in range(num):
        x, y = norm_xy((grid[idx].y, grid[idx].leadingEdge), wingData)
        outline.append((x, y))

    # setup tip joint (leading edge --> trailing edge)
    x, y = norm_xy((grid[-1].y, grid[-1].trailingEdge), wingData)
    outline.append((x, y))

    # add points of trailing edge to outline from tip --> root
    for idx in reversed(range(num)):
        x, y = norm_xy((grid[idx].y, grid[idx].trailingEdge), wingData)
        outline.append((x, y))

    # calculate length of outline (normalized)
    length = 0
    maxIdx = len(outline)-1
    # start with idx 2 (after root joint)
    for idx in range(2, maxIdx):
        x1, y1 = outline[idx]
        x2, y2 =  outline[idx+1]
        length += calculate_distance(x1, x2, y1, y2)

    # calculate distance between points
    distDelta = length / num_points

    dist = 0
    new_outline = []

    # always append first two points of outline to new outline
    new_outline.append(outline[0])
    new_outline.append(outline[1])

    # start with idx 1, as idx 0 --> idx 1 is the root joint
    x1, y1 = outline[1]
    for idx in range(1, maxIdx):
        x2, y2 = outline[idx]
        dist = calculate_distance(x1, x2, y1, y2)

        # check distance to last point that has been copied to new outline
        # and actual point
        if dist >= distDelta:
            # copy this point to new outline
            new_outline.append(outline[idx])
            x1, y1 = outline[idx]

    # check last point of outline and new_outline
    if outline[-1] != new_outline[-1]:
        new_outline.append(outline[-1])

    # now we have a normalzed outline with reduced number of points
    # --> denormalize
    num = len(new_outline)
    for idx in range(num):
        xy = denorm_xy(new_outline[idx], wingData)
        new_outline[idx] = xy

    # add leightweight polyline
    msp.add_lwpolyline(new_outline)

    # add hingeline #FIXME if we have more points than just start and end we must change algorithm here
    hingeline = []
    hingeline.append((grid[0].y * scaleFactor, grid[0].hingeLine * scaleFactor))
    hingeline.append((grid[-1].y * scaleFactor, grid[-1].hingeLine * scaleFactor))

    msp.add_lwpolyline(hingeline)

    # save to file
    doc.saveas(FileName)
    NoteMsg("DXF data was successfully written.")
    return 0

def import_fromDXF(FileName):
    try:
        sdoc = ezdxf.readfile(FileName)
    except:
        ErrorMsg("import_fromDXF: unable to read file %s" % FileName)

    tdoc = ezdxf.new()
    importer = Importer(sdoc, tdoc)

    # import all entities from source modelspace into modelspace of the target drawing
    importer.import_modelspace()

    # import all paperspace layouts from source drawing
    importer.import_paperspace_layouts()

    # import all CIRCLE and LINE entities from source modelspace into an arbitrary target layout.
    # create target layout
    tblock = tdoc.blocks.new('SOURCE_ENTS')

    # query source entities
    ents = sdoc.modelspace().query('CIRCLE LINE')

    # import source entities into target block
    importer.import_entities(ents, tblock)

    # This is ALWAYS the last & required step, without finalizing the target drawing is maybe invalid!
    # This step imports all additional required table entries and block definitions.
    importer.finalize()
    NoteMsg("import_fromDXF: planform was succesfully imported from file %s" % FileName)
    #tdoc.saveas('imported.dxf')
