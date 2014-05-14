# -*- coding: utf-8 -*-
"""
Created on Wed May 14 13:51:43 2014

@author: bmorris
"""

import os
import webbrowser
from calculateEphemerides import *

parfile = 'mro.par'
outputPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),'outputs','eventReport.html')

calculateEphemerides(parfile)
webbrowser.open_new_tab("file:"+2*os.sep+outputPath)


#if self.htmlBox.userParams["rbHtmlOut"].GetValue() == True:
#                        webbrowser.open_new_tab("file:"+2*os.sep+outputPath)