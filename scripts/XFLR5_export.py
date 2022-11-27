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

import xml.etree.ElementTree as ET
import os, re
from copy import deepcopy
from strak_machine import (ErrorMsg, WarningMsg, NoteMsg, DoneMsg, bs)

# Scale from mm --> m
scaleFactor = (1.0/1000.0)

# Minimum chord (in mm) in case chord is exactly 0.0
min_chord = 2.0

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

def export_toXFLR5(data, FileName, xPanels, yPanels):
    # basically parse the XML-file
    tree = ET.parse(FileName)

    # get root of XML-tree
    root = tree.getroot()

    # find wing-data
    wing = get_wing(root, data.params.isFin)

    if (wing == None):
        ErrorMsg("wing not found\n")
        return -1

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
        for x_number_of_panels in newSection.iter('x_number_of_panels'):
            x_number_of_panels.text = str(xPanels)

        for y_number_of_panels in newSection.iter('y_number_of_panels'):
            y_number_of_panels.text = str(yPanels)

        for yPosition in newSection.iter('y_position'):
            # convert float to text
            yPosition.text = str(section.y * scaleFactor)

        for chord in newSection.iter('Chord'):
            # limit chord to values >= 1 mm
            chord_float = max(min_chord, section.chord)
            # scale chord to m
            chord_float *= scaleFactor
            # convert float to text
            chord.text = str(chord_float)

        for xOffset in newSection.iter('xOffset'):
            # convert float to text
            xOffset.text = str(section.leadingEdge * scaleFactor)

        for dihedral in newSection.iter('Dihedral'):
            # convert float to text
            dihedral.text = str(section.dihedral)

        for foilName in newSection.iter('Left_Side_FoilName'):
            foilName.text = re.sub('.dat', '', section.airfoilName)

        for foilName in newSection.iter('Right_Side_FoilName'):
            foilName.text = re.sub('.dat', '', section.airfoilName)

        # add the new section to the tree
        wing.append(newSection)
        if (section.chord > 0.0):
            hingeDepthPercent = (section.flapDepth /section.chord )*100
        else:
            hingeDepthPercent = 0.0
        NoteMsg("Section %d: position: %.0f mm, chordlength %.0f mm, hingeDepth %.1f  %%, airfoilName %s was inserted" %
          (section.number, section.y, section.chord, hingeDepthPercent, section.airfoilName))

    # delete existing file, write all data to the new file
    os.remove(FileName)
    tree.write(FileName)
    NoteMsg("XFLR5 data was successfully written.")
    return 0
