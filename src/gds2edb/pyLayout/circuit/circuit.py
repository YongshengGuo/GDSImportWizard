#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-09


#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2023-04-09
'''

'''

import os,sys,re
import shutil
import time
from collections import Counter
import subprocess

from ..desktop import initializeDesktop,releaseDesktop


from ..common.complexDict import ComplexDict
from ..common.arrayStruct import ArrayStruct
#log is a globle variable
from ..common import common
from ..common.common import *
from ..common.common import log,isIronpython
from ..common.unit import Unit
from ..common.common import DisableAutoSave,ProcessTime

from ..options import options

from .solution import Solution

class Circuit(object):
    '''
    classdocs
    '''
    maps = {
        "InstallPath":"InstallDir",
        "Path":"ProjectPath",
        "Name":"DesignName",
        "Ver":"Version",
        "Comps":"Components"
        }
    
    #FindObjects 
    primitiveTypes = ['pin', 'via', 'rect','circle', 'arc', 'line', 'poly','plg', 'circle void','line void', 'rect void', 
           'poly void', 'plg void', 'text', 'cell','Measurement', 'Port', 'component', 'CS', 'S3D', 'ViaGroup']
    definitionTypes = ["Layer","Material","Setup","PadStack","ComponentDef","Variable","Net"]
    

    def __init__(self, version=None, installDir=None,nonGraphical=False,newDesktop=False,usePyAedt=True): #usePyAedt
        '''
        初始化PyLayout对象环境
        
        - version和installDir都为None，会尝试启动最新版本的AEDT
        - version和installDir都指定时， version优先级 高于 installDir
        Examples:
            >>> PyLayout()
            open least version AEDT, return PyLayout

            >>> PyLayout(version = "2013.1")
            open AEDT 2013R1, return PyLayout
        
        '''
        self._info = ComplexDict({
            "Version":None,
            "InstallDir":None,
            },maps=self.maps)
        
        self._info.update("Version", version)
        self._info.update("InstallDir", installDir)
        self._info.update("NonGraphical", nonGraphical)
        self._info.update("newDesktop", newDesktop)
        self._info.update("UsePyAedt", usePyAedt)
        self._info.update("PyAedtApp", None)
        self._info.update("Log", log)
        self._info.update("options",options)
        self._info.update("Maps", self.maps)
        
        
        if not isIronpython:
            # Check if the pyaedt library exists in Python
            try:
                import ansys.aedt.core
            except ImportError:
                log.info("In cpython environment, pyaedt shold be installed, install command: pip install pyaedt")
                        
#             self._info.update("UsePyAedt", True)
        
        #----- 3D Layout object
        self._oDesktop = None
        self._oProject = None
        self._oDesign = None
        self._oEditor = None
        

        
        
    def __del__(self):
        '''
        Destructor to clean up Circuit resources.
        Note: This only clears local references, not the AEDT application.
        Call release() explicitly to properly shut down AEDT.
        '''
        try:
            # Only clean up internal references, not the global AEDT instance
            # releaseDesktop() should be called explicitly via release() method
            pass
        except Exception:
            pass
        
    def __getitem__(self, key):
        
        if not isinstance(key, str):
            log.exception("key for layout must be str: %s"%key)

        if key in self._info:
            return self._info[key]
        
        if not self._oDesign:
            log.exception("layout should be intial use method: 'Layout.initDesign(projectName = None,designName = None)'")
            return
        
        log.debug("try to get element type: %s"%key)
        
        for ele in self.primitiveTypes:
            collection = ele+"s"
            if key in self._info[collection]:
                log.debug("Try to return %s for key: %s"%(collection,key))
                return self._info[collection][key]
            
        log.exception("not found element on layout: %s"%key)
        return None
        
    def __setitem__(self, key,value):
        self._info[key] = value
        
        
    def __getattr__(self,key):
#         当调用一个不存在的属性时，就会触发__getattr__()
#         __getattribute__() 方法是无条件触发
        if key in ['__get__','__set__']:
            #just for debug run
            return None

        try:
            return super(self.__class__,self).__getattribute__(key)
        except:
            log.debug("Layout __getattribute__ from info: %s"%str(key))
            return self[key]
        
    def __setattr__(self, key, value):
        if key in ["_oDesktop","_oProject","_oDesign","_oEditor","_info"]:
            object.__setattr__(self,key,value)
        else:
            self[key] = value
        
    def __dir__(self):
#         return object.__dir__(self)  + self.Props
        return dir(self.__class__) + list(self.__dict__.keys()) + self.Props
    
    def __repr__(self):
        
        temp = ""
        if "ProjectName" in self._info:
            temp += "Project: %s"%self._info["ProjectName" ]
        else:
            temp += "Project: %s"%"None"
            
        if "DesignName" in self._info:
            temp += "Design: %s"%self._info["DesignName" ]
        else:
            temp += "Design: %s"%"None"
        
        return "%s Object: %s"%(self.__class__.__name__,temp)
    
    @property
    def Info(self):
        return self._info
    
    @property
    def Props(self):
        propKeys = list(self.Info.Keys)
        if self.maps:
            propKeys += list(self.maps.keys())
             
        return propKeys
        
    def __initByPyaedt(self):    
        try:
            from ansys.aedt.core import launch_desktop
            log.info("try to initial oDesktop using pyaedt Lib... ")
            self.PyAedtApp = launch_desktop(version = self.version,non_graphical=self.NonGraphical,new_desktop = self.newDesktop,close_on_exit=False)
            self.UsePyAedt = True
            self._oDesktop = self.PyAedtApp.odesktop
            sys.modules["__main__"].oDesktop = self._oDesktop
            log.logger = self.PyAedtApp.logger
#             self._info.update("Log", self.PyAedtApp._logger)
#             common.log = self.PyAedtApp._logger
        except:
            log.warning("pyaedt lib should be installed, install command: pip install pyaedt")
#             log.info("if you don't want use pyaedt to intial pylayout, please set layout.usePyAedt = False before get oDesktop")
            self.UsePyAedt = False
            log.warning("pyaedt app intial error.")
        
    @property
    def oDesktop(self):
        
        if self._oDesktop:
            return self._oDesktop
        
        #try to initial use pyaedt
        log.debug("Try to load pyaedt.")
        
        #try to get global oDesktop, for run script from aedt 
        Module = sys.modules['__main__']
        if hasattr(Module, "oDesktop"):
            oDesktop = getattr(Module, "oDesktop")
            if oDesktop:
                self._oDesktop = oDesktop
                self.UsePyAedt = bool(self.PyAedtApp) #may be lanuched from aedt internal
                if "ANSYSEM_ROOT" not in os.environ:
                    os.environ["ANSYSEM_ROOT"] = self._oDesktop.GetExeDir()
                return oDesktop
        
        if self.NonGraphical:
            log.info("Will be intial oDesktop in nonGraphical mode.")
        
        #try to intial by pyaedt
#         self.UsePyAedt = False
        if self.UsePyAedt:
            self.__initByPyaedt()

        #try to intial by internal method
        if self._oDesktop == None: 
            log.info("try to initial oDesktop using internal method... ")
            self._oDesktop = initializeDesktop(self.version,self.installDir,nonGraphical=self.NonGraphical,newDesktop=self.newDesktop)
            self.installDir = self._oDesktop.GetExeDir()
            self.UsePyAedt = False
            
        #intial error
        if self._oDesktop == None: 
            log.exception("Intial oDesktop error... ")
        
        print("Aedt Version: %s"%self._oDesktop.GetVersion())
        if "ANSYSEM_ROOT" not in os.environ:
            os.environ["ANSYSEM_ROOT"] = self._oDesktop.GetExeDir()

        #do not set oDesktop to main modules, AEDT has a chance of crashing under certain circumstances.  
        sys.modules["__main__"].oDesktop = self._oDesktop
        return self._oDesktop

    def getInstallPath(self,version=None):
        if self.InstallDir: 
            return self.InstallDir

        if self._oDesktop:
            return self._oDesktop.GetExeDir()
        
        if "ANSYSEM_ROOT" in os.environ: 
            return os.environ["ANSYSEM_ROOT"]

        if version:
            ver = version.replace(".", "")[-3:]
            verEnv = "ANSYSEM_ROOT%s" % ver
            
            if verEnv in os.environ:
                return os.environ[verEnv] 
        

        ANSYSEM_ROOTs = list(
            filter(lambda x: "ANSYSEM_ROOT" in x, os.environ))
        if ANSYSEM_ROOTs:
            log.debug("Try to initialize Desktop in latest version")
            ANSYSEM_ROOTs.sort(key=lambda x: x[-3:])
            return os.environ[ANSYSEM_ROOTs[-1]]

        try:
            installPath = self.oDesktop.GetExeDir()
            return installPath
        except:
            log.exception("ANSYSEM_ROOT must be set to get InstallPath.")
            return None

    def initProject(self,projectName = None):
        #layout properties initial
        #----- 3D Layout object
#         self._oDesktop = None
        self._oProject = None
#         self._oDesign = None
#         self._oEditor = None
        oDesktop = self.oDesktop
         
#         log.debug("AEDT:"+self.Version)
        projectList = oDesktop.GetProjectList()
        #for COM Compatibility, yongsheng guo #20240422
        if "ComObject" in str(type(projectList)):
            projectList = [projectList[i] for i in range(projectList.count)]
             
        if len(projectList)<1:
#             log.error("Must have one project opened in aedt.")
#             exit()
#             log.error("Must have one project opened in aedt.")
            log.warning("not found opened projects, insert new one.")
            oProject = oDesktop.NewProject()
            oProject.InsertDesign("HFSS 3D Layout Design", "Layout1", "", "")
            self._oProject = oProject
         
        else:
         
            if projectName:
    #             messageBox("projectName&designName")
                if projectName not in projectList:
                    log.error("project not in aedt:%s"%projectName)
                    raise Exception("project not in aedt: %s"%projectName)
                self._oProject = oDesktop.SetActiveProject(projectName)
     
            else:
                self._oProject = oDesktop.GetActiveProject()
                 
                if not self._oProject:
                    self._oProject = oDesktop.GetProjects()[0]
                    oDesktop.SetActiveProject(self._oProject.GetName())
                 
        if not self._oProject:
            log.error("Must have one project opened in aedt.")
            raise Exception("Must have one project opened in aedt.")
         
        self._info.update("oProject",self._oProject)

        self._info.update("ProjectName", self._oProject.GetName())
        self._info.update("projectDir", self._oProject.GetPath())
         
        self._info.update("ProjectPath", os.path.join(self._info.projectDir,self._info.projectName+".aedt"))
        self._info.update("ResultsPath", os.path.join(self._info.projectDir,self._info.projectName+".aedtresults"))
        self._info.update("EdbPath", os.path.join(self._info.projectDir,self._info.projectName+".aedb"))
 
        self._info.update("Version", self.oDesktop.GetVersion())
        self._info.update("InstallDir", self.oDesktop.GetExeDir())
        self._info.update("InstallPath", self.oDesktop.GetExeDir())
    
    
    def initDesign(self,projectName = None,designName = None, initLayout = True):
        '''Try to intial project properties.
        
        AEDT must have on project and design opened.
        
        - if projectName give, will be initialize the given project.
        - if designName give and the projectName must give, will be initialize the given project and design
        - if projectName and designName not give, it will try to initialize the firt project or design in AEDT
        
        Args:
            projectName (str): projectName to be actived, default is first project in aedt
            designName (str): designName to be actived, default is first design in project
        
        Exceptions:
            Not have project or design in AEDT
        
        '''
        #layout properties initial
        #----- 3D Layout object
#         self._oDesktop = None
        self._oProject = None
        self._oDesign = None
        self._oEditor = None
        self._info.update("Solution", [])
        
        self.initProject(projectName)
 
        designList = self.getDesignNames()
        if len(designList)<1:
            log.error("Must have one design opened in project.")
            self._info.update("oDesign",None)
            self._info.update("oEditor",None)
            self._info.update("DesignName", "")
            
        else:
        
            if designName:
                if designName not in designList:
                    log.error("design not in project.%s"%designName)
                    raise Exception("design not in project.%s"%designName)
                self._oDesign = self._oProject.SetActiveDesign(designName)
            else:
                
                #update for 2025.1
                try:
                    self._oDesign = self._oProject.GetActiveDesign()
                except:
                    log.info("GetActiveDesign error.")
#                     log.info("try to get the first design")
#                     self._oDesign = self._oProject.SetActiveDesign(designList[0])
                
                #for 2024.2 GetActiveDesign() may return None
                if not self._oDesign:
                    log.info("try to get the first design")
                    self._oDesign = self._oProject.SetActiveDesign(designList[0])
                    
                    
                #make sure the design is 3DL
                designtype = self._oDesign.GetDesignType()
                if designtype == "Circuit":
                    self._info.update("oDesign",self._oDesign)
#                     self._info.update("oEditor",self._oDesign.SetActiveEditor("Layout"))
                    self._info.update("DesignName", self.getDesignName(self._oDesign))
                elif designtype == "Circuit Netlist":
                    self._info.update("oDesign",self._oDesign)
                    self._info.update("DesignName", self.getDesignName(self._oDesign))
                    oModule = self._oDesign.GetModule("ReportSetup")
                    solutions = oModule.GetAvailableSolutions("Standard")
                    
                    if len(solutions)>0:
                        self._info.update("DefaultSolution",self.getSolutionData(solutions[0],solutions[0]))
                else:
                    log.exception("design type error, not Circuit design.")  #exception if not 3DL design
                
                
                #intial log with design
                path = os.path.join(self._info.projectDir,"%s_%s.log"%(self._info.projectName,self._info.designName))
                if self.UsePyAedt or "AedtLogger" in str(type(log.logger)):
                    import logging
                    fileHandler = log.logger.logger.handlers[0]
                    # 显式设置文件编码为 UTF-8，避免 Windows 下 charmap/cp1252 编码错误
                    fileHandler2 = logging.FileHandler(path, encoding='utf-8')
                    fileHandler.stream = fileHandler2.stream
                    fileHandler.baseFilename = path
                    log.logger.logger.removeHandler(fileHandler)
                    log.logger.logger.addHandler(fileHandler)
                    del fileHandler2
                    del fileHandler
                    
                else:
                    log.setPath(path)
                    log.info("Simulation log recorded in: %s"%path)
                
                log.info("init design: %s : %s"%(self.projectName,self.designName))
                    

#                 #intial layout elements
#                 if initLayout and self._info.oEditor:
#                     self.initObjects()

    def initObjects(self):
        
        info = self._info
        
        info.update("Version",self.oDesktop.GetVersion())
        info.update("layout",self)
        
        
    def getDesignName(self,oDesign):
        return oDesign.GetName().split(';')[-1]
    
    def getDesignNames(self):
        return [name.split(';')[-1] for name in self._oProject.GetTopDesignList()]  
                
    #--- design

    def getSolutionData(self,name,type):
        if type == "DC":
            return Solution(name,type,self)
        elif type == "Transient":
            pass
        else:
            log.exception("not support solution type: %s"%type)

    def enableAutosave(self,flag=True):
        Enabled = self.oDesktop.GetAutoSaveEnabled()
        
        if bool(flag) == Enabled:
            return Enabled
        
        if flag:
            log.info("Enable autosave.")
            self.oDesktop.EnableAutoSave(True)
        else:
            log.info("Disenable autosave.")
            self.oDesktop.EnableAutoSave(False)
        
        return Enabled

    #--- objects

    
    
    def select(self,objs):
        '''
        objs: names of  objs
        '''
        if isinstance(objs, str):
            objs = [objs]
            
        self.oEditor.Select(objs)
        
    
    def delete(self,objs):
        '''
        objs: names of delete objs
        '''
        if isinstance(objs, str):
            objs = [objs]
            
        for name in objs:
            try:
                obj = self.Objects[name]
                self[obj.Type+"s"].pop(name)
            except:
                log.warning("%s: delete error from layout."%name)
                
        self.oEditor.Delete(objs)
        self.Objects.refresh()
        self.Traces.refresh()
        self.Shapes.refresh()
        self.Voids.refresh()

        

    
    #---functions
    
    #---Create objects

    #--- IO
    
    def newProject(self,projectName = None):
        oProject = self.oDesktop.NewProject()
        if projectName:
            oProject.Rename(projectName, True)
        self.initProject(projectName)
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
    
    
#     def newDesign(self,newDesignName,newPorjectName = None):
#         if newPorjectName:
#             oProject = oDesktop.NewProject()
#             oProject.Rename(os.path.join(oProject.GetPath(),newPorjectName), True)
#             oProject.InsertDesign("HFSS 3D Layout Design", newDesignName, "", "")
#             self.initDesign(newPorjectName, newDesignName)
#         else:
#             self.oProject.InsertDesign("HFSS 3D Layout Design", newDesignName, "", "")
#             self.initDesign(self.projectName, newDesignName)
    

    def openAedt(self,path,unlock=False):
        if unlock:
            if os.path.exists(path+".lock"):
                os.remove(path)
        
        log.info("OpenProject : %s"%path)
        self.oDesktop.OpenProject(path)
        self.initDesign()
        
        #if open sdf or netlist, projectname nay not same with file name
#         self.initDesign(projectName=os.path.splitext(os.path.basename(path))[0])
    
    def openArchive(self,archive,newPath):
        log.info("RestoreProjectArchive: %s"%archive)
        self.oDesktop.RestoreProjectArchive(archive, newPath, False, True) 
        self.initDesign(projectName=os.path.splitext(os.path.basename(newPath))[0])
    
    def reload(self):
        aedtPath = self.ProjectPath
        log.info("reload AEDT %s"%aedtPath)
        self.oProject.Save()
        self.oProject.Close()
        self.oDesktop.OpenProject(aedtPath)
        self.initDesign(projectName=os.path.splitext(os.path.basename(aedtPath))[0])

    def saveAs(self,path,OverWrite=True):
        log.info("save As %s"%path)
        
        subDir = os.path.dirname(path)
        if not os.path.exists(subDir):
            os.makedirs(subDir)
        
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
                log.info("QuitApplication.")
                oDesktop.QuitApplication()
        wait=5
        time.sleep(wait) #wait for aedt quit
    
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

    #---analyze and job   
    def analyze(self):
        self.oDesign.AnalyzeAll()
    
    def submitJob(self,host="localhost",cores=4):
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
#         with os.popen(cmd,"r") as output:
#             for line in output:
#                 log.info(line)
#             output.close()
        
        return jobId
    
    def batchNexxim(self,path,installPath=None):
        if not os.path.exists(path):
            log.info("spice file not exist: %s"%path)
            return

        #根据ANSYSEM_ROOT 环境变量，获取Ansys EM installPath安装路径

        if not installPath:
            installPath = self.getInstallPath()

        if installPath not in os.environ["PATH"]:
            os.environ["PATH"] = installPath + os.pathsep + os.environ["PATH"]

        #nexxim [–ooutput_file] [options] input_file
        #nexxim input_file [num_threadsworkgroup] [-hpc_type#] [-use_gpu#] [-enable_tpbs#]
        cmd = r'nexxim "{0}" -o "{1}" -logfile "{2}"' 
        logfile = os.path.splitext(path)[0] +".log"
        sdfFile = os.path.splitext(path)[0] +".sdf"
        cmd = cmd.format(path,sdfFile,logfile)
        log.info(cmd)
        output = os.popen(cmd,"r")
        for line in output:
            log.info(line)
        log.info("finished analysis %s"%path)
        return sdfFile

    def getHspicePath(self):

        if "installdir_Hspice" in os.environ:
            installPath = os.environ["installdir_Hspice"]
        else:
            for each in os.environ:
                if each.lower().startswith("installdir_"):
                    installPath = os.environ[each]

        if installPath and isinstance(installPath, str):
            if "nt" in os.name:
                if os.path.join(installPath,"WIN64") not in os.environ["PATH"]: #for windows
                    os.environ["PATH"] = os.path.join(installPath,"WIN64") + os.pathsep + os.environ["PATH"]
                return os.path.join(installPath,"WIN64")
            else:
                if os.path.join(installPath,"linux64") not in os.environ["PATH"]: #for Linux
                    os.environ["PATH"] = os.path.join(installPath,"linux64") + os.pathsep + os.environ["PATH"]
                return os.path.join(installPath,"linux64")
        else:
            log.info("Hspice in system path, installdir_ environment will be used if set.")


    def batchHSpice(self,path,installPath=None,cores=2):
        if not os.path.exists(path):
            log.info("spice file not exist: %s"%path)
            return

        if not installPath:
            installPath = self.getHspicePath()

#             if not os.path.exists(os.path.join(installPath,"WIN64/hspice.exe")):
#                 log.exception("hspice.exe not found,please set HSpice Install path in system environment")
        if installPath and isinstance(installPath, str):
            if installPath not in os.environ["PATH"]:
                os.environ["PATH"] = installPath + os.pathsep + os.environ["PATH"]
            
            if "nt" in os.name:
                if os.path.join(installPath,"WIN64") not in os.environ["PATH"]: #for windows
                    os.environ["PATH"] = os.path.join(installPath,"WIN64") + os.pathsep + os.environ["PATH"]
            else:
                if os.path.join(installPath,"linux64") not in os.environ["PATH"]: #for Linux
                    os.environ["PATH"] = os.path.join(installPath,"linux64") + os.pathsep + os.environ["PATH"]
                
        else:
            log.info("Hspice in system path environment will be used if set.")
    
        #\WIN64\hspice.com -i cpa_rh_pkg_wrapper_ASCII_hspice.sp -o cpa_rh_pkg_wrapper_ASCII_hspice.lis -mt 2
        cmd = r'hspice -mt {2} -i "{0}" -o "{1}"' 
        logfile = os.path.splitext(path)[0] +".lis"
        cmd = cmd.format(path,logfile,cores)
        log.info(cmd)
        output = os.popen(cmd,"r")
        for line in output:
            log.info(line)
        log.info("finished analysis %s"%path)
        return logfile

    def sdf2csv(self, sdfFile, csvPath=None):
        '''Convert SDF file to CSV format using sdf2csv tool'''
        #Usage: sdf2csv infile [-o outfile] [-t time_step | -f (use timestep from file) ]
        #sdf2csv 在installDir目录下
        #执行命令 sdf2csv sdfFile -o csvPath
        
        
        if not os.path.exists(sdfFile):
            log.error("SDF file not exist: %s"%sdfFile)
            return None

        if not csvPath:
            csvPath = os.path.splitext(sdfFile)[0] + ".csv"
        
        #sdf2csv 在 installDir 目录下
        installDir = self.getInstallPath()
        
        if "nt" in os.name:  # Windows
            sdf2csvExe = os.path.join(installDir, "sdf2csv.exe")
        else:  # Linux
            sdf2csvExe = os.path.join(installDir, "sdf2csv")
        
        #执行命令 sdf2csv sdfFile -o csvPath
        cmd = [sdf2csvExe, sdfFile, "-o", csvPath]
        
        log.info("Convert SDF to CSV: %s"%sdfFile)
        log.info("Command: %s"%" ".join(cmd))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20*60)
            
            if result.stdout:
                log.info(result.stdout)
            if result.stderr:
                log.warning(result.stderr)
            
            if result.returncode == 0 and os.path.exists(csvPath):
                log.info("SDF converted successfully: %s"%csvPath)
                return csvPath
            else:
                log.error("SDF convert failed with return code: %s"%result.returncode)
                return None
        except Exception as e:
            log.exception("Error executing sdf2csv: %s"%str(e))
            return None


    def batchAnalysis(self,host="localhost",cores=20):
        installPath = self.oDesktop.GetExeDir()
        jobId = "RSM_{:.5f}".format(time.time()).replace(".","")
        cmd = '"{exePath}" -jobid {jobId} -distributed -machinelist list={host}:-1:{cores}:90%:1 -auto -monitor \
                -useelectronicsppe=1 -ng -batchoptions "" -batchsolve {aedtPath}'.format(
                    exePath = os.path.join(installPath,"ansysedt.exe"),
                    jobId = jobId,
                    host = host, cores = cores, aedtPath = self.ProjectPath
                    )
        log.info("Project will be closed to batch Analysis.")
        log.info("submit job ID: %s"%jobId)
        self.close(save=True)
        log.info(cmd)
        with os.popen(cmd,"r") as output:
            for line in output:
                log.info(line)
            output.close()

    def setCores(self,cores,hpcType = None):
        '''
        cores (int): 
        hpcType (str): Pack or Workgroup
        '''
        
        oDesktop = self.oDesktop
        #worked
        activeHPCOption = oDesktop.GetRegistryString("Desktop/ActiveDSOConfigurations/HFSS 3D Layout Design")
        log.info("ActiveDSOConfigurations: %s"%activeHPCOption)
        #oDesktop.SetRegistryString(r"Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s/NumCores"%activeHPCOption)
        activeHpcStr = oDesktop.GetRegistryString("Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s"%activeHPCOption)
        
        cores_old = re.findall(r"NumCores=(\d+)", activeHpcStr)
        
        if cores_old and int(cores_old[0])!=int(cores):
            activeHpcStr = re.sub(r"NumCores=\d+","NumCores=%s"%int(cores), activeHpcStr)
            
            
    #         #not work
    #         log.info('set Active HPC Configuration "%s":  NumCores=%s'%(activeHPCOption,cores))
    #         oDesktop.SetRegistryString("Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s"%activeHPCOption,activeHpcStr)
    #         
            #workaround
            scfStr = "$begin 'Configs'\n$begin 'Configs'\n%s$end 'Configs'\n$end 'Configs'\n"%activeHpcStr
            pathScf = os.path.join(self.projectDir,"hpc.acf")
            writeData(scfStr, pathScf)
            log.info('set Active HPC Configuration "%s":  NumCores=%s'%(activeHPCOption,cores))
            self.oDesktop.SetRegistryFromFile(pathScf)
        else:
            log.info("ActiveDSOConfigurations have the same cores as required")
        
        if hpcType:
            self.setHPCType(hpcType)

        
    def setHPCType(self,hpcType):
        '''
        hpcType (str): Pack or Workgroup
        '''
        if hpcType:
            #oDesktop.GetRegistryString("Desktop/Settings/ProjectOptions/HPCLicenseType")
            log.info('set HPCLicenseType: %s'%(hpcType))
            self.oDesktop.SetRegistryString("Desktop/Settings/ProjectOptions/HPCLicenseType",hpcType)
        
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

    #---message  

    def message(self,msg,level = 0):
        global oDesktop
        log.debug(msg)
        self.oDesktop.AddMessage("","",0,msg)


    def release(self):
        '''
        Release COM resources and relinquish AEDT window control.
        
        This method releases the COM interface resources held by this Circuit object,
        allowing other applications or scripts to control AEDT. The AEDT application
        and open projects remain open.
        
        Behavior:
        - Closes the circuit's project reference
        - Clears internal object references
        - Calls releaseDesktop() to release COM resources
        
        Note:
            - AEDT window remains open
            - Open projects remain open (but are not held by this object anymore)
            - To fully close AEDT, call Circuit.quitAedt() instead
        
        Examples:
            >>> layout = Circuit()
            >>> layout.initDesign("MyProject", "MyDesign")
            >>> # ... do work ...
            >>> layout.release()  # Release COM resources
        '''
        try:
            # Clear internal references
            self._info = None
            self._oEditor = None
            self._oDesign = None
            self._oProject = None
            self._oDesktop = None
            import gc
            gc.collect()
        except AttributeError:
            pass
        
        # Release COM resources - this allows other apps/scripts to use AEDT
        releaseDesktop()

    @classmethod
    def setClr(cls):
        isIronpython = "IronPython" in sys.version
        is_linux = "posix" in os.name
        
        if is_linux and not isIronpython:
            try:
                from ansys.aedt.core.generic.clr_module import _clr
            except:
                log.exception("pyaedt must be install: pip3 install pyaedt")
        else:
            import clr as _clr
        return _clr

#for test
if __name__ == '__main__':
#     layout = Layout("2022.2")
    layout = Layout("2023.2")
    layout.initDesign()
    layout.via1062
    layout.port[0]
    U8 = layout["Component:U8"]
    U9 = layout["Component:U8"]
    a= layout.Copper
    a["Resistivity"]= 1.0e-08
    layout.Layers.addLayer("L0")
    pins = U8.Pins
    layout.Port1
    pin = layout["U8_1"]
    dir(U8)
    pin = layout["Pin:U8-1"]
#     top = layout["Layer:C:0"]
    fr4= layout.Materials["FR4_epoxy"]
#     rst = layout.Solutions.getAllSetupSolution()
#     layout.Variables.test
    layout.release()
#     rst[0].exportSNP("c:\work\1.txt")
    pass