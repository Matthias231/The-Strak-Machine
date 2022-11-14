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

# Scale from mm --> mm
scaleFactor = 1.0

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

def distance_between(p1, p2):
    '''calculates the distance between two given points'''
    x1, y1 = p1
    x2, y2 = p2
    dist = np.sqrt(np.square(x2-x1) + np.square(y2-y1))
    return dist

def calculate_length(line):
    '''calculates the length of a line'''
    length = 0
    length_table = [(0.0, 0.0)]

    for idx in range(len(line)-1):
        p1 = line[idx]
        p2 = line[idx+1]
        length += distance_between(p1, p2)
        # put x and length into length table
        x, y = p2
        length_table.append((length, x))

    return length, length_table

def line_angle(p1, p2):
    '''calculates angle clockwise between two given points'''
    x1, y1 = p1
    x2, y2 = p2
    GK = (y2-y1)
    AK = (x2-x1)
    
    if (AK > 0.0):
        ang1 = np.arctan(GK/AK)
        return np.rad2deg(ang1 % (2 * np.pi))
    else:
        # avoid division by zero
        if (y1 > y2):
            return 180.0
        else:
            return 0.0

def norm_xy(xy, wingData):
    offset_x = wingData.params.fuselageWidth/2
    scaleFactor_x = wingData.params.halfwingspan
    scaleFactor_y = wingData.params.rootchord

    (x, y) = xy
    x_norm = (x-offset_x) / scaleFactor_x
    y_norm = y / scaleFactor_y
    return (x_norm, y_norm)

def denorm_xy(xy_norm, wingData):
    global scaleFactor
    scaleFactor_x = wingData.params.halfwingspan
    scaleFactor_y = wingData.params.rootchord
    
    (x_norm, y_norm) = xy_norm
    x = x_norm * scaleFactor_x * scaleFactor
    y = y_norm * scaleFactor_y * scaleFactor
    return (x, y)

def interpolate(x1, x2, y1, y2, x):
    try:
        y = ((y2-y1)/(x2-x1)) * (x-x1) + y1
    except:
        ErrorMsg("Division by zero, x1:%f, x2:%f", (x1, x2))
        y = 0.0
    return y

def __get_yFromX(points, x):
    num = len(points)
    
    for idx in range(num):
        xp, yp = points[idx]
        # found identical point ?
        if (x == xp):
            x, y = points[idx]
            return y

        # find first point with x value >= x
        elif (xp >= x) and (idx>=1):
            x1, y1 = points[idx-1]
            x2, y2 = points[idx]
            y = interpolate(x1, x2, y1, y2, x)
            return y
    
    ErrorMsg("__get_yFromX, xcoordinate %f not found" % x)
    return None

################################################################################
#
# main function, export
#
################################################################################
def export_toDXF(wingData, FileName, num_points):
    params = wingData.params

    # create new dxf
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # get grid from wingData
    grid = wingData.planform.grid
    
    # setup root line (trailing edge --> leading edge)
    rootline = []
    LE_start = (0.0, grid[0].leadingEdge * scaleFactor)
    TE_start = (0.0, grid[0].trailingEdge * scaleFactor)
    rootline.append(LE_start)
    rootline.append(TE_start)

    num = len(grid)

    LE_norm = []
    # add points of leading edge from root --> tip
    for idx in range(num):
        x, y = norm_xy((grid[idx].y, grid[idx].leadingEdge), wingData)
        LE_norm.append((x, y))
    
    TE_norm = []
    # add points of trailing edge from root --> tip
    for idx in range(num):
        x, y = norm_xy((grid[idx].y, grid[idx].trailingEdge), wingData)
        TE_norm.append((x, y))

    # calculate length of LE and TE (normalized)
    LE_length, LE_length_table = calculate_length(LE_norm)
    TE_length, TE_length_table = calculate_length(TE_norm)

    # calculate distance between two consecutive points for exporting LE and TE
    LE_delta_length = LE_length / (num_points/2)
    TE_delta_length = TE_length / (num_points/2)
  
    # setup points of LE
    length = 0.0
    LE = []
    # iterate length
    while length < LE_length:
        # get x from length table
        x = __get_yFromX(LE_length_table, length)
        y = __get_yFromX(LE_norm, x)
        xy = denorm_xy((x,y), wingData)
        LE.append(xy)
        length += LE_delta_length

    # append last point of LE
    xy = denorm_xy(LE_norm[-1], wingData)
    LE.append(xy)   

    # setup points of TE
    length = 0.0
    TE = []
    while length < TE_length:
        x = __get_yFromX(TE_length_table, length)
        y = __get_yFromX(TE_norm, x)
        xy = denorm_xy((x,y), wingData)
        TE.append(xy)
        length += TE_delta_length
      
    # append last point of TE
    xy = denorm_xy(TE_norm[-1], wingData)
    TE.append(xy)

    # add hingeline #FIXME if we have more points than just start and end we must change algorithm here
    hingeline = []
    xy = norm_xy((grid[0].y, grid[0].hingeLine), wingData)
    hingeline.append(denorm_xy(xy, wingData))
    xy = norm_xy((grid[-1].y, grid[-1].hingeLine), wingData)
    hingeline.append(denorm_xy(xy, wingData))

    # add leightweight polylines to modelspace
    msp.add_lwpolyline(rootline)
    msp.add_lwpolyline(LE)
    msp.add_lwpolyline(TE)
    #msp.add_lwpolyline(hingeline)

    # save to file
    doc.saveas(FileName)
    NoteMsg("DXF data was successfully written.")
    return 0


################################################################################
#
# sub functions, import
#
################################################################################

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
    rootline = None
   
    num = len(lines)
    NoteMsg("trying to find rootline, number of lines: %d" % num)

    # check all lines
    for idx in range(num):
        line = lines[idx]

        # check angle, get first and last point of line (no matter, if polyline)
        p1, p2 = (line[0]), (line[-1])
        length = abs(distance_between(p1, p2))
        angle = line_angle(p1, p2)
        NoteMsg("checking line %d, length: %f, angle: %f" % (idx, length, angle))
        
        if (((angle>179.0) and (angle<181.0)) or
            (angle>359.0) or (angle<1.1)):
            NoteMsg("appending line %d to candidate list" % idx)
            # line runs nearly straight up or straight down, so is a candidate.
            # calculate length
            length = abs(distance_between(p1, p2))
            lengths.append(length)
            idxList.append(idx)
    
    # are there any candidates in the list ?
    if (len(idxList) != 0):
        # yes, find candidate with maximum length
        maxLength = max(lengths)
        idx = lengths.index(maxLength)
        rootlineIdx = idxList[idx]
        line = lines[rootlineIdx]
        
        # copy only first and last point to rootline, in case we have a polyline
        rootline = [line[0], line[-1]]
        
        # remove from list of lines
        lines.pop(rootlineIdx)
        lengths.pop(idx)

        NoteMsg("found rootline, length is %f, idx is %d" % (maxLength, rootlineIdx))    
        
        # check for duplicate rootline
        for idx in range(len(lengths)):
            if (lengths[idx] == maxLength):
                dupIdx = idxList[idx]
                NoteMsg("removing duplicate rootline at idx %d" % (dupIdx))
                lines.pop(dupIdx)
       
        # check if rootline has to be reverted
        (x1, y1), (x2, y2) = rootline
        if (y2 < y1):
            # revert line
            NoteMsg("reverting rootline")
            rootline = rootline[::-1]

    return rootline, lines

def __points_match(p1, p2):
    matching_range = 0.1 #FIXME: take into account the scaling of the planform, e.g. wingspan. m or mm?
    x1, y1 = p1
    x2, y2 = p2

    if ((abs(x2-x1) <= matching_range) and
        (abs(y2-y1) <= matching_range)):
        return True
    else:
        return False

def __get_matching_line(point, lines):
    x,y = point
    NoteMsg("searching for line with start- or endpoint %f, %f" % (x, y))
    
    # check number of lines
    num = len(lines)
    if num == 0:
        return None, None
    
    # search in all lines
    for idx in range(num):
        line = lines[idx]
        
        p1 = line[0]
        p2 = line[-1]
        x1, y1 = p1
        x2, y2 = p2

        NoteMsg("checking line %d. Startpoint: %f, %f, Endpoint %f, %f" % (idx, x1, y1, x2, y2))
        if __points_match(point, p1):
            # return idx and line as is
            NoteMsg("found matching startpoint")
            return idx, line
        elif __points_match(point, p2):
            # line has to be reverted
            NoteMsg("found matching endpoint, line has to be reverted")
            line = line[::-1]
            return idx, line
        
    # nothing was found
    ErrorMsg("No matching line was found")
    return None, None
   
# join all lines to contour
def __create_contour(rootline, lines):
    contour = []
    actual_point = rootline[0]
    endpoint = rootline[1]
    
    while True:
        # check lines
        idx, line  = __get_matching_line(actual_point, lines)
        
        if idx != None:
            # remove from list of polylines
            lines.pop(idx)
          
        # found a matching line ?
        if line == None:
            ErrorMsg("no matching line was found, contour could not be finished")
            return contour, lines
        else:    
            # append to contour
            contour.extend(line)
            
            # set new actual point, which is the endpoint of the current line
            actual_point = line[-1]
            
            # check if we have reached the endpoint
            if __points_match(endpoint, actual_point):
                # we have finished
                return contour, lines
    
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
    
    # first point always LE
    LE.append(contour[0])
    
    for idx in range(1, num):
        x, y = contour[idx]
        # determine idx of max x value
        if (x > max_x):
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

def __create_planformShape(wingData, lines):
    global num_gridPoints
    planformShape = []
    halfwingspan = wingData.params.halfwingspan
    rootchord = wingData.params.rootchord
       
    NoteMsg("creating planformshape")

    # get rootline
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
    contour, remaining_lines = __create_contour(rootline, remaining_lines)
    
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
    
    NoteMsg("DXF: rootchord: %f, halfwingspan: %f, x_offset: %f, y_offset: %f" % (dxf_rootchord, dxf_halfwingspan, x_offset, y_offset))

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
    num_segments = 100
    
    NoteMsg("Analysing entities in dxf file")
    for e in msp:
        NoteMsg("found entity %s" % e.dxftype())
    
    # empty list of lines
    myLines = []

    # get all lines
    lines = msp.query("LINE")
    
    # evaluate all lines and append to myLines
    idx = 0
    for line in lines:
        NoteMsg("getting line %d:" % idx)
        x1, y1, z = line.dxf.start
        x2, y2, z = line.dxf.end
        myLines.append(((x1, y1), (x2, y2)))   
        idx += 1
    
    # get all splines
    splines = msp.query("SPLINE")

    # evaluate all splines and convert into polylines
    idx = 0
    for spline in splines:
        NoteMsg("getting spline %d and converting to 2d polyline with %d segments" % (idx, num_segments))
        bspline = spline.construction_tool()
        xy_pts = [p.xy for p in bspline.approximate(segments=num_segments)]
        msp.add_lwpolyline(xy_pts, format='xy')
        idx += 1

    # get all polylines
    polylines = msp.query("LWPOLYLINE")
    
     # evaluate all polylines and append to myLines
    idx = 0
    for line in polylines:
        NoteMsg("getting polyline %d" % idx)
        with line.points("xy") as points:
            # append points of polyline
            myLines.append(points)    
            idx += 1
    
    # create grid from points
    planformShape = __create_planformShape(wingData, myLines)
    #FIXME insert planformshape into wingdata, etc.
    NoteMsg("Planform has been succesfully imported")
    return 0
    
################################################################################
#
# main function, import
#
################################################################################

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
