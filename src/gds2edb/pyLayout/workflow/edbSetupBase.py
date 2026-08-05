    #coding:utf-8
    #--- coding=utf-8
    #--- @author: yongsheng.guo@ansys.com
    #--- @Time: 20251021


'''
For EDB setup, addressing the problem of inaccurate execution on Linux systems.
'''

import sys,os,re
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

# from pyLayout import log,EdbApp
from ..pyLayout import Layout
from ..common.common import log
from ..edb.edbApp import EdbApp
from .simConfig import SimConfig
 
class EdbSetupBase(object):
    '''
    classdocs
    '''
    pass
 
    def __init__(self, simConfig=None):
        '''
        Constructor
        '''
        self.edbApp = None
        self.siwPath = None
        self._config = SimConfig(simConfig,defaultConfig = "default_edb.json")
 
 
    @property
    def Config(self):
        return self._config
 
    def loadLayout(self):
        
        if "Import" not in self.Config:
            return
        log.info("load EDB file")
        
        
        edbPath =  self.Config["Import"]["EdbPath"]
        if not os.path.exists(edbPath):
            log.exception("aedb not found: %s"%edbPath)
        
        if "RemoveAedt" in self.Config["Import"] and self.Config["Import"]["RemoveAedt"]:
            aedtPath = edbPath[:-5] + ".aedt"
            if os.path.exists(aedtPath):
                os.remove(aedtPath)
             
        installDir = self.Config["AEDT"]["InstallPath"]
        

        self.edbApp = EdbApp(installDir=installDir)
        logPath = self.Config["AEDT/LogPath"]
        if logPath:
            self.edbApp.setLogPath(logPath)
        
        self.edbApp.open(edbPath)

    def configNets(self):
        if "Net" not in self.Config:
            return
        log.info("EDB config Net")
        
        Net = self.Config["Net"]
        
        if not Net["Enable"]:
            log.info("Net not enable.")
            return
        
                    
        if "MergePhysicallyConnected" in Net and Net["MergePhysicallyConnected"]:
            log.info("Merge Physically Connected nets ...")
            self.edbApp.Nets.mergePhysicallyConnectedNets()
            
        if "DisjointNets" in Net and Net["DisjointNets"]:
            log.info("Merge Physically Connected nets ...")
            self.edbApp.Nets.disjointNets()
            
        if "MergeShortNets" in Net and Net["MergeShortNets"]:
            log.info("Merge Short Nets ...")
            self.edbApp.Nets.mergeShortNets()
            
        
        self.edbApp.save()
 
    def setSIwaveOption(self):
 
        if "SIwaveOption" not in self.Config:
            return
         
        SIwaveOption = self.Config["SIwaveOption"]
         
        if not SIwaveOption["Enable"]:
            log.info("SIwaveOption not enable.")
            return
        edbApp = self.edbApp
        siwOption = edbApp.SIwaveOptions
        edbApp.removeAllSimSetup() #remove exist simsetup
 
        for k,v in SIwaveOption["Options"].Dict.items():
            try:
                siwOption[k] = str(v)
            except:
                log.warning("Option %s not found in EDB"%(k))
        
        self.edbApp.save()
        
    def export(self):
        
        if "Export" not in self.Config:
            return
         
        Export = self.Config["Export"]
         
        if not Export["Enable"]:
            log.info("export not enable.")
            return
        self.edbApp.save()
        exportSIwave = False
        if "ExportSIwave" in Export:
            exportSIwave = bool(Export["ExportSIwave"])
        if exportSIwave:
            siwPath = None
            if "SIwavePath" in Export and Export["SIwavePath"]:
                siwPath = Export["SIwavePath"]
            siwPathOutput = self.edbApp.exportSiwave(path=siwPath)
            log.info("Export Siwave Path: %s"%siwPathOutput)


    def run(self):
        '''
        workflow:
        
        laod PCB -> load stackup -> configComponents -> ConfigNets -> Cutout -> Port -> solveSetup -> Solve -> datas -> Post
        '''

        #---load layout file
        self.loadLayout()
        
        #---configNets
        self.configNets()
        
        #---setSIwaveOption
        self.setSIwaveOption()
        
        #---Export to SIwave
        self.export()
        
        self.edbApp.save()
        self.edbApp.close()



