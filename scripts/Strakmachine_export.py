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
import json
import numpy as np
from copy import deepcopy
from strak_machine import (ErrorMsg, WarningMsg, NoteMsg, DoneMsg, bs,
                           airfoilPath, remove_suffix)


################################################################################
#
# main function
#
################################################################################
def update_seedfoilName(params, strakdata):
    seedfoilIdx = 0
    firstOptfoilIdx = 0

    # get number of airfoils
    num = len(params.airfoilTypes)

    # search for 'opt' airfoils, starting at the root of the wing
    for idx in range(num):
        if (params.airfoilTypes[idx] == "opt"):
            # we have found an optfoil
            firstOptfoilIdx = idx
            break

    # search for 'user' airfoils, starting from the optfoil, but search
    # backwards up to the root of the wing
    for idx in reversed(range(0, firstOptfoilIdx)):
        if (params.airfoilTypes[idx] == "user"):
            # we have found a user airfoil, this wiil be our seedfoil
            seedfoilIdx = idx
            break

    # set the new seedfoilname
    seedFoilName = params.airfoilNames[seedfoilIdx]
    strakdata["seedFoilName"] = airfoilPath + bs + remove_suffix(seedFoilName, ".dat")
    return seedfoilIdx


def update_airfoilNames(params, strakdata, seedfoilIdx):
    # all airfoil without tip-airfoil
    num = len(params.airfoilTypes) - 1

    airfoilNames = []

    # first append name of the seedfoil
    foilName = remove_suffix(params.airfoilNames[seedfoilIdx], ".dat")
    airfoilNames.append(foilName)

    # create list of airfoilnames that shall be created by the strak-machine
    for idx in range(num):
        if (params.airfoilTypes[idx] == "opt"):
            foilName = remove_suffix(params.airfoilNames[idx], ".dat")
            airfoilNames.append(foilName)

    # now set the new list in the strakdata-dictionary
    strakdata["airfoilNames"] = airfoilNames


def update_reynolds(params, strakdata, seedfoilIdx):
    # all airfoil without tip-airfoil
    num = len(params.airfoilTypes) -1
    reynolds = []

    # first append reynolds-number of the seedfoil
    reynolds.append(params.airfoilReynolds[seedfoilIdx])

    # create list of reynolds-numbers for the airfoils that shall be created by
    # the strak-machine
    for idx in range(num):
        if (params.airfoilTypes[idx] == "opt"):
            reynolds.append(params.airfoilReynolds[idx])

    # now set the new list in the strakdata-dictionary
    strakdata["reynolds"] = reynolds


def create_strakdataFile(strakDataFileName):
    data = { "seedFoilName": " ", "reynolds": [0,0], "airfoilNames": [" "," "]}
    json.dump(data, open(strakDataFileName,'w'))
    NoteMsg("strakdata was successfully created")


def export_strakdata(wingData, fileName):
    foundOptFoil = False
    params = wingData.params

    # first check if there are any 'opt' airfoils in the wing
    for airfoilType in params.airfoilTypes:
        if (airfoilType == "opt"):
            foundOptFoil = True

    if not foundOptFoil:
        # we have nothing to do
        return 0

    # try to open .json-file
    try:
        strakDataFile = open(fileName, "r")
    except:
        NoteMsg('failed to open file %s, creating new one' % fileName)
        create_strakdataFile(fileName)
        strakDataFile = open(fileName, "r")

    # load dictionary from .json-file
    try:
        strakdata = json.load(strakDataFile)
        strakDataFile.close()
    except ValueError as e:
        ErrorMsg('invalid json: %s' % e)
        ErrorMsg('failed to read data from file %s' % fileName)
        strakDataFile.close()
        return -1

    # update data coming from planform-creator
    seedfoilIdx = update_seedfoilName(params, strakdata)
    update_airfoilNames(params, strakdata, seedfoilIdx)
    update_reynolds(params, strakdata, seedfoilIdx)

##    # if there are any geo parameters, remove them now #FIXME: chek, if necessary
##    try:
##        del(strakdata['geoParams'])
##    except:
##        pass

    # write json-File
    with open(fileName, "w") as write_file:
        json.dump(strakdata, write_file, indent=4, separators=(", ", ": "), sort_keys=False)
        write_file.close()
    NoteMsg("strakdata was successfully updated")
    return 0

