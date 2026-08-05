#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2023-04-09



import os,sys,re
import shutil
import time

from ..desktop import initializeDesktop,releaseDesktop

#---library
from ..definition.padStack import PadStacks
from ..definition.componentLib import ComponentDefs
from ..definition.material import Materials
#---natural
from ..definition.setup import Setups
from ..definition.variable import Variables
from ..postData.solution import Solutions


from ..common.complexDict import ComplexDict
from ..common.arrayStruct import ArrayStruct

from .object3DModel import Objects3DModle

# from .lib.common.common import *
from ..common.common import log,isIronpython #log is a globle variable
from ..common.unit import Unit
from ..common.common import DisableAutoSave,ProcessTime
from ..common.licenseChecker import LicenseChecker
from ..pyLayout import Layout
from ..edb.edbApp import EdbApp,EdbSIwaveOptions,edbToSIwave

class Aedt3DToolBase(Layout):
    '''
    classdocs
    '''
    def __init__(self,toolType=None, version=None, installDir=None,nonGraphical=False,newDesktop=False,usePyAedt=False,oDesktop = None):
        super(Aedt3DToolBase,self).__init__(version=version, installDir=installDir,nonGraphical=nonGraphical,
                                          newDesktop=newDesktop,usePyAedt=usePyAedt,oDesktop = oDesktop)
        self._info.update("toolType",toolType)
    
    def __getitem__(self, key):
        
        if not isinstance(key, str):
            log.exception("key for layout must be str: %s"%key)
        
        if key in self._info:
            return self._info[key]
        
        if not self._oDesign:
            log.exception("layout should be intial use '%s.initDesign(projectName = None,designName = None)'"%self.toolType)
            return
        
        if key in self._info["Objects"]:
            return self._info["Objects"][key]
        
        log.exception("not found element on layout: %s"%key)
        return None
        
    def __setitem__(self, key,value):
        self._info[key] = value
        
    def initDesign(self,projectName = None,designName = None, initObjects = True):
        super(Aedt3DToolBase, self).initDesign(projectName,designName, False)
        # if self._oDesign:
        #     self._info.update("oEditor",self._oDesign.SetActiveEditor("3D Modeler"))
        if initObjects:
            if self.designtype == 'HFSS 3D Layout Design':
                pass
            else:
                self.initObjects()

    def initObjects(self):
        
        info = self._info
        info.update("self",self)
        
        def _getObjects(self2,name):
            return self2.oEditor.GetChildNames(name)
        
        childNames = ["AllParts","CoordinateSystems","Groups","Lists","ModelParts","NonModelParts","Planes","Points","SubmodelDefinitions"]
        for name in childNames:
#             info.update(name,self.oEditor.GetChildNames(name))
            info.update(name,name)
            self.maps.update({
                name:{
                "Key":("self",name),
                "Get": lambda s,n:_getObjects(s,n)
                }})
            
#         oEditor.GetChildNames("AllParts")
#           self.oEditor.GetChildNames("Groups")
#         Name    Type    Description
#         <category>    String    
#         Optional. Passing no input returns the list of possible strings:
#         
#         "AllParts" – Returns the names of all parts.
#         "CoordinateSystems" – Returns the names of all coordinate systems.
#         "Groups" – Returns the names of all groups.
#         "Lists" – Returns the names of all lists.
#         "ModelParts" – Returns names of model parts.
#         "NonModelParts" – Returns the names of non-model parts.
#         "Planes" – Returns the names of all planes.
#         "Points" – Returns the names of all points.
#         "SubmodelDefinitions" – Returns the names of submodel definitions.


        info.update("Materials", Materials(layout = self))
        info.update("Variables", Variables(layout = self))
        info.update("Setups", Setups(layout = self))
        info.update("Solutions", Solutions(layout = self))
        info.update("PadStacks", PadStacks(layout = self))
        info.update("ComponentDefs", ComponentDefs(layout = self))
        
        info.update("Objects",Objects3DModle(app = self))
#         info.update("Primitives",Primitives(layout = self))
        info.update("unit",self.oEditor.GetModelUnits())
        info.update("Version",self.oDesktop.GetVersion())
        info.update("layout",self)
 
                
    #--- design
        
    def enableAutosave(self,flag=True):
        Enabled = self.oDesktop.GetAutoSaveEnabled()
        
        if bool(flag) == Enabled:
            return Enabled
        
        if flag:
            self.oDesktop.EnableAutoSave(True)
        else:
            self.oDesktop.EnableAutoSave(False)
        
        return Enabled
    
    @ProcessTime
    @DisableAutoSave
    def groupbyNets(self,netInfo):
        '''
        netInfo: {objName:net}
        '''
#         netInfo = ComplexDict(netInfo)
        netDict = {}
        for obj in self.Objects.NameList:
            if obj in netInfo:
                net = netInfo[obj]
                if net in netDict:
                    netDict[net].append(obj)
                else:
                    netDict[net] = [obj]
            else:
                log.debug("skip group object:%s"%obj)
        i = 1
        n = len(netDict)
        for net in netDict:
            #group name: Valid characters are letters, numbers, underscores
            group = re.sub(r"\W","_",net) #match [^a-zA-Z0-9]
            log.info(("Add net Gruop: %s"%net).ljust(50,"-") + "%s/%s"%(i,n))
            self.add2Group(group, netDict[net])
            i = i+1
    
    def add2Group(self,group,objs):
        if isinstance(objs, str):
            objs = [objs]
        else:
            objs = list(objs)
        
        if group in self.oEditor.GetChildNames("Groups"):
            log.debug("Add %s to group %s"%(",".join(objs),group))
            self.oEditor.MoveEntityToGroup(
                [
                    "Objects:="        , objs
                ], 
                [
                    "ParentGroup:="        , group
                ])
        else:
            self.createGroup(group, objs)

     
    def createGroup(self,group,objs=[]): 
        groupTemp = self.oEditor.GetChildNames("Groups")
        log.debug("Create group %s and add  %s"%(group,",".join(objs)))
        self.oEditor.CreateGroup(
            [
                "NAME:GroupParameter",
                "ParentGroupID:="    , "Model",
                "Parts:="        , ",".join(objs),
                "SubmodelInstances:="    , "",
                "Groups:="        , group #group name not work
            ])
        
        group2 = self.oEditor.GetChildNames("Groups")
        
        #get new group name
        newGroup = list(set(group2).difference(groupTemp))
        if newGroup:
            self.oEditor.SetPropertyValue("Attributes",newGroup[0],"Name",group)
            return newGroup[0]
        else:
            log.exception("Group create error: %s"%group)
        
        

    def setUnit(self, unit = "um"):
        #return old unit
        self.oEditor.SetModelUnits(
            [
                "NAME:Units Parameter",
                "Units:="        , unit,
                "Rescale:="        , False,
                "Max Model Extent:="    , 10000
            ])
    
    def getUnit(self):
        return self.oEditor.GetModelUnits()
    #---functions
    
    #---UDP,UDM,UDO,3DComponent
    def createUDM(self,dllName, udmParams, szLib = 'syslib'):
    
        vArg1 = ["NAME:UserDefinedModelParameters", 
                 ["NAME:Definition"],["NAME:Options"],
                 "DllName:=", dllName, "Library:=", szLib]
        vArgParamVector = ["NAME:GeometryParams"]
    
        for pair in udmParams:
            vArgParamVector.append(["NAME:UDMParam", 
                                    "Name:=", pair["Name"], 
                                    "Value:=", pair["Value"],
                                    "PropType2:=", pair["PropType2"],
                                    "PropFlag2:=", pair["PropFlag2"]
                                    ])
         
        vArg1.append(vArgParamVector)
        self.oEditor.CreateUserDefinedModel(vArg1)

    #--- IO
    
    def newProject(self,projectName):
        oProject = self.oDesktop.NewProject()
        oProject.Rename(projectName, True)
        return oProject
    
    
    def newDesign(self,newDesignName,projectName = None):
        if projectName:
            oProject = self.oDesktop.SetActiveProject(projectName)
            oProject.InsertDesign(self._toolType, newDesignName, "", "")
            self.initDesign(projectName, newDesignName)
        else:
            self.oProject.InsertDesign(self._toolType, newDesignName, "", "")
            self.initDesign(self.projectName, newDesignName)
            
        return self.oDesign
    
    def deleteProject(self):
        self.oDesktop.DeleteProject(self.ProjectName)
        self._oProject = None
        self._oDesign = None
        self._oEditor = None
    
    def deleteDesign(self):
        self.oProject.DeleteDesign(self.DesignName)
        self._oDesign = None
        self._oEditor = None

    def openAedt(self,path):
        log.info("OpenProject : %s"%path)
        self.oDesktop.OpenProject(path)
        self.initDesign(projectName=os.path.splitext(os.path.basename(path))[0])
    
    def openArchive(self,archive,newPath):
        log.info("RestoreProjectArchive: %s"%archive)
        self.oDesktop.RestoreProjectArchive(archive, newPath, False, True) 
        self.initDesign(projectName=os.path.splitext(os.path.basename(newPath))[0])
    
    def reload(self):
        aedtPath = os.path.join(self.oProject.GetPath(),self.oProject.GetName()+".aedt")
        log.info("reload AEDT %s"%aedtPath)
        self.oProject.Save()
        self.oProject.Close()
        self.oDesktop.OpenProject(aedtPath)
        self.initDesign(projectName=os.path.splitext(os.path.basename(aedtPath))[0])


    def saveAs(self,path,OverWrite=True):
        log.info("save As %s"%path)
        self.oProject.SaveAs(path, OverWrite)
        self.initDesign(projectName=os.path.splitext(os.path.basename(path))[0])

    def save(self):
        log.info("Save project: %s"%self.ProjectPath)
        self.oProject.Save()

    def close(self,save=True):
        if save:
            self.save()
        log.info("Close project: %s"%self.ProjectPath)
        self.oProject.Close()
            
    def deleteFromDisk(self):
        log.info("delete project from disk: %s"%self.ProjectPath)
        self.oDesktop.DeleteProject(self.projectName)
        if os.path.exists(self.resultsPath):
            log.info("delete project from disk: %s"%self.resultsPath)
            shutil.rmtree(self.resultsPath)

    
    @classmethod
    def quitAedt(cls):
        Module = sys.modules['__main__']
        if hasattr(Module, "oDesktop"):
            oDesktop = getattr(Module, "oDesktop")
            if oDesktop:
                oDesktop.QuitApplication()
    
    @classmethod
    def copyAEDT(cls,source,target):
        from shutil import copy
        #source = (source,source+".aedt")(".aedt" in source)
        if ".aedt" not in source:
            print("source must .aedt file: %s"%source)
            return
        if not os.path.exists(source):
            print("source file not found: %s"%source)
            return
        
        
        aedtTarget = (target+".aedt",target)[".aedt" in target]
        aedtTargetDir = os.path.dirname(aedtTarget)
        if not os.path.exists(aedtTargetDir):
            print("make dir: %s"%aedtTargetDir)
            os.mkdir(aedtTargetDir)
        
        copy(source,aedtTarget)
        
        edbSource = source[:-5]+".aedb" +"/edb.def"
        if os.path.exists(edbSource):
            edbTargetdir = aedtTarget[:-5]+".aedb"
            
            if not os.path.exists(edbTargetdir):
                print("make dir: %s"%edbTargetdir)
                os.mkdir(edbTargetdir)
            copy(edbSource,edbTargetdir)
        return aedtTarget


    #---message and job   
    def submitJob(self,host="localhost",cores=20):
        installPath = self.oDesktop.GetExeDir()
        jobId = "RSM_{:.5f}".format(time.time()).replace(".","")
        cmd = '"{exePath}" -jobid {jobId} -distributed -machinelist list={host}:-1:{cores}:90%:1 -auto -monitor \
                -useelectronicsppe=1 -ng -batchoptions "" -batchsolve {aedtPath}'.format(
                    exePath = os.path.join(installPath,"ansysedt.exe"),
                    jobId = jobId,
                    host = host, cores = cores, aedtPath = self.ProjectPath
                    )
        log.info("Project will be closed to submit job.")
        log.info("submit job ID: %s"%jobId)
        self.close(save=True)
        log.info(cmd)
        os.system(cmd)
        return jobId


    @classmethod
    def isBatchMode(cls):
        Module = sys.modules['__main__']
        return hasattr(Module, "ScriptArgument")
    
    @classmethod
    def getScriptArgument(cls):
        Module = sys.modules['__main__']
        if hasattr(Module, "ScriptArgument"):
            return getattr(Module, "ScriptArgument")
        else:
            log.exception("Not running in batchmode")
    
    def getRelPath(self,path):
        
        try:
            relPath = os.path.relpath(path,self.ProjectDir)
            return os.path.join("$PROJECTDIR",relPath)
        except:
            return path


    def release(self):
        
        releaseDesktop()
        try:
            self._oEditor = None
            self._oDesign = None
            self._oProject = None
            self._oDesktop = None
            import gc
            gc.collect()
        except AttributeError:
            pass

#for test
if __name__ == '__main__':
#     layout = Layout("2022.2")
    layout = Aedt3DToolBase("2023.2")
    layout.initDesign()