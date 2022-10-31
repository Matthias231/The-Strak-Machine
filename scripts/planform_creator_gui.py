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
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import customtkinter as ctk
import os
from PIL import ImageTk, Image
from colorama import init
from copy import deepcopy

# imports to use matplotlib together with tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

# imports from strak machine
from strak_machine import (ErrorMsg, WarningMsg, NoteMsg, DoneMsg, bs,
          airfoilPath, buildPath, ressourcesPath)

# imports from planform creator
from planform_creator_new import (planform_creator, diagTypes, airfoilTypes,
                                  planformShapes, planformsPath, main_font)

# some global variables
num_diagrams = len(diagTypes)
diagram_width = 10
diagram_height = 7
ctrlFrame = None
creatorInstances:planform_creator = []

# path to airfoils library
airfoilLibrary_path = 'airfoil_library'

# names of the planformfiles
planformFiles = ["planformdataNew_wing.txt", "planformdataNew_tail.txt"]

bg_color_light = "#DDDDDD"
bg_color_dark =  "#222222"

# font sizes #FIXME: scaling for screen resolution
fs_label = 13
fs_entry = 11
fs_unit = 13

################################################################################
#
# helper functions
#
################################################################################
def is_List(obj):
    if obj == None:
        return False
    return isinstance(obj, list)

def is_str(obj):
    if obj == None:
        return False
    return isinstance(obj, str)

def is_float(obj):
    if obj == None:
        return False
    return isinstance(obj, float)

def is_int(obj):
    if obj == None:
        return False
    return isinstance(obj, int)

def get_dataType(obj):
    '''returns the dataType of an object as a string'''
    if obj == None:
        return None

    if is_str(obj):
        return 'str'
    elif is_int(obj):
        return 'int'
    elif is_float(obj):
        return 'float'
    elif is_list(obj):
        return 'list'
    else:
        ErrorMsg("get_dataType, unknown dataType")
        return None

# class control frame, change the input-variables / parameters of the
# planform creator
class control_frame():
    def __init__(self, master, side, labelsAndButtons, creatorInstances, scaleFactor):
        # store some variables in own class data structure
        self.master = master
        self.creatorInstances = creatorInstances
        self.scaleFactor = scaleFactor
        self.numPlanforms = len(creatorInstances)
        self.unsavedChangesFlags = []
        self.label_unsavedChanges = []
        self.planformNames = []
        self.params = []
        self.airfoilNames = []
        self.airfoilIdx = []
        self.basicParamsTextVars = []
        self.airfoilParamsTextVars = []
        self.latestPath = []
        self.postponeUpdate = False

        # determine screen size
        self.width = self.master.winfo_screenwidth()
        self.heigth = self.master.winfo_screenheight()

        # create left frame
        self.frame_left = ctk.CTkFrame(master=master, width=180,
                                            corner_radius=0)

        # create scrollable Frame
        self.container = ctk.CTkFrame(master=master, width=180,
                                            corner_radius=0)

        self.canvas = tk.Canvas(self.container, bg=bg_color_dark,
                                 highlightthickness=0)
        self.scrollbar_v = ctk.CTkScrollbar(self.container,
                                                command=self.canvas.yview)

        self.frame_right  = tk.Frame(self.canvas, width=180,
                                         bg = bg_color_dark)

        self.frame_right.bind("<Configure>", self.OnFrameConfigure)

        self.canvas.create_window((10, 10), window=self.frame_right , anchor="ne")
        self.canvas.configure(yscrollcommand=self.scrollbar_v.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_v.pack(side="right", fill="y")

        for i in range(self.numPlanforms):
            # new unsaved changes flag and label
            self.unsavedChangesFlags.append(False)
            widget_1 = ctk.CTkLabel(master=self.frame_left, text='',
             text_color = 'red' )
            self.label_unsavedChanges.append(widget_1)

            # get params
            params = self.creatorInstances[i].get_params()

            # append to list
            self.params.append(params)

            # append planformname to list of planformnames (option menu)
            self.planformNames.append(params["planformName"])

            # get airfoil names
            airfoilNames = self.creatorInstances[i].get_airfoilNames()
            self.airfoilNames.append(airfoilNames)

            # select root airfoil
            self.airfoilIdx.append(0)

            # append latest path
            self.latestPath.append(os.getcwd() + bs + airfoilLibrary_path)

        # add different widgets to upper frame (not scrollable)
        (labels, buttons) = labelsAndButtons
        nextRow = self.__add_labels(self.frame_left, labels, 0, 0)
        nextRow = self.__add_buttons(self.frame_left, buttons, 0, nextRow)
        nextRow = self.__add_appearanceModeMenu(self.frame_left, 0, nextRow)

        # right frame (scrollable)
        nextRow = self.__add_planformChoiceMenu(self.frame_right, 0, 0)

        # add entries
        nextRow = self.__add_basicParams(self.frame_right, 0, nextRow)

        # second column, start at row 1
        nextRow = self.__add_airfoilChoiceMenu(self.frame_right, 3, 1)
        nextRow = self.__add_airfoilTypeMenu(self.frame_right, 3, nextRow)
        nextRow = self.__add_userAirfoilWidgets(self.frame_right, 3, nextRow)

        # add entries
        nextRow = self.__add_airfoilParams(self.frame_right, 3, nextRow)

        # update alle entries
        self.update_Entries(self.master.planformIdx)

        # show left frame
        self.frame_left.pack(side = 'left', fill=tk.BOTH)

        # show right frame
        self.container.pack(side = 'right', fill=tk.BOTH, expand=1)


    def OnFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


    def set_unsavedChangesFlag(self, planformIdx):
        try:
            self.unsavedChangesFlags[planformIdx] = True
            self.label_unsavedChanges[planformIdx].configure(text = 'unsaved changes')
        except:
            ErrorMsg("invalid planformIdx: %d" % planformIdx)


    def clear_unsavedChangesFlag(self, planformIdx):
        try:
            self.unsavedChangesFlags[planformIdx] = False
            self.label_unsavedChanges[planformIdx].configure(text = '')
        except:
            ErrorMsg("invalid planformIdx: %d" % planformIdx)


    def get_unsavedChangesFlags(self):
        return (self.unsavedChangesFlags)


    def __add_labels(self, frame, labels, column, row):
        labelList = []

        for label in labels:
            newLabel = self.__create_label(frame, label, -16)
            labelList.append(newLabel)

        self.__place_widgetsInRow(labelList, column, row)
        return (row + 1)

    def __get_buttonWidgetsRow(self, buttonWidgetsArray, rowIdx):
        row = []
        num_columns = len(buttonWidgetsArray)

        for columnIdx in range(num_columns):
            try:
                row.append(buttonWidgetsArray[columnIdx][rowIdx])
            except:
                row.append(None)
        return row

    def __get_bg_color(self, theme):
        '''get background color according to \'theme\''''
        if (theme == 'Dark'):
            return bg_color_dark
        else:
            return bg_color_light

    def __place_widgetsInColumn(self, widgets, column, startRow):
        '''place widgets in the list \'widgets\' in the same column'''
        row = startRow

        for widget in widgets:
            if widget != None:
                widget.grid(row=row, column=column, pady=5, padx=5, sticky="e")
            row += 1
        return row

    def __place_widgetsInRow(self, widgets, startColumn, row):
        '''place widgets in the list \'widgets\' in the same row'''
        column = startColumn

        for widget in widgets:
            if widget != None:
                widget.grid(row=row, column=column, pady=5, padx=5, sticky="e")
            column += 1
        return column

    def __add_buttons(self, frame, buttonArray, column, row):
        buttonWidgetsArray = []
        max_rows = 0

        # build up array of button widgets, also store number of entries for
        # each column
        for buttonColumn in buttonArray:
            buttonWidgetsColumn = []

            for button in buttonColumn:
                buttonWidgetsColumn.append(self.__create_button(frame, button))

            buttonWidgetsArray.append(buttonWidgetsColumn)
            num_rows = len(buttonWidgetsColumn)
            max_rows = max(num_rows, max_rows)

        # place buttons, row after row
        for rowIdx in range(max_rows):
            buttonWidgetsRow = self.__get_buttonWidgetsRow(buttonWidgetsArray, rowIdx)
            self.__place_widgetsInRow(buttonWidgetsRow, column, row)
            row += 1

        return row

    def __create_label(self, frame, text, size):
        label = ctk.CTkLabel(master=frame,
                text=text, text_font=(main_font, size), anchor="e")
        return label

    def __get_basicParamsTable(self):
        table = [#{"txt": "Planform name",                "variable" : params.planformName,     "unit" : None, "scaleFactor" : None},
                 #{"txt": "Planform shape",               "variable" : params.planformShape,    "unit" : None, "scaleFactor" : None },
                  {"txt": "Airfoils basic name",          "variable" : 'airfoilBasicName',      "idx": None, "unit" : None, "scaleFactor" : None,   "decimals": 0, "f_read" : None,   "f_write" :None},
                  {"txt": "wingspan",                     "variable" : 'wingspan',              "idx": None, "unit" : "mm", "scaleFactor" : 1000,   "decimals": 0, "f_read" : None,   "f_write" :None},
                  {"txt": "Width of fuselage",            "variable" : 'fuselageWidth',         "idx": None, "unit" : "mm", "scaleFactor" : 1000,   "decimals": 0, "f_read" : None,   "f_write" :None},
                  {"txt": "Root chord",                   "variable" : 'rootchord',             "idx": None, "unit" : "mm", "scaleFactor" : 1000,   "decimals": 0, "f_read" : None,   "f_write" :None},
                  {"txt": "Tip chord",                    "variable" : 'tipchord',              "idx": None, "unit" : "mm", "scaleFactor" : 1000,   "decimals": 0, "f_read" : None,   "f_write" :None},
                  {"txt": "Tip sharpness",                "variable" : 'tipSharpness',          "idx": None, "unit" : None, "scaleFactor" : None,   "decimals": 1, "f_read" : None,   "f_write" :None},
                  {"txt": "Ellipse correction",           "variable" : 'ellipseCorrection',     "idx": None, "unit" : None, "scaleFactor" : 100.0,  "decimals": 1, "f_read" : None,   "f_write" :None},
                  {"txt": "Leading edge correction",      "variable" : 'leadingEdgeCorrection', "idx": None, "unit" : None, "scaleFactor" : 100.0,  "decimals": 1, "f_read" : None,   "f_write" :None},
                  {"txt": "Dihedral",                     "variable" : 'dihedral',              "idx": None, "unit" : "°",  "scaleFactor" : None,   "decimals": 1, "f_read" : None,   "f_write" :None},
                  {"txt": "Hingeline angle @root",        "variable" : 'hingeLineAngle',        "idx": None, "unit" : "°",  "scaleFactor" : None,   "decimals": 1, "f_read" : None,   "f_write" :None},
                  {"txt": "Flap depth @root",             "variable" : 'flapDepthRoot',         "idx": None, "unit" : "%",  "scaleFactor" : None,   "decimals": 1, "f_read" : None,   "f_write" :None},
                  {"txt": "Flap depth @tip",              "variable" : 'flapDepthTip',          "idx": None, "unit" : "%",  "scaleFactor" : None,   "decimals": 1, "f_read" : None,   "f_write" :None},
                  #{"txt": "NCrit",                        "variable" : 'polar_Ncrit',           "idx": None, "unit" : None, "scaleFactor" : None},
                  #{"txt": "Interpolation Segments",       "variable" : 'interpolationSegments', "idx": None, "unit" : None,  "scaleFactor" : None},
                ]
        return table

    def __get_airfoilParamsTable(self):
        planformIdx = self.master.planformIdx
        params = self.params[planformIdx]

        # idx of selected airfoil
        idx = self.airfoilIdx[planformIdx]

        # scale functions for position values
        f_read = self.creatorInstances[planformIdx].denormalize_position
        f_write = self.creatorInstances[planformIdx].normalize_position

        table = [
                 {"txt": "selected Airfoil: Position",            "variable" : 'airfoilPositions', "idx": idx, "unit" : 'mm', "scaleFactor" : 1000.0, "decimals": 0, "f_read" : f_read, "f_write" :f_write},
                 {"txt": "selected Airfoil: Re*Sqrt(Cl)",         "variable" : 'airfoilReynolds',  "idx": idx, "unit" : 'K',  "scaleFactor" : 0.001,  "decimals": 0, "f_read" : None,   "f_write" :None},
                 {"txt": "selected Airfoil: assign to flap",      "variable" : 'flapGroup',        "idx": idx, "unit" : None, "scaleFactor" : None,   "decimals": 0, "f_read" : None,   "f_write" :None},
                ]
        return table


    def __create_widgets(self, paramTable, frame, update_function):
        param_labels = []
        entries = []
        unit_labels = []
        textVars = []

        params = self.params[self.master.planformIdx]

        # create entries and assign values
        for paramTableEntry in paramTable:
            # Add Label (display name of the parameter)
            param_label = ctk.CTkLabel(master=frame,
                  text=paramTableEntry["txt"], text_font=(main_font, 13),
                   anchor="e")
            param_labels.append(param_label)

            # create text-Vars to interact with entries
            value = self.__get_paramValue(params, paramTableEntry)
            value_txt = tk.StringVar(frame, value=value)
            textVars.append(value_txt)

            # create entry for param value
            value_entry = ctk.CTkEntry(frame, show=None,
                textvariable = value_txt, text_font=(main_font, fs_entry),
                width=140, height=16, justify='right')

            # bind to "Enter"-Message
            value_entry.bind('<Return>', update_function)

            # append entry to list
            entries.append(value_entry)

            unit = paramTableEntry["unit"]
            if unit != None:
                unit_label = ctk.CTkLabel(master=frame,
                  text=unit, text_font=(main_font, fs_unit), anchor="w")
            else:
                unit_label = None
            unit_labels.append(unit_label)

        widgets = [param_labels, entries, unit_labels]
        return (widgets, textVars, entries)

    def __add_basicParams(self, frame, column, startRow):
        # init some structures to store data locally
        self.basicParamsTextVars = []
        self.basicParamsEntries = []

        # get table with basic parameters for active planform
        basicParams = self.__get_basicParamsTable()

        # create widgets
        (widgets, textVars, entries) = self.__create_widgets(basicParams, frame,
                                          self.update_basicParams)

        self.basicParamsEntries = entries
        self.basicParamsTextVars = textVars

        # place widgets column by column
        endRow = 0
        for widgetRow in widgets:
            row = self.__place_widgetsInColumn(widgetRow, column, startRow)
            column += 1
            endRow = max(endRow, row)

        return endRow

    def __add_airfoilParams(self, frame, column, startRow):
        # init some structures to store data locally
        self.airfoilParamsTextVars = []
        self.airfoilParamsEntries = []

        # add Flag for recursion-check
        self.update_airfoilEntries_active = False

        # get table with airfoil parameters for active planform
        airfoilParams = self.__get_airfoilParamsTable()

        # create widgets
        (widgets, textVars, entries) = self.__create_widgets(airfoilParams, frame,
                                          self.update_airfoilParams)

        self.airfoilParamsEntries = entries
        self.airfoilParamsTextVars = textVars

        # place widgets column by column
        endRow = 0
        for widgetColumn in widgets:
            row = self.__place_widgetsInColumn(widgetColumn, column, startRow)
            endRow = max(endRow, row)
            column += 1

        return endRow

    def  __getDictValueAndDataType(self, dictionary, key, idx):
        '''get value and datatype of a dictionary member, specified by key and index'''
        # check, if dictionary entry is a list
        if is_List(dictionary[key]):
            # yes, get value of a list element
            dictValue = dictionary[key][idx]

            # get data type, search for first valid element being not 'None'
            for obj in dictionary[key]:
                dataType = get_dataType(obj)
                if dataType != None:
                    # we found the data type
                    break
        else:
            # no, get value directly
            dictValue = dictionary[key]
            dataType = get_dataType(dictValue)

        return (dictValue, dataType)

    def __get_paramValue(self, params, tableEntry):
        '''get value of a parameter which is specified by tableEntry'''
        # get additional information from param tableEntry
        variableName = tableEntry["variable"]
        idx = tableEntry["idx"]
        scaleFactor = tableEntry["scaleFactor"]
        scaleFunction = tableEntry["f_read"]
        decimals = tableEntry["decimals"]


        # get actual parameter value and -type
        value, dataType = self.__getDictValueAndDataType(params,
                                        variableName, idx)
        # check value
        if value == None:
            # nothing more to do
            return value

        # is there a scale function?
        if scaleFunction != None:
            # carry out the scale function
            value = scaleFunction(value)

        # convert and optionally scale value
        if dataType == 'str':
            value_param = value
        elif dataType == 'float':
            float_value = value
            if (scaleFactor != None):
                float_value = float_value * scaleFactor
            if (decimals > 0):
                value_param = str(round(float_value, decimals))
            else:
                value_param = str(int(float_value))
        elif dataType == 'int':
            int_value = value
            if (scaleFactor != None):
                int_value = int(int_value * scaleFactor)
            value_param = str(int_value)
        else:
            ErrorMsg("__get_Values(): unimplemented handling of parameter %s" % variableName)

        return value_param

    def  __setDictValue(self, dictionary, key, idx, value):
        # check, if dictionary entry is a list
        if is_List(dictionary[key]):
            # yes, set value of a list element
            dictionary[key][idx] = value
        else:
            # no, set value directly
            dictionary[key] = value

    def __getDatFileNames(self, params):
        datFileNames = []
        names = params["userAirfoils"]

        for name in names:
            if (name != None):
                name = os.path.basename(name)
            datFileNames.append(name)

        return datFileNames

    def __set_paramValue(self, params, tableEntry, value:str):
        # get additional information from param tableEntry
        variableName = tableEntry["variable"]
        idx = tableEntry["idx"]
        scaleFactor = tableEntry["scaleFactor"]
        scaleFunction = tableEntry["f_write"]

        # check value
        if (value == 'None') or (value == ''):
            # just write None to the variable in the dictionary and return, no
            # need to check datatype etc.
            self.__setDictValue(params, variableName, idx, None)
            return

        # get actual parameter value and -type
        paramValue, dataType = self.__getDictValueAndDataType(params,
                                        variableName, idx)
        if dataType == 'str':
            self.__setDictValue(params, variableName, idx, value)

        elif dataType == 'float':
            float_value = float(value)
            if (scaleFactor != None):
                float_value = float_value / scaleFactor
                # is there a scale function?
                if scaleFunction != None:
                    # carry out the scale function
                    float_value = scaleFunction(float_value)
            self.__setDictValue(params, variableName, idx, float_value)

        elif dataType == 'int':
            int_value = int(value)
            if (scaleFactor != None):
                int_value = int(int_value / scaleFactor)
                # is there a scale function?
                if scaleFunction != None:
                    # carry out the scale function
                    int_value = scaleFunction(int_value)
            self.__setDictValue(params, variableName, idx, int_value)
        else:
            ErrorMsg("__set_paramValue(): unimplemented handling of parameter %s" % variableName)

    def __update_Entries(self, paramTable, textVars, planformIdx):
        # get parameters for active planform
        params = self.params[planformIdx]
        num = len(textVars)

        # copy all param values to textvars
        for idx in range(num):
            textVars[idx].set(self.__get_paramValue(params, paramTable[idx]))

    def __perform_update(self):
        if (self.postponeUpdate == True):
            return

        planformIdx = self.master.planformIdx
        params = self.params[planformIdx]

        # notify the unsaved changes
        self.set_unsavedChangesFlag(planformIdx)
        if params == {}:
            ErrorMsg("empty dictionary detected!")
            exit(-1)

        # perform update of the planform
        self.creatorInstances[planformIdx].update_planform(params)

        # notify the diagram frame about the change
        self.master.set_updateNeeded()


    def update_airfoilEntries(self, planformIdx):
        # Set Flag to avoid recursive calls
        self.update_airfoilEntries_active = True

        # get airfoil parameter table for active planform
        table = self.__get_airfoilParamsTable()
        textVars = self.airfoilParamsTextVars
        params = self.params[planformIdx]

        # update airfoil names, as they could have been changed
        self.airfoilNames[planformIdx] = self.creatorInstances[planformIdx].get_airfoilNames()

        # update option menues
        self.__update_OM_airfoilType(planformIdx)
        self.__update_OM_airfoilChoice(planformIdx)

        # update name of .dat file
        self.__update_datFileName(params, planformIdx)

        # update entries for airfoil parameters
        self.__update_Entries(table, textVars, planformIdx)

        # Clear Flag to avoid recursive calls
        self.update_airfoilEntries_active = False


    def update_Entries(self, planformIdx):
        # get basic parameter table for active planform
        table = self.__get_basicParamsTable()
        textVars = self.basicParamsTextVars

        # update entries for basic parameters
        self.__update_Entries(table, textVars, planformIdx)

        # Check for recursion
        if self.update_airfoilEntries_active == False:
            # update entries for airfoil parameters
            self.update_airfoilEntries(planformIdx)

    def __update_params(self, paramTable, params, entries):
        # get instance of planform-creator
        creatorInst:planform_creator = self.creatorInstances[self.master.planformIdx]
        change_detected = False

        for idx in range(len(paramTable)):
            paramTableEntry = paramTable[idx]
            entry = entries[idx]
            value_param = self.__get_paramValue(params, paramTableEntry)
            value_entry = entry.get()

            # compare if something has changed
            if (value_entry != value_param):
                self.__set_paramValue(params, paramTableEntry, value_entry)
                # set notification variable
                change_detected = True

            idx = idx + 1

        if (change_detected):
            self.__perform_update()

    def update_basicParams(self, command):
        planformIdx = self.master.planformIdx

        # get parameter table for active planform
        paramTable = self.__get_basicParamsTable()
        params = self.params[planformIdx]

        try:
            self.__update_params(paramTable, params, self.basicParamsEntries)
        except:
            ErrorMsg("update_basicParams() failed")
            pass

         # update option menues
        self.__update_OM_airfoilType(planformIdx)
        self.__update_OM_airfoilChoice(planformIdx)

        # Check for recursion
        if self.update_airfoilEntries_active == False:
            # update entries for airfoil parameters
            self.update_airfoilEntries(planformIdx)


    def update_airfoilParams(self, command):
        planformIdx = self.master.planformIdx

        # get parameter table for active planform
        paramTable = self.__get_airfoilParamsTable()
        params = self.params[planformIdx]

        # Update label showing the name of the datFile
        self.__update_datFileName(params, planformIdx)

        try:
            self.__update_params(paramTable, params, self.airfoilParamsEntries)
        except:
            ErrorMsg("update_airfoilParams() failed")
            pass

    def __update_OM_airfoilType(self, planformIdx):
        params = self.params[planformIdx]
        airfoilIdx = self.airfoilIdx[planformIdx]
        airfoilType = params["airfoilTypes"][airfoilIdx]

        self.OM_airfoilType.set(airfoilType)

    def __update_OM_airfoilChoice(self, planformIdx):
        params = self.params[planformIdx]
        airfoilIdx = self.airfoilIdx[planformIdx]
        airfoilNames = self.airfoilNames[planformIdx]

        self.OM_airfoilChoice.configure(values = airfoilNames)
        self.OM_airfoilChoice.set(airfoilNames[airfoilIdx])

    def changeFlap(self, x, y, idx):
        if idx == None:
            return

        # get instance of planform-creator
        creatorInst:planform_creator = self.creatorInstances[self.master.planformIdx]
        params = self.params[self.master.planformIdx]

        # limit to possible range
        y = np.clip(y, 0.0, 100.0)

        # round number of decimals
        depth = (round(y,1))

        # FIXME : also flapDepth of intermediate flap separation lines
        # FIXME : also change Flap position
        if (idx == 0):
            params["flapDepthRoot"] = depth
        else:
            params["flapDepthTip"] = depth

        # carry out functions needed for update
        self.__perform_update()

    def change_airfoilPosition(self, x, y, idx):
        if idx == None:
            return

        # get instance of planform-creator
        creatorInst:planform_creator = self.creatorInstances[self.master.planformIdx]
        params = self.params[self.master.planformIdx]

        # calculate position from x value (normalize)
        position = float(x/1000.0) # mm -> m
        position = creatorInst.normalize_position(position)

        # limit to possible range
        position = np.clip(position, 0.0, 1.0)

        # set new position in dictionary
        params["airfoilPositions"][idx] = position

        # carry out functions needed for update
        self.__perform_update()

    def __create_button(self, frame, button):
        text = button["txt"]
        callback = button["cmd"]
        param = button["param"]

        # create new button
        button = ctk.CTkButton(master=frame, text=text,
                                            fg_color=("gray75", "gray30"),
                                            command= lambda ztemp=param : callback(ztemp))
        return button

    def __add_appearanceModeMenu(self, frame, column, row):
        self.label_mode = ctk.CTkLabel(master=frame, text="Appearance Mode:")
        self.OM_apperanceMode = ctk.CTkOptionMenu(master=frame,
                                                        values=["Dark", "Light"],
                                                        command=self.__change_appearance_mode)
        self.__place_widgetsInRow([self.label_mode, self.OM_apperanceMode], column, row)
        return (row + 1)

    def __add_planformChoiceMenu(self, frame, column, row):
        self.label_planformChoice = self.__create_label(frame, "Choose planform:", fs_label)
        self.OM_planformChoice = ctk.CTkOptionMenu(master=frame,
                                                        values=self.planformNames,
                                                        command=self.__change_planform)
        self.__place_widgetsInRow([self.label_planformChoice, self.OM_planformChoice], column, row)
        return (row + 1)

    def __add_airfoilChoiceMenu(self, frame, column, row):
        self.label_airfoilChoice = self.__create_label(frame, "Choose airfoil:", fs_label)
        self.OM_airfoilChoice = ctk.CTkOptionMenu(master=frame,
                                                        values=self.airfoilNames[self.master.planformIdx],
                                                        command=self.__change_airfoil)
        self.__place_widgetsInRow([self.label_airfoilChoice, self.OM_airfoilChoice] ,column, row)
        return (row + 1)

    def __add_airfoilTypeMenu(self, frame, column, row):
        self.label_airfoilType = self.__create_label(frame, "Selected airfoil: type", fs_label)
        self.OM_airfoilType = ctk.CTkOptionMenu(master=frame,
                                                        values=airfoilTypes,
                                                        command=self.__change_airfoilType)
        self.__place_widgetsInRow([self.label_airfoilType, self.OM_airfoilType] ,column, row)
        return (row + 1)

    def __add_userAirfoilWidgets(self, frame, column, row):
        self.label_userAirfoil = self.__create_label(frame, "Selected (user) airfoil: .dat file", fs_label)
        self.label_datFile = self.__create_label(frame, '', fs_entry)
        self.label_datFile.configure(bg_color='gray')

        button = {"txt": "Choose file", "cmd" : self.__choose_datFile, "param" : None}
        self.button_datFile = self.__create_button(frame,button)

        self.__place_widgetsInRow([self.label_userAirfoil, self.label_datFile, self.button_datFile]
                                  ,column, row)
        return (row + 1)

    def __change_appearance_mode(self, new_appearanceMode):
        ctk.set_appearance_mode(new_appearanceMode)
        self.master.appearance_mode = new_appearanceMode

        # change the color of the scrollable frame manually,as this is not a
        # ctk frame
        bg_color = self.__get_bg_color(new_appearanceMode)
        self.frame_right.configure(bg = bg_color)
        self.canvas.configure(bg = bg_color)

        # change appearance mode in planform-creator
        for idx in range (len(self.creatorInstances)):
            creatorInst = self.creatorInstances[idx]
            creatorInst.set_appearance_mode(new_appearanceMode)

        # notify the diagram frame about the change
        self.master.set_updateNeeded()

         # maximize the window again using state property
        self.master.state('zoomed')

    def __change_planform(self, planformName):
        # convert planformName to an index
        planformIdx = self.planformNames.index(planformName)

        # check if idx has been changed
        if (self.master.planformIdx == planformIdx):
            return

        # set new idx
        self.master.planformIdx = planformIdx
        self.postponeUpdate = True

        # update entry-frame
        self.update_Entries(planformIdx)
        self.postponeUpdate = False

        # carry out functions needed for update
        self.__perform_update()


    def __change_airfoil(self, airfoilName):
        planformIdx = self.master.planformIdx
        params = self.params[planformIdx]
        airfoilNames = self.airfoilNames[planformIdx]

        # convert planformName to an index
        airfoilIdx = airfoilNames.index(airfoilName)

        # check if idx has been changed
        if (self.airfoilIdx[planformIdx] == airfoilIdx):
            return

        # set new idx
        self.airfoilIdx[planformIdx] = airfoilIdx
        self.postponeUpdate = True

        # Check for recursion
        if self.update_airfoilEntries_active == False:
            # update only airfoil entries, not basic parameter entries
            self.update_airfoilEntries(planformIdx)

        # carry out functions needed for update
        self.postponeUpdate = False
        self.__perform_update()


    def __change_airfoilType(self, airfoilType):
        planformIdx = self.master.planformIdx
        params = self.params[planformIdx]
        airfoilIdx = self.airfoilIdx[planformIdx]

        # set new type
        params["airfoilTypes"][airfoilIdx] = airfoilType
        self.postponeUpdate = True

        # Check for recursion
        if self.update_airfoilEntries_active == False:
            # update only airfoil entries, not basic parameter entries
            self.update_airfoilEntries(planformIdx)

        # carry out functions needed for update
        self.postponeUpdate = False
        self.__perform_update()


    def __choose_datFile(self, dummy):
        planformIdx = self.master.planformIdx
        params = self.params[planformIdx]
        airfoilIdx = self.airfoilIdx[planformIdx]

        # clear old filename
        params["userAirfoils"][airfoilIdx] = None

        filetypes = (('.dat files', '*.dat'),
                     ('All files', '*.*'))

        absFilename = tk.filedialog.askopenfilename(
                    title='Open a file',
                    initialdir=self.latestPath[planformIdx],
                    filetypes=filetypes)

        # Compute the relative file path
        relFilename = os.path.relpath(absFilename)

        # update name of .dat file in params (None is allowed value)
        params["userAirfoils"][airfoilIdx] = relFilename
        self.__update_datFileName(params, planformIdx)

        # store latest path
        self.latestPath[planformIdx] = os.path.dirname(filename)

        # carry out functions needed for update
        self.__perform_update()


    def __update_datFileName(self, params, planformIdx):
        params = self.params[planformIdx]
        airfoilIdx = self.airfoilIdx[planformIdx]
        types = params['airfoilTypes']

        # is it a 'user' airfoil ?
        if (types[airfoilIdx] == airfoilTypes[0]):
            # activate file selection button
            self.button_datFile.configure(state = "normal")

            # name of the .dat file shall be shown
            datFiles = self.__getDatFileNames(params)
            filename = datFiles[airfoilIdx]

            # check valid filename
            if (filename == None) or (filename == 'None') or (filename == ''):
                # no valid filename, this is an undesired state
                self.label_datFile.configure(text='')
                self.label_datFile.configure(bg_color='red')
            else:
                # valid filename, everything o.k.
                self.label_datFile.configure(text=filename)
                self.label_datFile.configure(bg_color='dim gray')
        else:
            # deactivate file selection button
            self.button_datFile.configure(state = "disabled")

            # no .dat file possible
            self.label_datFile.configure(text='')

            # hide the label by configuring it to background color
            bg_color = self.__get_bg_color(self.master.appearance_mode)
            self.label_datFile.configure(bg_color=bg_color_dark)


    def on_closing(self, event=0):
        self.destroy()

class diagram(ctk.CTkFrame):

    def __init__(self, parent, controller, bufferIdx, fig):
        ctk.CTkFrame.__init__(self, parent)

        # canvas
        canvas = FigureCanvasTkAgg(fig, self)
        canvas._tkcanvas.pack(fill=tk.BOTH, expand=1)
        canvas.draw()

        # index of targetValue that shall be graphically edited
        self._ind = None
        self.controller = controller

        canvas.mpl_connect('button_press_event', self.on_button_press)
        canvas.mpl_connect('button_release_event', self.on_button_release)
        canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        canvas.mpl_connect('scroll_event', self.on_scrollwheel_turn)

    def __get_ind_under_point(self, event):
        """
        Return the index of the point closest to the event position or *None*
        if no point is within catching range to the event position.
        """
        global ctrlFrame
        planformIdx = self.controller.master.planformIdx
        params = ctrlFrame.params[planformIdx]
        creatorInst = ctrlFrame.creatorInstances[planformIdx]

        # get current zoom factor
        zoom_factor = self.controller.get_zoom_factor()

        # check type of active diagram
        if ((self.controller.activeDiagram == diagTypes[2]) or
            (self.controller.activeDiagram == diagTypes[3])):
            mouse_x = event.xdata
            mouse_y = event.ydata

            # set ranges to catch points, consider zoomfactor
            # wingspan (m -->  mm) / 50 --> * 20.0
            catching_range = params["wingspan"] * 20.0 * zoom_factor
        else:
            #print("not implemented yet") #FIXME
            return None

        # search entry with closest coordinates.

        # change of FlapDepth requested ?
        if (self.controller.activeDiagram == diagTypes[2]):
            # get flap positions (x-coordinate and depth)
            flapPositions_x, flapPositions_y = creatorInst.get_flapPositions()
            num = len(flapPositions_x)
            for idx in range(num):
                x = flapPositions_x[idx]
                if ((abs(mouse_x - x) < catching_range)):
                    # found idx. BUT: at the moment, we only support changing
                    # flap depth at root and tip
                    if ((idx==0) or (idx==(num-1))):
                        return idx

        # change of airfoil-position requested ?
        elif (self.controller.activeDiagram == diagTypes[3]):
            airfoilPositions = creatorInst.get_airfoilPositions()
            airfoilReynolds = params["airfoilReynolds"]

            for idx in range(len(airfoilPositions)):
                x = airfoilPositions[idx]
                Re = airfoilReynolds[idx]

                # only airfoils with a specified position and without Re are movable
                if (x != None) and (Re == None):
                    if ((abs(mouse_x - x) < catching_range)):
                        return idx

        # nothing was found
        return None


    def on_scrollwheel_turn(self, event):
        """Callback for scrollwheel turn."""
        if event.inaxes is None:
            return
        self.controller.zoom_in_out(event)


    def on_button_press(self, event):
        """Callback for mouse button presses."""
        if event.inaxes is None:
            return
        if event.button == 1: # left mouse button
            # determine index of target point to change
            self._ind = self.__get_ind_under_point(event)
        elif event.button == 2: # middle mouse button / scrollwheel
            # restore default zoom
            self.controller.default_zoom()
        elif event.button == 3: # right mouse button
            # capture actual position
            self.controller.capture_position(event)
        else:
            return



    def on_button_release(self, event):
        """Callback for mouse button releases."""
        if event.button == 1: # left mouse button
            # clear index of target point to change
            self._ind = None
        else:
            return


    def on_mouse_move(self, event):
        """Callback for mouse movements."""
        global ctrlFrame

        if event.inaxes is None:
            return
        if event.button == 1:
            if self._ind is None:
                return
            # check type of active diagram
            if (self.controller.activeDiagram == diagTypes[2]):
                # Flap distribution
                x, y = event.xdata, event.ydata
                # set new flap depth
                ctrlFrame.changeFlap(x,y,self._ind)
            elif (self.controller.activeDiagram == diagTypes[3]):
                # airfoil distribution
                x, y = event.xdata, event.ydata
                # set new airfoil position
                ctrlFrame.change_airfoilPosition(x,y,self._ind)
        elif event.button == 3: # right mouse button
            # move visible area of the window
            self.controller.move_visibleArea(event)


# class creator diagrams, will store figures and also related data of a planform
# creator instance
class creatorDiagrams():
    def __init__(self, creatorInst):
        self.creatorInst = creatorInst
        self.figures = []
        self.axes = []
        self.initial_limits = {}
        self.zoomed_limits = {}
        self.offsets = {}
        self.zoom_factors = {}
        self.zoom_factors_old = {}
        self.captured_x_Position = 0.0
        self.captured_y_Position = 0.0

    def get_figures(self):
        return self.figures

    def get_axes(self):
        return self.axes

    def get_initial_limits(self):
        return self.initial_limits

    def get_zoomed_limits(self):
        return self.zoomed_limits

    def create_figures(self, scaleFactor):
        global num_diagrams
        global diagram_width
        global diagram_height

        # add figures for different diagram types
        figures = {}
        axes = {}
        limits = {}

        # set 'dark' style
        plt.style.use('dark_background')

        for diagType in diagTypes:
            # new figure
            x = diagram_width* scaleFactor
            y = diagram_height* scaleFactor
            fig = Figure(figsize=(x, y))
            ax = fig.add_subplot()

            # initial diagram (limits will be determined automatically)
            self.creatorInst.plot_diagram(diagType, ax, None, None)

            # get initial limits
            (x_limits, y_limits) = (ax.get_xlim(), ax.get_ylim())

            # append to lists
            figures[diagType] = fig
            axes[diagType] = ax
            limits[diagType] = (x_limits, y_limits)

        return (figures, axes, limits)

    def create_figures_buffered(self, scaleFactor):
        # create figures initially (two of each kind for buffering)
        for i in range(2):
            (figures, axes, limits) =  self.create_figures(scaleFactor)

            self.figures.append(figures)
            self.axes.append(axes)

            # initial limits unbuffered (only once each type)
            if (i == 0):
                self.initial_limits = limits

        # set zoomed limits
        self.zoomed_limits = deepcopy(self.initial_limits)

        # set initial zoomfactors and offsets
        for diagType in diagTypes:
            self.zoom_factors[diagType] = 1.0
            self.zoom_factors_old[diagType] = 1.0
            self.offsets[diagType] = (0.0, 0.0)

    def change_zoom_factor(self, step):
        zoomsteps = 30.0
        max_zoom = 1.0
        min_zoom = 0.08

        # get actual zoom factor for diagType
        zoom_factor = self.zoom_factors[self.activeDiagram]

        # store as "old" zoom factor
        self.zoom_factors_old[self.activeDiagram] = zoom_factor

        # change zoom factor, steps is either -1.0 (scroll down) or +1.0 (scroll up)
        zoom_factor = zoom_factor + (step/zoomsteps)

        # limit zoom_factor
        if (zoom_factor > max_zoom):
                zoom_factor = max_zoom
        elif (zoom_factor < min_zoom):
              zoom_factor = min_zoom

        # writeback
        self.zoom_factors[self.activeDiagram] = zoom_factor


    def get_zoom_factor(self):
        return self.zoom_factors[self.activeDiagram]


    def calculate_zoomed_limits(self, x_pos, y_pos):
        # get zoom factor for diagType
        zoom_factor = self.zoom_factors[self.activeDiagram]
        zoom_factor_old = self.zoom_factors_old[self.activeDiagram]
        zoom_change = zoom_factor / zoom_factor_old

        # get actual limits for diagType
        (x_limTuple, y_limTuple) = self.zoomed_limits[self.activeDiagram]
        (x_limits, y_limits) = (list(x_limTuple), list(y_limTuple))

        # adjust limits relative to mouse position
        x_left = x_pos - x_limits[0]
        x_right = x_limits[1] - x_pos
        x_left = x_left * zoom_change
        x_right = x_right * zoom_change
        x_left_lim = x_pos - x_left
        x_right_lim = x_pos + x_right

        y_below = y_pos - y_limits[0]
        y_beyond = y_limits[1] - y_pos
        y_below = y_below * zoom_change
        y_beyond = y_beyond * zoom_change
        y_below_lim = y_pos - y_below
        y_beyond_lim = y_pos + y_beyond

        # write zoomed limits
        self.zoomed_limits[self.activeDiagram] = ((x_left_lim, x_right_lim),
                                                  (y_below_lim, y_beyond_lim))


    def zoom_in_out(self, event):
        # check if there is an update going on
        if (self.master.get_updateNeeded()):
            return

        # change zoom_factor first
        self.change_zoom_factor(event.step)

        # calculate zoomed_limits
        self.calculate_zoomed_limits(event.xdata, event.ydata)

        # set notification flag / update diagram
        self.master.set_updateNeeded()


    def capture_position(self, event):
        # get curretn offsets
        (x_offset, y_offset) = self.offsets[self.activeDiagram]
        # capture new postion, including old offsets
        self.captured_x_Position = event.x - x_offset
        self.captured_y_Position = event.y - y_offset


    def move_visibleArea(self, event):
        # calculate offsets for x, y
        x_offset = event.x - self.captured_x_Position
        y_offset = event.y - self.captured_y_Position

        # store offsets for active diagram type
        self.offsets[self.activeDiagram] = (x_offset, y_offset)

         # set notification flag / update diagram
        self.master.set_updateNeeded()


    def default_zoom(self):
        # set zoom factor for active diagram to default
        self.zoom_factors[self.activeDiagram] = 1.0
        self.zoom_factors_old[self.activeDiagram] = 1.0

        # restore initial limits for active diagram
        self.zoomed_limits[self.activeDiagram] =\
                self.initial_limits[self.activeDiagram]

        # set offsets to zero
        self.offsets[self.activeDiagram] = (0.0, 0.0)

        # set notification flag / update diagram
        self.master.set_updateNeeded()


    def get_limits(self):
        # get zoomed limits
        (x_limTuple, y_limTuple) = self.zoomed_limits[self.activeDiagram]
        (x_limits, y_limits) = (list(x_limTuple), list(y_limTuple))

        # get offsets
        (x_offset, y_offset) = self.offsets[self.activeDiagram]

        # get diagram width and height
        x_width = x_limits[1] - x_limits[0]
        y_width = y_limits[1] - y_limits[0]

        # determine scaler, depending on the screen resolution
        scaler = 1000.0 * self.scaleFactor

        # scale offsets to diagram width / height and screen resoultion
        x_offset = x_offset * x_width / scaler
        y_offset = y_offset * y_width / scaler

        # shift the limits by offset values
        x_limits[0] = x_limits[0] - x_offset
        x_limits[1] = x_limits[1] - x_offset
        y_limits[0] = y_limits[0] - y_offset
        y_limits[1] = y_limits[1] - y_offset

        return (tuple(x_limits), tuple(y_limits))


# class diagram frame, shows the graphical output of the planform creator
class diagram_frame():
    def __init__(self, master, side, creatorInstances:planform_creator, scaleFactor):
        self.master = master
        self.creatorInstances = creatorInstances
        self.scaleFactor = scaleFactor
        self.Diagrams = []
        self.figures = []
        self.axes = []
        self.initial_limits = {}
        self.zoomed_limits = {}
        self.offsets = {}
        self.zoom_factors = {}
        self.zoom_factors_old = {}
        self.captured_x_Position = 0.0
        self.captured_y_Position = 0.0

        for creatorInst in creatorInstances:
            diagrams = creatorDiagrams(creatorInst)
            diagrams.create_figures_buffered(scaleFactor)
            self.Diagrams.append(diagrams)


        # create figures initially (two of each kind for buffering)
        for i in range(2):
            (figures, axes, limits) =  self.create_figures(creatorInstances[0], scaleFactor)

            self.figures.append(figures)
            self.axes.append(axes)

            # initial limits unbuffered (only once each type)
            if (i == 0):
                self.initial_limits = limits

        # set zoomed limits
        self.zoomed_limits = deepcopy(self.initial_limits)

        # set initial zoomfactors and offsets
        for diagType in diagTypes:
            self.zoom_factors[diagType] = 1.0
            self.zoom_factors_old[diagType] = 1.0
            self.offsets[diagType] = (0.0, 0.0)

        # create new frame (container)
        self.container = ctk.CTkFrame(master=master, width=180,
                                            corner_radius=0)
        self.container.pack(side = side, fill=tk.BOTH, expand=1)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # empty list of frame dictionaries
        self.frames = []

        # create frame for each diagram class (two of each kind for buffering)
        for i in range(2):
            self.frames.append(self.create_frames(i))

        # set initial value of active buffer idx
        self.activeBufferIdx = 0

            # set initial value of active diagram
        self.activeDiagram = diagTypes[0]

        # show initial diagram
        self.master.set_updateNeeded()
        self.update_diagram(master)

    def create_figures(self, creatorInst, scaleFactor):
        global num_diagrams
        global diagram_width
        global diagram_height

        # add figures for different diagram types
        figures = {}
        axes = {}
        limits = {}

        # set 'dark' style
        plt.style.use('dark_background')

        for diagType in diagTypes:
            # new figure
            x = diagram_width* scaleFactor
            y = diagram_height* scaleFactor
            fig = Figure(figsize=(x, y))
            ax = fig.add_subplot()

            # initial diagram (limits will be determined automatically)
            creatorInst.plot_diagram(diagType, ax, None, None)

            # get initial limits
            (x_limits, y_limits) = (ax.get_xlim(), ax.get_ylim())

            # append to lists
            figures[diagType] = fig
            axes[diagType] = ax
            limits[diagType] = (x_limits, y_limits)

        return (figures, axes, limits)

    def create_frames(self, bufferIdx):
        # empty dictionary of frames
        frames = {}

        for diagType in diagTypes:
            frame = diagram(self.container, self, bufferIdx,
                        self.figures[bufferIdx][diagType])
            frame.grid(row=0, column=0, sticky="nsew")

            # put into dictionary
            frames[diagType] = frame

        return frames

    def change_zoom_factor(self, step):
        zoomsteps = 30.0
        max_zoom = 1.0
        min_zoom = 0.08

        # get actual zoom factor for diagType
        zoom_factor = self.zoom_factors[self.activeDiagram]

        # store as "old" zoom factor
        self.zoom_factors_old[self.activeDiagram] = zoom_factor

        # change zoom factor, steps is either -1.0 (scroll down) or +1.0 (scroll up)
        zoom_factor = zoom_factor + (step/zoomsteps)

        # limit zoom_factor
        if (zoom_factor > max_zoom):
                zoom_factor = max_zoom
        elif (zoom_factor < min_zoom):
              zoom_factor = min_zoom

        # writeback
        self.zoom_factors[self.activeDiagram] = zoom_factor


    def get_zoom_factor(self):
        return self.zoom_factors[self.activeDiagram]


    def calculate_zoomed_limits(self, x_pos, y_pos):
        # get zoom factor for diagType
        zoom_factor = self.zoom_factors[self.activeDiagram]
        zoom_factor_old = self.zoom_factors_old[self.activeDiagram]
        zoom_change = zoom_factor / zoom_factor_old

        # get actual limits for diagType
        (x_limTuple, y_limTuple) = self.zoomed_limits[self.activeDiagram]
        (x_limits, y_limits) = (list(x_limTuple), list(y_limTuple))

        # adjust limits relative to mouse position
        x_left = x_pos - x_limits[0]
        x_right = x_limits[1] - x_pos
        x_left = x_left * zoom_change
        x_right = x_right * zoom_change
        x_left_lim = x_pos - x_left
        x_right_lim = x_pos + x_right

        y_below = y_pos - y_limits[0]
        y_beyond = y_limits[1] - y_pos
        y_below = y_below * zoom_change
        y_beyond = y_beyond * zoom_change
        y_below_lim = y_pos - y_below
        y_beyond_lim = y_pos + y_beyond

        # write zoomed limits
        self.zoomed_limits[self.activeDiagram] = ((x_left_lim, x_right_lim),
                                                  (y_below_lim, y_beyond_lim))


    def zoom_in_out(self, event):
        # check if there is an update going on
        if (self.master.get_updateNeeded()):
            return

        # change zoom_factor first
        self.change_zoom_factor(event.step)

        # calculate zoomed_limits
        self.calculate_zoomed_limits(event.xdata, event.ydata)

        # set notification flag / update diagram
        self.master.set_updateNeeded()


    def capture_position(self, event):
        # get curretn offsets
        (x_offset, y_offset) = self.offsets[self.activeDiagram]
        # capture new postion, including old offsets
        self.captured_x_Position = event.x - x_offset
        self.captured_y_Position = event.y - y_offset


    def move_visibleArea(self, event):
        # calculate offsets for x, y
        x_offset = event.x - self.captured_x_Position
        y_offset = event.y - self.captured_y_Position

        # store offsets for active diagram type
        self.offsets[self.activeDiagram] = (x_offset, y_offset)

         # set notification flag / update diagram
        self.master.set_updateNeeded()


    def default_zoom(self):
        # set zoom factor for active diagram to default
        self.zoom_factors[self.activeDiagram] = 1.0
        self.zoom_factors_old[self.activeDiagram] = 1.0

        # restore initial limits for active diagram
        self.zoomed_limits[self.activeDiagram] =\
                self.initial_limits[self.activeDiagram]

        # set offsets to zero
        self.offsets[self.activeDiagram] = (0.0, 0.0)

        # set notification flag / update diagram
        self.master.set_updateNeeded()


    def get_limits(self):
        # get zoomed limits
        (x_limTuple, y_limTuple) = self.zoomed_limits[self.activeDiagram]
        (x_limits, y_limits) = (list(x_limTuple), list(y_limTuple))

        # get offsets
        (x_offset, y_offset) = self.offsets[self.activeDiagram]

        # get diagram width and height
        x_width = x_limits[1] - x_limits[0]
        y_width = y_limits[1] - y_limits[0]

        # determine scaler, depending on the screen resolution
        scaler = 1000.0 * self.scaleFactor

        # scale offsets to diagram width / height and screen resoultion
        x_offset = x_offset * x_width / scaler
        y_offset = y_offset * y_width / scaler

        # shift the limits by offset values
        x_limits[0] = x_limits[0] - x_offset
        x_limits[1] = x_limits[1] - x_offset
        y_limits[0] = y_limits[0] - y_offset
        y_limits[1] = y_limits[1] - y_offset

        return (tuple(x_limits), tuple(y_limits))

    def get_controlPoints(self):
        # get instance of planform-creator
        creatorInst:planform_creator = self.creatorInstances[self.master.planformIdx]

        # get control points
        controlPoints = creatorInst.newWing.chordDistribution.controlPoints
        return controlPoints


    def update_diagram(self, master):
        creatorInst = self.creatorInstances[master.planformIdx]

        # check if an update has to be carried out
        if (self.master.get_updateNeeded()):
            # get buffer idx for modifing the frames that are currently not visible
            if self.activeBufferIdx == 0:
                backgroundIdx = 1
            else:
                backgroundIdx = 0

            # get limits for active diagram
            (x_limits, y_limits) = self.get_limits()

            # update active diagram in background
            ax = self.axes[backgroundIdx][self.activeDiagram]

            # clear existing diagram
            ax.clear()

            # plot new diagram
            creatorInst.plot_diagram(self.activeDiagram, ax, x_limits, y_limits)

            # update figure
            figure = self.figures[backgroundIdx][self.activeDiagram]
            figure.canvas.draw()

            # show the updated frame
            frame = self.frames[backgroundIdx][self.activeDiagram]
            frame.tkraise()

            # switch buffer index
            self.activeBufferIdx = backgroundIdx

            # clear notification variable
            self.master.clear_updateNeeded()


    def change_diagram(self, diagram):
        if (self.activeDiagram != diagram):
            # set new active diagram
            self.activeDiagram = diagram
            # trigger update of diagram frame
            self.master.set_updateNeeded()


# main application
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        global ctrlFrame
        global creatorInstances

        self.app_running = False

        # index of active planform
        self.planformIdx = 0
        self.appearance_mode = "Dark" # Modes: "System" (standard), "Dark", "Light"
        self.exportFlags = []

        # configure customtkinter
        ctk.set_appearance_mode(self.appearance_mode)    # Modes: "System" (standard), "Dark", "Light"
        ctk.set_default_color_theme("blue") # Themes: "blue" (standard), "green", "dark-blue"

        # set window title
        self.title("Planform Creator")

        # maximize the window using state property
        self.state('zoomed')

        # call .on_closing() when app gets closed
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # determine screen size and scale factor
        width = self.winfo_screenwidth()
        heigth = self.winfo_screenheight()
        scaleFactor = width/1980

        for creatorInst in creatorInstances:
            # set screen parameters
            creatorInst.set_screenParams(width, heigth)
            # append export flag for planform export dialog
            self.exportFlags.append((tk.BooleanVar(value=True)))

        # notification variable for updating the diagrams
        self.updateNeeded = 0

        # create diagram frame, which is on the top
        self.frame_top = diagram_frame(self, tk.TOP, creatorInstances,
         scaleFactor)

        # create control frame, which is on the bottom
        self.frame_bottom = control_frame(self, tk.BOTTOM,
         self.get_Buttons(), creatorInstances,
          scaleFactor)

        # set global variable
        ctrlFrame = self.frame_bottom
    def __center(self, win):
        """
        centers a tkinter window
        :param win: the main window or Toplevel window to center
        """
        win.update_idletasks()
        width = win.winfo_width()
        frm_width = win.winfo_rootx() - win.winfo_x()
        win_width = width + 2 * frm_width
        height = win.winfo_height()
        titlebar_height = win.winfo_rooty() - win.winfo_y()
        win_height = height + titlebar_height + frm_width
        x = win.winfo_screenwidth() // 2 - win_width // 2
        y = win.winfo_screenheight() // 2 - win_height // 2
        win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        win.deiconify()

    def get_Buttons(self):
        headlines = []
        buttons = []
        buttonsColumn = []

        # 1st column
        headlines.append("Choose diagram")
        for diagType in diagTypes:
            buttonsColumn.append({"txt": diagType, "cmd" : self.set_diagram, "param" : diagType})
        buttons.append(buttonsColumn)

        # 2nd column
        headlines.append("Planform actions")
        buttonsColumn = [{"txt": "Add planform",     "cmd" : self.add_planform,     "param" : None},
                         {"txt": "Remove planform",  "cmd" : self.remove_planform,  "param" : None},
                         {"txt": "Export planforms", "cmd" : self.export_planformsDialog, "param" : None}
                        ]
        buttons.append(buttonsColumn)

        # 3nd column
        headlines.append("Airfoil actions")
        buttonsColumn = [{"txt": "Add airfoil",     "cmd" : self.add_airfoil,     "param" : None},
                         {"txt": "Remove airfoil",  "cmd" : self.remove_airfoil,  "param" : None},
                         {"txt": "Export airfoils", "cmd" : self.export_airfoils, "param" : None}
                        ]
        buttons.append(buttonsColumn)

        # 4th column
        headlines.append("Parameter actions")
        buttonsColumn = [{"txt": "Load",  "cmd" : self.load,  "param" : None},
                         {"txt": "Save",  "cmd" : self.save,  "param" : None},
                         {"txt": "Reset", "cmd" : self.reset, "param" : None}
                        ]
        buttons.append(buttonsColumn)


        return (headlines, buttons)

    def set_updateNeeded(self):
        self.updateNeeded = True

    def get_updateNeeded(self):
        return self.updateNeeded

    def clear_updateNeeded(self):
        self.updateNeeded = False

    def set_diagram(self, newDiagram):
        self.frame_top.change_diagram(newDiagram)

    def load(self, dummy):
        creatorInst = creatorInstances[self.planformIdx]
        planformName = self.frame_bottom.planformNames[self.planformIdx]
        filePath = bs + ressourcesPath + bs + planformFiles[self.planformIdx]

        # FIXME use filePath, file selector dialog?
        result = creatorInst.load()

        # check if everything was o.k.
        if result == 0:
            creatorInst.update_planform(creatorInst.get_params())
            self.frame_bottom.update_Entries(self.planformIdx)
            self.frame_bottom.clear_unsavedChangesFlag(self.planformIdx)
            self.updateNeeded = True

            # create message text
            msgText =  "Parameters of planform \'%s\'\n" % planformName
            msgText += " have been successfully loaded from file\n\'%s\'\n" % filePath
            messagebox.showinfo(title='Load', message=msgText)
        else:
            # create message text
            msgText =  "Error, loading parameters of planform \'%s\'\n" % planformName
            msgText += "from file \'%s\'\nfailed, errorcode %d\n" % (filePath, result)
            messagebox.showerror(title='Load', message=msgText )

    def add_planform(self, dummy):
        self.notImplemented_Dialog() #FIXME implement

    def remove_planform(self, dummy):
        self.notImplemented_Dialog() #FIXME implement

    def export_planformsDialog(self, dummy):
        exportWindow = ctk.CTkToplevel()
        self.exportWindow = exportWindow
        exportWindow.wm_title("Export planforms")

        planformnames = self.frame_bottom.planformNames
        num = len(planformnames)
        row = 1

        label = ctk.CTkLabel(master=exportWindow, text="Select planforms to be exported:",
        text_font=(main_font, fs_label), pady=10, padx=20, anchor="e")
        label.grid(row=row, column=0)

        for idx in range(num):
            checkbox = ctk.CTkCheckBox(master=exportWindow, text=planformnames[idx],
                       variable=self.exportFlags[idx], text_font=(main_font, fs_label))
            checkbox.grid(row=row, column=1, pady=10, padx=20, sticky="w")
            row += 1

        button = ctk.CTkButton(exportWindow, text="OK", command=self.export_planforms)
        button.grid(row=row+1, column=0, pady=10, padx=20, sticky="e")
        button = ctk.CTkButton(exportWindow, text="Cancel", command=self.cancel_export_planforms)
        button.grid(row=row+1, column=1, pady=10, padx=20, sticky="w")
        self.__center(exportWindow)

    def cancel_export_planforms(self):
        self.exportWindow.destroy()

    def export_planforms(self):
        self.exportWindow.destroy()
        num = len(creatorInstances)
        exportNames = []
        title='Export planforms'
        filePath = buildPath + bs + planformsPath

        for idx in range(num):
            # check if planform shall be exported
            if (self.exportFlags[idx].get() == True):
                result = creatorInstances[idx].export_planform(filePath)
                exportNames.append(ctrlFrame.planformNames[idx])
                # check result
                if result != 0:
                    break

        if result == 0:
            # create message text
            msgText =  "The selected planforms:\n\n"
            for name in exportNames:
                msgText += "%s\n" % name

            msgText += "\nhave been successfully exported to file\n\'%s\'\n" % filePath
            messagebox.showinfo(title=title, message=msgText)
        else:
            # create message text
            msgText =  "Error, export of selected planforms to file\n"
            msgText += " \'%s\'\nfailed, errorcode %d\n" % (filePath, result)
            messagebox.showerror(title=title, message=msgText )

    def add_airfoil(self, dummy):
        self.notImplemented_Dialog() #FIXME implement

    def remove_airfoil(self, dummy):
        self.notImplemented_Dialog() #FIXME implement

    def export_airfoils(self, dummy):
        creatorInst = creatorInstances[self.planformIdx]
        planformName = self.frame_bottom.planformNames[self.planformIdx]
        filePath = bs + buildPath + bs + airfoilPath
        title = 'Export airfoils'

        # call function of planform creator
        (result, userAirfoils, blendedAirfoils) = creatorInst.export_airfoils()

        msgExported =  "The following airfoils of planform \'%s\'\n" % planformName
        msgExported += "have been successfully exported to path \'%s\':\n\n" % filePath
        msgExported += "\'user\' airfoils:\n"
        for airfoil in userAirfoils:
            msgExported += "%s\n" % airfoil

        msgExported += "\n\'blend\' airfoils:\n"
        for airfoil in blendedAirfoils:
            msgExported += "%s\n" % airfoil

        # check if everything was o.k.
        if result == 0:
            # create message text
            msgText =  msgExported
            msgText += "\nPlease use \'The Strak Machine\' to create \'opt\' airfoils (if any):"
            messagebox.showinfo(title=title, message=msgText)
        else:
            # create message text
            msgText =  "Error, exporting airfoils of planform \'%s\'\n" % planformName
            msgText += "to path \'%s\'\nfailed, errorcode: %d\n\n" % (filePath, result)
            msgText += "There might be some \'user\', \'opt\' or \'blend\' airfoils missing.\n"
            msgText += "Please make sure, that all \'user\' airfoils have been assigned correctly "
            msgText += "and use \'The Strak Machine\' to create missing \'opt\' airfoils (if any):\n\n"
            msgText += msgExported
            messagebox.showerror(title=title, message=msgText )

    def save(self, dummy):
        creatorInst = creatorInstances[self.planformIdx]
        planformName = self.frame_bottom.planformNames[self.planformIdx]
        filePath = bs + ressourcesPath + bs + planformFiles[self.planformIdx]

        # FIXME use filePath, file selector dialog?
        result = creatorInst.save()

        # check if everything was o.k.
        if result == 0:
            # create message text
            msgText =  "Parameters of planform \'%s\'\n" % planformName
            msgText += "have been successfully saved to file \'%s\'" % filePath
            messagebox.showinfo(title='Save', message=msgText )
            self.frame_bottom.clear_unsavedChangesFlag(self.planformIdx)
        else:
            # create message text
            msgText =  "Error, saving parameters of planform \'%s\'\n" % planformName
            msgText += "to file \'%s\'\nfailed, errorcode: %d" % (filePath, result)
            messagebox.showerror(title='Save', message=msgText )


    def reset(self, dummy):
        self.notImplemented_Dialog() #FIXME implement
##        creatorInst = creatorInstances[self.planformIdx]
##        result = creatorInst.reset()
##        if (result == 0):
##           self.frame_bottom.set_unsavedChangesFlag(self.planformIdx)
##           self.updateNeeded = True

    def start(self):
        self.app_running = True
        while self.app_running:
            self.update_idletasks()
            self.update()
            self.frame_top.update_diagram(self)

        self.destroy()

    def notImplemented_Dialog(self):
        # create mesage text
        msgText =  "   Sorry...\n"
        msgText += "   Function has not been not implemented yet   \n"

        messagebox.showwarning(title='Not implemented :-(', message=msgText )


    def unsaved_changesDialog(self, flags):
        # create complete dialog text
        dialogText =  "There are unsaved changes...\n"
        dialogText += "To quit without saving type \'quit'\n"
        dialogText += "To quit and save the changes type \'save'"

        # create dialog
        dialog = ctk.CTkInputDialog(master=None, text=dialogText,
                        title = 'Unsaved Changes detected')

        # get user input, what to do
        inputstring = dialog.get_input()
        return inputstring


    def save_unsavedChanges(self, flags):
        num = len(flags)

        # check all flags,
        for i in range(num):
            if (flags[i] == True):
                # save the data of the airfoil. We have no flag for the
                # root airfoil, so start at the first strak airfoil
                print("FIXME")


    def on_closing(self, event=0):
        unsavedChanges = False

        # get unsaved changes flags
        flags = self.frame_bottom.get_unsavedChangesFlags()

        # check all flags
        for flag in flags:
            if (flag == True):
                unsavedChanges = True

        if unsavedChanges:
            # we have unsaved changes - get user input, what to do
            userInput = self.unsaved_changesDialog(flags)

            if userInput == 'quit':
                # quit without saving
                self.app_running = False
            elif userInput == 'save':
                # first save, then quit
                self.save_unsavedChanges(flags)
                self.app_running = False
        else:
            # no unsaved changes, just quit
            self.app_running = False

if __name__ == "__main__":
    # init colorama
    init()

    # bugfix (wrong scaling matplotlib)
    ctypes.windll.shcore.SetProcessDpiAwareness(0)

     # init planform creator instances
    NoteMsg("Starting Planform Creator...")

    # check working-directory, have we been started from "scripts"-dir? (Debugging)
    currentDir = os.getcwd()
    if (currentDir.find("scripts")>=0):
        startedFromScriptsFolder = True
        os.chdir("..")
    else:
        startedFromScriptsFolder = False

    try:
        for fileName in planformFiles:
            newInst = planform_creator(ressourcesPath + bs + fileName)
            creatorInstances.append(newInst)
    except:
        ErrorMsg("Planform Creator could not be started")
        input("Press any key to quit")
        exit(-1)

    NoteMsg("Starting Graphical User Interface...")
    app = App()
    app.start()