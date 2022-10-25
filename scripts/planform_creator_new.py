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

import ctypes
import customtkinter
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
import argparse
from sys import version_info
import os
from os import listdir, path, system, makedirs, chdir, getcwd, remove
import f90nml
from shutil import copyfile
from matplotlib import pyplot as plt
from matplotlib.patches import Wedge
from matplotlib.figure import Figure
from matplotlib import rcParams
from matplotlib import bezier
import numpy as np
from scipy.interpolate import make_interp_spline
from scipy.interpolate import UnivariateSpline
from scipy import interpolate as scipy_interpolate
from math import log10, floor, tan, atan, sin, cos, pi, sqrt
import json
import tkinter
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
import tkinter.font as font
from strak_machine import (copyAndSmooth_Airfoil, get_ReString,
                             ErrorMsg, WarningMsg, NoteMsg, DoneMsg,
                             remove_suffix, interpolate, round_Re,
                             bs, buildPath, ressourcesPath, airfoilPath,
                             scriptPath, exePath, smoothInputFile,
                             strakMachineInputFileName, xfoilWorkerName,
                             T1_polarInputFile)

from colorama import init
from termcolor import colored
from FLZ_Vortex_export import export_toFLZ

################################################################################
# some global variables

# disables all print output to console
print_disabled = False

# folder where the generated planforms can be found
planformsPath = '02_planforms'

# folder containing the output / result-files
outputFolder = buildPath + bs + planformsPath

# colours, lineStyles
cl_background = None
cl_grid = None
cl_quarterChordLine = None
cl_geometricalCenterLine = None
cl_geoCenter = None
cl_hingeLine = None
cl_hingeLineFill = None
cl_planform = None
cl_planformFill = None
cl_sections = None
cl_userAirfoil = None
cl_optAirfoil = None
cl_infotext = None
cl_diagramTitle = None
cl_legend = None
cl_chordlengths = None
cl_referenceChord = None
cl_normalizedChord = None
cl_controlPoints = None

# linestyles
ls_grid = 'dotted'
ls_quarterChordLine = 'solid'
ls_geometricalCenterLine = 'solid'
ls_hingeLine = 'solid'
ls_planform = 'solid'
ls_sections = 'solid'

# linewidths
lw_grid = 0.3
lw_quarterChordLine  = 0.8
lw_geometricalCenterLine = 0.8
lw_hingeLine = 0.6
lw_planform = 1.0
lw_sections = 0.4

# fontsizes
fs_diagramTitle = 20
fs_infotext = 9
fs_legend = 9
fs_axes = 20
fs_ticks = 10

# fonts
main_font = "Roboto Medium"

# scaling information
scaled = False
scaleFactor = 1.0

# types of diagrams
diagTypes = ["Chord distribution", "Planform shape", "Flap distribution",
             "Airfoil distribution", "Wing"]

planformShapes = ['elliptical', 'trapezoidal']

xfoilWorkerCall = "..\\..\\bin\\" + xfoilWorkerName + '.exe'
inputFilename = "..\\..\\ressources\\" + smoothInputFile

################################################################################
#
# helper functions
#
################################################################################
def calculate_distance(x1, x2, y1, y2):
    '''calculates the distance between two given points'''
    dist = np.sqrt(np.square(x2-x1) + np.square(y2-y1))
    return dist

def bullseye(center, radius, color, ax, **kwargs):
    '''function for plotting a bullseye with given radius and center'''
    circle1 = plt.Circle(center, radius=radius, color=color, fill=False)
    w1 = Wedge(center, radius, 90, 180, fill=True, color=color)
    w2 = Wedge(center, radius, 270, 360, fill=True, color=color)
    ax.add_patch(circle1)
    ax.add_artist(w1)
    ax.add_artist(w2)

################################################################################
#
# wingSection class
#
################################################################################
class wingSection:

    #class init
    def __init__(self):
        self.number = 0

        # geometrical data of the wing planform
        self.y = 0
        self.chord = 0
        self.Re = 0.0
        self.leadingEdge = 0
        self.trailingEdge = 0
        self.hingeDepth = 0
        self.hingeLine = 0
        self.quarterChordLine = 0
        self.geometricalCenterLine = 0
        self.dihedral= 3.00
        self.flapGroup = 0

        # name of the airfoil-file that shall be used for the section
        self.airfoilName = ""

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
# wingGrid class
#
################################################################################
class wingGrid:

    # class init
     def __init__(self):
        self.y = 0.0
        self.chord = 0.0
        self.leadingEdge = 0.0
        self.trailingEdge = 0.0
        self.hingeDepth = 0.0
        self.hingeLine = 0.0
        self.quarterChordLine = 0.0
        self.LE_derivative = 0.0
        self.geometricalCenterLine = 0.0

################################################################################
#
# params class
#
################################################################################
class params:
    # class init
    def __init__(self):
        # single parameters, strings
        self.planformName = 'main wing'
        self.planformShape = 'elliptical'
        self.leadingEdgeOrientation = 'up'
        self.airfoilBasicName = 'airfoil'
        self.theme = 'Dark'

        # single parameters,boolean
        self.isFin = False
        self.smoothUserAirfoils = False
        self.showQuarterChordLine = True
        self.showTipLine = False
        self.showHingeLine = True

        # single parameters, double /float
        self.wingspan = 0.0
        self.rootchord = 0.0
        self.rootReynolds = 0.0
        self.tipchord = 0.0
        self.tipSharpness = 0.0
        self.fuselageWidth = 0.0
        self.leadingEdgeCorrection = 0.0
        self.hingeLineAngle = 0.0
        self.hingeDepthRoot = 0.0
        self.hingeDepthTip = 0.0
        self.dihedral = 0.0
        self.NCrit = 0.0

        # single parameters, int
        self.numAirfoils = 0
        self.interpolationSegments = 0

        # lists, double / float
        self.polarReynolds = []
        self.airfoilPositions = []
        self.airfoilReynolds = []
        self.flapGroups = []

        # lists, string
        self.airfoilTypes = []
        self.userAirfoils = []
        self.airfoilNames = []

        # dependend parameters double / float
        self.tipDepthPercent = 0.0
        self.halfwingspan = 0.0
        self.area = 0.0
        self.aspectRatio = 0.0

        # dependend parameters int
        self.rootReynolds = 0

        # dependend parameters, array
        self.chordDistribution = None

    ################################################################################
    # function that gets a single boolean parameter from dictionary and returns a
    #  default value in case of error
    def __get_booleanParameterFromDict(self, dict, key, default):
        value = default
        try:
            string = dict[key]
            if (string == 'true') or (string == 'True') or (string == True):
                value = True
            else:
                value = False
        except:
            NoteMsg('parameter \'%s\' not specified, using' \
            ' default-value \'%s\'' % (key, str(value)))
        return value

    ################################################################################
    # function that gets a single mandatory parameter from dictionary and exits, if
    # the key was not found
    def __get_MandatoryParameterFromDict(self, dict, key):
        try:
            value = dict[key]
        except:
            ErrorMsg('parameter \'%s\' not specified, this key is mandatory!'% key)
            value = None
        return value


    def read_fromDict(self, dictData):
        '''Function that reads parameters from a given dictionary'''
        # initialize params first
        self.__init__()

        # now check dictionary and read values into params
        self.planformName = self.__get_MandatoryParameterFromDict(dictData, "planformName")
        self.rootchord =  self.__get_MandatoryParameterFromDict(dictData, "rootchord")
        self.wingspan =  self.__get_MandatoryParameterFromDict(dictData, "wingspan")
        self.fuselageWidth =  self.__get_MandatoryParameterFromDict(dictData, "fuselageWidth")
        self.planformShape =  self.__get_MandatoryParameterFromDict(dictData, "planformShape")

        if ((self.planformShape != 'elliptical') and\
            (self.planformShape != 'trapezoidal')):
            ErrorMsg("planformshape must be elliptical or trapezoidal")
            sys.exit(-1)

        if self.planformShape == 'elliptical':
            self.leadingEdgeCorrection = self.__get_MandatoryParameterFromDict(dictData, "leadingEdgeCorrection")
            self.tipSharpness =  self.__get_MandatoryParameterFromDict(dictData, "tipSharpness")
        else:
            self.leadingEdgeCorrection = 0.0
            self.tipSharpness = 0.0

        if (self.planformShape == 'elliptical') or\
           (self.planformShape == 'trapezoidal'):
            self.tipchord =  self.__get_MandatoryParameterFromDict(dictData, "tipchord")

        self.hingeLineAngle = self.__get_MandatoryParameterFromDict(dictData, "hingeLineAngle")
        self.hingeDepthRoot = self.__get_MandatoryParameterFromDict(dictData, "hingeDepthRoot")
        self.hingeDepthTip = self.__get_MandatoryParameterFromDict(dictData, "hingeDepthTip")
        self.dihedral = self.__get_MandatoryParameterFromDict(dictData, "dihedral")

        # get existing chord distribution, if any
        try:
            self.chordDistribution = dictData["chordDistribution"]
        except:
            # not found, initially calculate chord distribution
            WarningMsg("parameter \'chordDistribution\' not found, initializing chord distribution")

        # get airfoil- / section data
        self.airfoilTypes = self.__get_MandatoryParameterFromDict(dictData, 'airfoilTypes')
        self.airfoilPositions = self.__get_MandatoryParameterFromDict(dictData, 'airfoilPositions')
        self.airfoilReynolds = self.__get_MandatoryParameterFromDict(dictData, 'airfoilReynolds')
        self.flapGroups = self.__get_MandatoryParameterFromDict(dictData, 'flapGroup')

        # number of airfoils equals number of specified airfoil types
        self.numAirfoils = len(self.airfoilTypes)

        # check number of airfoils
        if (self.numAirfoils == 0):
            ErrorMsg("number of airfoils must be >= 1")
            exit(-1)

        # check if the above parameters have the same number of elements
        if ((self.numAirfoils != len(self.airfoilPositions)) or
            (self.numAirfoils != len(self.airfoilReynolds))):
            ErrorMsg("airfoilTypes, airfoilPositions and airfoilReynolds must have the same number of elements")
            exit(-1)

        # After all types are known, the number of user airfoils can be determined
        numUserAirfoils = self.get_numUserAirfoils()

        # check number of user-airfoils
        if (numUserAirfoils == 0):
            ErrorMsg("number of user-airfoils must be >= 1")
            exit(-1)

        # check if first airfoil is user-airfoil
        if (self.airfoilTypes[0] != "user"):
            ErrorMsg("type of first airfoils must \"user\"")
            exit(-1)

        # check if reynolds number of root airfoil was specified separately
        try:
            self.rootReynolds = dictData["rootReynolds"]
            # overwrite reynolds number of first airfoil
            self.airfoilReynolds[0] = self.rootReynolds
        except:
            # not specified.
            # check if there is a valid reynolds number specified for the first airfoil
            if (self.airfoilReynolds[0] == None):
                ErrorMsg("reynolds of first airfoils must not be \"None\"")
                exit(-1)
            else:
                # copy reynolds number of first airfoil to rootReynolds
                self.rootReynolds = self.airfoilReynolds[0]

        # get names and paths of user-defined airfoils
        self.userAirfoils = dictData["userAirfoils"]

        # check userAirfoil names against number
        numDefinedUserAirfoils = len(self.userAirfoils)
        if (numDefinedUserAirfoils < numUserAirfoils):
            ErrorMsg("%d airfoils have type \"user\", but only %d user-airfoils"\
            " were defined in \"user-airfoils\""\
             % (numUserAirfoils, numDefinedUserAirfoils))
            exit(-1)
        elif (numDefinedUserAirfoils > numUserAirfoils):
            WarningMsg("%d airfoils have type \"user\", but %d user-airfoils"\
            " were defined in \"user-airfoils\""\
             % (numUserAirfoils, numDefinedUserAirfoils))
            self.userAirfoils = self.userAirfoils[0:numUserAirfoils]

        # -------------- get optional parameters --------------------
        try:
            self.leadingEdgeOrientation = dictData["leadingEdgeOrientation"]
        except:
              NoteMsg("leadingEdgeOrientation not defined")

        try:
            self.interpolationSegments= dictData["interpolationSegments"]
        except:
              NoteMsg("interpolationSegments not defined")

        try:
            self.theme = dictData["theme"]
        except:
            NoteMsg("theme not defined")

        # get user-defined list of airfoil-names
        try:
            self.airfoilNames = dictData["airfoilNames"]
        except:
            NoteMsg("No user-defined airfoil names specified")
            self.airfoilNames = []

        try:
            self.airfoilBasicName = dictData["airfoilBasicName"]
        except:
             NoteMsg("No basic airfoil name specified")
             self.airfoilBasicName = None

        # if there are user defined airfoilnames, check if every airfoil has a
        # user defined name
        if ((len(self.airfoilNames) != self.numAirfoils) and
            (len(self.airfoilNames) != 0)):
            ErrorMsg("number of airfoilNames does not match the number of airfoils, which is %d" % self.numAirfoils)
            exit(-1)

        # if no basic airfoil name was defined, check if there are user defined arifoil names
        if ((len(self.airfoilNames) == 0) and (self.airfoilBasicName == None)):
            ErrorMsg("\"airfoilBasicName\" not defined and also \"airfoilNames\" not defined")
            exit(-1)

        # polar-generation feature
        try:
            self.polarReynolds = dictData["polar_Reynolds"]
            try:
                self.NCrit = dictData["polar_Ncrit"]
            except:
                NoteMsg("polar_Ncrit not defined, using default-value %f" %\
                  self.NCrit)
        except:
            NoteMsg("polar_Reynolds not defined, no Information for polar creation available")

        # evaluate additional boolean data
        self.isFin = self.__get_booleanParameterFromDict(dictData, "isFin", self.isFin)

        self.smoothUserAirfoils = self.__get_booleanParameterFromDict(dictData,
                                  "smoothUserAirfoils", self.smoothUserAirfoils)

        self.showQuarterChordLine = self.__get_booleanParameterFromDict(dictData,
                                  "showQuarterChordLine", self.showQuarterChordLine)

        self.showTipLine = self.__get_booleanParameterFromDict(dictData,
                                  "showTipLine", self.showTipLine)

        self.showHingeLine = self.__get_booleanParameterFromDict(dictData,
                                   "showHingeLine", self.showHingeLine)


    def write_toDict(self, dictData):
        '''Function that writes actual parameter values to a given dictionary'''
        # Clear Dictionary first
        dictData.clear()

        # Now export all parameters to empty dictionary.
        # Remove references / make real copy by using [:] (important!)
        dictData["planformName"] = self.planformName[:]
        dictData["rootchord"] = self.rootchord
        dictData["rootReynolds"] = self.airfoilReynolds[0]
        dictData["wingspan"] = self.wingspan
        dictData["fuselageWidth"] = self.fuselageWidth
        dictData["planformShape"] = self.planformShape
        dictData["tipSharpness"] = self.leadingEdgeCorrection
        dictData["tipSharpness"] = self.tipSharpness
        dictData["leadingEdgeCorrection"] = self.leadingEdgeCorrection
        dictData["tipchord"] = self.tipchord
        dictData["hingeLineAngle"] = self.hingeLineAngle
        dictData["hingeDepthRoot"] = self.hingeDepthRoot
        dictData["hingeDepthTip"] = self.hingeDepthTip
        dictData["dihedral"] = self.dihedral
        dictData['airfoilTypes'] = self.airfoilTypes[:]
        dictData['airfoilPositions'] = self.airfoilPositions[:]
        dictData['airfoilReynolds'] = self.airfoilReynolds[:]
        dictData['flapGroup'] = self.flapGroups[:]
        dictData["userAirfoils"] = self.userAirfoils[:]
        dictData["chordDistribution"] = self.chordDistribution[:]

        # -------------- set optional parameters --------------------
        dictData["leadingEdgeOrientation"] = self.leadingEdgeOrientation
        dictData["interpolationSegments"] = self.interpolationSegments
        dictData["theme"] = self.theme
        dictData["airfoilNames"] = self.airfoilNames[:]
        dictData["airfoilBasicName"] = self.airfoilBasicName
        dictData["polar_Reynolds"] = self.polarReynolds[:]
        dictData["polar_Ncrit"] = self.NCrit

        # set additional boolean data
        dictData["smoothUserAirfoils"] = self.smoothUserAirfoils
        dictData["isFin"] = self.isFin
        dictData["showQuarterChordLine"] = self.showQuarterChordLine
        dictData["showTipLine"] = self.showTipLine
        dictData["showHingeLine"] = self.showHingeLine

    def calculate_dependendValues(self):
        # calculate dependent parameters
        self.tipDepthPercent = (self.tipchord/self.rootchord)*100
        self.halfwingspan = (self.wingspan/2)-(self.fuselageWidth/2)

        # determine reynolds-number for root-airfoil
        self.rootReynolds = self.airfoilReynolds[0]

    def normalize_positions(self):
        for idx in range(len(self.airfoilPositions)):
            if self.airfoilPositions[idx] != None:
                self.airfoilPositions[idx] = self.airfoilPositions[idx] / self.halfwingspan

    def denormalize_positions(self):
        for idx in range(len(self.airfoilPositions)):
            if self.airfoilPositions[idx] != None:
                self.airfoilPositions[idx] = self.airfoilPositions[idx] * self.halfwingspan


    # calculate missing Re-numbers from positions
    def calculate_ReNumbers(self):
        num = len(self.airfoilReynolds)

        # loop over list of specified Re-numbers
        for idx in range(num):
            if self.airfoilReynolds[idx] == None:
                # for this position no reynolds-number has been specified.
                # calculate the number from postition now
                Re = self.get_ReFromPosition(self.airfoilPositions[idx])
                self.airfoilReynolds[idx] = int(round(Re ,0))


    def get_shapeParams(self):
        normalizedTipChord = self.tipDepthPercent / 100
        shapeParams = (normalizedTipChord, self.tipSharpness,
                       self.leadingEdgeCorrection)
        return (self.planformShape, shapeParams)


    # get the number of user defined airfoils
    def get_numUserAirfoils(self):
        num = 0
        for foilType in self.airfoilTypes:
            if (foilType == "user"):
                num = num + 1

        return num


################################################################################
#
# chordDistribution class
#
################################################################################
class chordDistribution:
    # class init
    def __init__(self):
        self.num_gridPoints = 16384
        self.num_controlPoints = 30
        self.normalizedGridPoints = []
        self.controlPoints = []

    def __elliptical_shape(self, x, shapeParams):
        (normalizedTipChord, tipSharpness, leadingEdgeCorrection) = shapeParams

        # calculate distance to tip, where rounding starts
        tipRoundingDistance = normalizedTipChord * tipSharpness

        # calculate actual distance to tip
        distanceToTip = 1.0 - x

       # calculate delta that will be added to pure ellipse
        if (distanceToTip > tipRoundingDistance):
            # add constant value, as we are far away from the tip
            delta = normalizedTipChord
        else:
            # add decreasing value according to quarter ellipse
            a = tipRoundingDistance
            x1 = tipRoundingDistance - distanceToTip
            b = normalizedTipChord
            radicand = (a*a)-(x1*x1)

            if radicand > 0:
                # quarter ellipse formula
                delta = (b/a) * np.sqrt(radicand)
            else:
                delta = 0

        # elliptical shaping of the wing plus additonal delta
        chord = (1.0-delta) * np.sqrt(1.0-(x*x)) + delta

        # correct chord with leading edge correction
        chord = chord - leadingEdgeCorrection * sin(interpolate(0.0, 1.0, 0.0, pi, x))

        return chord


    def __trapezoidal_shape(self, x, shapeParams):
        (normalizedTipChord, tipSharpness, leadingEdgeCorrection) = shapeParams

        chord = (1.0-x) + (normalizedTipChord * x)
        return chord


    def __calculate_chord(self, x, shape, shapeParams):
        if (shape == 'elliptical'):
                # elliptical shaping of the wing
                chord = self.__elliptical_shape(x, shapeParams)
        elif (shape == 'trapezoidal'):
            # trapezoidal shaping of the wing
            chord = self.__trapezoidal_shape(x, shapeParams)

        return chord


    def __calculate_shapeLength(self, shape, shapeParams):
        last_x = 0.0
        last_chord = 1.0
        totalDistance = 0.0
        num_points = 1024

        # calculate interval for setting up the grid
        delta_x = 1 / (num_points-1)

        for i in range(1, (num_points+1)):
            x = delta_x * (i-1)

            # normalized chord-length
            chord = self.__calculate_chord(x, shape, shapeParams)

            # distance to previous point that was stored
            totalDistance = totalDistance + calculate_distance(x, last_x, chord,
                                                               last_chord)
            last_x = x
            last_chord = chord

        return totalDistance


    def init_controlPoints(self, shape, shapeParams):
        # get total distance along shape
        totalDistance = self.__calculate_shapeLength(shape, shapeParams)

        # setup first control point of normalized chord distribution and the
        # distance between the points
        self.controlPoints = [(0.0, 1.0)]
        last_x = 0.0
        last_y = 1.0
        delta_x = 1 / (self.num_gridPoints-1)
        distDelta = totalDistance / (self.num_controlPoints-1)

        for i in range(1, (self.num_gridPoints + 1)):
            x = delta_x * (i-1)

            # normalized chord-length
            y = self.__calculate_chord(x, shape, shapeParams)

            # distance to last point, that was stored
            dist = calculate_distance(x, last_x, y, last_y)

            if (dist >= distDelta):
                # append new point to list of control points
                self.controlPoints.append((x, y))
                last_x = x
                last_y = y

        # append last point of normalized chord distribution
        self.controlPoints.append((1.0, 0.0))

    def get_controlPoints(self):
        return self.controlPoints

    def set_controlPoints(self, controlPoints):
        self.controlPoints = controlPoints

    # calculate a chord-distribution, which is normalized to root_chord = 1.0
    # half wingspan = 1
    def calculate_grid(self, shape, shapeParams):
        self.normalizedGridPoints.clear()
        # calculate interval for setting up the grid
        grid_delta = 1 / (self.num_gridPoints-1)
        self.normalizedGrid = []

        # calculate all Grid-chords
        for i in range(1, (self.num_gridPoints + 1)):
            # create new normalized grid
            grid = normalizedGrid()

            # calculate grid coordinates
            grid.y = grid_delta * (i-1)

            # pure elliptical shaping of the wing as a reference
            grid.referenceChord = np.sqrt(1.0-(grid.y*grid.y))

            # normalized chord-length
            grid.chord = self.__calculate_chord(grid.y, shape, shapeParams)

            # append section to section-list of wing
            self.normalizedGrid.append(grid)

    def get_normalizedGrid(self, idx):
        return self.normalizedGrid[idx]

    def get_numGridPoints(self):
        return self.num_gridPoints

    # get chordlength from position, according to the chord distribution
    def get_chordFromPosition(self, position):
        # valid position specified ?
        if (position == None):
            ErrorMsg("invalid position")
            return None

        # get chord from planform
        for gridData in self.normalizedGrid:
            if (gridData.y >= position):
                return gridData.chord
        ErrorMsg("no chordlength was found for position %f" % position)
        return None

    def plot(self, ax):
        # generate lists of x and y-coordinates
        normalizedHalfwingspan = []
        normalizedChord = []
        referenceChord = []

        for element in self.normalizedGrid:
            normalizedHalfwingspan.append(element.y)
            normalizedChord.append(element.chord)
            referenceChord.append(element.referenceChord)

        # plot reference chord (pure ellipse)
        ax.plot(normalizedHalfwingspan, referenceChord, color=cl_referenceChord,
                linewidth = lw_planform, solid_capstyle="round",
                label = "pure ellipse")

        # plot normalized chord that will be taken for planform generation
        ax.plot(normalizedHalfwingspan, normalizedChord, color=cl_normalizedChord,
                 linewidth = lw_planform, solid_capstyle="round",
                 label = "normalized chord")

##        # plot control points
##        pts = np.vstack([self.controlPoints])
##        x, y = pts.T
##        ax.scatter(x, y, color=cl_normalizedChord)

        # place legend
        ax.legend(loc='upper right', fontsize=fs_legend, labelcolor=cl_legend,
         frameon=False)


################################################################################
#
# planform class
#
################################################################################
class planform:
    # class init
    def __init__(self):
        self.num_gridPoints = 0
        self.grid = []
        self.hingeInnerPoint = 0
        self.hingeOuterPoint = 0
        self.hingeLineAngle = 0.0
        self.dihedral = 0.00
        self.wingArea = 0.0
        self.geometricalCenter = (0.0, 0.0)
        self.aspectRatio = 0.0

    def __calculate_wingArea(self):
        grid_delta_y = self.grid[1].y - self.grid[0].y
        center_x = 0.0
        center_y = 0.0
        self.wingArea = 0.0

        for element in self.grid:
            # sum up area of the grid elements
            area = (grid_delta_y*10 * element.chord*10)
            center_y = center_y + element.centerLine*area
            center_x = center_x + element.y*area

            # sum up area of the grid elements, which in the end will be half of
            # the wing area
            self.wingArea = self.wingArea + area

        # Calculate geometrical center of the halfwing
        center_x = center_x / self.wingArea
        center_y = center_y / self.wingArea
        self.geometricalCenter = (center_x, center_y)

        # calculate area of the whole wing
        self.wingArea = self.wingArea * 2.0

    # calculate planform-shape of the half-wing (high-resolution wing planform)
    def calculate(self, params:params, chordDistribution:chordDistribution):
        self.grid.clear()
        self.num_gridPoints = chordDistribution.get_numGridPoints()
        self.hingeInnerPoint = (1-(params.hingeDepthRoot/100))*params.rootchord

        # calculate tip-depth
        self.tipDepth = params.rootchord*(params.tipDepthPercent/100)

        # calculate the depth of the hinge at the tip
        tipHingeDepth = self.tipDepth *(params.hingeDepthTip/100)

        # calculate quarter-chord-lines
        rootQuarterChord = params.rootchord/4
        tipQuarterChord = self.tipDepth/4

        # hinge line angle: convert radian measure --> degree
        hingeLineAngle_radian = (params.hingeLineAngle/180) * pi

        # calculate hingeOuterPoint from hinge line angle
        AK = params.halfwingspan
        GK = tan(hingeLineAngle_radian)*AK
        self.hingeOuterPoint = self.hingeInnerPoint + GK

        # calculate interval for setting up the grid
        grid_delta_y = (params.halfwingspan / (self.num_gridPoints-1))

        # init areaCenter
        area_Center = 0.0

        # track maximum value of leading edge derivative
        LE_derivative_max = 0.0

        # track maximum value of hingeDepth
        hingeDepthPercent_max = 0.0

        # calculate all Grid-chords
        for i in range(1, (self.num_gridPoints + 1)):

            # Get normalized grid for chordlength calculation
            normalizedGrid = chordDistribution.get_normalizedGrid(i-1)
            normalizedChord = normalizedGrid.chord

            # create new grid
            grid = wingGrid()

            # calculate grid coordinates
            grid.y = grid_delta_y * (i-1)

            # chord-length
            grid.chord = params.rootchord * normalizedChord

            # calculate hingeDepth in percent at this particular point along the wing
            hingeDepth_y = interpolate(0.0, params.halfwingspan,
                                       params.hingeDepthRoot, params.hingeDepthTip,
                                       grid.y)

            # correction of leading edge for elliptical planform, avoid swept forward part of the wing
            #delta = self.leadingEdgeCorrection * sin(interpolate(0.0, self.halfwingspan, 0.0, pi, grid.y))#FIXME

            grid.hingeDepth = (hingeDepth_y/100)*grid.chord #+ delta FIXME
            grid.hingeLine = (self.hingeOuterPoint-self.hingeInnerPoint)/(params.halfwingspan) * (grid.y) + self.hingeInnerPoint
            grid.leadingEdge = grid.hingeLine -(grid.chord-grid.hingeDepth)

            # calculate trailing edge according to chordlength at this particular
            # point along the wing
            grid.trailingEdge = grid.leadingEdge + grid.chord

            # calculate centerLine, quarterChordLine
            grid.centerLine = grid.leadingEdge + (grid.chord/2)
            grid.quarterChordLine = grid.leadingEdge + (grid.trailingEdge-grid.leadingEdge)/4

            # Calculate derivative of Leading edge
            if (i>3):
                grid.LE_derivative = -1.0*(self.grid[i-2].leadingEdge - self.grid[i-3].leadingEdge) / (self.grid[i-2].y - self.grid[i-3].y)
            else:
                grid.LE_derivative = 0.0

            # Tracking of LE-derative Maximum-value
            if (grid.LE_derivative < LE_derivative_max):
                LE_derivative_max = grid.LE_derivative

            # calculate percentual hingeDepth
            grid.hingeDepthPercent = ((grid.trailingEdge - grid.hingeLine) / grid.chord) * 100.0

            # Tracking of hingeDepth maximum value
            if (grid.hingeDepthPercent > hingeDepthPercent_max):
                hingeDepthPercent_max = grid.hingeDepthPercent


            # append section to section-list of wing
            self.grid.append(grid)

        # calculate the area of the wing
        self.__calculate_wingArea()

        # calculate aspect ratio of the wing
        self.aspectRatio = params.wingspan*params.wingspan / (self.wingArea/100)

        # get geometrical center
        (center_x, center_y) = self.geometricalCenter

        # add offset of half of the fuselage-width to the y-coordinates
        for element in self.grid:
            element.y = element.y + params.fuselageWidth/2
            element.geometricalCenterLine = center_x

        #self.draw_LE_derivative() #FIXME Debug-plot

        return (LE_derivative_max, hingeDepthPercent_max)


    def find_grid(self, chord):
        for element in self.grid:
            if (element.chord <= chord):
              return element


################################################################################
#
# Wing class
#
################################################################################
class wing:
    # class init
    def __init__(self):
        # create instance of params
        self.params = params()

        # dictionary, that will store actual params in dictionary format
        self.paramsDict = {}

        # create instance of chordDistribution
        self.chordDistribution = chordDistribution()

        # create instance of planform
        self.planform = planform()

        # empty list of chords and sections
        self.chords = []
        self.sections = []

    def set_colours(self):
        global cl_background
        global cl_grid
        global cl_quarterChordLine
        global cl_geometricalCenterLine
        global cl_geoCenter
        global cl_hingeLine
        global cl_planform
        global cl_hingeLineFill
        global cl_planformFill
        global cl_sections
        global cl_userAirfoil
        global cl_optAirfoil
        global cl_infotext
        global cl_diagramTitle
        global cl_legend
        global cl_controlPoints
        global cl_normalizedChord
        params = self.params

        if params.theme == 'Light':
            # black and white theme
            cl_background = 'lightgray'
            cl_grid = 'black'
            cl_quarterChordLine = 'blue'
            cl_geometricalCenterLine = 'black'
            cl_geoCenter = 'black'
            cl_hingeLine = 'DeepSkyBlue'
            cl_planform = 'black'
            cl_hingeLineFill = 'DeepSkyBlue'
            cl_planformFill = 'darkgray'
            cl_sections = 'black'
            cl_userAirfoil = 'black'
            cl_optAirfoil = 'black'
            cl_infotext = 'black'
            cl_chordlengths = 'darkgray'
            cl_referenceChord = 'dark'
            cl_diagramTitle = 'darkgray'
            cl_legend = 'black'
            cl_normalizedChord = 'black'
            cl_controlPoints = 'red'
        elif params.theme == 'Dark':
            # dark theme
            cl_background = 'black'
            cl_grid = 'ghostwhite'
            cl_quarterChordLine = 'orange'
            cl_geometricalCenterLine = 'blue'
            cl_geoCenter = 'lightgray'
            cl_hingeLine = 'DeepSkyBlue'
            cl_hingeLineFill ='DeepSkyBlue'
            cl_planform = 'gray'
            cl_planformFill = 'lightgray'
            cl_sections = 'grey'
            cl_userAirfoil = 'DeepSkyBlue'
            cl_optAirfoil = 'orange'
            cl_infotext = 'DeepSkyBlue'
            cl_chordlengths = 'darkgray'
            cl_referenceChord = 'gray'
            cl_diagramTitle = 'dimgray'
            cl_legend = 'ghostwhite'
            cl_normalizedChord = 'orange'
            cl_controlPoints = 'red'
        else:
            ErrorMsg("undefined Theme: %s" %params.theme)

    # compose a name from the airfoil basic name and the Re-number
    def set_AirfoilNamesFromRe(self):
        params = self.params
        # loop over all airfoils (without tip and fuselage section)
        for idx in range(params.numAirfoils):
            Re = params.airfoilReynolds[idx]
            airfoilName = (params.airfoilBasicName + "-%s.dat") % get_ReString(Re)
            params.airfoilNames.append(airfoilName)


    # set missing airfoilnames from basic name and Re-number
    def set_AirfoilNames(self):
        params = self.params
        if (len(params.airfoilNames) == 0):
            # list is empty and has to be created
            self.set_AirfoilNamesFromRe()

        # check if the .dat ending was appended to all airfoils.
        # if not, append the ending
        for idx in range(params.numAirfoils):
            if (params.airfoilNames[idx].find('.dat')<0):
                params.airfoilNames[idx] = params.airfoilNames[idx] +'.dat'


    def insert_fuselageData(self):
        params = self.params
        params.airfoilNames.insert(0, params.airfoilNames[0])

        # root airfoil must be of type "user", so always insert user-airfoil
        params.userAirfoils.insert(0, params.userAirfoils[0])
        params.airfoilTypes.insert(0, params.airfoilTypes[0])

        # section has same chord, same reynolds
        self.chords.insert(0, self.chords[0])
        params.airfoilPositions.insert(0, 0.0)
        params.airfoilReynolds.insert(0, params.airfoilReynolds[0])


    def insert_tipData(self):
        params = self.params
        params.airfoilNames.append(params.airfoilNames[-1])
        params.airfoilTypes.append(params.airfoilTypes[-1])
        params.airfoilPositions.append(params.wingspan/2)

        # is last airfoil of type "user" ?
        if params.airfoilTypes[-1] == "user":
            # yes, so append user-airfoil
            params.userAirfoils.append(params.userAirfoils[-1])

        reynolds = (params.tipchord / self.chords[-1]) * params.airfoilReynolds[-1]
        params.airfoilReynolds.append(int(round(reynolds,0)))
        self.chords.append(params.tipchord)

    # get the number of user defined airfoils
    def get_numUserAirfoils(self):
        num = 0
        for foilType in self.airfoilTypes:
            if (foilType == "user"):
                num = num + 1

        return num

    def apply_params(self):
        # first clean up in case this function was repeatedly called
        self.chords.clear()
        self.sections.clear()

        params = self.params

        # start modifying and applying params now
        params.calculate_dependendValues()
        params.denormalize_positions()

        # get basic shape parameters
        (shape, shapeParams) = params.get_shapeParams()

        # setup chordDistribution
        self.chordDistribution.calculate_grid(shape, shapeParams)

        # calculate planform
        self.planform.calculate(self.params, self.chordDistribution)

        # calculate Re-numbers, the chordlengths of the airfoils and the sections
        self.calculate_ReNumbers()
        self.calculate_chordlengths()
        self.calculate_positions() # must be done after chordlenghts ar known
        self.set_AirfoilNames()

        # if there is a fuselage, insert data for the fuselage section
        # at the beginning of the list.
        if self.fuselageIsPresent():
            self.insert_fuselageData()

        # always insert data for the wing tip
        self.insert_tipData()

        # calculate the sections now
        self.calculate_sections()

        # assign the flap groups to the different sections
        self.assignFlapGroups()

        # set colours according to selected theme
        self.set_colours()

    # set basic data of the wing
    def set_Data(self, dictData):
        params = self.params

        # read initial parameters from dictionary
        params.read_fromDict(dictData)

        # are there control-points?
        if (params.chordDistribution != None):
            self.chordDistribution.set_controlPoints(params.chordDistribution)
        else:
            # get basic shape parameters and init control points
            (shape, shapeParams) = params.get_shapeParams()
            self.chordDistribution.init_controlPoints(shape, shapeParams)
            # writeback control points to params
            controlPoints = self.chordDistribution.get_controlPoints()
            params.chordDistribution = controlPoints[:]

        # export initial params to dictionary
        params.write_toDict(self.paramsDict)

        # now apply params which will modify the content of params
        self.apply_params()

    # get name of the user defined airfoil, as it will appear in the planform
    def get_UserAirfoilName(self, userAirfoil_idx):
        userAirfol_num = 0
        # loop through all airfoils
        for idx in range(len(self.airfoilTypes)):
            # Is the airfoil a user-defined airfoil ?
            if self.airfoilTypes[idx] == "user":
                # was the desired index found?
                if (userAirfoil_idx == userAirfol_num):
                    # Found
                    return self.airfoilNames[idx]
                else:
                    # only increment number of user-airfoil
                    userAirfol_num = userAirfol_num + 1

        # nothing was found
        return None


    # find planform-values for a given chord-length
    def find_PlanformData(self, chord):
        return self.planform.find_grid(chord)
        for element in self.grid:
            if (element.chord <= chord):
              return element


    # copy planform-values to section
    def copy_PlanformDataToSection(self, grid, section):
        params = self.params
        section.y = grid.y
        section.chord = grid.chord
        section.hingeDepth = grid.hingeDepth
        section.hingeLine = grid.hingeLine
        section.trailingEdge = grid.trailingEdge
        section.leadingEdge = grid.leadingEdge
        section.quarterChordLine = grid.quarterChordLine
        section.geometricalCenterLine = grid.geometricalCenterLine
        section.dihedral = params.dihedral

        # set Re of the section (only for proper airfoil naming)
        section.Re = (section.chord / params.rootchord) * params.rootReynolds


    # sets the airfoilname of a section
    def set_AirfoilName(self, section):
        params = self.params
        try:
            section.airfoilName = params.airfoilNames[section.number-1]
        except:
            ErrorMsg("No airfoilName found for section %d" % section.number)

    def set_lastSectionAirfoilName(self, section):
        params = self.params
        section.airfoilName = params.airfoilNames[section.number-2]

    def get_params(self):
        return self.paramsDict

    def get_distributionParams(self):
        distributionParams = (self.params.planformShape,
        self.params.tipDepthPercent, self.params.tipSharpness,
        self.params.leadingEdgeCorrection)
        return distributionParams


    # get Re from position, according to the planform-data
    def get_ReFromPosition(self, position):
        chordRatio = self.chordDistribution.get_chordFromPosition(position)
        if (chordRatio != None):
            Re = self.params.airfoilReynolds[0] * chordRatio
            return Re
        else:
            ErrorMsg("no Re could not be caclulated for position %f" % position)
            return None


    # get chordlength from position, according to the planform-data
    def get_chordFromPositionOrReynolds(self, position, reynolds):
        params = self.params
        # valid reynolds number specified ?
        if (reynolds != None):
            # calculate chord from ratio reynolds to rootReynolds
            return (reynolds / params.rootReynolds) * params.rootchord

        # valid position specified ?
        elif (position != None):
            # get chord from chord distribution
            chordRatio = self.chordDistribution.get_chordFromPosition(position)
            chord = chordRation * params.rootchord

        # nothing was found
        ErrorMsg("position or reynolds not found inside planform")
        NoteMsg("position was: %f, reynolds was %d" % (position, reynolds))
        return None


    # calculate all chordlenghts from the list of airfoil positions
    # and the given planform-data
    def calculate_chordlengths(self):
        self.chords.clear()
        params = self.params
        for idx in range(len(params.airfoilPositions)):
            position = params.airfoilPositions[idx]
            reynolds = params.airfoilReynolds[idx]
            chord = self.get_chordFromPositionOrReynolds(position, reynolds)
            self.chords.append(chord)

    def calculate_positions(self):
        params = self.params
        for idx in range(len(params.airfoilPositions)):
            if params.airfoilPositions[idx] == None:
                # no position defined yet, calculate now
                chord = self.chords[idx]
                grid = self.planform.find_grid(chord)
                params.airfoilPositions[idx] = grid.y


    # calculate missing Re-numbers from positions
    def calculate_ReNumbers(self):
        num = len(self.params.airfoilReynolds)

        # loop over list of specified Re-numbers
        for idx in range(num):
            if self.params.airfoilReynolds[idx] == None:
                # for this position no reynolds-number has been specified.
                # calculate the number from postition now
                Re = self.get_ReFromPosition(self.params.airfoilPositions[idx])
                self.params.airfoilReynolds[idx] = int(round(Re ,0))


    # determine weather a fuselage shall be used
    def fuselageIsPresent(self):
        # check, if a fuselageWidth > 0 was defined
        if self.params.fuselageWidth >= 0.0001:
            return True
        else:
            return False

    def getFlapPartingLines(self):
        params = self.params
        flapPositions_x = []
        flapPositions_y =[]
        flapPositions_x_left =[]
        flapPositions_x_right =[]

        # As we have a projected drawing of the wing, we must consider the
        # projection factor
        proj_fact = cos(params.dihedral*pi/180.0)
        proj_halfwingSpan = params.halfwingspan * proj_fact

        sections = self.sections
        numSections = len(sections)
        actualFlapGroup = 0

        # Calculate zero Axis (center of the wing)
        zeroAxis = proj_halfwingSpan + params.fuselageWidth/2

        # check all sections
        for idx in range (0, numSections):
            # Change of Flap-Group ? -->Parting line
            if (actualFlapGroup != sections[idx].flapGroup):
                # determine x_pos to zeroAxis
                x_pos_rightZeroAxis = sections[idx].y * proj_fact
                # Shift by offset of zeroAxis
                x_pos_right = x_pos_rightZeroAxis + zeroAxis
                x_pos_leftZeroAxis = -1.0*x_pos_rightZeroAxis
                x_pos_left = x_pos_leftZeroAxis + zeroAxis
                x_tupel_left = (x_pos_left, x_pos_left)
                x_tupel_right = (x_pos_right, x_pos_right)
                y_tupel = (sections[idx].hingeLine, sections[idx].trailingEdge)
                flapPositions_x_right.append(x_tupel_right)
                flapPositions_x_left.append(x_tupel_left)
                flapPositions_y.append(y_tupel)

            actualFlapGroup = sections[idx].flapGroup

        # join all values
        flapPositions_x = flapPositions_x_left + flapPositions_x_right
        flapPositions_y = flapPositions_y + flapPositions_y

        return (flapPositions_x, flapPositions_y)

    # adds a section using given grid-values
    def add_sectionFromGrid(self, grid):
         # create new section
        section = wingSection()

        # append section to section-list of wing
        self.sections.append(section)

        # set number of the section
        section.number = len(self.sections)

        # copy grid-coordinates to section
        self.copy_PlanformDataToSection(grid, section)

        # set the airfoil-Name
        self.set_AirfoilName(section)


    # adds a section using given chord
    def add_sectionFromChord(self, chord):
        # find grid-values matching the chordlength of the section
        grid = self.find_PlanformData(chord)

        if (grid == None):
            ErrorMsg("chord-length %f not found in planform-data\n" % chord)
            exit(-1)
        else:
            self.add_sectionFromGrid(grid)


    # add an own section for the fuselage and use rootchord
    def add_fuselageSection(self):
        # get the root grid-values
        grid = deepcopy(self.planform.grid[0])

        # set offset to zero so the section will start exactly in the center
        grid.y = 0

        # add section now
        self.add_sectionFromGrid(grid)

    def remove_fuselageSection(self):
       del(self.sections[0])

    # calculate all sections of the wing, oriented at the grid
    def calculate_sections(self):
        self.sections.clear()
        # check if fuselageWidth is > 0
        if self.fuselageIsPresent():
            # first add section for fuselage
            self.add_fuselageSection()
            startIdx = 1
        else:
            startIdx = 0

        # create all sections, according to the precalculated chords
        for chord in self.chords[startIdx:]:
            startIdx = 0
            # add section according to chord
            self.add_sectionFromChord(chord)


    # function to interpolate within sections. This is very useful to get a very
    # accurate calculation of lift-distribution for elliptical wings
    # e.g in FLZ-Vortex or XFLR5.
    # Also other calculations, like wing area, aspect ratio etc. get
    # more accurate
    def interpolate_sections(self):
        params = self.params
        if params.interpolationSegments < 1:
            self.interpolated_params = None
            # nothing to do
            return

        self.interpolated_params = interpolated_params(params)
        NoteMsg("Interpolation of sections was requested, interpolating each section with"\
                " additional %d steps" % params.interpolationSegments)

        new_positions = []
        new_chords = []
        new_airfoilNames = []
        new_airfoilTypes = []
        new_flapGroups = []

        num = len(params.airfoilPositions)

        if self.fuselageIsPresent():
            # do not interpolate fuselage section
            startIdx = 1
            new_positions.append(params.airfoilPositions[0])
            new_chords.append(params.chords[0])
            new_airfoilNames.append(params.airfoilNames[0])
            new_airfoilTypes.append(params.airfoilTypes[0])
            # assinging flapGroup of fuselage not necessary, will be done
            # in assignFlapGroups!
        else:
            startIdx = 0

        for idx in range(startIdx, num-1):
            # determine interpolation-distance
            posDelta = params.airfoilPositions[idx+1]-params.airfoilPositions[idx]
            posDelta = posDelta / float(params.interpolationSegments+1)

            # add existiong position and name
            new_positions.append(params.airfoilPositions[idx])
            new_chords.append(params.chords[idx])
            new_airfoilNames.append(params.airfoilNames[idx])
            new_airfoilTypes.append(params.airfoilTypes[idx])
            new_flapGroups.append(params.flapGroups[idx])

            # add interpolated position and name
            for n in range(params.interpolationSegments):
                position = params.airfoilPositions[idx] + (float(n+1)*posDelta)
                new_positions.append(position)
                chordRatio = self.chordDistribution.get_chordFromPosition(position)
                chord = chordRatio * params.rootchord
                new_chords.append(chord)
                new_airfoilNames.append(params.airfoilNames[idx])
                new_flapGroups.append(params.flapGroups[idx])
                new_airfoilTypes.append("blend")

        # set Tip values
        new_positions.append(params.airfoilPositions[-1])
        new_chords.append(params.chords[-1])
        new_airfoilNames.append(params.airfoilNames[-1])
        new_airfoilTypes.append(params.airfoilTypes[-1])
        # assigning of flapGroup for tip not  not necessary, will be done in
        # assignFlapGroups!

        # assign interpolated lists
        params.interpolated_airfoilPositions = new_positions
        params.interpolated_airfoilTypes = new_airfoilTypes
        params.interpolated_airfoilNames = new_airfoilNames
        params.interpolated_chords = new_chords
        params.interpolated_flapGroups = new_flapGroups

        # calculate the interpolated sections
        self.calculate_sections()

        # do not forget: assign the flap groups to the different sections
        self.assignFlapGroups()

    # assigns the user defined flap groups to the different sections
    def assignFlapGroups(self):
        params = self.params
        if self.fuselageIsPresent():
            # add flapGroup 0 at the beginning of the list
            params.flapGroups.insert(0,0)

        # append flapGroup for the tip section, which is the same as for the section before
        params.flapGroups.append(params.flapGroups[-1])
        num = len(self.sections)
        num_flap_groups = len(params.flapGroups)

        if (num_flap_groups != num):
            ErrorMsg("number of sections %d != number of flap groups %d" %(num, num_flap_groups))
        else:
            # assign flap groups now
            for idx in range (len(self.sections)):
                self.sections[idx].flapGroup = params.flapGroups[idx]

    # get color for plotting
    def get_colorFromAirfoilType(self, airfoilType):
        if (airfoilType == 'user'):
            color = cl_userAirfoil
        elif (airfoilType == 'opt'):
            color = cl_optAirfoil
        else:
            color = cl_sections

        return color


    def plot_PlanformShape(self, ax):
        params = self.params

        # create empty lists
        xValues = []
        leadingEdge = []
        trailingeEge = []
        hingeLine = []
        quarterChordLine = []
        geometricalCenterLine = []

        # setup empty lists for new tick locations
        x_tick_locations = []
        y_tick_locations = [params.rootchord]

        grid = self.planform.grid
        for element in grid:
            # build up list of x-values
            xValues.append(element.y)

            # build up lists of y-values
            leadingEdge.append(element.leadingEdge)
            quarterChordLine.append(element.quarterChordLine)
            geometricalCenterLine.append(element.geometricalCenterLine)
            hingeLine.append(element.hingeLine)
            trailingeEge.append(element.trailingEdge)

        # setup root- and tip-joint
        trailingeEge[0] = leadingEdge[0]
        trailingeEge[-1] = leadingEdge[-1]

        # compose labels for legend
        labelHingeLine = ("hinge line (%.1f %% / %.1f %%)" %
                           (params.hingeDepthRoot, params.hingeDepthTip))

        # plot quarter-chord-line
        if (params.showQuarterChordLine == True):
            ax.plot(xValues, quarterChordLine, color=cl_quarterChordLine,
              linestyle = ls_quarterChordLine, linewidth = lw_quarterChordLine,
              solid_capstyle="round", label = "quarter-chord line")

        # plot hinge-line
        if (params.showHingeLine == True):
            ax.plot(xValues, hingeLine, color=cl_hingeLine,
              linestyle = ls_hingeLine, linewidth = lw_hingeLine,
              solid_capstyle="round", label = labelHingeLine)

        # plot geometrical center
        center = self.planform.geometricalCenter
        radius = params.rootchord/20
        bullseye(center, radius, cl_geoCenter, ax)

        # plot the planform last
        ax.plot(xValues, leadingEdge, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")
        ax.plot(xValues, trailingeEge, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")

        # place legend
        ax.legend(loc='upper right', fontsize=fs_legend, labelcolor=cl_legend,
         frameon=False)

        # show grid
        ax.grid(True)

        # both axes shall be equal
        ax.axis('equal')

        # revert y-axis on demand
        if (params.leadingEdgeOrientation == 'up'):
            ax.set_ylim(ax.get_ylim()[::-1])


    def plot_FlapDistribution(self, ax):
        '''plots a diagram that shows distribution of flaps and also hinge depth'''
        params = self.params

        # create empty lists
        xValues = []
        leadingEdge = []
        trailingeEge = []
        hingeLine = []
        quarterChordLine = []
        geometricalCenterLine = []

        # setup empty lists for new tick locations
        x_tick_locations = []
        y_tick_locations = [params.rootchord]

        grid = self.planform.grid
        for element in grid:
            #build up list of x-values
            xValues.append(element.y)

            #build up lists of y-values
            leadingEdge.append(element.leadingEdge)
            quarterChordLine.append(element.quarterChordLine)
            geometricalCenterLine.append(element.geometricalCenterLine)
            hingeLine.append(element.hingeLine)
            trailingeEge.append(element.trailingEdge)

        # setup root- and tip-joint
        trailingeEge[0] = leadingEdge[0]
        trailingeEge[-1] = leadingEdge[-1]

        # compose labels for legend
        labelHingeLine = ("hinge line (%.1f %% / %.1f %%)" %
                           (params.hingeDepthRoot, params.hingeDepthTip))

        # plot quarter-chord-line
        if (params.showQuarterChordLine == True):
            ax.plot(xValues, quarterChordLine, color=cl_quarterChordLine,
              linestyle = ls_quarterChordLine, linewidth = lw_quarterChordLine,
              solid_capstyle="round", label = "quarter-chord line")

        # plot hinge-line
        if (params.showHingeLine == True):
            ax.plot(xValues, hingeLine, color=cl_hingeLine,
              linestyle = ls_hingeLine, linewidth = lw_hingeLine,
              solid_capstyle="round", label = labelHingeLine)

        # plot geometrical center
        center = self.planform.geometricalCenter
        radius = params.rootchord/20
        bullseye(center, radius, cl_geoCenter, ax)

        # plot the planform last
        ax.plot(xValues, leadingEdge, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")
        ax.plot(xValues, trailingeEge, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")

        # place legend
        ax.legend(loc='upper right', fontsize=fs_legend, labelcolor=cl_legend,
           frameon=False)

        # show grid
        ax.grid(True)

        # both axes shall be equal
        ax.axis('equal')

        # revert y-axis on demand
        if (params.leadingEdgeOrientation == 'up'):
            ax.set_ylim(ax.get_ylim()[::-1])

    # plot planform of the half-wing
    def plot_AirfoilDistribution(self, ax):
        params = self.params

        # create empty lists
        xValues = []
        leadingEdge = []
        trailingeEge = []

        # setup empty lists for new tick locations
        x_tick_locations = []

        # plot sections in reverse order
        idx = len(params.airfoilTypes) - 1

        # check if there is a fuselage section
        if self.fuselageIsPresent():
            # skip fuselage section
            sectionsList = self.sections[1:]
        else:
            # plot all sections
            sectionsList = self.sections

        # compose labels for airfoil types
        label_user =  'airfoiltype \'user\''
        label_blend = 'airfoiltype \'blend\''
        label_opt = 'airfoiltype \'opt\''

        for element in reversed(sectionsList):
            # determine type of airfoil of this section
            try:
                airfoilType = params.airfoilTypes[idx]
            except:
                airfoilType = 'blend'

            # get labeltext
            if (airfoilType == 'user'):
                if label_user != None:
                    labelText = label_user[:]
                    label_user = None
                else:
                    labelText = None
            elif (airfoilType == 'opt'):
                if label_opt != None:
                    labelText = label_opt[:]
                    label_opt = None
                else:
                    labelText = None
            else:
                if label_blend != None:
                    labelText = label_blend[:]
                    label_blend = None
                else:
                    labelText = None

            # get labelcolor, which will also be the color of the plotted line
            labelColor = self.get_colorFromAirfoilType(airfoilType)

            ax.plot([element.y, element.y] ,[element.leadingEdge, element.trailingEdge],
            color=labelColor, linestyle = ls_sections, linewidth = lw_sections,
            solid_capstyle="round", label = labelText)

            # determine x and y Positions of the labels
            xPos = element.y
            if (params.leadingEdgeOrientation == 'up'):
                yPosChordLabel = element.trailingEdge
                yPosOffsetSectionLabel = 32
            else:
                yPosChordLabel = element.leadingEdge
                yPosOffsetSectionLabel = -32

            yPosSectionLabel = element.leadingEdge

            # plot label for chordlength of section
            try:
                text = ("%d mm" % int(round(element.chord*1000)))
            except:
                text = ("0 mm" )
                ErrorMsg("label for chordlength of section could not be plotted")

            ax.annotate(text,
            xy=(xPos, yPosChordLabel), xycoords='data',
            xytext=(2, 5), textcoords='offset points', color = cl_chordlengths,
            fontsize=fs_infotext, rotation='vertical')


            # plot label for airfoil-name / section-name
            text = ("%s" % (remove_suffix(element.airfoilName,'.dat')))
            props=dict(arrowstyle="-", connectionstyle= "angle,angleA=-90,angleB=30,rad=10",
             color=labelColor)

            ax.annotate(text,
            xy=(xPos, yPosSectionLabel), xycoords='data',
            xytext=(8, yPosOffsetSectionLabel), textcoords='offset points',
            color = labelColor,fontsize=fs_infotext, rotation='vertical', arrowprops=props)

            # append position of section to x-axis ticks
            x_tick_locations.append(xPos)
            idx = idx - 1

        # set new ticks for the x-axis according to the positions of the sections
        ax.set_xticks(x_tick_locations)

        # set new fontsize of the x-tick labels
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(fs_ticks)
            tick.label.set_rotation('vertical')

        # set new fontsize of the y-tick labels
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(fs_ticks)

        grid = self.planform.grid
        for element in grid:
            # build up list of x-values
            xValues.append(element.y)

            # build up lists of y-values
            leadingEdge.append(element.leadingEdge)
            trailingeEge.append(element.trailingEdge)

        # setup root- and tip-joint
        trailingeEge[0] = leadingEdge[0]
        trailingeEge[-1] = leadingEdge[-1]

        # plot the planform last
        ax.plot(xValues, leadingEdge, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")
        ax.plot(xValues, trailingeEge, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")

        # plot additional point (invisible) to expand the y-axis and
        # get the labels inside the diagram
        ax.plot(xValues[0], -1*(params.rootchord/2))

        # place legend
        ax.legend(loc='upper right', fontsize=fs_legend, labelcolor=cl_legend,
         frameon=False)

        # show grid
        ax.grid(True)

        # both axes shall be equal
        ax.axis('equal')

        # revert y-axis on demand
        if (params.leadingEdgeOrientation == 'up'):
            ax.set_ylim(ax.get_ylim()[::-1])


    # plot planform of the complete wing
    def plot_WingPlanform(self, ax):
        params = self.params

        #create empty lists
        xValues = []
        xValuesLeft = []
        xValuesRight = []
        leadingEdge = []
        trailingEdge = []
        hingeLine = []
        leadingEdgeLeft = []
        trailingEdgeLeft = []
        hingeLineLeft = []
        leadingEdgeRight = []
        trailingEdgeRight = []
        hingeLineRight = []

        # determine factor for projection of the wing according the dihedral
        proj_fact = cos(params.dihedral*pi/180.0)

        # Halfwingspan already without fuselage
        proj_halfwingSpan = params.halfwingspan * proj_fact

        # Caution, fuselageWidth does not change due to projection
        proj_wingspan = (2*proj_halfwingSpan) + params.fuselageWidth

        # build up list of x-values,
        # first left half-wing
        grid = self.planform.grid
        for element in grid:
            proj_y = (element.y- (params.fuselageWidth/2)) * proj_fact
            xVal = proj_y#-(self.fuselageWidth/2)
            #xValues.append(xVal)
            xValuesLeft.append(xVal)

        # offset for beginning of right half-wing
        xOffset = proj_halfwingSpan + params.fuselageWidth

        # center-section / fuselage (x)
        Left_x = xValuesLeft[-1]
        Right_x = Left_x + params.fuselageWidth
        leftWingRoot_x = (Left_x, Left_x)
        rightWingRoot_x = (Right_x, Right_x)

        # right half-wing (=reversed right-half-wing)
        for element in grid:
            proj_y = (element.y - (params.fuselageWidth/2)) * proj_fact
            xVal = proj_y + xOffset
            xValues.append(xVal)
            xValuesRight.append(xVal)

        # build up lists of y-values
        # left half wing
        for element in reversed(grid):
            leadingEdgeLeft.append(element.leadingEdge)
            hingeLineLeft.append(element.hingeLine)
            trailingEdgeLeft.append(element.trailingEdge)

        # center-section / fuselage (y)
        #wingRoot_y = (leadingEdgeLeft[lastElement],trailingEdgeLeft[lastElement])
        wingRoot_y = (leadingEdgeLeft[-1],trailingEdgeLeft[-1])

        # right half wing
        for element in grid:
            leadingEdgeRight.append(element.leadingEdge)
            hingeLineRight.append(element.hingeLine)
            trailingEdgeRight.append(element.trailingEdge)

        # setup root- and tip-joint
        trailingEdgeLeft[0] = leadingEdgeLeft[0]
        trailingEdgeRight[-1] = leadingEdgeRight[-1]

        # get flap parting lines
        (flapPositions_x, flapPositions_y) = self.getFlapPartingLines()

        # plot the flap parting lines
        numLines = len(flapPositions_x)
        for idx in range(numLines):
            ax.plot(flapPositions_x[idx], flapPositions_y[idx],
            color=cl_hingeLine, linewidth = lw_hingeLine, solid_capstyle="round")

        # plot the hingeline
        ax.plot(xValuesLeft, hingeLineLeft, color=cl_hingeLine,
                linewidth = lw_hingeLine, solid_capstyle="round")
        ax.plot(xValuesRight, hingeLineRight, color=cl_hingeLine,
                linewidth = lw_hingeLine, solid_capstyle="round")

        # plot the planform last
        ax.plot(xValuesLeft, leadingEdgeLeft, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")
        ax.plot(xValuesRight, leadingEdgeRight, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")

        ax.plot(xValuesLeft, trailingEdgeLeft, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")
        ax.plot(xValuesRight, trailingEdgeRight, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")

        # center-section
        ax.plot(leftWingRoot_x, wingRoot_y, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")

        ax.arrow(proj_wingspan/2, 0.0, 0.0, -1*(params.rootchord/3),head_width=params.fuselageWidth/4)

        ax.plot(rightWingRoot_x, wingRoot_y, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")

        # both axes shall be equal
        ax.axis('equal')

        # revert y-axis on demand
        if (params.leadingEdgeOrientation == 'up'):
            ax.set_ylim(ax.get_ylim()[::-1])

        # plot hinge-line
##        if (self.showHingeLine == 'true'):
##            ax.plot(xValuesLeft, hingeLine, color=cl_hingeLine,
##              linestyle = ls_hingeLine, linewidth = lw_hingeLine,
##              solid_capstyle="round")

        # fill the wing
        ax.fill_between(xValuesLeft, leadingEdgeLeft, hingeLineLeft, color=cl_planformFill, alpha=0.4)
        ax.fill_between(xValuesLeft, hingeLineLeft, trailingEdgeLeft, color=cl_hingeLineFill, alpha=0.4)
        ax.fill_between(xValuesRight, leadingEdgeRight, hingeLineRight, color=cl_planformFill, alpha=0.4)
        ax.fill_between(xValuesRight, hingeLineRight, trailingEdgeRight, color=cl_hingeLineFill, alpha=0.4)

        # setup list for new x-tick locations
        new_tick_locations = [0.0, proj_halfwingSpan, (proj_halfwingSpan + params.fuselageWidth/2),
                             (proj_halfwingSpan + params.fuselageWidth), proj_wingspan]

        # set new ticks for the x-axis according to the positions of the sections
        ax.set_xticks(new_tick_locations)

        # set new fontsize of the x-tick labels
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(fs_ticks)
            tick.label.set_rotation('vertical')

        # set new fontsize of the y-tick labels
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(fs_ticks)

    def draw_LE_derivative(self):
        # set background style
        plt.style.use(cl_background)

        # customize grid
        plt.grid(True, color='dimgrey',  linestyle='dotted', linewidth=0.4)

        x = []
        y = []

        for element in self.grid:
            x.append(element.y)
            if (element.LE_derivative > 0.0):
                y.append(element.LE_derivative)
            else:
                y.append(0.0)


        plt.plot(x, y, color=cl_normalizedChord,
                linewidth = lw_planform, solid_capstyle="round",
                label = "LE derivative")

        # maximize window
        figManager = plt.get_current_fig_manager()
        try:
            figManager.window.Maximize(True)
        except:
            try:
                figManager.window.state('zoomed')
            except:
                pass

        # show diagram
        plt.show()



##    def getFigure(self):
##        # set 'dark' style
##        plt.style.use('dark_background')
##
##        # setup subplots
##        fig, (upper,lower) = plt.subplots(2,1)
##
##        # compose diagram-title
##        wingspan_mm = int(round(self.wingspan*1000))
##        text = "\"%s\"\n wingspan: %d mm, area: %.2f dm², aspect ratio: %.2f, root-tip sweep: %.2f°\n"\
##         % (self.planformName, wingspan_mm, self.area, self.aspectRatio, self.rootTipSweep)
##
##        fig.suptitle(text, fontsize = 12, color="darkgrey", **csfont)
##
##        # first figure, display detailed half-wing
##        self.plot_AirfoilDistribution(upper)
##
##        # second figure, display
##        self.plot_AirfoilDistribution(lower)
##
##        return fig

    def draw_diagram(self, diagramType, ax, x_limits, y_limits):
        if diagramType == diagTypes[0]:
            self.chordDistribution.plot(ax)
        elif diagramType == diagTypes[1]:
            self.plot_PlanformShape(ax)
        elif diagramType == diagTypes[2]:
            self.plot_FlapDistribution(ax)
        elif diagramType == diagTypes[3]:
            self.plot_AirfoilDistribution(ax)
        elif diagramType == diagTypes[4]:
            self.plot_WingPlanform(ax)

        else:
            ErrorMsg("undefined diagramtype")

################################################################################
# find the wing in the XML-tree
def get_wing(root, wingFinSwitch):
    for wing in root.iter('wing'):
        for XMLwingFinSwitch in wing.iter('isFin'):
            # convert string to boolean value
            if (XMLwingFinSwitch.text == 'true') or (XMLwingFinSwitch.text == 'True'):
                value = True
            else:
                value = False

            # check against value of wingFinswitch
            if (value == wingFinSwitch):
                return wing


# insert the planform-data into XFLR5-xml-file
def insert_PlanformDataIntoXFLR5_File(data, inFileName, outFileName):

    # basically parse the XML-file
    tree = ET.parse(inFileName)

    # get root of XML-tree
    root = tree.getroot()

    # find wing-data
    wing = get_wing(root, data.isFin)

    if (wing == None):
        ErrorMsg("wing not found\n")
        return

    # find sections-data-template
    for sectionTemplate in wing.iter('Sections'):
        # copy the template
        newSection = deepcopy(sectionTemplate)

        # remove the template
        wing.remove(sectionTemplate)

    # write the new section-data to the wing
    for section in data.sections:
        # copy the template
        newSection = deepcopy(sectionTemplate)

        # enter the new data
        for yPosition in newSection.iter('y_position'):
            # convert float to text
            yPosition.text = str(section.y)

        for chord in newSection.iter('Chord'):
            # convert float to text
            chord.text = str(section.chord)

        for xOffset in newSection.iter('xOffset'):
            # convert float to text
            xOffset.text = str(section.leadingEdge)

        for dihedral in newSection.iter('Dihedral'):
            # convert float to text
            dihedral.text = str(section.dihedral)

        for foilName in newSection.iter('Left_Side_FoilName'):
            # convert float to text
            foilName.text = remove_suffix(str(section.airfoilName), '.dat')

        for foilName in newSection.iter('Right_Side_FoilName'):
            # convert float to text
            foilName.text = remove_suffix(str(section.airfoilName), '.dat')

        # add the new section to the tree
        wing.append(newSection)
        hingeDepthPercent = (section.hingeDepth /section.chord )*100
        NoteMsg("Section %d: position: %.0f mm, chordlength %.0f mm, hingeDepth %.1f  %%, airfoilName %s was inserted" %
          (section.number, section.y*1000, section.chord*1000, hingeDepthPercent, section.airfoilName))

    # write all data to the new file file
    tree.write(outFileName)

################################################################################
# function that gets the name of the planform-data-file
def get_planformDataFileName(args):

    if args.planforminput:
        inFileName = args.planforminput
    else:
        # use Default-name
        inFileName = ressourcesPath + bs + 'planformdata'

    inFileName = inFileName + '.txt'
    NoteMsg("filename for planform input-data is: %s" % inFileName)
    return inFileName


################################################################################
# function that gets the name of the strak-data-file
def get_strakDataFileName(args):

    if args.strakinput:
        inFileName = args.strakinput
    else:
        # use Default-name
        inFileName = ressourcesPath + bs + strakMachineInputFileName

    NoteMsg("filename for strak input-data is: %s" % inFileName)
    return inFileName


def copy_userAirfoils(wingData):
    userAirfoil_idx = 0

    if wingData.fuselageIsPresent():
        userAirfoils = wingData.userAirfoils[1:]
        userAirfoil_idx = 1
    else:
        userAirfoils = wingData.userAirfoils
        userAirfoil_idx = 0


    for airfoil in userAirfoils:
        splitnames = airfoil.split("\\")
        airfoilName = splitnames[-1]
        airfoilName = remove_suffix(airfoilName, ".dat")

        if (splitnames[0]=='.'):
            srcPath = "..\\..\\" + '\\'.join(splitnames[1:-1])
        else:
            srcPath = '\\'.join(splitnames[0:-1])

        destName = wingData.get_UserAirfoilName(userAirfoil_idx)
        destName = remove_suffix(destName, ".dat")

        copyAndSmooth_Airfoil(xfoilWorkerCall, inputFilename, airfoilName,
                              srcPath, destName, wingData.smoothUserAirfoils)
        userAirfoil_idx = userAirfoil_idx + 1


def get_rightFoilData(wingData, start):
    end = len(wingData.airfoilTypes)

    # loop over all airfoil-Types
    for idx in range(start, end):
        # Get the first "non-blend" airfoil beginning from "start"
        if (wingData.airfoilTypes[idx] != "blend"):
            return ( wingData.airfoilNames[idx], wingData.chords[idx])

    # Nothing was found
    return (None, None)


def calculate_Blend(chord_left, chord_blend, chord_right):
    if (chord_left < chord_blend < chord_right):
        # decreasing chord from left to right (normal)
        diff = chord_right - chord_left
        diff_blend = chord_blend - chord_left
    elif (chord_left > chord_blend > chord_right):
        # increasing chord from left to right (unusual)
        diff = chord_left - chord_right
        diff_blend = chord_left - chord_blend
    else:
        # unknown behaviour
        ErrorMsg("calculate_Blend()")
        diff = diff_blend = 1

    # calculate blend now
    blend = (diff_blend / diff) * 100
    blend = round(blend, 0)
    return int(blend)


def check_airfFoilsExist(name_1, name_2):
    try:
        file = open(name_1)
        file.close()
        file = open(name_2)
        file.close()
    except:
        return False

    return True



def create_blendedArifoils(wingData):
    num = len(wingData.airfoilTypes)

    # loop over all airfoil-Types
    for idx in range(num):
        # not a "blend" airfoil ?
        if (wingData.airfoilTypes[idx] != "blend"):
            # yes, take this airfoil as the "left-side" airfoil for blending
            leftFoilName = wingData.airfoilNames[idx]
            leftFoilChord = wingData.chords[idx]
        else:
            # no, this is a "blend" airfoil that must be created
            blendFoilName = wingData.airfoilNames[idx]
            blendFoilName = remove_suffix(blendFoilName , ".dat")
            blendFoilChord = wingData.chords[idx]

            # get data of the "right-side" airfoil for blending
            (rightFoilName, rightFoilChord) = get_rightFoilData(wingData, idx+1)
            # check if left- and right-side airfoils exist

            if (check_airfFoilsExist(leftFoilName, rightFoilName) == True):
                NoteMsg("creating blended airfoil %s" % blendFoilName)

                # calculate the blend-factor
                blend = calculate_Blend(leftFoilChord, blendFoilChord, rightFoilChord)

                # compose XFOIL-worker-call
                worker_call = xfoilWorkerCall + " -w blend %d -a %s -a2 %s -o %s"\
                        % (blend, leftFoilName, rightFoilName, blendFoilName)
                print(worker_call) #Debug

                # call worker now by system call
                os.system(worker_call)
            else:
                NoteMsg("at least one airfoil for blending does not exist,"\
                 "skipping blending for airfoil %s" % blendFoilName)


def update_seedfoilName(wingData, strakdata):
    seedfoilIdx = 0
    firstOptfoilIdx = 0

    # get number of airfoils
    num = len(wingData.airfoilTypes)

    # search for 'opt' airfoils, starting at the root of the wing
    for idx in range(num):
        if (wingData.airfoilTypes[idx] == "opt"):
            # we have found an optfoil
            firstOptfoilIdx = idx
            break

    # search for 'user' airfoils, starting from the optfoil, but search
    # backwards up to the root of the wing
    for idx in reversed(range(0, firstOptfoilIdx)):
        if (wingData.airfoilTypes[idx] == "user"):
            # we have found a user airfoil, this wiil be our seedfoil
            seedfoilIdx = idx
            break

    # set the new seedfoilname
    seedFoilName = wingData.airfoilNames[seedfoilIdx]
    strakdata["seedFoilName"] = airfoilPath + bs + remove_suffix(seedFoilName, ".dat")
    return seedfoilIdx


def update_airfoilNames(wingData, strakdata, seedfoilIdx):
    # all airfoil without tip-airfoil
    num = len(wingData.airfoilTypes) - 1

    airfoilNames = []

    # first append name of the seedfoil
    foilName = remove_suffix(wingData.airfoilNames[seedfoilIdx], ".dat")
    airfoilNames.append(foilName)

    # create list of airfoilnames that shall be created by the strak-machine
    for idx in range(num):
        if (wingData.airfoilTypes[idx] == "opt"):
            foilName = remove_suffix(wingData.airfoilNames[idx], ".dat")
            airfoilNames.append(foilName)

    # now set the new list in the strakdata-dictionary
    strakdata["airfoilNames"] = airfoilNames


def update_reynolds(wingData, strakdata, seedfoilIdx):
    # all airfoil without tip-airfoil
    num = len(wingData.airfoilTypes) -1
    reynolds = []

    # first append reynolds-number of the seedfoil
    reynolds.append(wingData.airfoilReynolds[seedfoilIdx])

    # create list of reynolds-numbers for the airfoils that shall be created by
    # the strak-machine
    for idx in range(num):
        if (wingData.airfoilTypes[idx] == "opt"):
            reynolds.append(wingData.airfoilReynolds[idx])

    # now set the new list in the strakdata-dictionary
    strakdata["reynolds"] = reynolds


def create_strakdataFile(strakDataFileName):
    data = { "seedFoilName": " ", "reynolds": [0,0], "airfoilNames": [" "," "]}
    json.dump(data, open(strakDataFileName,'w'))
    NoteMsg("strakdata was successfully created")


# generates batchfile for polar-creation
def generate_polarCreationFile(wingData):
    # check, if polar- Re-numbers defined, determine number of polars for
    # each airfoil
    numPolars = len(wingData.polarReynolds)
    if numPolars == 0:
        NoteMsg("no reynolds numbers for polar creation defined, skipping"\
        " generation of polar creation file")
        return

    # set NCrit in T1-polar creation input-file
    set_NCrit(wingData.NCrit, T1_polarInputFile)

    # set name of polar creation file
    if (wingData.isFin):
        polarCreationFileName = "create_tail_polars.bat"
    else:
        polarCreationFileName = "create_wing_polars.bat"

    File = open(polarCreationFileName, 'w+')
    File.write("cd .\\build\n")

    # set list of re-numbers and airfoil names
    if wingData.fuselageIsPresent():
        airfoilNames = wingData.airfoilNames[1:-1]
        airfoilReynolds = wingData.airfoilReynolds[1:-1]
    else:
        airfoilNames = wingData.airfoilNames[:-1]
        airfoilReynolds = wingData.airfoilReynolds[:-1]

    # determine number of airfoils
    numAirfoils = len(airfoilNames)

    # determine Re-number or Resqrt(Cl) of root airfoil
    rootAirfoilRe = airfoilReynolds[0]

    # loop over all airfoils
    for idx in range(numAirfoils):
        airfoilName = remove_suffix(airfoilNames[idx], '.dat')
        airfoilRe = airfoilReynolds[idx]

        # determine factor, ratio of current airfoil-Re to rootAirfoil-Re
        ReFactor = airfoilRe / rootAirfoilRe
        ReList = []

        # build up List of Re-numbers for the airfoil
        for element in wingData.polarReynolds:
            ReList.append(element * ReFactor)

        # open File for polar creation for this airfoil
        AirfoilPolarCreationFileName = "create_%s_polars.bat" % airfoilName
        AirfoilPolarCreationFile = open((".\\build\\%s" %AirfoilPolarCreationFileName), 'w+')

        # generate lines of the batchfile for this airfoil, write to file
        for Re in ReList:
            workerCall = "echo y | ..\\bin\\xfoil_worker.exe -i \"..\\ressources\\i"\
            "Polars_T1.txt\" -a \".\\%s\%s.dat\" -w polar -o \"%s\" -r %d\n" \
            %(airfoilPath, airfoilName, airfoilName, Re)

            # write worker call to batchfile
            AirfoilPolarCreationFile.write(workerCall)

        # append small timeout and close the window
        AirfoilPolarCreationFile.write("timeout 5 >nul\n")
        AirfoilPolarCreationFile.write("exit\n")

        # finished polar cration for this airfoil
        AirfoilPolarCreationFile.close()

        # append entry to main polar cration file
        File.write("Start %s\n" % AirfoilPolarCreationFileName)

    # change back directory
    File.write("cd ..\n")
    File.close()
    NoteMsg("polar creation file \"%s\" was successfully generated"\
             % polarCreationFileName)



def set_NCrit(NCrit, filename):
        fileNameAndPath = ressourcesPath + bs + filename

        # read namelist form file
        dictData = f90nml.read(fileNameAndPath)

        # change ncrit in namelist / dictionary
        xfoil_run_options = dictData["xfoil_run_options"]
        xfoil_run_options['ncrit'] = NCrit

        # delete file and writeback namelist
        os.remove(fileNameAndPath)
        f90nml.write(dictData, fileNameAndPath)


# write Re-numbers and seedfoil to strakdata.txt
def update_strakdata(wingData):
    foundOptFoil = False

    # first check if there are any 'opt' airfoils in the wing
    for airfoilType in wingData.airfoilTypes:
        if (airfoilType == "opt"):
            foundOptFoil = True

    if not foundOptFoil:
        # we have nothing to do
        return

    # try to open .json-file
    try:
        strakDataFile = open(strakDataFileName, "r")
    except:
        NoteMsg('failed to open file %s, creating new one' % strakDataFileName)
        create_strakdataFile(strakDataFileName)
        strakDataFile = open(strakDataFileName, "r")

    # load dictionary from .json-file
    try:
        strakdata = json.load(strakDataFile)
        strakDataFile.close()
    except ValueError as e:
        ErrorMsg('invalid json: %s' % e)
        ErrorMsg('failed to read data from file %s' % strakDataFileName)
        strakDataFile.close()
        return

    # update data coming from planform-creator
    seedfoilIdx = update_seedfoilName(wingData, strakdata)
    update_airfoilNames(wingData, strakdata, seedfoilIdx)
    update_reynolds(wingData, strakdata, seedfoilIdx)

    # if there are any geo parameters, remove them now
    try:
        del(strakdata['geoParams'])
    except:
        pass

    # write json-File
    with open(strakDataFileName, "w") as write_file:
        json.dump(strakdata, write_file, indent=4, separators=(", ", ": "), sort_keys=False)
        write_file.close()
    NoteMsg("strakdata was successfully updated")


def update_planformdata(wingdata, dictData):
    # update parameters in json dictionary
    dictData["chordDistribution"] = wingdata.chordDistribution

    # write json-File
    with open(planformDataFileName, "w") as write_file:
        json.dump(dictData, write_file, indent=4, separators=(", ", ": "), sort_keys=False)
        write_file.close()

################################################################################
#
# planform-creator class
#
################################################################################
class planform_creator:
    def __init__(self, paramFileName):
        '''class init'''
        global print_disabled

        # store paramFileName for later use
        self.paramFileName = paramFileName

        # check working-directory, have we been started from "scripts"-dir? (Debugging)
        currentDir = getcwd()
        if (currentDir.find("scripts")>=0):
            self.startedFromScriptsFolder = True
            chdir("..")
        else:
            self.startedFromScriptsFolder = False

        # get current working dir
        self.workingDir = getcwd()

        # load parameters from file
        fileContent = self.__load_paramFile()

        # create a new wing
        self.newWing:wing = wing()

        # set parameters for the wing
        self.newWing.set_Data(fileContent)

    def __load_paramFile(self):
        # try to open .json-file
        try:
            paramFile = open(self.paramFileName)
        except:
            ErrorMsg("failed to open file %s" % self.paramFileName)
            return None

        # load parameter dictionary from .json-file
        try:
            fileContent = json.load(paramFile)
            paramFile.close()
        except ValueError as e:
            ErrorMsg('invalid json: %s' % e)
            ErrorMsg('Error, failed to read data from file %s' % self.paramFileName)
            paramFile.close()
            return None

        return fileContent

    def __save_paramFile(self):
        # try to open .json-file for writing / overwrite existing file
        try:
            paramFile = open(self.paramFileName, 'w')
        except:
            ErrorMsg("failed to open file %s" % self.paramFileName)
            return -1

        # get actual parameters
        fileContent = self.newWing.get_params()

        # save parameter dictionary to .json-file
        try:
            json.dump(fileContent, paramFile, indent=2, separators=(',', ':'))
            paramFile.close()
        except ValueError as e:
            ErrorMsg('invalid json: %s' % e)
            ErrorMsg('Error, failed to save data to file %s' % self.paramFileName)
            paramFile.close()
            return -1

        return 0

    def __exit_action(self, value):
        global print_disabled
        print_disabled = True

        return value

    def __entry_action(self, airfoilIdx):
        global print_disabled
        print_disabled = False

    def __set_AxesAndLabels(self, ax, title):
        global cl_grid
        global cl_diagramTitle
        global ls_grid
        global lw_grid
        global fs_diagramTitle
        global main_font

        # set title of the plot
        text = (title)
        ax.set_title(text, font = main_font, fontsize = fs_diagramTitle,
           color=cl_diagramTitle)

        # customize grid
        ax.grid(True, color=cl_grid,  linestyle=ls_grid, linewidth=lw_grid)

    def set_screenParams(self, width, height):
        '''set scalings for fonts and linewidths depending on screen resolution'''
        global scaled
        global scaleFactor

        # linewidths
        global lw_grid
        global lw_quarterChordLine
        global lw_geometricalCenterLine
        global lw_hingeLine
        global lw_planform
        global lw_sections

        # fontsizes
        global fs_diagramTitle
        global fs_infotext
        global fs_legend
        global fs_axes
        global fs_ticks

        if (scaled == False):
            # scale font sizes (1920 being default screen width)
            scaleFactor = int(width/1920)
            if (scaleFactor < 1):
                scaleFactor = 1

            # linewidths
            lw_grid *= scaleFactor
            lw_quarterChordLine *= scaleFactor
            lw_geometricalCenterLine *= scaleFactor
            lw_hingeLine *= scaleFactor
            lw_planform *= scaleFactor
            lw_sections *= scaleFactor

            # fontsizes
            fs_diagramTitle *= scaleFactor
            fs_infotext *= scaleFactor
            fs_legend *= scaleFactor
            fs_axes *= scaleFactor
            fs_ticks *= scaleFactor

            fs_infotext *= scaleFactor
            fs_legend *= scaleFactor
            fs_axes *= scaleFactor
            fs_ticks *= scaleFactor

            scaled = True

    def set_appearance_mode(self, theme):
        '''applies the given theme / appearance mode'''
        self.newWing.params.theme = theme
        self.newWing.set_colours()

    def load(self):
        '''restores parameters that are stored in .json-file'''
        # load parameters from file
        fileContent = self.__load_paramFile()

        if fileContent != None:
            # set parameters for the wing
            self.newWing.set_Data(fileContent)
            return 0
        else:
            return -1

    def save(self):
        '''saves all parameters to .json-file'''
        return self.__save_paramFile()

    def reset(self):
        '''sets all parameters to default'''
        print("reset")

    def get_params(self):
        '''gets parameters as a dictionary'''
        return self.newWing.get_params()

    def update_planform(self, paramDict):
        '''applies parameters coming with paramDict'''
        self.newWing.set_Data(paramDict)

    def plot_diagram(self, diagramType, ax, x_limits, y_limits):
        '''plots diagram to ax according to diagraType'''
        global cl_background

        # set background first (dark or light)
        ax.set_facecolor(cl_background)

        # set axes and labels
        self.__set_AxesAndLabels(ax, diagramType)

        # draw the graph
        self.newWing.draw_diagram(diagramType, ax, x_limits, y_limits)

################################################################################
# function that gets arguments from the commandline
def get_Arguments():

    # initiate the parser
    parser = argparse.ArgumentParser('')

    parser.add_argument("-planforminput", "-p", help="filename of planformdata input"\
                        "-file (e.g. planformdata)")


    parser.add_argument("-strakinput", "-s", help="filename of strakdata input"\
                        "-file (e.g. strakdata)")

    # read arguments from the command line
    args = parser.parse_args()
    return (get_planformDataFileName(args), get_strakDataFileName(args))


# Main program
if __name__ == "__main__":
    init()

    # bugfix (wrong scaling matplotlib)
    ctypes.windll.shcore.SetProcessDpiAwareness(0)

    # get command-line-arguments or user-input
    (planformDataFileName, strakDataFileName) = get_Arguments()

    # check working-directory, have we been started from "scripts"-dir?
    if (os.getcwd().find("scripts")>=0):
        os.chdir("..")

    # create instance of planform creator
    creatorInst = planform_creator(planformDataFileName)


##
##
##    # try to open .json-file
##    try:
##     planform = open(planformDataFileName)
##    except:
##        ErrorMsg("failed to open file %s" % planformDataFileName)
##        exit(-1)
##
##    # load dictionary of planform-data from .json-file
##    try:
##        planformData = json.load( planform)
##        planform.close()
##    except ValueError as e:
##        ErrorMsg('invalid json: %s' % e)
##        ErrorMsg('Error, failed to read data from file %s' % planformDataFileName)
##        planform.close()
##        exit(-1)
##
##    # set data for the planform
##    newWing.set_Data(planformData)
##
##    # before calculating the planform with absolute numbers,
##    # calculate normalized chord distribution
##    newWing.calculate_normalizedChordDistribution()
##
##    # denormalize position / calculate absolute numbers
##    newWing.denormalize_positions()
##
##    # calculate the grid, the chordlengths of the airfoils and the sections
##    newWing.calculate_planform()
##    newWing.calculate_ReNumbers()
##    newWing.calculate_chordlengths()
##    newWing.calculate_positions() # must be done after chordlenghts ar known
##    newWing.set_AirfoilNames()
##
##    # if there is a fuselage, insert data for the fuselage section
##    # at the beginning of the list.
##    if newWing.fuselageIsPresent():
##        newWing.insert_fuselageData()
##
##    # always insert data for the wing tip
##    newWing.insert_tipData()
##
##    # calculate the sections now
##    newWing.calculate_sections()
##
##    # assign the flap groups to the different sections
##    newWing.assignFlapGroups()
##
##    # create outputfolder, if it does not exist
##    if not os.path.exists(outputFolder):
##        os.makedirs(outputFolder)
##
##    # get current working dir
##    workingDir = os.getcwd()
##
##    # check if output-folder exists. If not, create folder.
##    if not os.path.exists(buildPath):
##        os.makedirs(buildPath)
##
##    # check if airfoil-folder exists. If not, create folder.
##    if not os.path.exists(buildPath + bs + airfoilPath):
##        os.makedirs(buildPath + bs + airfoilPath)
##
##    # change working-directory to output-directory
##    os.chdir(workingDir + bs + buildPath + bs + airfoilPath)
##
##    # copy and rename user-airfoils, the results will be copied to the
##    # airfoil-folder specified in the strak-machine
##    copy_userAirfoils(newWing)
##
##    # create blended airfoils using XFOIL_worker
##    create_blendedArifoils(newWing)
##
##    # change working-directory back
##    os.chdir(workingDir)
##
##    # update "strakdata.txt" for the strakmachine
##    update_strakdata(newWing)
##
##    # interpolation of sections, make complete 1:1 copy first
##    # in the drawing we only want to see the non-interpolated sections
##    interpolatedWing = deepcopy(newWing)
##    interpolatedWing.interpolate_sections()
##
##    # insert the generated-data into the XFLR5 File (interpolated data)
##    try:
##        # get filename of XFLR5-File
##        XFLR5_inFileName =  planformData["XFLR5_inFileName"]
##        if (XFLR5_inFileName.find(bs) < 0):
##            XFLR5_inFileName = ressourcesPath + bs + XFLR5_inFileName
##
##        # compose output-filename for planform-xml-file
##        XFLR5_outFileName =  planformData["XFLR5_outFileName"]
##        if (XFLR5_outFileName.find(bs) < 0):
##            XFLR5_outFileName = outputFolder + bs + XFLR5_outFileName
##
##
##        if ((XFLR5_inFileName != None) and (XFLR5_outFileName != None)):
##            insert_PlanformDataIntoXFLR5_File(interpolatedWing, XFLR5_inFileName, XFLR5_outFileName)
##            NoteMsg("XFLR5 file \"%s\" was successfully created" % XFLR5_outFileName)
##    except:
##        NoteMsg("creating XFLR5 file was skipped")
##
##    # insert the generated-data into the FLZ-Vortex File (interpolated data)
##    try:
##        FLZ_inFileName  = planformData["FLZVortex_inFileName"]
##        if (FLZ_inFileName.find(bs) < 0):
##            FLZ_inFileName = ressourcesPath + bs + FLZ_inFileName
##
##        FLZ_outFileName = planformData["FLZVortex_outFileName"]
##        if (FLZ_outFileName.find(bs) < 0):
##            FLZ_outFileName = outputFolder + bs + FLZ_outFileName
##
##        export_toFLZ(interpolatedWing, FLZ_inFileName, FLZ_outFileName)
##        NoteMsg("FLZ vortex file \"%s\" was successfully created" % FLZ_outFileName)
##    except:
##        NoteMsg("creating FLZ vortex file was skipped")
##
##    # generate batchfile for polar creation (non interpolated data)
##    generate_polarCreationFile(newWing)
##
##    # set colours according to selected theme
##    newWing.set_colours()
##
##    # plot the normalized chord distribution
##    newWing.draw_NormalizedChordDistribution()
##
##    # plot the planform
##    newWing.draw()
