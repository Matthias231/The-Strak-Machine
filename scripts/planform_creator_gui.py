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
from tkinter import ttk
import customtkinter
import os
from PIL import ImageTk, Image
from colorama import init
from copy import deepcopy

# imports to use matplotlib together with tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# imports from strak machine
from strak_machine import (ErrorMsg, WarningMsg, NoteMsg, DoneMsg,
                           bs, ressourcesPath)

# imports from planform creator
from planform_creator_new import (planform_creator, diagTypes)

# some global variables
num_diagrams = len(diagTypes)
diagram_width = 10
diagram_height = 7
controlFrame = None
creatorInstances = []

# names of the planformfiles
planformFiles = ["planformdata_wing.txt", "planformdata_tail.txt"]

bg_color_light = "#DDDDDD"
bg_color_dark =  "#222222"

# class control frame, change the input-variables / parameters of the
# planform creator
class control_frame():
    def __init__(self, master, side, left_Buttons, right_Buttons):
        # store some variables in own class data structure
        self.master = master
        self.unsavedChangesFlags = [0,0]

        # determine screen size
        self.width = self.master.winfo_screenwidth()
        self.heigth = self.master.winfo_screenheight()

        # create top frame
        self.frame_top = customtkinter.CTkFrame(master=master, width=180,
                                            corner_radius=0)

        # create scrollable Frame
        self.container = customtkinter.CTkFrame(master=master, width=180,
                                            corner_radius=0)

        self.canvas = tk.Canvas(self.container, bg=bg_color_dark,
                                 highlightthickness=0)
        self.scrollbar_v = customtkinter.CTkScrollbar(self.container,
                                                command=self.canvas.yview)

        self.frame_bottom  = tk.Frame(self.canvas, width=180,
                                         bg = bg_color_dark)

        self.frame_bottom.bind("<Configure>", self.OnFrameConfigure)

        self.canvas.create_window((10, 10), window=self.frame_bottom , anchor="ne")
        self.canvas.configure(yscrollcommand=self.scrollbar_v.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_v.pack(side="right", fill="y")

        # init nextRow (where to place next widget)
        self.nextRow = 0

        # add different widgets to upper frame (not scrollable)
        self.add_label(self.frame_top)
        self.add_buttons(self.frame_top, left_Buttons, right_Buttons)
        self.add_appearanceModeMenu(self.frame_top)

        self.nextRow = 0

        # show upper frame
        self.frame_top.pack(side = 'top', fill=tk.BOTH)

        # show lower frame
        self.container.pack(side = 'bottom', fill=tk.BOTH, expand=1)


    def OnFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


    def get_valuesFromDict(self, targetValue):
        # type of oppoint
        mode = targetValue["type"]

        if (mode == 'spec-cl'):
            # oppoint is lift (CL)
            oppoint = round(targetValue["oppoint"], CL_decimals)
            # target is drag (CD)
            target = round(targetValue["target"], CD_decimals)
        elif (mode == 'spec-al'):
            # oppoint is angle of attack (alpha)
            oppoint = round(targetValue["oppoint"], AL_decimals)
            # target is lift (CL)
            target = round(targetValue["target"], CL_decimals)
        else:
            ErrorMsg("undefined oppoint type %s" % mode)
            return (None, None, None)

        weighting = targetValue["weighting"]
        if weighting != None:
            weighting = round(weighting, 1)

        return (mode, oppoint, target, weighting)


    def write_valuesToDict(self, idx, mode, oppoint, target, weighting):
        targetValue = self.targetValues[idx]

        if (mode == 'spec-cl'):
            # oppoint is lift (CL)
            oppoint = round(oppoint, CL_decimals)

            # target is drag (CD)
            target = round(target, CD_decimals)
        elif (mode == 'spec-al'):
            # oppoint is angle of attack (alpha)
            oppoint = round(oppoint, AL_decimals)
            # target is lift (CL)
            target = round(target, CL_decimals)
        else:
            ErrorMsg("undefined oppoint type %s" % mode)

        targetValue["oppoint"] = oppoint
        targetValue["target"] = target

        if (weighting != None):
            weighting = round(weighting, 1)
        targetValue["weighting"] = weighting

        #targetValue["type"] = mode # FIXME We do not support changing mode at the moment
        self.targetValues[idx] = targetValue


    def set_unsavedChangesFlag(self, planformIdx):
        try:
            i = planformIdx-1
            self.unsavedChangesFlags[i] = True
            self.label_unsavedChanges[i].configure(text = 'unsaved changes')
        except:
            ErrorMsg("invalid planformIdx: %d" & planformIdx)


    def clear_unsavedChangesFlag(self, planformIdx):
        try:
            i = planformIdx
            self.unsavedChangesFlags[i] = False
            self.label_unsavedChanges[i].configure(text = '')
        except:
            ErrorMsg("invalid planformIdx: %d" % planformIdx)


    def get_unsavedChangesFlags(self):
        return (self.unsavedChangesFlags)


    def place_widgets(self, widget1, widget2):
        if widget1 != None:
            widget1.grid(row=self.nextRow, column=0, pady=5, padx=5, sticky="e")

        if widget2 != None:
            widget2.grid(row=self.nextRow, column=1, pady=5, padx=5, sticky="w")

        self.nextRow = self.nextRow + 1


    def place_3_widgets(self, widget1, widget2, widget3):
        if widget1 != None:
            widget1.grid(row=self.nextRow, column=0, pady=0, padx=1, sticky="e")

        if widget2 != None:
            widget2.grid(row=self.nextRow, column=1, pady=0, padx=1, sticky="e")

        if widget3 != None:
            widget3.grid(row=self.nextRow, column=2, pady=0, padx=1, sticky="e")
        self.nextRow = self.nextRow + 1


    def add_label(self, frame):
        # Label
        label = customtkinter.CTkLabel(master=frame,
                                              text="Select diagram",
                                              text_font=("Roboto Medium", -16))
        self.place_widgets(label, None)


    def add_buttons(self, frame, left_Buttons, right_Buttons):
        buttonsLeft = []
        buttonsRight = []

        # create all buttons and add to list
        for button in left_Buttons:
            buttonsLeft.append(self.create_button(frame, button))

        for button in right_Buttons:
            buttonsRight.append(self.create_button(frame, button))


        numButtonsLeft = len(buttonsLeft)
        numButtonsRight = len(buttonsRight)
        numTotal = max(numButtonsLeft, numButtonsRight)

        # place buttons
        for idx in range(numTotal):
            if idx < numButtonsLeft:
                left = buttonsLeft[idx]
            else:
                left = None

            if idx < numButtonsRight:
                right = buttonsRight[idx]
            else:
                right = None

            self.place_widgets(left, right)


    def create_button(self, frame, button):
        text = button["txt"]
        callback = button["cmd"]
        param = button["param"]

        # create new button
        button = customtkinter.CTkButton(master=frame, text=text,
                                            fg_color=("gray75", "gray30"),
                                            command= lambda ztemp=param : callback(ztemp))
        return button

    def add_appearanceModeMenu(self, frame):
        self.label_mode = customtkinter.CTkLabel(master=frame, text="Appearance Mode:")
        self.optionmenu_1 = customtkinter.CTkOptionMenu(master=frame,
                                                        values=["Dark", "Light"],
                                                        command=self.change_appearance_mode)
        self.place_widgets(self.label_mode, self.optionmenu_1)

    def add_blankRow(self):
        self.nextRow = self.nextRow + 1


    def change_appearance_mode(self, new_appearanceMode):
        customtkinter.set_appearance_mode(new_appearanceMode)

        # change the color of the scrollable frame manually,as this is not a
        # customtkinter frame
        if (new_appearanceMode == 'Dark'):
            self.frame_bottom.configure(bg = bg_color_dark)
            self.canvas.configure(bg = bg_color_dark)
        else:
            self.frame_bottom.configure(bg = bg_color_light)
            self.canvas.configure(bg = bg_color_light)

        # change appearance mode in strak machine
        self.strak_machine.set_appearance_mode(new_appearanceMode)

        # notify the diagram frame about the change
        self.master.set_updateNeeded()

         # maximize the window again using state property
        self.master.state('zoomed')



    def on_closing(self, event=0):
        self.destroy()

class diagram(customtkinter.CTkFrame):

    def __init__(self, parent, controller, bufferIdx, fig):
        customtkinter.CTkFrame.__init__(self, parent)

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

    def get_ind_under_point(self, event):
        """
        Return the index of the point closest to the event position or *None*
        if no point is within catching range to the event position.
        """
        global targetValues
        global controlFrame

        # set ranges to catch points, consider zoomfactor
        zoom_factor = self.controller.get_zoom_factor()
        catching_range_oppoint = 0.01 * zoom_factor
        catching_range_targetValue = 0.001 * zoom_factor

        mouse_target = event.xdata
        mouse_oppoint = event.ydata

        # check type of active diagram
        if (self.controller.activeDiagram == "CL_CD_diagram"):
            edit_mode = 'spec-cl'
            mouse_target = event.xdata  # target  -> CD
            mouse_oppoint = event.ydata # oppoint -> CL
        elif (self.controller.activeDiagram == "CLCD_CL_diagram"):
            edit_mode = 'spec-cl'
            mouse_oppoint = event.xdata # oppoint -> CL
            # convert y-coordinates, CL/CD -> CD
            mouse_target = event.xdata / event.ydata # target  -> CL/CD
        elif (self.controller.activeDiagram == "CL_alpha_diagram"):
            edit_mode = 'spec-al'
            mouse_target = event.ydata  # target  -> CL
            mouse_oppoint = event.xdata # oppoint -> alpha
            catching_range_oppoint = 0.1 * zoom_factor
            catching_range_targetValue = 0.01 * zoom_factor


        # check visibility of editable polar
        if (controlFrame.check_activePolarVisibility() == False):
            return None

        # search entry with closest coordinates
        idx = 0
        for targetValue in controlFrame.targetValues:
            # get values from dictinory
            (mode, oppoint, target, weighting) = controlFrame.get_valuesFromDict(targetValue)

            if (mode != edit_mode):
                # not graphically editable in this diagram
                idx = idx + 1
                continue

            if ((abs(mouse_target - target) < catching_range_targetValue) and
                (abs(mouse_oppoint - oppoint) < catching_range_oppoint)):
                return idx

            idx = idx + 1
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
            self._ind = self.get_ind_under_point(event)
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
        global controlFrame
        if event.inaxes is None:
            return
        if event.button == 1:
            if self._ind is None:
                return
            # check type of active diagram
            if (self.controller.activeDiagram == "CLCD_CL_diagram"):
                # convert coordinates
                x, y = event.ydata, event.xdata
                x = y/x
            elif (self.controller.activeDiagram == "CL_alpha_diagram"):
                x, y = event.ydata, event.xdata
            else:
                x, y = event.xdata, event.ydata
                    # set new target value
            controlFrame.change_targetValue(x,y,self._ind)
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
    def __init__(self, master, side, creatorInstances, scaleFactor):
        self.master = master
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
        self.container = customtkinter.CTkFrame(master=master, width=180,
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


    def update_diagram(self, master):
        global creatorInstances
        creatorInst = creatorInstances[0]

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
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        global controlFrame
        global creatorInstances

        self.app_running = False

        # index of active planform
        self.planformIdx = 0

        # configure customtkinter
        customtkinter.set_appearance_mode("Dark")    # Modes: "System" (standard), "Dark", "Light"
        customtkinter.set_default_color_theme("blue") # Themes: "blue" (standard), "green", "dark-blue"

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
            creatorInst.set_screenParams(width, heigth)

        # notification variable for updating the diagrams
        self.updateNeeded = 0

        # create diagram frame, which is on the top
        self.frame_top = diagram_frame(self, tk.TOP, creatorInstances,
         scaleFactor)

        # create control frame, which is on the left
        self.frame_bottom = control_frame(self, tk.BOTTOM,
         self.get_leftButtons(), self.get_rightButtons())

        # set global variable
        controlFrame = self.frame_bottom

    def get_leftButtons(self):
        buttons = []
        for diagType in diagTypes:
            buttons.append({"txt": diagType, "cmd" : self.set_diagram, "param" : diagType})
        return buttons

    def get_rightButtons(self):
        buttons = []
        buttons.append({"txt": "Load", "cmd" : self.load, "param" : None})
        buttons.append({"txt": "Save", "cmd" : self.save, "param" : None})
        buttons.append({"txt": "Reset", "cmd" : self.reset, "param" : None})
        return buttons

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
        result = creatorInst.load()
        if (result == 0):
            creatorInst.update_planform()
            self.frame_bottom.clear_unsavedChangesFlag(self.planformIdx)

            self.updateNeeded = True


    def save(self, dummy):
        creatorInst = creatorInstances[self.planformIdx]
        creatorInst.save()
        self.frame_bottom.clear_unsavedChangesFlag(self.planformIdx)


    def reset(self, dummy):
        creatorInst = creatorInstances[self.planformIdx]
        result = creatorInst.reset()
        if (result == 0):
           self.frame_bottom.set_unsavedChangesFlag(self.planformIdx)
           self.updateNeeded = True

    def start(self):
        self.app_running = True
        while self.app_running:
            self.update_idletasks()
            self.update()
            self.frame_top.update_diagram(self)

        self.destroy()


    def unsaved_changesDialog(self, flags):
        # create complete dialog text
        dialogText ="There are unsaved changes...FIXME\n"
        dialogText = dialogText + "To quit without saving type \'quit'\n"
        dialogText = dialogText + "To quit and save the changes type \'save'"

        # create dialog
        dialog = customtkinter.CTkInputDialog(master=None, text=dialogText,
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