# coding=utf-8
'''
Created on 2021-03-08
Version 3.4

modify 2021-12-16
Version 4.3
@author: yongsheng.guo@ansys.com
'''

import sys,os
import clr
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0]
sys.path.append(appDir)
gdslibPath = os.path.join(appDir,'gdslib.dll')
clr.AddReferenceToFileAndPath(gdslibPath)

def runInGUI():
    
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
    from System.Windows.Forms import Application
    import MainForm
    Application.EnableVisualStyles()
    form = MainForm.MainForm()
    form.Text = MainForm.titleWin
    Application.Run(form)
    form.Dispose()

def runInBatchMode():
    from GDS2EDB import gds2edbBatch
    gds2edbBatch()

def main():
#     runInGUI()
    for arg in sys.argv[1:]:
        if "-gui" in arg.lower():
            runInGUI()
            return
    
    if 'oDesktop' in globals():
        try:
            sArg = ScriptArgument
        except:
            sArg = None
        
        if sArg:
            runInBatchMode()
        else:
            #run GUI mode
            runInGUI()
    else:
        runInBatchMode()

if __name__ == '__main__':
    main()
