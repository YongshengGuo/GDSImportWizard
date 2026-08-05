    #coding:utf-8
    #--- coding=utf-8
    #--- @author: yongsheng.guo@ansys.com
    #--- @Time: 20260419


'''
调用runscipt运行分析，并输入S参数,输入参数为json文件
假设Project下只有一个要分析的Design, 求解设定为HFSS or SIwave SYZ
ansysedt  -RunScriptAndExit batchSim.py -ScriptArgs config.json
'''

import sys,os,re
appPath = os.path.realpath(__file__)

MessageBox = None
try:
    import clr
    # Add reference to System.Windows.Forms if not already loaded
    try:
        clr.AddReference('System.Windows.Forms')
        from System.Windows.Forms import MessageBox
    except:
        pass # Handle import error if not in .NET environment
except Exception:
    pass

# Use .NET MessageBox when available
try:
    if MessageBox:
        MessageBox.Show(appPath)
    else:
        print(appPath)
except:
    print(appPath) # Fallback to print if MessageBox fails


appDir = os.path.split(appPath)[0]
sys.path.append(appDir)
pylayoutLibDir = os.path.dirname(os.path.dirname(appDir))
print("pylayout App dir:%s"%pylayoutLibDir)
sys.path.append(pylayoutLibDir)
from pyLayout import Layout
from pyLayout import log
from pyLayout import SimConfig
def batchSim(configPath):

    config = SimConfig(configPath)
    aedtPath = config["Import/LayoutPath"]
    if "SaveAs" in config["Import"] and config["Import/SaveAs"]:
        aedtPath = config["Import/SaveAs"]

    layout = Layout()
    layout.openAedt(aedtPath)
    layout.initDesign()
    

    if "Analysis" not in config:
        return
    
    log.info("Run the simution")
    
    Analysis = config["Analysis"]
    if not Analysis["Enable"]:
        log.info("Analysis not enable.")
        return
    
    setup = config["Setup"] 
    sweepName = ""
    if setup["Enable"]:
        setupName = setup["Name"]
        if "Sweep" in setup and "Name" in setup["Sweep"]:
            sweepName = setup["Sweep/Name"]
    else:
        setups = layout.Setups
        if len(setups)<1:
            log.exception("layout don't have any analysis setup ...")
        
        setup2 = setups[0]
        setupName = setup2.name
        if setup2.Sweeps:
            sweepName = setup2.Sweeps[0].name
    
    # if "Cores" in Analysis and Analysis["Cores"]:
    #     config.layout.setCores(cores=Analysis["Cores"], hpcType=Analysis["HPCType"])
    
    log.info("Starting analysis for setup %s ..."%setupName)       
    layout.Setups[setupName].analyze()
    
    if "ExportSNP" in Analysis:
        #not work for SIwaveDC, CPA
        solution = layout.Solutions["%s:%s"%(setupName,sweepName)]
        if "ExportSNP" in Analysis and Analysis["ExportSNP"]:
            if not Analysis["SnpPath"] and config["Header"]["Name"]:
                Analysis["SnpPath"] = os.path.join(config.layout.ProjectDir,config["Header"]["Name"])
            solution.exportSNP(Analysis["SnpPath"])
    layout.save()

args = None
Module = sys.modules['__main__']
if hasattr(Module, "ScriptArgument"):
    args = getattr(Module, "ScriptArgument")
    if MessageBox:
        MessageBox.Show(args)
    batchSim(args)
else:
    log.info("Not running in batchmode,runing in test mode")
    if len(sys.argv) > 1:
        args = sys.argv[1]
        batchSim(args)
    else:
        log.warning("No config path input for test mode, skip batchSim.")
