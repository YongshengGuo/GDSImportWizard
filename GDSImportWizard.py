  # coding=utf-8
'''
Created on 2020-06-27
Version 1.0

@author: yongsheng.guo@ansys.com
'''
import sys,os

appPath = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(appPath)


import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
clr.AddReferenceToFile('gdslib.dll')
from System.Windows.Forms import Application
import MainForm

global oDesktop
try:
    import ScriptEnv
    ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
    oDesktop.RestoreWindow()
except ImportError:
    print('Not Run from AEDT')
    oDesktop = None
else:
    print('Running in AEDT environment')
    
MainForm.oDesktop = oDesktop
MainForm.appPath = appPath

Application.EnableVisualStyles()
form = MainForm.MainForm()
try:
    
    Application.Run(form)
except:
    form.Show()
