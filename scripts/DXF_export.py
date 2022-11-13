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
#from planform_creator import wingGrid

# Scale from mm --> m
scaleFactor = (1.0/1000.0)

# maximum number of points that identify a polyline as a hingeline
max_hingelinePoints = 10

# number of grid points for planformshape and chord distribution
num_gridPoints = 1000

################################################################################
#
# wingGrid class
#
################################################################################
class wingGrid:

    # class init
     def __init__(self):
        self.y = 0.0
        self.chord = 0.0
        self.leadingEdge = 0.0
        self.quarterChordLine = 0.0
        self.hingeLine = 0.0
        self.flapDepth = 0.0
        self.trailingEdge = 0.0

################################################################################
#
# normalizedGrid class
#
################################################################################
class normalizedGrid:

    # class init
     def __init__(self):
        self.y = 0.0
        self.chord = 0.0
        self.referenceChord = 0.0
        self.hinge = 0.0

################################################################################
#
# helper functions
#
################################################################################
def calculate_distance(x1, x2, y1, y2):
    '''calculates the distance between two given points'''
    dist = np.sqrt(np.square(x2-x1) + np.square(y2-y1))
    return dist

def distance_between(p1, p2):
    '''calculates the distance between two given points'''
    x1, y1 = p1
    x2, y2 = p2
    dist = np.sqrt(np.square(x2-x1) + np.square(y2-y1))
    return dist
    '''calculates angle clockwise between two given points'''

def angle_between(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    GK = y2-y1
    AK = x2-x1
    
    if (AK > 0.0):
        ang1 = np.arctan2(GK/AK)
        return np.rad2deg(ang1 % (2 * np.pi))
    else:
        # avoid division by zero
        if (y1 > y2):
            return 180.0
        else:
            return 0.0

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

def interpolate(x1, x2, y1, y2, x):
    try:
        y = ((y2-y1)/(x2-x1)) * (x-x1) + y1
    except:
        ErrorMsg("Division by zero, x1:%f, x2:%f", (x1, x2))
        y = 0.0
    return y

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

def __get_min_max(points):
    num_points = len(points)
    idx_min_x = 0
    idx_max_x = 0
    idx_min_y = 0
    idx_max_y = 0
    min_x = -1000000000.0
    max_x = -1000000000.0
    min_y = 1000000000.0
    max_y = -1000000000.0

    for idx in range(num_points):
        (x, y, d1, d2, d3) = points[idx]
        if (x < min_x):
            x = min_x
            idx_min_x = idx
        if (y < min_y):
            y = min_y
            idx_min_y = idx
        if (x > max_x):
            x = max_x
            idx_max_x = idx
        if (y > max_y):
            y = max_y
            idx_max_y = idx
    
    minMax_coordinates = (min_x, max_x, min_y, max_y)
    minMax_idx =  (idx_min_x, idx_max_x, idx_min_y, idx_max_y)
    return (minMax_idx, minMax_coordinates)

def __get_root(points, idx_min_x, ):
    num_points = len(points)
    root_x1 = 1000000000.0
    root_x2 = 1000000000.0
    # find smallest y-coordinate
    # find greatest y-coordinate

    # find point with smallest x-coordinate 
    for idx in range(num_points):
        (x, y, d1, d2, d3) = points[idx]
        if (x < root_x1):
            root_x1 = x
            root_y1 = y
            idx_root_x1y1 = idx

def __convert(xy, x_offset, y_offset, scaleFactor_x, scaleFactor_y):
    x, y = xy
    x -= x_offset
    x *= scaleFactor_x
    y -= y_offset
    y *= scaleFactor_y

    return (x,y)


def __get_rootline(lines):
    lengths = []
    idxList = []
    num = len(lines)
    
    if num == 0:
        ErrorMsg("there are no lines")
        return None

    # check all lines
    for idx in range(num):
        # check angle
        p1, p2 = lines[idx]
        angle = angle_between(p1, p2)
        
        if (((angle>179.0) and (angle<181.0)) or
            (angle>359.0) or (angle<1.1)):
            # line runs nearly straight up or straight down, calculate length
            length = abs(distance_between(p1, p2))
            lengths.append(length)
            idxList.append(idx)
    
    maxLength = max(lengths)
    rootlineIdx = lengths.index(maxLength)    
    rootline = lines[rootlineIdx]
       
    # check if line has to be reverted
    (x1, y1), (x2, y2) = rootline
    if (y2 < y1):
        # revert line
        rootline = rootline[::-1]

    # get remaining lines
    remaining_lines =[]
    for idx in range(num):
        if (idx != rootlineIdx):
            remaining_lines.append(lines[idx])

    return rootline, remaining_lines

def __points_match(p1, p2):
    matching_range = 0.0001 #FIXME
    x1, y1 = p1
    x2, y2 = p2

    if ((abs(x2-x1) <= matching_range) and
        (abs(y2-y1) <= matching_range)):
        return True
    else:
        return False

def __get_matching_line(point, lines):
    # check number of lines
    num = len(lines)
    if num == 0:
        return None, None
    
    # search in all lines
    for idx in range(num):
        line = lines[idx]
        p1 = line[0]
        p2 = line[-1]
        if __points_match(point, p1):
            # return idx and line as is
            return idx, line
        elif __points_match(point, p2):
            # line has to be reverted
            line = line[::-1]
            return idx, line
        
    # nothing was found
    return None, None
   
# join all lines to contour
def __create_contour(rootline, lines, polylines):
    contour = []
    actual_point = rootline[0]
    endpoint = rootline[1]
    
    while True:
        # check polylines
        idx, line  = __get_matching_line(actual_point, polylines)
        
        if idx != None:
            # remove from list of polylines
            polylines.pop(idx)
        else:
            # check lines
            idx, line  = __get_matching_line(actual_point, lines)
            if idx != None:
                # remove from list of lines
                lines.pop(idx)
        
        # found a matching line ?
        if line == None:
            ErrorMsg("no matching line or polyline was found, contour could not be finished")
            return contour, lines, polylines
        else:    
            # append to contour
            contour.extend(line)
            
            # set new actual point
            actual_point = line[-1]
            
            # check if we have reached the endpoint
            if __points_match(endpoint, actual_point):
                # we have finished
                return contour, lines, polylines
    
    


# split contour into leading edge and trailing edge
def __split_contour(contour):
    LE = []
    TE = []
    num = len(contour)
    
    if (num == 0):
        ErrorMsg("__split_contour: contour has no points")
        return (LE, TE)
    
    # initialize max_x with root
    max_x, y = contour[0]
    
    for idx in range(num):
        x, y = contour[idx]
        # determine idx of max x value
        if (x >= max_x):
            # if we have not reached maximum, append to LE
            max_x = x
            maxIdx = idx
            LE.append(contour[idx])
        else:
            # after we have reached maximum append to TE
            TE.append(contour[idx])
    
    # revert TE
    TE = TE[::-1]

    return LE, TE  

def __get_yFromX(points, x):
    num = len(points)
    
    for idx in range(num):
        xp, yp = points[idx]
        # found identical point ?
        if (x == xp):
            x, y = points[idx]
            return y

        # find first point with x value > x
        elif (xp > x) and (idx>=1):
            x1, y1 = points[idx-1]
            x2, y2 = points[idx]
            y = interpolate(x1, x2, y1, y2, x)
            return y
    
    ErrorMsg("__get_yFromX, xcoordinate %f not found" % x)
    return None

def __create_planformShape(wingData, lines, polylines):
    global num_gridPoints
    planformShape = []
    halfwingspan = wingData.params.halfwingspan
    rootchord = wingData.params.rootchord
       
    NoteMsg("creating planformshape")
    
    # first get rootline
    rootline, remaining_lines = __get_rootline(lines)
    
    if rootline == None:
        ErrorMsg("root line not found")
        return None

    # calculate rootchord, determine scale factor and offsets    
    (x1, y1) , (x2, y2) = rootline
    dxf_rootchord = y2 - y1
    scaleFactor_y = 1 / dxf_rootchord
    x_offset = x1
    y_offset = y1
    
    # second join all remaining lines and polylines to contour/ planformshape
    contour, remaining_lines, remaining_polylines = __create_contour(rootline, remaining_lines, polylines)
    
    # split contour into leading edge and trailing edge
    LE, TE = __split_contour(contour)       
   
    # check number of points
    if (len(LE) == 0):
        ErrorMsg("number of LE points is zero")
        return None

    if (len(TE) == 0):
        ErrorMsg("number of TE points is zero")
        return None
    
    # calculate halfwingspan, determine scale factor 
    x1, y1 = LE[0]
    x2, y2 = LE[-1]

    dxf_halfwingspan = abs(x2-x1)
    scaleFactor_x = 1.0/dxf_halfwingspan
    
    # normalize LE
    # first point, x-coordinate 0
    LE_norm = [(0.0, 0.0)]
    # further points
    for idx in range(1, len(LE)):
        LE_x, LE_y = __convert(LE[idx], x_offset, y_offset, scaleFactor_x, scaleFactor_y)
        LE_norm.append((LE_x, LE_y))

    # normalize TE
    # first point, x-coordinate 0
    TE_norm = [(0.0, 1.0)]
    # further points
    for idx in range(1, len(TE)):
        TE_x, TE_y = __convert(TE[idx], x_offset, y_offset, scaleFactor_x, scaleFactor_y)
        TE_norm.append((TE_x, TE_y))
    
    # calculate increment 
    delta_x = 1.0 / num_gridPoints
   
    # start at root, which always is 0.0
    x = 0.0

    # calculate planform shape and also normalized chord distribution
    planformShape = []
    chordDistribution = []
    while (x < 1.0):
        # get normalized LE, TE
        LE_y = __get_yFromX(LE_norm, x)
        TE_y = __get_yFromX(TE_norm, x)
        
        if (LE_y == None) or (TE_y == None):
            ErrorMsg("y-coordinate not found, planform could not be created")
            return

        # setup normalized chord distribution
        norm_grid = normalizedGrid()
        norm_grid.y = x
        norm_grid.chord = TE_y-LE_y
        norm_grid.referenceChord = 0.0 #FIXME calculate ellipse
        chordDistribution.append(norm_grid)

        # setup absolute planformshape
        grid = wingGrid()
        grid.y = x * halfwingspan
        grid.leadingEdge = LE_y * rootchord
        grid.trailingEdge = TE_y * rootchord
        grid.chord = grid.trailingEdge - grid.leadingEdge
        grid.quarterChordLine = grid.chord/4
        grid.hingeLine = 0.0 # we have no hingeline at the moment
        grid.flapDepth = 0.0  # we have no hingeline at the moment
        planformShape.append(grid)
        
        # increment y coordinate
        x += delta_x
    #FIXME setup hingeline
    return planformShape

def __insert_hingeline(planformShape, points):
    return #FIXME implement

def __convert_toWingData(msp, wingData):
    num_segments = 1000
    
    NoteMsg("Analysing entities in dxf file")
    for e in msp:
        NoteMsg("found entity %s" % e.dxftype())
    
    # get all lines
    lines = msp.query("LINE")
    
    # evaluate all lines and append to myLines
    idx = 0
    myLines = []
    for line in lines:
        NoteMsg("getting line %d:" % idx)
        x1, y1, z = line.dxf.start
        x2, y2, z = line.dxf.end
        myLines.append(((x1, y1), (x2, y2)))   
        idx += 1
    
    # get all splines, convert into polylines
    splines = msp.query("SPLINE")

    idx = 0
    for spline in splines:
        NoteMsg("getting spline %d and converting to 2d polyline with %d segments" % (idx, num_segments))
        bspline = spline.construction_tool()
        xy_pts = [p.xy for p in bspline.approximate(segments=num_segments)]
        msp.add_lwpolyline(xy_pts, format='xy')
        idx += 1

    # get all polylines
    polylines = msp.query("LWPOLYLINE")
    
    # evaluate polylines (one polyline for LE, one polyline for TE)
    idx = 0
    myPolylines = []
    for line in polylines:
        NoteMsg("getting polyline %d" % idx)
        with line.points("xy") as points:
            # append points of polyline
            myPolylines.append(points)    
            idx += 1
    
    # create grid from points
    planformShape = __create_planformShape(wingData, myLines, myPolylines)
    print ("Done")



def import_fromDXF(wingData, FileName):
    try:
        sdoc = ezdxf.readfile(FileName)
    except:
        ErrorMsg("import_fromDXF: unable to read file %s" % FileName)

    tdoc = ezdxf.new()
    importer = Importer(sdoc, tdoc)

    # import all entities from source modelspace into modelspace of the target drawing
    importer.import_modelspace()

    # import all paperspace layouts from source drawing
    #importer.import_paperspace_layouts()

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
    
    # Convert data and insert into wingdata
    __convert_toWingData(sdoc.modelspace(), wingData)
    NoteMsg("import_fromDXF: planform was succesfully imported from file %s" % FileName)

    
    #tdoc.saveas('imported.dxf')
