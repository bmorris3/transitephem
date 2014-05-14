# -*- coding: utf-8 -*-
"""
Created on Wed May 14 13:51:43 2014

@author: bmorris
"""

import os
import webbrowser
from calculateEphemerides import *

# Path to ".par" file, with the observatory parameters
parfile = 'mro.par'

# Path to the output HTML file -- this script will assume that the
# "html_out" parameter in the .par file is set to True
outputPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),'outputs','eventReport.html')

# Calculate the ephemeris for all visible planets within stated limits
calculateEphemerides(parfile)

# Open the HTML output in a new tab of the default browser
webbrowser.open_new_tab("file:"+2*os.sep+outputPath)