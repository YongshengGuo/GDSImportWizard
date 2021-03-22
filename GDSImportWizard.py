# coding=utf-8
'''
Created on 2021-03-08
Version 3.4

@author: yongsheng.guo@ansys.com
'''

import sys,os
import clr
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0]
sys.path.append(appDir)
gdslibPath = os.path.join(appDir,'gdslib.dll')
clr.AddReferenceToFileAndPath(gdslibPath)
aedtInstallDir = r"C:\Program Files\AnsysEM\AnsysEM21.1\Win64"

def runInGUI():
    
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
    from System.Windows.Forms import Application
#     global oDesktop
    import MainForm
    
    Application.EnableVisualStyles()
    form = MainForm.MainForm()
    form.Text = MainForm.titleWin
    Application.Run(form)
    form.Dispose()

def runGDSPostBatch(edbPath):
    from gdsPost import gdsPost
    gds = gdsPost(edbPath)
    gds.gdsAutoPostBatch()

def runInBatchMode(argv):
    from GDS2XML import GDS2XML
    g2x = GDS2XML()
    global aedtInstallDir
    g2x.aedtInstallPath = aedtInstallDir = os.environ['aedtInstallPath'] if 'aedtInstallPath' in os.environ else ""
    g2x.tech.ircxPath = os.environ['ircxPath'] if 'ircxPath' in os.environ else ""
    g2x.gds.gdsPath = os.environ['gdsPath'] if 'gdsPath' in os.environ else ""    

    #option
    g2x.tech.simplifyDieletricMethod = 2
    g2x.mergeDielectricMethod = 0
    g2x.legacyXml = False
    g2x.CreatViaGroups = True
    
    #generate netlist
    g2x.netlistPath = os.environ['netlistPath'] if 'netlistPath' in os.environ else os.path.splitext( g2x.gds.gdsPath)[0]+".net"
    netLayerMap = g2x.tech.getNetLayerMapText()
    layermapDict = dict([x.split(':', 1) for x in netLayerMap.split()]) 
    nets = g2x.extractNetlist(layermapDict, r'.*')
    g2x.writeData(nets,g2x.netlistPath)
    
    #generate XML
    g2x.xmlPath = os.environ['xmlPath'] if 'xmlPath' in os.environ else os.path.splitext( g2x.gds.gdsPath)[0]+".xml"
    g2x.tech.netlistFile = g2x.netlistPath 
    g2x.tech.writeXmlControlFile(g2x.xmlPath)
    
    #generate ebd
    g2x.edbPath = os.environ['edbPath'] if 'edbPath' in os.environ else os.path.splitext( g2x.gds.gdsPath)[0]+".aedb"
    g2x.tech.stackupXmlPath = g2x.xmlPath
    g2x.generateEBD()
    runGDSPostBatch(g2x.edbPath)
    


if __name__ == '__main__':
#     runInGUI()
    
    if len(sys.argv) == 1 or 'oDesktop' in dir():
        #run GUI mode
        runInGUI()
    elif "GUI" in sys.argv[1]:
        runInGUI()
    elif "runGDSPostBatch" in sys.argv[1]:
        runGDSPostBatch(sys.argv[2])
    else:
        runInBatchMode(sys.argv[1:])

"""    
run in batchmode:
@windows
set aedtInstallPath=C:\Program Files\AnsysEM\AnsysEM20.2\Win64
set gdsPath=D:\Study\Script\repository\HFSS\GDSII\GDS2XML\TECH2XML_test\test2.gds
set ircxPath=D:\Study\Script\repository\HFSS\GDSII\GDS2XML\TECH2XML_test\TSMC_INTERPOSER.ircx
set path=%aedtInstallPath%\common\IronPython;%path%
ipy64 GDSImportWizard.py -batch

@Linux
export aedtInstallPath='/home/ansys/app/AnsysEM20.1/Linux64'
export ipy64="$aedtInstallPath/common/mono/Linux64/bin/mono $aedtInstallPath/common/IronPython/ipy64.exe"
export gdsPath=/home/ansys/yguo/test/test.gds
export ircxPath=/home/ansys/yguo/test/TSMC_INTERPOSER.ircx
$ipy64  GDSImportWizard.py -batch

"""