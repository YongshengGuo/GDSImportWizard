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
from ..common import hfss3DLParameters
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
    mapsForHFSS = {
        "SweepData":"Sweeps/Data",
        "UseQ3D":"UseQ3DForDC",
        "Tolerance":"SAbsError",
        "InterpolatingTolerance":"SAbsError",
        "SweepType":{"Key":"FreqSweepType",
                     "Get": lambda x: x[1:],
                     "Set":lambda x: {"interpolating":"kInterpolating","discrete":"kDiscrete"}[x.lower()]} #kInterpolating or discrete
        
        }
    
    mapsForSIwave = {
        "SweepData":"Sweeps/Data",
        "UseQ3D":"UseQ3DForDC",
        "Tolerance":"RelativeSError",
        "InterpolatingTolerance":"RelativeSError",
        "SweepType":{"Key":"FreqSweepType",
                     "Get": lambda x: x[1:],
                     "Set":lambda x: {"interpolating":"kInterpolating","discrete":"kDiscrete"}[x.lower()]} #kInterpolating or discrete
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
        return self.oDesign.GetModule("SolveSetups")

    
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
        SolveSetupType =  self.layout.Setups[self._info.setupName].SolveSetupType 
        
        maps = {}
        if SolveSetupType== "HFSS":
            maps = self.mapsForHFSS
        elif SolveSetupType== "SIwave":
            maps = self.mapsForSIwave
        else:
            maps = self.mapsForSIwave
            log.error("Unknow setup type:%s"%self._info.setupName)
 
        datas = self.oModule.GetSweepInfo(self._info.setupName,self._info.sweepName)
        if datas:
            _array = ArrayStruct(tuple2list(datas),maps)
        else:
            _array = []
            
        self._info.update("Name",self.name)
        self._info.update("Array", _array)
#         self.__class__.maps = maps
        self._info.update("self", self)
        self.parsed = True


    def update(self):
#         self.oManager.EditSweep(self.setupName,self.Array.Datas)
        self.oModule.EditSweep(self.setupName,self.sweepName,self.Array.Datas)
        self.parse()

    def delete(self):
        self.oModule.DeleteSweep(self.Info.setupName,self.Info.sweepName)
    
    
    def analyze(self):
        self.oModule.AnalyzeSweep(self.Info.setupName,self.Info.sweepName)
    

class Sweeps(Definitions):
 
    def __init__(self,layout=None,setupName = None):
        super(self.__class__,self).__init__(layout, type="Sweep",definitionCalss=Sweep)
        self.setupName = setupName
     
    @property
    def oModule(self):
        return self.layout.oDesign.GetModule("SolveSetups")

     
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
            "Order": {"Key":"AdvancedSettings/OrderBasis",
                    "Set":lambda x:[-1,1,2][("mixed","first","second").index(x.lower())],
                    "Get":lambda y:("mixed","first","second")[(-1,1,2).index(y)],
                    },
            "PortMaxDeltaZo":"AdvancedSettings/MaxDeltaZo",
            #for Siwave
            "SISliderPos":"SimulationSettings/SISliderPos", #0:Speed, 1:Balanced, 2:Accurary
            "PISliderPos":"SimulationSettings/PISliderPos", #0:Speed, 1:Balanced, 2:Accurary
            }
        self._info.update("arrayMaps",arrayMaps)
        
        self.maps = {
            "DeltaS": {"Key":"self",
                    "Set":lambda s,x:s.updateByKey("MaxDelta",x),
                    "Get":lambda s:s["AdaptiveSettings/SingleFrequencyDataList/AdaptiveFrequencyData/MaxDelta"],
                    },
            "MaxPasses": {"Key":"self",
                    "Set":lambda s,x:s.updateByKey("MaxPasses",x),
                    "Get":lambda s:s["AdaptiveSettings/SingleFrequencyDataList/AdaptiveFrequencyData/MaxPasses"],
                    },
            "AdaptiveFrequency": {
                "Key":"self",
                "Set":lambda s,v:s.setAdaptiveFrequency(v),
                "Get":lambda s: s["AdaptiveSettings/SingleFrequencyDataList/AdaptiveFrequencyData/AdaptiveFrequency"]
            }
        }
    
    @property
    def oModule(self):
        return self.oDesign.GetModule("SolveSetups")

    
    @property
    def oManager(self):
        return self.oModule
    
    @property
    def Name(self):
        return self.name

    
    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        
        log.debug("parse hfss setup: %s"%self.name)
    
        datas = self.oModule.GetSetupData(self.name)
        if datas:
            _array = ArrayStruct(tuple2list(datas),self._info.arrayMaps)
        else:
            _array = []
            
            
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
            freqData (_type_): "5Ghz" or "1Ghz:15Ghz" or "5Ghz,15Ghz,20Ghz"
        '''
        if not isinstance(freqData,(str)):
            freqData = str(freqData)

        if ":" in freqData:
            #kBroadband
            log.info("set Broadband frequency: %s"%freqData)
            freqs = re.split(r"\s*:\s*",freqData)
            if len(freqs) != 2:
                log.exception("Invalid Broadband frequency data:%s"%freqData)
            self["AdaptiveSettings/AdaptType"] = "kBroadband"
            AdaptiveFrequencyData = self["AdaptiveSettings/BroadbandFrequencyDataList"]
            AdaptiveFrequencyData[1][2] = freqs[0]
            AdaptiveFrequencyData[2][2] = freqs[1]
            self["AdaptiveSettings/BroadbandFrequencyDataList"] = AdaptiveFrequencyData.Datas
        elif "," in freqData or ";" in freqData:
            #kMultiFrequencies
            log.info("set MultiFrequencies frequency: %s"%freqData)
            freqs = re.split(r"\s*[,;]\s*",freqData)
            if len(freqs) <2:
                log.exception("Invalid MultiFrequencies frequency data:%s"%freqData)
            self["AdaptiveSettings/AdaptType"] = "kMultiFrequencies"
            DeltaS = self["AdaptiveSettings/SingleFrequencyDataList/AdaptiveFrequencyData/MaxDelta"]
            MaxPasses = self["AdaptiveSettings/SingleFrequencyDataList/AdaptiveFrequencyData/MaxPasses"]
            AdaptiveFrequencyData = ["NAME:MultiFrequencyDataList"]
            for freq in freqs:
                AdaptiveFrequencyData.append([
                    "NAME:AdaptiveFrequencyData",
                    "AdaptiveFrequency:="    , freq,
                    "MaxDelta:="        , str(DeltaS),
                    "MaxPasses:="        , int(MaxPasses),
                    "Expressions:="        , []
                ])
            
            self["AdaptiveSettings/MultiFrequencyDataList"] = AdaptiveFrequencyData
        else:
            self["AdaptiveSettings/AdaptType"] = "kSingleFrequency"
            AdaptiveFrequencyData = self["AdaptiveSettings/SingleFrequencyDataList"]
            AdaptiveFrequencyData[1][2] = freqData
            self["AdaptiveSettings/SingleFrequencyDataList"] = AdaptiveFrequencyData.Datas
    #--- Sweep
    def findSweep(self,sweepName):
        target = str(sweepName).lower()
        for swp in self.getSweepNames():
            if swp.lower() == target:
                log.info("Sweep exist: %s."%swp)
                return swp
            
        return False
    
    def addSweep(self,sweepName="Sweep1",sweepFreqData=None):

        #has bug for SIwave sweep

        swp = self.findSweep(sweepName)
        if swp:
            log.info("Sweep already exist: %s %s"%(self.name,sweepName))
            return Sweep(swp,self.name,layout=self.layout)

        log.info("Add sweep: %s %s"%(self.name,sweepName))
#         self.oModule.AddSweep(self.name,["NAME:%s"%sweepName])
        if sweepName in self.getAllSweeps():
            self.delSweep(sweepName)
            
        self.oModule.AddSweep(self.name, 
            [
                "NAME:%s"%sweepName,
                [
                    "NAME:Properties",
                    "Enable:="        , "true"
                ],
                [
                    "NAME:Sweeps",
                    "Variable:="        , sweepName,
                    "Data:="        , sweepFreqData if sweepFreqData else "LIN 0GHz 10GHz 0.01GHz",
                    "OffsetF1:="        , False,
                    "Synchronize:="        , 0
                ]
            ])
        
        
        return self.Sweeps[sweepName]
        
    
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
        datas = ArrayStruct(self.oModule.GetSweepInfo(self.name,sweepName))
        if not path:
            return datas
        
        return datas.get(path)
    
    def setSweepData(self,sweepName,path=None,value=None,arrayDatas = None):
        if arrayDatas:
            self.oModule.EditSweep(self.name,sweepName,arrayDatas)
            return
        datas = ArrayStruct(self.oModule.GetSweepInfo(self.name,sweepName))
        datas.set(path,value)
        self.oModule.EditSweep(self.name,sweepName,datas.Array)
        log.info("Set Sweep Data Success: %s"%(path))
      
    def delete(self):
        oModule = self.layout.oDesign.GetModule("SolveSetups")
        oModule.Delete(self.name)
      
        
    #--- Analyze 

    def analyze(self):
        if self.layout.options["AEDT_WaitForLicense"]:
            if self.layout.options["AEDT_HPC_NumCores"]:
                cores = int(self.layout.options["AEDT_HPC_NumCores"])
                self.layout.setCores(cores)
            else:
                oDesktop = self.layout.oDesktop
                #worked
                activeHPCOption = oDesktop.GetRegistryString("Desktop/ActiveDSOConfigurations/HFSS 3D Layout Design")
                log.info("ActiveDSOConfigurations: %s"%activeHPCOption)
                #oDesktop.SetRegistryString(r"Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s/NumCores"%activeHPCOption)
                activeHpcStr = oDesktop.GetRegistryString("Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s"%activeHPCOption)
                rst = re.findall(r"NumCores=(\d+)", activeHpcStr)
                if rst:
                    cores = int(rst[0])
                else:
                    cores = 0
            if cores:
                self.layout.waitForlicense([{"module":"HFSSSolver"},{"feature":"anshpc_pack","count":self.layout._getPackCount(cores)}])
        
        self.oDesign.Analyze(self.name)
    
    def exportToHfss(self,path = None,timeout = 10*60):
        if not path:
            path = os.path.join(self.layout.projectDir, "%s_%s.aedt"%(self.layout.projectName,self.layout.designName))
        
        #如果存在path则先删除文件        
        if os.path.exists(path):
            log.info("File exist, will be removed first: %s"%path)
            os.remove(path)
        
        log.info("Export 3D Layout design to HFSS: %s"%path)
        self.oModule.ExportToHfss(self.name, path)
        
        #wait for output
        import time
        i = 0
        bar = ProgressBar(prompt="Export to 3D Model")
        bar.showProgress()
        while(i<timeout):
            if os.path.exists(path):
                break
            time.sleep(2) #sleep 1s
            i += 2
        bar.stop()
        if i>=timeout:
            log.exception("time out (>30 mins), Execution interrupt... .")
            
        from ..model3D.HFSS import HFSS
        hfss = HFSS()
        hfss.openAedt(path)
        unit = hfss.getUnit()
        netInfo = {}
        log.info("Get net information ... ")
        
        bar = ProgressBar(len(hfss.Objects),"Get net information progress")
        
        for obj in hfss.Objects:
            bar.showPercent()
            #skip sheet objects
            if "Material" not in obj:
                log.debug("%s not have Material property, skip."%obj.name)
                continue
            
            #skip dielectric
            if not hfss.Materials[obj.Material].isConductor():
                log.debug("%s is dielectric object, skip."%obj.name)
                continue
            
            flag = 1
            #20240821 try all vertex for net
            for vertex in obj.Vertexs.values():
                pt0 = ["%s%s"%(x,unit) for x in vertex]
                layer = self.layout.layers.getLayerByHeight(pt0[2])
                layoutObjs = self.layout.getObjectByPoint([pt0[0],pt0[1]],layer=layer)
                if layoutObjs:
                    net = None
                    for obj2 in layoutObjs:
                        try:
                            element = self.layout[obj2]
                        except:
                            continue
                        
                        if "Net" in  element.Props:
                            net = element.Net
                            break
                        else:
                            continue
                    if not net:
                        log.error("\nobj %s not found."%obj2)
                    else:
                        netInfo.update({obj.name:net})
                        flag = 0
                        break
            if flag:
                log.debug("Not found object on layout:%s"%obj.name)                 
        
        bar.stop()
        
        hfss.groupbyNets(netInfo)
                
        return hfss


    def exportToQ3D(self,path = None,timeout = 30*60):
        if not path:
            path = os.path.join(self.layout.projectDir, "%s_%s.aedt"%(self.layout.projectName,self.layout.designName))
            
        #如果存在path则先删除文件        
        if os.path.exists(path):
            log.info("File exist, will be removed first: %s"%path)
            os.remove(path)
            
        log.info("Export 3D Layout design to Q3D: %s"%path)
        self.oModule.ExportToQ3D (self.name, path)
        
        #wait for output
        import time
        i = 0
        bar = ProgressBar(prompt="Export to 3D Model")
        bar.showProgress()
        while(i<timeout):
            if os.path.exists(path):
                break
            time.sleep(2) #sleep 1s
            i += 2
            
#             if i%5 == 0:
#                 log.info("Export to Q3D project ... : %ss"%i)
        bar.stop()
        
        if i>=timeout:
            log.exception("time out (>30 mins), Execution interrupt... .")
            
        from ..model3D.Q3D import Q3D
        q3d = Q3D()
        q3d.openAedt(path)
        unit = q3d.getUnit()
        netInfo = {}
        log.info("Get net information ... please wait for some minitus ...........")
        
        bar = ProgressBar(len(q3d.Objects),"Get net information progress")
        for obj in q3d.Objects:
            bar.showPercent()
            #skip sheet objects
            if "Material" not in obj:
                log.debug("%s not have Material property, skip."%obj.name)
                continue
            
            #skip dielectric
            if not q3d.Materials[obj.Material].isConductor():
                log.debug("%s is dielectric object, skip."%obj.name)
                continue
            
            flag = 1
            #20240821 try all vertex for net
            for vertex in obj.Vertexs.values():
                pt0 = ["%s%s"%(x,unit) for x in  vertex]
                layer = self.layout.layers.getLayerByHeight(pt0[2])
                layoutObjs = self.layout.getObjectByPoint([pt0[0],pt0[1]],layer=layer)
                if layoutObjs:
                    net = None
                    for obj2 in layoutObjs:
                        try:
                            element = self.layout[obj2]
                        except:
                            continue
                        
                        if "Net" in  element.Props:
                            net = element.Net
                            break
                        else:
                            continue
                    if not net:
                        log.error("\nobj %s not found."%obj2)
                    else:
                        netInfo.update({obj.name:net})
                        flag = 0
                        break
            if flag:
                log.debug("Not found object on layout:%s"%obj.name)                      
                
                 
        bar.stop()
        q3d.groupbyNets(netInfo)
        return q3d
    
    

    def exportToMaxwell(self,path = None,timeout = 30*60):
        log.info("First export to Q3D, then Copy to Maxwell")
        q3d = self.exportToQ3D(path, timeout)
        
        from ..model3D.maxwell import Maxwell
        maxwell = Maxwell()
        maxwell.newDesign(q3d.designName+"_maxwell",q3d.projectName)
        q3d.oEditor.Copy(["NAME:Selections","Selections:=",",".join(q3d.AllParts)])
        maxwell.oEditor.Paste()
        q3d.deleteDesign()
        log.info("Finished to export 3D Layout design to  Maxwell.")

    
    def exportProfile(self,profilePath):
        self.layout.oDesign.ExportProfile(self.name, '', profilePath, '')
        
    def exportSnp(self):
        sweeps = self.getAllSweeps()
        for sweep in sweeps:
            solutionName = "%s_%s"%(self.name,sweep.name)
            self.layout.Solutions[solutionName].exportSNP()

    def getSolutions(self):
        return [self.layout.Solutions["%s:%s"%(self.name,sweep.name)] for sweep in self.getAllSweeps()]

    #--- mesh
#         
#     def addMeshOperationOnNets(self,nets,meshLength = '5mil'):
#         oDesign = self.oDesign
#         log.debug("add mesh opertion on nets: meshlength %s"%meshLength)
#         layers = self.getSignalLayers()
#         meshOperations = [
#             [
#                 "NAME:MeshEntityInfo",
#                 "IsFcSel:="        , False,
#                 "EntID:="        , -1,
#                 "FcIDs:="        , [],
#                 [
#                     "NAME:MeshBody",
#                     "Id:="            , -1,
#                     "Nam:="            , "",
#                     "Mat:="            , "",
#                     "Layer:="        , layer,
#                     "Net:="            , net,
#                     "OrigNet:="        , net
#                 ],
#                 "BBox:="        , []
#             ] for net in nets for layer in layers
#         ]
#         
#         oModule = oDesign.GetModule("SolveSetups")    
#         setupName = self.getSetups(oDesign)[0]
# #         log.debug("add mesh opertion on net: %s"%net)
#         oModule.AddMeshOperation(setupName, 
#             [
#                 "NAME:Length1",
#                 "RefineInside:="    , False,
#                 "Type:="        , "LengthBased",
#                 "Enabled:="        , True,
#                 [
#                     "NAME:Assignment",
#                 ] + meshOperations,
#                 "RestrictElem:="    , False,
#                 "NumMaxElem:="        , "1000",
#                 "RestrictLength:="    , True,
#                 "MaxLength:="        , meshLength
#             ])
# 
# 
#     def setHfssExtent(self,extent = "1.5mm"):
#         #self.oEditor.SetHfssExtentsVisible(True)
#         self.oDesign.EditHfssExtents(
#             [
#             ])
# 

        
class Setups(Definitions):

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Setup",definitionCalss=Setup)
    
    @property
    def DefinitionDict(self):
        if self._definitionDict is None:
            if "Aedt3DToolBase" in str(self.layout.__class__):
                #3d moudle
                oModule = self.layout.oDesign.GetModule("AnalysisSetup")
            else:
                #hfss 3d layout
                oModule = self.layout.oDesign.GetModule("SolveSetups") 

            self._definitionDict = ComplexDict(dict([(name,Setup(name,layout=self.layout)) for name in oModule.GetSetups()]))
#             self._definitionDict.setMaps(dict([(re.sub(r'[-\.\s]','_',pin),pin) for pin in self._definitionDict.Keys]))
        return self._definitionDict
    
    
    def add(self,name,solutionType = "HFSS"):
        if name in self.getAllSetupNames():
            log.info('setupName "%s" exist, will be not add'%name)
            oModule = self.layout.oDesign.GetModule("SolveSetups")
            log.info('setupName "%s" exist, will be remove first.'%name)
            oModule.Delete(name)
            oModule.Add(["NAME:%s"%name,"SolveSetupType:=", solutionType])
            
        else:
            log.info('add setup: "%s" type: %s'%(name,solutionType))
            oModule = self.layout.oDesign.GetModule("SolveSetups")
            oModule.Add(["NAME:%s"%name,"SolveSetupType:=", solutionType])
        
        #refresh _definitionDict
        self._definitionDict = None
        return self.DefinitionDict[name]
    

    def getByName(self,name):
        if name in self.getAllSetupNames():
            return Setup(name,layout=self.layout)
        else:
            log.exception('setupName "%s" not exist'%name)
    
    def getAllSetupNames(self):
        oModule = self.layout.oDesign.GetModule("SolveSetups")
        return oModule.GetSetups()
    
    def analyzeAll(self):
        #Analyze Nominal and optimetircs
        self.layout.oDesign.AnalyzeAll()

        
