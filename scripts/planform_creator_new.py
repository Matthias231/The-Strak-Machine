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
import shutil
import customtkinter
import re
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
from strak_machine import ( get_ReString,
                             ErrorMsg, WarningMsg, NoteMsg, DoneMsg,
                             remove_suffix, interpolate, round_Re,
                             bs, buildPath, ressourcesPath, airfoilPath,
                             scriptPath, exePath, smoothInputFile,
                             strakMachineInputFileName, xfoilWorkerName,
                             T1_polarInputFile)
from change_airfoilname import change_airfoilName
from colorama import init
from termcolor import colored
from FLZ_Vortex_export import export_toFLZ
from XFLR5_export import export_toXFLR5
from DXF_export import export_toDXF

################################################################################
# some global variables

# disables all print output to console
print_disabled = False

# folder where the generated planforms can be found
planformsFolder = '02_planforms'

# folders containing the output / result-files
planformsPath = buildPath + bs + planformsFolder
airfoilsPath = buildPath + bs + airfoilPath

# name of template files for planform export
XFLR5_template = 'plane_template.xml'
FLZ_template = 'plane_template.flz'
XFLR5_output = 'XFLR5_plane.xml'
FLZ_output = 'FLZ_plane.flz'

# colours, lineStyles
cl_background = None
cl_grid = None
cl_quarterChordLine = None
cl_geoCenter = None
cl_hingeLine = None
cl_flapFill = None
cl_planform = None
cl_planformFill = None
cl_sections = None
cl_userAirfoil = None
cl_userAirfoil_unassigned = None
cl_optAirfoil = None
cl_infotext = None
cl_diagramTitle = None
cl_legend = None
cl_chordlengths = None
cl_referenceChord = None
cl_normalizedChord = None
cl_controlPoints = None
cl_flapGroup = None

# linestyles
ls_grid = 'dotted'
ls_quarterChordLine = 'solid'
ls_hingeLine = 'solid'
ls_planform = 'solid'
ls_sections = 'solid'

# linewidths
lw_grid = 0.3
lw_quarterChordLine  = 0.8
lw_hingeLine = 0.6
lw_planform = 1.0
lw_sections = 0.4

# fontsizes
fs_diagramTitle = 20
fs_infotext = 9
fs_legend = 9
fs_axes = 20
fs_ticks = 10
fs_flapGroup = 20

# fonts
main_font = "Roboto Medium"

# scaling information
scaled = False
scaleFactor = 1.0

# types of diagrams
diagTypes = ["Chord distribution", "Planform shape", "Flap distribution",
             "Airfoil distribution", "Projected wingplan"]
airfoilTypes = ['user', 'blend', 'opt']
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

def bullseye_BW(center, radius, ax, **kwargs):
    '''function for plotting a bullseye with given radius and center'''
    w1 = Wedge(center, radius, 90, 180, fill=True, color='white', alpha = 1.0)
    w2 = Wedge(center, radius, 270, 360, fill=True, color='white', alpha = 1.0)
    w3 = Wedge(center, radius, 180, 270, fill=True, color='black', alpha = 1.0)
    w4 = Wedge(center, radius, 0, 90, fill=True, color='black', alpha = 1.0)
    ax.add_artist(w1)
    ax.add_artist(w2)
    ax.add_artist(w3)
    ax.add_artist(w4)

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
        self.flapDepth = 0
        self.hingeLine = 0
        self.quarterChordLine = 0
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
        self.quarterChordLine = 0.0
        self.hingeLine = 0.0
        self.flapDepth = 0.0
        self.trailingEdge = 0.0

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

        # single parameters, double /float
        self.wingspan = 0.0
        self.rootchord = 0.0
        self.rootReynolds = 0.0
        self.tipchord = 0.0
        self.tipSharpness = 0.0
        self.fuselageWidth = 0.0
        self.leadingEdgeCorrection = 0.0
        self.ellipseCorrection = 0.0
        self.hingeLineAngle = 0.0
        self.flapDepthRoot = 0.0
        self.flapDepthTip = 0.0
        self.dihedral = 0.0
        self.NCrit = 0.0

        # single parameters, int
        self.numAirfoils = 0
        self.interpolationSegments = 0

        # lists, double / float
        self.polarReynolds = []
        self.airfoilPositions_normalized = []
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
            exit(-1)

        if self.planformShape == 'elliptical':
            self.leadingEdgeCorrection = self.__get_MandatoryParameterFromDict(dictData, "leadingEdgeCorrection")
            self.tipSharpness =  self.__get_MandatoryParameterFromDict(dictData, "tipSharpness")
            self.ellipseCorrection = self.__get_MandatoryParameterFromDict(dictData, "ellipseCorrection")
        else:
            self.leadingEdgeCorrection = 0.0
            self.ellipseCorrection = 0.0
            self.tipSharpness = 0.0

        if (self.planformShape == 'elliptical') or\
           (self.planformShape == 'trapezoidal'):
            self.tipchord =  self.__get_MandatoryParameterFromDict(dictData, "tipchord")

        self.hingeLineAngle = self.__get_MandatoryParameterFromDict(dictData, "hingeLineAngle")
        self.flapDepthRoot = self.__get_MandatoryParameterFromDict(dictData, "flapDepthRoot")
        self.flapDepthTip = self.__get_MandatoryParameterFromDict(dictData, "flapDepthTip")
        self.dihedral = self.__get_MandatoryParameterFromDict(dictData, "dihedral")

        # get airfoil- / section data
        self.airfoilTypes = self.__get_MandatoryParameterFromDict(dictData, 'airfoilTypes')
        self.airfoilPositions_normalized = self.__get_MandatoryParameterFromDict(dictData, 'airfoilPositions')
        self.airfoilReynolds = self.__get_MandatoryParameterFromDict(dictData, 'airfoilReynolds')
        self.flapGroups = self.__get_MandatoryParameterFromDict(dictData, 'flapGroup')

        # number of airfoils equals number of specified airfoil types
        self.numAirfoils = len(self.airfoilTypes)

        # check number of airfoils
        if (self.numAirfoils == 0):
            ErrorMsg("number of airfoils must be >= 1")
            exit(-1)

        # check if the above parameters have the same number of elements
        if ((self.numAirfoils != len(self.airfoilPositions_normalized)) or
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
        numDefinedUserAirfoils = 0
        for element in self.userAirfoils:
            if element != None:
                numDefinedUserAirfoils += 1

        if (numDefinedUserAirfoils < numUserAirfoils):
            WarningMsg("%d airfoils have type \"user\", but only %d user-airfoils"\
            " were defined in \"user-airfoils\""\
             % (numUserAirfoils, numDefinedUserAirfoils))
        elif (numDefinedUserAirfoils > numUserAirfoils):
            WarningMsg("%d airfoils have type \"user\", but %d user-airfoils"\
            " were defined in \"user-airfoils\""\
             % (numUserAirfoils, numDefinedUserAirfoils))

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
        dictData["ellipseCorrection"] = self.ellipseCorrection
        dictData["tipchord"] = self.tipchord
        dictData["hingeLineAngle"] = self.hingeLineAngle
        dictData["flapDepthRoot"] = self.flapDepthRoot
        dictData["flapDepthTip"] = self.flapDepthTip
        dictData["dihedral"] = self.dihedral
        dictData['airfoilTypes'] = self.airfoilTypes[:]
        dictData['airfoilPositions'] = self.airfoilPositions_normalized[:]
        dictData['airfoilReynolds'] = self.airfoilReynolds[:]
        dictData['flapGroup'] = self.flapGroups[:]
        dictData["userAirfoils"] = self.userAirfoils[:]

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

    def calculate_dependendValues(self):
        # calculate dependent parameters
        self.tipDepthPercent = (self.tipchord/self.rootchord)*100
        self.halfwingspan = (self.wingspan/2)-(self.fuselageWidth/2)

        # determine reynolds-number for root-airfoil
        self.rootReynolds = self.airfoilReynolds[0]

    def normalize_positionValue(self, position):
        # correct position offset, if fuselage is present
        position -= (self.fuselageWidth/2)

        # normalize to halfwingspan
        if self.halfwingspan > 0:
            position /= self.halfwingspan
        else:
            ErrorMsg("normalize_positionValue, halfwingspan is 0")
        return position

    def denormalize_positionValue(self, position):
        # denormalize
        position *= self.halfwingspan

        # correct position offset, if fuselage is present
        position += (self.fuselageWidth/2)
        return position

##    def normalize_positions(self):
##        for idx in range(len(self.airfoilPositions)):
##            if self.airfoilPositions[idx] != None:
##                self.airfoilPositions_normalized[idx] = self.airfoilPositions[idx] / self.halfwingspan
##            else:
##                self.airfoilPositions_normalized[idx] = None

    def denormalize_positions(self):
        self.airfoilPositions.clear()
        num = len(self.airfoilPositions_normalized)

        for idx in range(num):
            normalized_position = self.airfoilPositions_normalized[idx]
            if normalized_position != None:
                position = self.denormalize_positionValue(normalized_position)
                self.airfoilPositions.append(normalized_position)
            else:
                self.airfoilPositions.append(None)


    # calculate missing Re-numbers from positions
    def calculate_ReNumbers(self):
        num = len(self.airfoilReynolds)

        # loop over list of specified Re-numbers
        for idx in range(num):
            if self.airfoilReynolds[idx] == None:
                # for this position no reynolds-number has been specified.
                # calculate the number from postition now
                Re = self.get_ReFromPosition(self.airfoilPositions_normalized[idx])
                self.airfoilReynolds[idx] = int(round(Re ,0))


    def get_shapeParams(self):
        normalizedTipChord = self.tipDepthPercent / 100
        shapeParams = (normalizedTipChord, self.tipSharpness,
                       self.ellipseCorrection)
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
        self.num_gridPoints = 0
        self.grid_delta = 0
        self.normalizedGrid = []

    def __elliptical_shape(self, x, shapeParams):
        (normalizedTipChord, tipSharpness, ellipseCorrection) = shapeParams

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

        # correct chord with ellipseCorrection
        chord = chord - ellipseCorrection * sin(interpolate(0.0, 1.0, 0.0, pi, x))

        return chord


    def __trapezoidal_shape(self, x, shapeParams):
        (normalizedTipChord, tipSharpness, ellipseCorrection) = shapeParams

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

    # calculate a chord-distribution, which is normalized to root_chord = 1.0
    # half wingspan = 1
    def calculate_grid(self, shape, shapeParams, num_gridPoints):
        self.num_gridPoints = num_gridPoints
        self.normalizedGrid.clear()

        # calculate interval for setting up the grid
        self.grid_delta = 1 / (self.num_gridPoints-1)

        grid_delta = self.grid_delta

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

    def get_chordFromPosition(self, position):
        '''get normalized chordlength from normalized position, using the chord distribution '''
        # valid position specified ?
        if (position == None):
            ErrorMsg("invalid position")
            return None

        # calculate index at which the position will be found in the
        # chord distribution
        idx = int(position/self.grid_delta)
        gridData = self.normalizedGrid
        maxIdx = len(gridData)

        if idx > maxIdx:
            # outside specified range
            ErrorMsg("position %f outside normalized chord distribution" % position)
            return 0.0
        elif idx == maxIdx:
            # last value
            return gridData[idx].chord
        else:
            # interpolate for better precision
            pos_left = gridData[idx].y
            chord_left = gridData[idx].chord
            pos_right = gridData[idx+1].y
            chord_right = gridData[idx+1].chord
            chord = interpolate(pos_left, pos_right,chord_left, chord_right, position)
            return chord

    def get_positionFromChord(self, chord):
        '''get normalized position from normalized chordlength, using the chord distribution '''
        # valid chord specified ?
        if (chord == None):
            ErrorMsg("invalid chord")
            return None

        # search in chord distribution for the desired chord.
        # CAUTION: we assume that chordlength is constantly decreasing !!
        gridData = self.normalizedGrid
        maxIdx = len(gridData)

        # search in the chord distribution
        for idx in range(maxIdx):
            if (gridData[idx].chord < chord):
                # found chordlength smaller than the given chord
                # first value?
                if idx==0:
                    return gridData[idx].y
                else:
                    # interpolate for better precision
                    pos_left = gridData[idx-1].y
                    chord_left = gridData[idx-1].chord
                    pos_right = gridData[idx].y
                    chord_right = gridData[idx].chord
                    position = interpolate(chord_left, chord_right, pos_left, pos_right, chord)
                    return position

        ErrorMsg("no chordlength was found for position %f" % position)
        return (0.0)


    def plot(self, ax):
        global cl_referenceChord
        global cl_normalizedChord

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

        ax.annotate('Root',
            xy=(0.0, 0.0), xycoords='data',
            xytext=(0, 5), textcoords='offset points', color = cl_legend,
            fontsize=fs_legend, rotation='vertical')

        ax.annotate('Tip',
            xy=(1.0, 0.0), xycoords='data',
            xytext=(5, 5), textcoords='offset points', color = cl_legend,
            fontsize=fs_legend, rotation='vertical')

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
        self.flapArea = 0.0

        for element in self.grid:
            # sum up area of the grid elements.
            area = grid_delta_y * element.chord
            flapArea = grid_delta_y * element.flapDepth
            center_y = center_y + element.centerLine*area
            center_x = center_x + element.y*area

            # sum up area of the grid elements, which in the end will be half of
            # the total wing area / flap area
            self.wingArea += area
            self.flapArea += flapArea

        # Calculate geometrical center of the halfwing
        center_x /= self.wingArea
        center_y /= self.wingArea
        self.geometricalCenter = (center_x, center_y)

        # calculate area/ flap area of the whole wing
        self.wingArea *= 2.0
        self.flapArea *= 2.0


    # calculate planform-shape of the half-wing (high-resolution wing planform)
    def calculate(self, params:params, chordDistribution:chordDistribution):
        self.grid.clear()
        self.num_gridPoints = chordDistribution.get_numGridPoints()
        self.hingeInnerPoint = (1-(params.flapDepthRoot/100))*params.rootchord

        # calculate tip-depth
        self.tipDepth = params.rootchord*(params.tipDepthPercent/100)

        # calculate the depth of the hinge at the tip
        tipHingeDepth = self.tipDepth *(params.flapDepthTip/100)

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
                                       params.flapDepthRoot, params.flapDepthTip,
                                       grid.y)

            # correction of leading edge for elliptical planform, avoid swept forward part of the wing
            delta = (params.leadingEdgeCorrection) * sin(interpolate(0.0, params.halfwingspan, 0.0, pi, grid.y))

            grid.flapDepth = (hingeDepth_y/100)*grid.chord + delta
            grid.hingeLine = (self.hingeOuterPoint-self.hingeInnerPoint)/(params.halfwingspan) * (grid.y) + self.hingeInnerPoint
            grid.leadingEdge = grid.hingeLine -(grid.chord-grid.flapDepth)

            # calculate trailing edge according to chordlength at this particular
            # point along the wing
            grid.trailingEdge = grid.leadingEdge + grid.chord

            # calculate centerLine, quarterChordLine
            grid.centerLine = grid.leadingEdge + (grid.chord/2)
            grid.quarterChordLine = grid.leadingEdge + (grid.trailingEdge-grid.leadingEdge)/4

            # append section to section-list of wing
            self.grid.append(grid)

        # calculate the area of the wing
        self.__calculate_wingArea()

        # calculate aspect ratio of the wing
        # use "halfwingspan", as the fuselage-width has already been substracted
        self.aspectRatio = ((params.halfwingspan*2)**2) / self.wingArea

        # add offset of half of the fuselage-width to the y-coordinates
        for element in self.grid:
            element.y = element.y + params.fuselageWidth/2



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
        self.normalized_chords = []
        self.chords = []
        self.sections = []

    def set_colours(self):
        global cl_background
        global cl_grid
        global cl_quarterChordLine
        global cl_geoCenter
        global cl_hingeLine
        global cl_planform
        global cl_flapFill
        global cl_planformFill
        global cl_sections
        global cl_userAirfoil
        global cl_userAirfoil_unassigned
        global cl_optAirfoil
        global cl_infotext
        global cl_diagramTitle
        global cl_legend
        global cl_controlPoints
        global cl_normalizedChord
        global cl_referenceChord
        global cl_flapGroup
        params = self.params

        # common colors
        cl_userAirfoil_unassigned = 'red'

        # theme specific colors
        if params.theme == 'Light':
            # black and white theme
            cl_background = 'dimgray'
            cl_grid = 'black'
            cl_quarterChordLine = 'darkblue'
            cl_geoCenter = 'black'
            cl_hingeLine = 'DeepSkyBlue'
            cl_planform = 'white'
            cl_flapFill = 'DeepSkyBlue'
            cl_planformFill = 'darkgray'
            cl_sections = 'darkgray'
            cl_userAirfoil = 'gray'
            cl_optAirfoil = 'black'
            cl_infotext = 'black'
            cl_chordlengths = 'darkgray'
            cl_diagramTitle = 'darkgray'
            cl_legend = 'black'
            cl_referenceChord = 'lightgray'
            cl_normalizedChord = 'DeepSkyBlue'
            cl_controlPoints = 'red'
            cl_flapGroup = 'darkgray'
        elif params.theme == 'Dark':
            # dark theme
            cl_background = 'black'
            cl_grid = 'ghostwhite'
            cl_quarterChordLine = 'orange'
            cl_geoCenter = 'lightgray'
            cl_hingeLine = 'DeepSkyBlue'
            cl_flapFill ='DeepSkyBlue'
            cl_planform = 'gray'
            cl_planformFill = 'lightgray'
            cl_sections = 'grey'
            cl_userAirfoil = 'DeepSkyBlue'
            cl_optAirfoil = 'orange'
            cl_infotext = 'DeepSkyBlue'
            cl_chordlengths = 'darkgray'
            cl_diagramTitle = 'dimgray'
            cl_legend = 'ghostwhite'
            cl_referenceChord = 'gray'
            cl_normalizedChord = 'orange'
            cl_controlPoints = 'red'
            cl_flapGroup = 'gray'
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
        params.airfoilPositions_normalized.insert(0, 0.0)
        params.airfoilPositions.insert(0, 0.0)
        params.airfoilReynolds.insert(0, params.airfoilReynolds[0])


    def insert_tipData(self):
        params = self.params
        params.airfoilNames.append(params.airfoilNames[-1])
        params.airfoilTypes.append(params.airfoilTypes[-1])
        params.airfoilPositions_normalized.append(1.0)
        params.airfoilPositions.append(params.wingspan/2)

        # is last airfoil of type "user" ?
        if params.airfoilTypes[-1] == "user":
            # yes, so append user-airfoil
            params.userAirfoils.append(params.userAirfoils[-1])
        elif params.airfoilTypes[-1] == "opt":
            # append 'None'
            params.userAirfoils.append(None)

        reynolds = (params.tipchord / self.chords[-1]) * params.airfoilReynolds[-1]
        params.airfoilReynolds.append(int(round(reynolds,0)))
        self.chords.append(params.tipchord)
        self.normalized_chords.append(params.tipchord/params.rootchord)

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

        # get basic shape parameters
        (shape, shapeParams) = params.get_shapeParams()

        # number of grid points equals 2*halfwingspan (which is half of wingspan
        # without fuselage) in mm. If fuselage width is e.g. 35 mm, the offset
        # will be 17.5 mm, so we must have a resolution of 0.5 mm and a maximum
        # value of halfwingspan
        num_gridPoints = int(params.halfwingspan * 2000)

        # setup chordDistribution
        self.chordDistribution.calculate_grid(shape, shapeParams, num_gridPoints)

        # calculate planform
        self.planform.calculate(self.params, self.chordDistribution)

        # calculate chordlengths, either by position or reynolds of the airfoil
        self.calculate_chordlengths()

        # normalized positions: 0.0...1.0 --> positions 0.0..halfwingspan
        params.denormalize_positions()

        # calculate missing Re-numbers (if only airfoil position had been specified)
        # CAUTION: Re-numbers will be rounded to int (loss of precision)
        self.calculate_ReNumbers()

        # calculate missing positions (if only airfoil Re-number had been specified),
        # therefore use chordlengths (more accurate than reynolds)
        self.calculate_Positions()

        # airfoil names can be set after all re numbers are known
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
        section.flapDepth = grid.flapDepth
        section.hingeLine = grid.hingeLine
        section.trailingEdge = grid.trailingEdge
        section.leadingEdge = grid.leadingEdge
        section.quarterChordLine = grid.quarterChordLine
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

    def get_planformName(self):
        return self.paramsDict["planformName"]

    def get_airfoilNames(self):
        newList = self.params.airfoilNames[:]

        # remove duplicate tip airfoil (last element)
        newList.pop()

        if self.fuselageIsPresent():
            # remove duplicate root airfoil
            newList.pop(0)

        airfoilNames = []
        for element in newList:
            airfoilNames.append(re.sub('.dat', '', element))

        return airfoilNames


    def get_airfoilPositions(self):
        airfoilPositions = []

        # determine number of airfoil positions from sections, without tip
        # airfoil
        num = len(self.sections) - 1

        if self.fuselageIsPresent():
             # remove root airfoil
            startIdx = 1
            num -= 1
        else:
            startIdx = 0

        for idx in range(startIdx, num):
            # get position, scale from m to mm
            position = self.sections[idx].y * 1000.0
            airfoilPositions.append(position)

        return airfoilPositions

    def get_flapPositions(self):
        flapPos_x = []
        flapPos_y = []
        # get flap groups, separation lines and airfoil names at the separation lines
        (flap_groups, flapPositions_x, flapPositions_y, airfoilNames) = self.get_flapGroups()

        num = len(flapPositions_x)
        for idx in range(num):
            (dummy, x) = flapPositions_x[idx]
            (dummy, y) = flapPositions_y[idx]
            flapPos_x.append(x)
            flapPos_y.append(y)

        return (flapPos_x, flapPos_y)

    def get_distributionParams(self):
        distributionParams = (self.params.planformShape,
        self.params.tipDepthPercent, self.params.tipSharpness,
        self.params.ellipseCorrection)
        return distributionParams


    # get Re from position, according to the planform-data
    def get_ReFromPosition(self, normalized_position):
        normalized_chord = self.chordDistribution.get_chordFromPosition(normalized_position)
        if (normalized_chord != None):
            Re = self.params.airfoilReynolds[0] * normalized_chord
            return Re
        else:
            ErrorMsg("no Re could not be caclulated for position %f" % normalized_position)
            return None


    # get chordlength from position, according to the planform-data
    def get_chordFromPositionOrReynolds(self, normalized_position, reynolds):
        params = self.params
        # valid reynolds number specified ? Will be preferred before position
        if (reynolds != None):
            # calculate chord from reynolds to rootReynolds ratio
            normalizedChord = (reynolds/params.rootReynolds)
            chord = normalizedChord * params.rootchord
            return (normalizedChord, chord)

        # valid position specified ?
        elif (normalized_position != None):
            # get normalized chord from chord distribution
            normalizedChord = self.chordDistribution.get_chordFromPosition(normalized_position)
            chord = normalizedChord * params.rootchord
            return (normalizedChord, chord)

        # nothing was found
        ErrorMsg("position or reynolds not found inside planform")
        NoteMsg("position was: %f, reynolds was %d" % (normalized_position, reynolds))
        return (None, None)


    # calculate all chordlenghts from the list of airfoil positions
    # and the given planform-data
    def calculate_chordlengths(self):
        self.normalized_chords.clear()
        self.chords.clear()
        params = self.params
        for idx in range(len(params.airfoilPositions_normalized)):
            normalized_position = params.airfoilPositions_normalized[idx]
            reynolds = params.airfoilReynolds[idx]
            (normalized_chord, chord) = self.get_chordFromPositionOrReynolds(normalized_position, reynolds)
            self.normalized_chords.append(normalized_chord)
            self.chords.append(chord)

    def calculate_Positions(self):
        '''calculates missing positions'''
        params = self.params
        num = len(params.airfoilPositions_normalized)
        for idx in range(num):
            if params.airfoilPositions_normalized[idx] == None:
                # no position defined yet, calculate now
                normalized_chord = self.normalized_chords[idx]
                normalized_position = self.chordDistribution.get_positionFromChord(normalized_chord)
                params.airfoilPositions_normalized[idx] = normalized_position
                params.airfoilPositions[idx] = self.params.denormalize_positionValue(normalized_position)


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

    def get_flapGroups(self):
        params = self.params
        sections = self.sections
        numSections = len(sections)
        flapGroups = []
        flapPositions_x = []
        flapPositions_y = []
        airfoilNames = []
        actualFlapGroup = 0

        # check all sections
        for idx in range (0, numSections):
            section = sections[idx]

            # Change of Flap-Group or last section? -->separation line
            if ((actualFlapGroup != section.flapGroup) or
               ((idx == (numSections-1)) and (section.flapGroup !=0))):
                # determine x_pos and flapDepth
                x = section.y * 1000.0 # m --> mm
                flapDepthPercent = (section.flapDepth / section.chord) * 100

                # append tupel to lists
                flapPositions_x.append((x,x))
                flapPositions_y.append((0,flapDepthPercent))
                flapGroups.append(section.flapGroup)
                airfoilNames.append(re.sub('.dat', '', section.airfoilName))

            # store actual flapGroup for comparison
            actualFlapGroup = section.flapGroup

        return (flapGroups, flapPositions_x, flapPositions_y, airfoilNames)

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
    def interpolate_sections(self, steps):
        params = self.params
        if steps < 1:
            # nothing to do
            return

        NoteMsg("Interpolation of sections was requested, interpolating each section with"\
                " additional %d steps" % steps)

        new_positions = []
        new_positions_normalized = []
        new_chords = []
        new_airfoilNames = []
        new_airfoilTypes = []
        new_flapGroups = []

        num = len(params.airfoilPositions)

        if self.fuselageIsPresent():
            # do not interpolate fuselage section
            startIdx = 1
            new_positions.append(params.airfoilPositions[0])
            new_positions_normalized.append(params.airfoilPositions_normalized[0])
            new_chords.append(self.chords[0])
            new_airfoilNames.append(params.airfoilNames[0])
            new_airfoilTypes.append(params.airfoilTypes[0])
            # assigning flapGroup of fuselage not necessary, will be done
            # in assignFlapGroups!
        else:
            startIdx = 0

        for idx in range(startIdx, num-1):
            # determine interpolation-distance
            posDelta = float(params.airfoilPositions[idx+1]-params.airfoilPositions[idx])
            posDelta /= (steps+1)

            posDelta_normalized  = float(params.airfoilPositions_normalized[idx+1] - params.airfoilPositions_normalized[idx])
            posDelta_normalized /= (steps+1)

            # add existiog position and name
            new_positions.append(params.airfoilPositions[idx])
            new_positions_normalized.append(params.airfoilPositions_normalized[idx])
            new_chords.append(self.chords[idx])
            new_airfoilNames.append(params.airfoilNames[idx])
            new_airfoilTypes.append(params.airfoilTypes[idx])
            new_flapGroups.append(params.flapGroups[idx])

            # add interpolated position and name
            for n in range(steps):
                position = params.airfoilPositions[idx] + float((n+1)*posDelta)
                position_normalized = params.airfoilPositions_normalized[idx] + float((n+1)*posDelta_normalized)
                new_positions.append(position)
                new_positions_normalized.append(position_normalized)
                normalized_chord = float(self.chordDistribution.get_chordFromPosition(position_normalized))
                chord = float(normalized_chord * params.rootchord)
                new_chords.append(chord)
                new_airfoilNames.append(params.airfoilNames[idx])
                new_flapGroups.append(params.flapGroups[idx])
                new_airfoilTypes.append("blend")

        # set Tip values
        new_positions.append(params.airfoilPositions[-1])
        new_positions_normalized.append(params.airfoilPositions_normalized[-1])
        new_chords.append(self.chords[-1])
        new_airfoilNames.append(params.airfoilNames[-1])
        new_airfoilTypes.append(params.airfoilTypes[-1])
        # assigning of flapGroup for tip not  not necessary, will be done in
        # assignFlapGroups!

        # assign interpolated lists
        params.airfoilPositions = new_positions
        params.airfoilPositions_normalized = new_positions_normalized
        params.airfoilTypes = new_airfoilTypes
        params.airfoilNames = new_airfoilNames
        self.chords = new_chords
        params.flapGroups = new_flapGroups

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
    def get_AirfoilTypeAndColor(self, idx):
        global cl_userAirfoil_unassigned
        global cl_userAirfoil
        global cl_optAirfoil
        global cl_sections

        # get type of airfoil
        try:
            airfoilType = self.params.airfoilTypes[idx]
        except:
            airfoilType = 'blend'
        try:
            filename = self.params.userAirfoils[idx]
            if (filename == 'None') or (filename == ''):
                filename == None
        except:
            filename = None

        if (airfoilType == 'user'):
            if (filename != None):
                color = cl_userAirfoil
            else:
                color = cl_userAirfoil_unassigned
                airfoilType = 'user_unassigned'
        elif (airfoilType == 'opt'):
            color = cl_optAirfoil
        else:
            color = cl_sections

        return (airfoilType, color)

    def __plot_planformDataLabel(self, ax, x):
        params = self.params
        planform = self.planform

        wingArea_dm = planform.wingArea*100

        proj_fact = cos(params.dihedral*pi/180.0)
        proj_wingArea_dm = proj_fact * planform.wingArea*100
        flapToWingAreaRatio = (planform.flapArea / planform.wingArea)*100

        # plot label containing basic planform data
        text = ("Wing Area: %.1f dm² / proj. wing area: %.1f dm²\nAspect ratio: %.1f\nFlap area / wing area ratio: %.1f %%" %\
                (wingArea_dm, proj_wingArea_dm, planform.aspectRatio, flapToWingAreaRatio))

        (y_min,y_max) = ax.get_ylim()
        y_off = -1 * (fs_legend * 4)

        ax.annotate(text, xy=(x, y_min), xycoords='data', xytext=(0, y_off),
         textcoords='offset points', color = cl_legend,fontsize=fs_legend)

    def plot_PlanformShape(self, ax):
        params = self.params

        # create empty lists
        xValues = []
        leadingEdge = []
        trailingeEge = []
        hingeLine = []
        quarterChordLine = []

        grid = self.planform.grid
        for element in grid:
            # build up list of x-values
            xValues.append(element.y)

            # build up lists of y-values
            leadingEdge.append(element.leadingEdge)
            quarterChordLine.append(element.quarterChordLine)
            hingeLine.append(element.hingeLine)
            trailingeEge.append(element.trailingEdge)

        # setup root- and tip-joint
        trailingeEge[0] = leadingEdge[0]
        trailingeEge[-1] = leadingEdge[-1]

        # compose labels for legend
        labelHingeLine = ("hinge line (%.1f %% / %.1f %%)" %
                           (params.flapDepthRoot, params.flapDepthTip))

        # plot quarter-chord-line
        ax.plot(xValues, quarterChordLine, color=cl_quarterChordLine,
          linestyle = ls_quarterChordLine, linewidth = lw_quarterChordLine,
          solid_capstyle="round", label = "quarter-chord line")

        # plot hinge-line
        ax.plot(xValues, hingeLine, color=cl_hingeLine,
          linestyle = ls_hingeLine, linewidth = lw_hingeLine,
          solid_capstyle="round", label = labelHingeLine)

        # plot geometrical center
        (center_x, center_y) = self.planform.geometricalCenter
        (y_min,y_max) = ax.get_ylim()
        radius = (y_max-y_min)/10
        bullseye((center_x, center_y), radius, cl_geoCenter, ax)

        # plot the planform last
        ax.plot(xValues, leadingEdge, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")
        ax.plot(xValues, trailingeEge, color=cl_planform,
                linewidth = lw_planform, solid_capstyle="round")

        x_min = params.fuselageWidth/2
        # set new ticks for the x-axis according to the positions of the sections
        ax.set_xticks([x_min, center_x, params.wingspan/2])
        ax.set_yticks([0.0, center_y, params.rootchord])

        # set new fontsize of the x-tick labels
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(fs_ticks)
            tick.label.set_rotation('vertical')

        # set new fontsize of the y-tick labels
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(fs_ticks)

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

        # label with additional information concerning planform
        #self.__plot_planformDataLabel(ax, x_min) #FIXME is this necessary ?

    def plot_FlapDistribution(self, ax):
        '''plots a diagram that shows distribution of flaps and also depth of flaps'''
        params = self.params

        # get flap groups, separation lines and airfoil names at the separation lines
        (flap_groups, flapPositions_x, flapPositions_y, airfoilNames) = self.get_flapGroups()

        # control points for flaps
        controlPoints_x = []
        controlPoints_y = []
        numLines = len(flapPositions_x)

        # setup empty lists for new tick locations
        x_tick_locations = []

        for idx in range(numLines):
            (dummy, x) = flapPositions_x[idx]
            (dummy, y) = flapPositions_y[idx]
            controlPoints_x.append(x)
            controlPoints_y.append(y)

            text = "%2.1f %%" % y
            ax.annotate(text,
            xy=(x, y), xycoords='data',
            xytext=(5, -15), textcoords='offset points', color = cl_legend,
            fontsize=fs_legend)

            # append position of section to x-axis ticks
            x_tick_locations.append(x)

        # set new ticks for the x-axis according to the positions of the flap
        # separation lines
        ax.set_xticks(x_tick_locations)

        # get control points for root and tip only
        x = [controlPoints_x[0], controlPoints_x[-1]]
        y = [controlPoints_y[0], controlPoints_y[-1]]

        # plot control-points (root / tip)
        ax.scatter(x, y, color=cl_hingeLine)

        # plot the flap separation lines
        for idx in range(numLines):
            ax.plot(flapPositions_x[idx], flapPositions_y[idx],
            color=cl_hingeLine, linewidth = lw_hingeLine, solid_capstyle="round")

        # plot the airfoil names
        num = len(airfoilNames)
        for idx in range (num):
            (dummy, x) = flapPositions_x[idx]

           # last element or not
            if idx < (num-1):
                # no, text position right beside line
                ha = 'left'
                xOff = 4
            else:
                # yes, text position left beside line
                ha = 'right'
                xOff = -1

            ax.annotate(airfoilNames[idx],  xy=(x, 0), xycoords='data',
            xytext=(xOff, -1*fs_legend), textcoords='offset points', color = cl_legend,
            fontsize=fs_legend, rotation='vertical', va='top', ha=ha)

        # plot the flap groups between flap separation lines.
        # the number of flap groups is always one smaller than the number of
        # flap separation lines
        for idx in range (numLines-1):
            # determine x position for the text, shall be centered
            (x2, dummy) = flapPositions_x[idx+1]
            (x1, dummy) = flapPositions_x[idx]
            x = x1 + ((x2-x1)/2)

            text = ("Flap %d" % flap_groups[idx])
            ax.annotate(text,xy=(x, 0), xycoords='data',
              xytext=(0, -0.2*fs_flapGroup), textcoords='offset points',
              ha='center', va='top', color = cl_flapGroup, fontsize=fs_flapGroup)

        # create empty lists
        xValues = []
        flapDepth = []

        # build up list of x- and y-values
        grid = self.planform.grid
        for idx in range(len(grid)-1):
            x = grid[idx].y *1000.0 # m --> mm
            xValues.append(x)
            flapDepth.append((grid[idx].flapDepth / grid[idx].chord) * 100)

        # plot flap depth in percent
        ax.plot(xValues, flapDepth, color=cl_hingeLine,
          linestyle = ls_hingeLine, linewidth = lw_hingeLine,
          solid_capstyle="round", label = "Flap depth (%)")

        # fill between zero line and flapDepth
        ax.fill_between(xValues, flapDepth, color=cl_flapFill, alpha=0.4)

        # helper texts, Root and Tip
        (dummy, y) = flapPositions_y[0]
        ax.annotate('Root',
            xy=(0.0, y), xycoords='data',
            xytext=(-10, 5), textcoords='offset points', color = cl_legend,
            fontsize=fs_legend, rotation='vertical')

        # plot additional point (invisible) to expand the y-axis
        ax.plot(0.0, 1.8*y)

        (dummy, y) = flapPositions_y[-1]
        (dummy, x) = flapPositions_x[-1]
        ax.annotate('Tip',
            xy=(x, y), xycoords='data',
            xytext=(10, 5), textcoords='offset points', color = cl_legend,
            fontsize=fs_legend, rotation='vertical')

        # place legend
        ax.legend(loc='upper right', fontsize=fs_legend, labelcolor=cl_legend,
           frameon=False)

        # show grid
        ax.grid(True)

        # revert y-axis
        ax.set_ylim(ax.get_ylim()[::-1])

    # plot planform of the half-wing
    def plot_AirfoilDistribution(self, ax):
        params = self.params

        # scale all values from m to mm
        scaleFactor = 1000.0

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
        label_user_unassigned = 'airfoiltype \'user\', not assigned yet (!)'
        label_user =  'airfoiltype \'user\''
        label_blend = 'airfoiltype \'blend\''
        label_opt = 'airfoiltype \'opt\''

        for element in reversed(sectionsList):
            # determine type of airfoil of this section,
            # get labelcolor, which will also be the color of the plotted line
            airfoilType, labelColor = self.get_AirfoilTypeAndColor(idx)

            # get labeltext
            if (airfoilType == 'user'):
                if label_user != None:
                    labelText = label_user[:]
                    label_user = None
                else:
                    labelText = None
            elif (airfoilType == 'user_unassigned'):
                if label_user_unassigned != None:
                    labelText = label_user_unassigned[:]
                    label_user_unassigned = None
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

            # scale all values from m to mm
            x = element.y * scaleFactor
            LE = element.leadingEdge * scaleFactor
            TE = element.trailingEdge * scaleFactor

            ax.plot([x, x] ,[LE, TE],
            color=labelColor, linestyle = ls_sections, linewidth = lw_sections,
            solid_capstyle="round", label = labelText)

            # determine x and y Positions of the labels
            if (params.leadingEdgeOrientation == 'up'):
                yPosChordLabel = TE
                yPosOffsetSectionLabel = 32
            else:
                yPosChordLabel = LE
                yPosOffsetSectionLabel = -32

            # plot label for chordlength of section
            try:
                text = ("%d mm" % int(round(element.chord*1000)))
            except:
                text = ("0 mm" )
                ErrorMsg("label for chordlength of section could not be plotted")

            ax.annotate(text,
            xy=(x, yPosChordLabel), xycoords='data',
            xytext=(2, 5), textcoords='offset points', color = cl_chordlengths,
            fontsize=fs_infotext, rotation='vertical')

            # plot label for airfoil-name / section-name
            text = ("%s" % (remove_suffix(element.airfoilName,'.dat')))
            props=dict(arrowstyle="-", connectionstyle= "angle,angleA=-90,angleB=30,rad=10",
             color=labelColor)

            ax.annotate(text,
            xy=(x, LE), xycoords='data',
            xytext=(8, yPosOffsetSectionLabel), textcoords='offset points',
            color = labelColor,fontsize=fs_infotext, rotation='vertical', arrowprops=props)

            # append position of section to x-axis ticks
            x_tick_locations.append(x)
            idx = idx - 1

        # set new ticks for the x-axis according to the positions of the sections
        ax.set_xticks(x_tick_locations)

        # set new ticks for the y-axis
        ax.set_yticks([0.0, params.rootchord])

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
            xValues.append(element.y * scaleFactor)

            # build up lists of y-values
            leadingEdge.append(element.leadingEdge * scaleFactor)
            trailingeEge.append(element.trailingEdge * scaleFactor)

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

        # create empty lists
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

        # adapt coordinates of geometrical center
        (center_x, center_y) = self.planform.geometricalCenter
        center_x *= proj_fact
        center_right_x = center_x +xOffset
        center_left_x = (self.params.wingspan/2)*proj_fact - center_x
        center_right = (center_right_x, center_y)
        center_left = (center_left_x, center_y)

        # build up lists of y-values
        # left half wing
        for element in reversed(grid):
            leadingEdgeLeft.append(element.leadingEdge)
            hingeLineLeft.append(element.hingeLine)
            trailingEdgeLeft.append(element.trailingEdge)

        # center-section / fuselage (y)
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

        # fill the wing
        ax.fill_between(xValuesLeft, leadingEdgeLeft, hingeLineLeft, color=cl_planformFill, alpha=0.4)
        ax.fill_between(xValuesLeft, hingeLineLeft, trailingEdgeLeft, color=cl_flapFill, alpha=0.4)
        ax.fill_between(xValuesRight, leadingEdgeRight, hingeLineRight, color=cl_planformFill, alpha=0.4)
        ax.fill_between(xValuesRight, hingeLineRight, trailingEdgeRight, color=cl_flapFill, alpha=0.4)

        # plot geometrical center, left and right halfwing
        (y_min,y_max) = ax.get_ylim()
        radius = (y_max-y_min)/15
        bullseye_BW(center_left, radius, ax)
        bullseye_BW(center_right, radius, ax)

        # setup list for new x-tick locations
        new_tick_locations_x = [0.0, proj_halfwingSpan, center_left_x,
                                (proj_halfwingSpan + params.fuselageWidth),
                                center_right_x, proj_wingspan]

        # set new ticks
        ax.set_xticks(new_tick_locations_x)
        ax.set_yticks([0.0, center_y, params.rootchord])

        # set new fontsize of the x-tick labels
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(fs_ticks)
            tick.label.set_rotation('vertical')

        # set new fontsize of the y-tick labels
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(fs_ticks)

        # label with additional information concerning planform
        self.__plot_planformDataLabel(ax, 0)

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


    def __copyAndSmooth_Airfoil(self, srcNameAndPath, destName, destPath, smooth):
        global xfoilWorkerCall
        global inputFilename

        # copy airfoil from src path to destination path
        NoteMsg("Copying airfoil \'%s\' to \'%s\'" % (srcNameAndPath, destPath))
        shutil.copy2(srcNameAndPath, destPath)

        # store current working directory and change working directory to
        # destPath
        workingDir = os.getcwd()
        os.chdir(destPath)

        srcName = os.path.basename(srcNameAndPath)

        # check if the airfoil shall get a new name
        if (srcName != destName):
            # rename the airfoil
            NoteMsg("Renaming airfoil \'%s\' to \'%s\'" % (srcName, destName))
            result = change_airfoilName(srcName, destName + '.dat')

            if result != 0:
                ErrorMsg("change_airfoilName failed, errorcode %d" % result)
                NoteMsg("working dir was %s" % getcwd())

                # change back working directory
                os.chdir(workingDir)
                return result
            else:
                # delete the airfoil file with original name
                os.remove(srcName)

        if (smooth):
            NoteMsg("Smoothing airfoil \'%s\'" % destName)

            # compose system-string for smoothing the airfoil
            systemString = xfoilWorkerCall + " -w smooth -i %s -a %s -o %s" % \
                           (inputFilename, destName +'.dat', destName)

            # execute xfoil-worker / create the smoothed root-airfoil
            result = system(systemString)

        # change back working directory
        os.chdir(workingDir)
        return result


    def copy_userAirfoils(self, dest_Path):
        airfoilNames = []
        userAirfoils = []
        dest_airfoilNames = []
        result = 0
        params = self.params
        smooth = params.smoothUserAirfoils

        # create a list of user airfoils and destination airfoil names
        num = len(params.airfoilTypes)
        for idx in range(num):
            if params.airfoilTypes[idx] == 'user':
                userAirfoils.append(params.userAirfoils[idx])
                dest_airfoilNames.append(params.airfoilNames[idx])

        # remove all duplicates
        userAirfoils = list(dict.fromkeys(userAirfoils))
        dest_airfoilNames = list(dict.fromkeys(dest_airfoilNames))

        # check number of list elements
        num = len(userAirfoils)
        if num != len(dest_airfoilNames):
            ErrorMsg("userAirfoils and dest_airfoilNames must contain same number of elements")
            return (-99, airfoilNames)

        for idx in range(num):
            airfoil = userAirfoils[idx]

            if airfoil == None:
                # no valid user airfoil
                continue

            dest_airfoilName = remove_suffix(dest_airfoilNames[idx], ".dat")
            result = self.__copyAndSmooth_Airfoil(airfoil, dest_airfoilName,
                                                  dest_Path, smooth)

            if result == 0:
                airfoilNames.append(dest_airfoilName)
            else:
                # error
                ErrorMsg("copyAndSmooth_Airfoil() failed, airfoil: %s, errorcode %d" %\
                  (airfoil, result))
                break

        return (result, airfoilNames)

    def __get_rightFoilData(self, start, airfoilTypes, airfoilNames, chords):
        end = len(airfoilTypes)

        # loop over all airfoil-Types
        for idx in range(start, end):
            # Get the first "non-blend" airfoil beginning from "start"
            if (airfoilTypes[idx] != "blend"):
                return (airfoilNames[idx], chords[idx])

        # Nothing was found
        return (None, None)

    def create_blendedAirfoils(self, dest_path):
        params = self.params
        my_airfoilTypes = params.airfoilTypes[:]
        my_airfoilNames = params.airfoilNames[:]
        my_chords = self.normalized_chords[:]
        blendfoilNames = []
        result = 0

        if self.fuselageIsPresent():
            # remove duplicate root airfoil
            my_airfoilTypes.pop(0)
            my_airfoilNames.pop(0)

        # remove duplicate tip airfoil
        my_airfoilTypes.pop()
        my_airfoilNames.pop()

        num = len(my_airfoilTypes)

        # check if lists contain same number of elements
        if ((num != len(my_airfoilNames)) or
            (num != len(my_chords))):
            ErrorMsg("my_airfoilTypes, my_airfoilNames and my_chords must contain same number of elements")
            return(-99, blendfoilNames)

        # store current working directory and change working directory to
        # destPath
        workingDir = os.getcwd()
        os.chdir(dest_path)

        # loop over all airfoil-Types
        for idx in range(num):
            # not a "blend" airfoil ?
            if (my_airfoilTypes[idx] != "blend"):
                # yes, take this airfoil as the "left-side" airfoil for blending
                leftFoilName = my_airfoilNames[idx]
                leftFoilChord = my_chords[idx]
            else:
                # no, this is a "blend" airfoil that must be created
                blendFoilName = my_airfoilNames[idx]
                blendFoilName = remove_suffix(blendFoilName , ".dat")
                blendFoilChord = my_chords[idx]

                # get data of the "right-side" airfoil for blending
                (rightFoilName, rightFoilChord) =\
                  self.__get_rightFoilData((idx+1), my_airfoilTypes, my_airfoilNames, my_chords)

                # check if left- and right-side airfoils exist
                if (check_airfFoilsExist(leftFoilName, rightFoilName) == True):#FIXME refactoring, own class function
                    NoteMsg("creating blended airfoil %s" % blendFoilName)

                    # calculate the blend-factor
                    blend = calculate_Blend(leftFoilChord, blendFoilChord, rightFoilChord)#FIXME refactoring, own class function

                    # compose XFOIL-worker-call
                    worker_call = xfoilWorkerCall + " -w blend %d -a %s -a2 %s -o %s"\
                            % (blend, leftFoilName, rightFoilName, blendFoilName)
                    print(worker_call) #Debug

                    # call worker now by system call
                    workerResult = os.system(worker_call)

                    # Evaluate result
                    if workerResult == 0:
                        blendfoilNames.append(blendFoilName)
                    else:
                        # store errorcode
                        if result == 0:
                            result = workerResult
                else:
                    NoteMsg("at least one airfoil for blending does not exist,"\
                          "skipping blending for airfoil %s" % blendFoilName)
                    # store errorcode
                    if result == 0:
                        result = -1

        # change back working directory
        os.chdir(workingDir)
        return (result, blendfoilNames)




################################################################################
# find the wing in the XML-tree
##def get_wing(root, wingFinSwitch):
##    for wing in root.iter('wing'):
##        for XMLwingFinSwitch in wing.iter('isFin'):
##            # convert string to boolean value
##            if (XMLwingFinSwitch.text == 'true') or (XMLwingFinSwitch.text == 'True'):
##                value = True
##            else:
##                value = False
##
##            # check against value of wingFinswitch
##            if (value == wingFinSwitch):
##                return wing
##
##
### insert the planform-data into XFLR5-xml-file
##def insert_PlanformDataIntoXFLR5_File(data, FileName):
##
##    # basically parse the XML-file
##    tree = ET.parse(inFileName)
##
##    # get root of XML-tree
##    root = tree.getroot()
##
##    # find wing-data
##    wing = get_wing(root, data.isFin)
##
##    if (wing == None):
##        ErrorMsg("wing not found\n")
##        return
##
##    # find sections-data-template
##    for sectionTemplate in wing.iter('Sections'):
##        # copy the template
##        newSection = deepcopy(sectionTemplate)
##
##        # remove the template
##        wing.remove(sectionTemplate)
##
##    # write the new section-data to the wing
##    for section in data.sections:
##        # copy the template
##        newSection = deepcopy(sectionTemplate)
##
##        # enter the new data
##        for yPosition in newSection.iter('y_position'):
##            # convert float to text
##            yPosition.text = str(section.y)
##
##        for chord in newSection.iter('Chord'):
##            # convert float to text
##            chord.text = str(section.chord)
##
##        for xOffset in newSection.iter('xOffset'):
##            # convert float to text
##            xOffset.text = str(section.leadingEdge)
##
##        for dihedral in newSection.iter('Dihedral'):
##            # convert float to text
##            dihedral.text = str(section.dihedral)
##
##        for foilName in newSection.iter('Left_Side_FoilName'):
##            # convert float to text
##            foilName.text = remove_suffix(str(section.airfoilName), '.dat')
##
##        for foilName in newSection.iter('Right_Side_FoilName'):
##            # convert float to text
##            foilName.text = remove_suffix(str(section.airfoilName), '.dat')
##
##        # add the new section to the tree
##        wing.append(newSection)
##        hingeDepthPercent = (section.flapDepth /section.chord )*100
##        NoteMsg("Section %d: position: %.0f mm, chordlength %.0f mm, hingeDepth %.1f  %%, airfoilName %s was inserted" %
##          (section.number, section.y*1000, section.chord*1000, hingeDepthPercent, section.airfoilName))
##
##    # write all data to the new file file
##    tree.write(outFileName)

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

    def __export_airfoils(self):
        # check if output (build) folder exists. If not, create folder.
        if not os.path.exists(buildPath):
            os.makedirs(buildPath)

        # compose destination path (airfoil folder)
        dest_path = buildPath + bs + airfoilPath

        # check if airfoil folder exists. If not, create folder.
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)

        # copy and rename user-airfoils
        (result, userAirfoils) = self.newWing.copy_userAirfoils(dest_path)

        if (result != 0):
            # error
            ErrorMsg("copy_userAirfoils() failed")
            return (result, userAirfoils, [])

        # create blended airfoils using XFOIL_worker
        (result, blendedAirfoils) = self.newWing.create_blendedAirfoils(dest_path)

        if (result != 0):
            # error
            ErrorMsg("create_blendedAirfoils() failed")

        return (result, userAirfoils, blendedAirfoils)

    def __export_planform(self, outputPath, interpolationSteps, yPanels, append):
        global XFLR5_template
        global FLZ_template
        exportedFiles = []

        # interpolation of sections, make copy first
        interpolatedWing = deepcopy(self.newWing)
        interpolatedWing.interpolate_sections(interpolationSteps)

        # copy template files to output folder and rename
        XFLR5_FileName = outputPath + bs + XFLR5_output
        FLZ_FileName = outputPath + bs + FLZ_output

        # DXF does not need template at the moment
        DXF_output = self.newWing.get_planformName()
        DXF_output = DXF_output.replace(' ', '_') + '.dxf'
        DXF_FileName = outputPath + bs + DXF_output

        # check if output folder exists
        if (os.path.exists(outputPath) == False):
            try:
                os.makedirs(outputPath)
            except:
                ErrorMsg("creating ouputPath failed")
                return (-1, exportedFiles)

        if append == False:
            try:
                # remove existing files
                if os.path.exists(XFLR5_FileName):
                    os.remove(XFLR5_FileName)

                if os.path.exists(FLZ_FileName):
                    os.remove(FLZ_FileName)

                # copy template files
                shutil.copy2((ressourcesPath + bs + XFLR5_template), XFLR5_FileName)
                shutil.copy2((ressourcesPath + bs + FLZ_template), FLZ_FileName)
            except:
                ErrorMsg("__export_planform: delete or copy template files failed")
                return (-1, exportedFiles)
        try:
            result = export_toXFLR5(interpolatedWing, XFLR5_FileName)
        except:
            ErrorMsg("export_toXFLR5 failed")
            return (-2, exportedFiles)

        if result == 0:
            exportedFiles.append(XFLR5_FileName)
        else:
            return (result, exportedFiles)

        try:
            result = export_toFLZ(interpolatedWing, FLZ_FileName)
        except:
            ErrorMsg("export_toFLZ failed")
            return (-3, exportedFiles)

        if result == 0:
            exportedFiles.append(FLZ_FileName)

        try:
            result = export_toDXF(interpolatedWing, DXF_FileName)
        except:
            ErrorMsg("export_toDXF failed")
            return (-4, exportedFiles)

        if result == 0:
            exportedFiles.append(DXF_FileName)

        return (result, exportedFiles)

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
        global lw_hingeLine
        global lw_planform
        global lw_sections

        # fontsizes
        global fs_diagramTitle
        global fs_infotext
        global fs_legend
        global fs_axes
        global fs_ticks
        global fs_flapGroup

        if (scaled == False):
            # scale font sizes (1920 being default screen width)
            scaleFactor = int(width/1920)
            if (scaleFactor < 1):
                scaleFactor = 1

            # linewidths
            lw_grid *= scaleFactor
            lw_quarterChordLine *= scaleFactor
            lw_hingeLine *= scaleFactor
            lw_planform *= scaleFactor
            lw_sections *= scaleFactor

            # fontsizes
            fs_diagramTitle *= scaleFactor
            fs_infotext *= scaleFactor
            fs_legend *= scaleFactor
            fs_axes *= scaleFactor
            fs_ticks *= scaleFactor
            fs_flapGroup *= scaleFactor

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

    def export_airfoils(self):
        '''exports all 'user' and 'blend' airfoils'''
        return self.__export_airfoils()

    def export_planform(self, filePath, steps, panels, append):
        '''exports planform to given filepath'''
        return self.__export_planform(filePath, steps, panels, append)

    def get_params(self):
        '''gets parameters as a dictionary'''
        return self.newWing.get_params()

    def normalize_position(self, position):
        return self.newWing.params.normalize_positionValue(position)

    def denormalize_position(self, position):
        return self.newWing.params.denormalize_positionValue(position)

    def get_airfoilNames(self):
        '''gets airfoilnames as a list of strings'''
        return self.newWing.get_airfoilNames()

    def get_airfoilPositions(self):
        '''gets list of airfoilpositions in mm'''
        return self.newWing.get_airfoilPositions()

    def get_flapPositions(self):
        '''gets list of flap positions along the halfwing and flapDepth in percent'''
        return self.newWing.get_flapPositions()

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
