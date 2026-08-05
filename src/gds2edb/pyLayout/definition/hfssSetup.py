#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2023-04-24

'''
setupName for hfss 3D Layout

Examples:
    Add HFSS setupName and Sweep
    >>> setup1 = Setup.add("setup1")
    >>> setup1.addSweep("sweepName")
    
    >>> setup1["setup1"]
    return Setup object of "setup1"
'''

import re,os
from ..common import hfssParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,tuple2list
from .definition import Definitions,Definition
from ..common.progressBar import ProgressBar


class Sweep(Definition):
    
    '''
    hfss3DLParameters.hfssSweep
    '''
    maps = {
        "SweepData":"",
        "Tolerance":"InterpDerivTolerance",
        "InterpolatingTolerance":"InterpDerivTolerance",
        }
    

    def __init__(self,sweepName = None,setupName=None,layout=None):
        super(self.__class__,self).__init__(sweepName,type="Sweep",layout=layout)
        self._info.update("sweepName",sweepName)
        self._info.update("setupName",setupName)
        self._info.update("layout",layout)
        
    @property
    def SolutionName(self):
        return "%s:%s"%(self.Info.setupName,self.Info.sweepName)
    
    @property
    def oModule(self):
        return self.oDesign.GetModule("AnalysisSetup")

    
    @property
    def oManager(self):
        return self.oModule

    
    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        
        log.debug("parse Setup: %s"%self.name)
        datas = hfssParameters.hfssSetupSweep
        datas[0] = "NAME:%s"%self.name
        _array = ArrayStruct(tuple2list(datas),self.maps)

        self._info.update("Name",self.name)
        self._info.update("Array", _array)
        self._info.update("self", self)
        self.parsed = True

    def setSweepData(self,sweepData):
        #sweepFreqData:<SweepType>, <StartV>, <StopV>, <StepV> 
        # LIN 0GHz 20GHz 0.01GHz, "LINC 0GHz 10GHz 100", "DEC 1GHz 10GHz 10","DEC 1GHz 10GHz 10 LIN 1GHz 10GHz 0.1GHz"
        #RangeType LinearCount  RangeStart RangeEnd  RangeCount
        #RangeType=LinearStep, RangeStart, RangeEnd, RangeStep
        datas = sweepData.split()
        if len(datas) != 4:
            log.exception("Invalid sweepFreqData: %s"%sweepData)

        if datas[0].upper() == "LINC":
            self.Array["RangeType"] = "LinearCount"
            self.Array["RangeStart"] = datas[1]
            self.Array["RangeEnd"] = datas[2]
            if "RangeCount" not in self.Array.Datas:
                self.Array.replaceKey("RangeStep","RangeCount")
            self.Array["RangeCount"] = int(datas[3])
        elif datas[0].upper() == "LIN":
            self.Array["RangeType"] = "LinearStep"
            self.Array["RangeStart"] = datas[1]
            self.Array["RangeEnd"] = datas[2]
            if "RangeStep" not in self.Array.Datas:
                self.Array.replaceKey("RangeCount","RangeStep")
            self.Array["RangeStep"] = datas[3]
        elif datas[0].upper() == "DEC":
            self.Array["RangeType"] = "LogScale"
            self.Array["RangeStart"] = datas[1]
            self.Array["RangeEnd"] = datas[2]
            if "RangeCount" not in self.Array.Datas:
                self.Array.replaceKey("RangeStep","RangeCount")
            self.Array["RangeCount"] = int(datas[3])
        else:
            log.exception("Invalid sweepFreqData: %s"%sweepData)
            
        self.update()

    def update(self):
        self.oModule.EditFrequencySweep(self.setupName,self.sweepName,self.Array.Datas)
        self.parse()

    def delete(self):
        self.oModule.DeleteSweep(self.Info.setupName,self.Info.sweepName)
    
    def analyze(self):
        self.layout.oDesign.Analyze(self.SolutionName)

class Sweeps(Definitions):
 
    def __init__(self,layout=None,setupName = None):
        super(self.__class__,self).__init__(layout, type="Sweep",definitionCalss=Sweep)
        self.setupName = setupName
     
    @property
    def oModule(self):
        return self.layout.oDesign.GetModule("AnalysisSetup")

     
    @property
    def DefinitionDict(self):
        if self._definitionDict is None:
            self._definitionDict = ComplexDict(dict([(name,Sweep(name,self.setupName,layout=self.layout)) for name in self.oModule.GetSweeps(self.setupName)]))
#             self._definitionDict.setMaps(dict([(re.sub(r'[-\.\s]','_',pin),pin) for pin in self._definitionDict.Keys]))
        return self._definitionDict

    def _getSweeps(self):
#         sweepDict = {}
#         for name in self.oModule.GetSweeps(self.setupName):
#             sweepDict[name] = Sweep(name,self.setupName,layout=self.layout)
        
        return ComplexDict(dict([(name,Sweep(name,self.setupName,layout=self.layout)) for name in self.oModule.GetSweeps(self.setupName)]))

class Setup(Definition):


    
    def __init__(self,name = None,layout=None):
        super(self.__class__,self).__init__(name,type="Setup",layout=layout)
        arrayMaps = {
            # "AdaptiveFrequency":"AdaptiveSettings/SingleFrequencyDataList/AdaptiveFrequencyData/AdaptiveFrequency",
            # "DeltaS": "AdaptiveSettings/SingleFrequencyDataList/AdaptiveFrequencyData/MaxDelta",
            "Order": {"Key":"BasisOrder",
                    "Set":lambda x:[-1,1,2][("mixed","first","second").index(x.lower())],
                    "Get":lambda y:("mixed","first","second")[(-1,1,2).index(y)],
                    },
            "PortMaxDeltaZo":"PortAccuracy",
            }
        self._info.update("arrayMaps",arrayMaps)
        
        self.maps = {
            "AdaptiveFrequency": {
                "Key":"self",
                "Set":lambda s,v:s.setAdaptiveFrequency(v),
                "Get":lambda s: s["Frequency"]
            }
        }
    
    @property
    def oModule(self):
        return self.oDesign.GetModule("AnalysisSetup")

    
    @property
    def oManager(self):
        return self.oModule
    
    @property
    def Name(self):
        return self.name

    def update(self):
        self.oManager.EditSetup(self.Name,self.Array.Datas)
        # self.parse(force=True) #不能直接获取参数

    
    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        
        log.debug("parse hfss setup: %s"%self.name)

        datas = hfssParameters.hfssSetup
        datas[0] = "NAME:%s"%self.name
        _array = ArrayStruct(tuple2list(datas),self._info.arrayMaps)
   
        self._info.update("Array", _array)
        self._info.update("Name",self.name)
        maps = self.maps
        maps.update({"Sweeps":{
            "Key":"self",
            "Get":lambda s: Sweeps(layout=s.layout,setupName=s.name) #[Sweep(k,sweepName) for sweepName in self.oModule.GetSweeps(self.name)]
            }})
        
        self._info.setMaps(maps)
        self._info.update("self", self)
        self.parsed = True

    #---setup
    def setAdaptiveFrequency(self,freqData):
        '''_summary_

        Args:
            freqData (_type_):Single "5Ghz" or Broadband "1Ghz:15Ghz" or MultiFrequency "5Ghz,15Ghz,20Ghz"
        '''
        if not isinstance(freqData,(str)):
            freqData = str(freqData)

        if ":" in freqData:
            #kBroadband
            log.info("set Broadband frequency: %s"%freqData)
            freqs = re.split(r"\s*:\s*",freqData)
            if len(freqs) != 2:
                log.exception("Invalid Broadband frequency data:%s"%freqData)
                
            self["SolveType"] = "Broadband"
            AdaptiveFrequencyData = [
                "NAME:MultipleAdaptiveFreqsSetup",
                "Low:="			, freqs[0],
                "High:="		, freqs[1]
            ]
            self.Array.insert(AdaptiveFrequencyData,"SolveType")
        elif "," in freqData or ";" in freqData:
            #kMultiFrequencies
            log.info("set MultiFrequencies frequency: %s"%freqData)
            freqs = re.split(r"\s*[,;]\s*",freqData)
            if len(freqs) <2:
                log.exception("Invalid MultiFrequencies frequency data:%s"%freqData)
            self["SolveType"] = "MultiFrequency"
            AdaptiveFrequencyData = ["NAME:MultipleAdaptiveFreqsSetup"]
            for freq in freqs:
                AdaptiveFrequencyData.append([
                    "NAME:AdaptAt",
                    "Frequency:="		, freq,
                    "Delta:="		, 0.02
                ])
            self.Array.insert(AdaptiveFrequencyData,"SolveType")
                
        else:
            self["SolveType"] = "SingleFrequency"
            self["Frequency"] = freqData
        
        self.update()

    #--- Sweep
    def findSweep(self,sweepName):
        target = str(sweepName).lower()
        for swp in self.getSweepNames():
            if swp.lower() == target:
                log.info("Sweep exist: %s."%swp)
                return swp
            
        return False
    
    def addSweep(self,sweepName="Sweep",sweepFreqData=None):

        swp = self.findSweep(sweepName)
        if swp:
            log.info("Sweep already exist: %s %s"%(self.name,sweepName))
            return Sweep(swp,self.name,layout=self.layout)

        log.info("Add sweep: %s %s"%(self.name,sweepName))
#         self.oModule.AddSweep(self.name,["NAME:%s"%sweepName])
        
        sweepData = hfssParameters.hfssSetupSweep
        sweepData[0] = "NAME:%s"%sweepName
        _array = ArrayStruct(tuple2list(sweepData),self._info.arrayMaps)

        if sweepName in self.getAllSweeps():
            self.delSweep(sweepName)
        
        self.oModule.InsertFrequencySweep(self.name,_array.Array)
        sweep = Sweep(sweepName,self.name,layout=self.layout)
        if sweepFreqData:
            sweep.setSweepData(sweepFreqData)

        self.Sweeps.push(sweepName,sweep)
        return sweep
    
    def delSweep(self,sweepName):
        swp = self.findSweep(sweepName)
        if swp:
            self.oModule.DeleteSweep(self.name,swp)
    
    def getSweep(self,sweepName):
        target = str(sweepName).lower()
        for swp in self.getSweepNames():
            if swp.lower() == target:
                return Sweep(swp,self.name,layout=self.layout)
        
        log.exception("Sweep not found: %s"%sweepName)
    
    def getAllSweeps(self):
        return [Sweep(sweepName,self.name,layout=self.layout) for sweepName in self.oModule.GetSweeps(self.name)]
    
    def getSweepNames(self):
        return self.oModule.GetSweeps(self.name)
    
    def getSweepData(self,sweepName,path = None):
        sweep = self.getSweep(sweepName)
        datas = sweep.Array
        if not path:
            return datas
        
        return datas.get(path)
    
    def setSweepData(self,sweepName,path=None,value=None,arrayDatas = None):
        if arrayDatas:
            self.oModule.EditFrequencySweep(self.name,sweepName,arrayDatas)
            return
        datas = self.getSweepData(sweepName)
        datas.set(path,value)
        self.oModule.EditFrequencySweep(self.name,sweepName,datas.Array)
        log.info("Set Sweep Data Success: %s"%(path))
      
    def delete(self):
        oModule = self.layout.oDesign.GetModule("AnalysisSetup")
        oModule.DeleteSetups([self.name])
      
    #--- Analyze 

    def analyze(self):
        if self.layout.options["AEDT_WaitForLicense"]:
            if self.layout.options["AEDT_HPC_NumCores"]:
                cores = int(self.layout.options["AEDT_HPC_NumCores"])
                self.layout.setCores(cores)
            else:
                oDesktop = self.layout.oDesktop
                #worked
                activeHPCOption = oDesktop.GetRegistryString("Desktop/ActiveDSOConfigurations/HFSS")
                log.info("ActiveDSOConfigurations: %s"%activeHPCOption)
                #oDesktop.SetRegistryString(r"Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s/NumCores"%activeHPCOption)
                activeHpcStr = oDesktop.GetRegistryString("Desktop/DSOConfigurationsEx/HFSS/%s"%activeHPCOption)
                rst = re.findall(r"NumCores=(\d+)", activeHpcStr)
                if rst:
                    cores = int(rst[0])
                else:
                    cores = 0
            if cores:
                self.layout.waitForlicense([{"module":"HFSSSolver"},{"feature":"anshpc_pack","count":self.layout._getPackCount(cores)}])
        
        self.oDesign.Analyze(self.name)
    

    def getSolutions(self):
        return [self.layout.Solutions["%s:%s"%(self.name,sweep.name)] for sweep in self.getAllSweeps()]

    def exportProfile(self,profilePath):
        self.layout.oDesign.ExportProfile(self.name, '', profilePath, '')
        
    def exportSnp(self):
        sweeps = self.getAllSweeps()
        for sweep in sweeps:
            solutionName = "%s_%s"%(self.name,sweep.name)
            self.layout.Solutions[solutionName].exportSNP()

class Setups(Definitions):

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Setup",definitionCalss=Setup)
    
    @property
    def DefinitionDict(self):
        if self._definitionDict is None:
            oModule = self.layout.oDesign.GetModule("AnalysisSetup")
            self._definitionDict = ComplexDict(dict([(name,Setup(name,layout=self.layout)) for name in oModule.GetSetups()]))
#             self._definitionDict.setMaps(dict([(re.sub(r'[-\.\s]','_',pin),pin) for pin in self._definitionDict.Keys]))
        return self._definitionDict
    
    
    def add(self,name,solutionType = "HFSS"):
        log.info('add setup: "%s" type: %s'%(name,solutionType))
        oModule = self.layout.oDesign.GetModule("AnalysisSetup")
        if name in self.getAllSetupNames():
            log.info('setupName "%s" exist, will be remove first.'%name)
            oModule.DeleteSetups([name])
        oModule.InsertSetup("HfssDriven", ["NAME:%s"%name])
        #refresh _definitionDict
        self._definitionDict = None
        return self.DefinitionDict[name]
    

    def getByName(self,name):
        if name in self.getAllSetupNames():
            return Setup(name,layout=self.layout)
        else:
            log.exception('setupName "%s" not exist'%name)
    
    def getAllSetupNames(self):
        oModule = self.layout.oDesign.GetModule("AnalysisSetup")
        return oModule.GetSetups()
    
    def analyzeAll(self):
        #Analyze Nominal and optimetircs
        self.layout.oDesign.AnalyzeAll()
        #self.layout.oDesign.AnalyzeAllNominal()
        
    def deleteAllSetups(self):
        oModule = self.layout.oDesign.GetModule("AnalysisSetup")
        oModule.DeleteSetups(self.getAllSetupNames())
        self._definitionDict = None