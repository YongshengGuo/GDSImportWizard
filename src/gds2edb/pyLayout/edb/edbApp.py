#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20250403

import os,sys,re
from ..common.common import *
from ..common.log import switchLogPath
# from ..common.common import readCfgFile,log

from ..common.complexDict import ComplexDict
from ..common.config import Config
from .edbSiwaveOption import EdbSIwaveOptions
from .edbPinGroup import EdbPinGroup,EdbPinGroups
from .edbComponent import EdbComponent,EdbComponents
from .edbLayer import EdbLayer,EdbLayers
from .edbPrimitive import EdbPrimitive,EdbPrimitives
from .edbDefinition import EdbDefinition,EdbDefinitions
from .edbVia import EdbVia,EdbVias
from .edbNet import EdbNet,EdbNets
from .edbNetClass import EdbNetClass,EdbNetClasses
import shutil

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)


try:
    _clr = initClr()
    from System import String
except:
    log.debug("CLR initialization failed in child process (likely duplicate init). Ignoring if not needed.")

def edbToSIwave(edbPath,siwPath=None,installDir=None):
#     log.info(str(installDir)) #for debug
#     log.info(str(edbPath)) #for debug
#     log.info(str(siwPath)) #for debug
    
    if not siwPath:
        siwPath = os.path.splitext(edbPath)[0]+".siw"
    
    if not installDir:
        if 'Ansys.Ansoft.Edb' in sys.modules:
            installDir = os.path.dirname(sys.modules['Ansys.Ansoft.Edb'].__file__)
        elif "ANSYSEM_ROOT" in os.environ:
            installDir = os.environ["ANSYSEM_ROOT"]
        else:
            log.exception("Aedt installDir or ANSYSEM_ROOT must set before translate edb to siwave.")
    
    execPath = os.path.join(os.path.dirname(siwPath), "SaveSiw.exec") 
    with open(execPath,"w+") as f:
        f.write("SaveSiw %s\n"%siwPath)
        f.write("WaitForLicense  true")
        f.close()
    cmd = '"{0}" {1} {2} -formatOutput'.format(os.path.join(installDir,"siwave_ng"),edbPath,execPath)
    log.info("Save project to Siwave: %s"%siwPath)
    with os.popen(cmd,"r") as output:
        for line in output:
            log.info(line)
        output.close()
    
    return siwPath


def initEdb(version=None, installDir=None):

    aedtInstallDir = None
    if installDir:
        aedtInstallDir = os.path.abspath(installDir)
    else:
        if version:
            ver = version.replace(".", "")[-3:]
            verEnv = "ANSYSEM_ROOT%s" % ver
            
            if verEnv in os.environ:
                aedtInstallDir = os.environ[verEnv] 
        
        if aedtInstallDir:
            pass
        elif "ANSYSEM_ROOT" in os.environ:
            aedtInstallDir = os.environ["ANSYSEM_ROOT"]
        else:
            ANSYSEM_ROOTs = list(
                filter(lambda x: "ANSYSEM_ROOT" in x, os.environ))
            if ANSYSEM_ROOTs:
                log.debug("Try to initialize Desktop in latest version")
                ANSYSEM_ROOTs.sort(key=lambda x: x[-3:])
                aedtInstallDir = os.environ[ANSYSEM_ROOTs[-1]]

    # set version from aedtInstallDir
    if version == None:
        if not aedtInstallDir:
            log.exception("please set environ ANSYSEM_ROOT=Ansys EM install path...")
        ver1 = re.split(r"[\\/]+", aedtInstallDir)[-2]
        ver2 = ver1.replace(".", "")[-3:]
        version = "Ansoft.ElectronicsDesktop.20%s.%s" % (ver2[0:2],ver2[2])
    else:
        if "Ansoft.ElectronicsDesktop" not in version:
            version = "Ansoft.ElectronicsDesktop." + version

    if aedtInstallDir: 
        
        print("AEDT InstallDir: %s"%aedtInstallDir)

        if "ANSYSEM_ROOT" not in os.environ:
            os.environ["ANSYSEM_ROOT"] = aedtInstallDir
        os.environ["ANSYS_OADIR"] = os.path.join(aedtInstallDir,'common','oa')
        sys.path.append(aedtInstallDir)
        os.environ["PATH"] = os.pathsep.join([aedtInstallDir,os.path.join(aedtInstallDir,r"common/mono/Linux64/bin"),os.environ["PATH"] ])
        #for edb evniron
        if is_linux:
            old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join([os.path.join(aedtInstallDir,r"common/mono/Linux64/lib64"),
                                                         os.path.join(aedtInstallDir,r"Delcross"),old_ld])
        #export LD_LIBRARY_PATH=/usr/lib64:/usr/local/lib:$LD_LIBRARY_PATH<---- Added

    else:
        log.exception("please set environ ANSYSEM_ROOT=Ansys EM install path...")
    
    if isPython:
    
#         _clr.AddReference("System.Core")
        _clr.AddReference('Ansys.Ansoft.CoreDotNet')
        _clr.AddReference("Ansys.Ansoft.Edb")
        _clr.AddReference("Ansys.Ansoft.EdbBuilderUtils")
        _clr.AddReference("Ansys.Ansoft.SimSetupData")
    else:
#         import clr
        # Configure EDB path information
#         oaDir = Path.Combine(aedtInstallDir, os.path.join('common','oa'))
#         Environment.SetEnvironmentVariable("ANSYS_OADIR", oaDir)
#         sys.path.append(aedtInstallDir) # configure sys.path to see the assembly
#         Environment.SetEnvironmentVariable("PATH", aedtInstallDir + ";" + Environment.GetEnvironmentVariable("PATH")) # configure PATH env to so assembly can see shared dll's
        _clr.AddReference('Ansys.Ansoft.CoreDotNet.dll')
        _clr.AddReference('Ansys.Ansoft.PluginCoreDotNet.dll')
        _clr.AddReference('Ansys.Ansoft.Edb.dll')
        _clr.AddReference('Ansys.Ansoft.SimSetupData.dll')

    import Ansys.Ansoft.Edb as Edb
#     Edb = __import__("Ansys.Ansoft.Edb")
    
    if Edb:
        Edb.Database.SetRunAsStandAlone(True)
        return Edb
    else:
        log.exception("load edb module failed")
    # self.edb = edb.Ansoft.Edb
    # edbbuilder = __import__("Ansys.Ansoft.EdbBuilderUtils")
    # self.edbutils = edbbuilder.Ansoft.EdbBuilderUtils
    # self.simSetup = __import__("Ansys.Ansoft.SimSetupData")
    # self.simsetupdata = self.simSetup.Ansoft.SimSetupData.Data



class EdbApp(object):
    
    def __init__(self,edbPath=None,version=None,installDir=None):

        self.maps = {
            "InstallPath":"InstallDir",
            "Path":"edbPath",
            "Name":"DesignName",
            "Ver":"Version",
            "Comps":"Components"
            }
        
        self._info = ComplexDict({
            "Version":version,
            "InstallDir":installDir,
            "edbPath":edbPath,
            "db":None,
            "cell":None,
            "layout":None,
            "SiaveOptions":None,
            "PinGroups":None,
            "edb":None,
            "LogPath":None,
            "pyEdb":None
            },maps=self.maps)
        self._info.update("Log", log)

        if edbPath:
            self.open(edbPath)

    def __del__(self):
        """
        destructor saves and closes active db if valid
        """
        #if self.saveEdb and self.db and not self.db.IsNull():
#         self.del2()
        try:
            if self.db and not self.db.IsNull():
                self.db.Save()
                self.db.Close()
        except:
            pass

    def __getitem__(self, key):
        
        if not isinstance(key, str):
            log.exception("key for layout must be str: %s"%key)

        if key in self._info:
            return self._info[key]
        
        if not self._info.cell:
            log.exception("Edb should be intial use method: 'EdbApp.initLayout()'")
            return
        
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
            return object.__getattribute__(self,key)
        except:
            log.debug("EdbApp __getattribute__ from info: %s"%str(key))
            return self[key]
        
    def __setattr__(self, key, value):
        if key in ["_info","maps"]:
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

    def initPyEdb(self):
        try:
            from ansys.aedt.core import Edb  # @UnresolvedImport
            edbapp = Edb(edbversion=self.version)
            self.pyEdb = edbapp
            self.edb = edbapp._edb
#                 os.environ["ANSYSEM_ROOT"] = edbapp.base_path
            self.installDir = os.path.dirname(self.edb.__file__)
            if "ANSYSEM_ROOT" not in os.environ:
                os.environ["ANSYSEM_ROOT"] = self.installDir
                
            return self.edb
        except:
            log.error("init edb error form ansys pyedb ... ")

    @property
    def Edb(self):
        
        if self.edb:
            return self.edb
        
#         if is_linux and isPython:
#             self.edb = self.initPyEdb()
#             return self.edb
        
        try:
            self.edb = initEdb(self.version,installDir=self.InstallDir)
#                 self.installDir = os.environ["ANSYSEM_ROOT"]
            if not self.installDir:
                self.installDir = os.path.dirname(self.edb.__file__)
            if "ANSYSEM_ROOT" not in os.environ:
                os.environ["ANSYSEM_ROOT"] = self.installDir
            return self.edb
        except:
            log.error("init edb error , try to init using pyedb mathod.")
        
        #other method
        self.initPyEdb()
    
        if not self.edb:
            log.exception("init edb error ... ")
                
        return self.edb
        
    def setLogPath(self,path):
        self.LogPath = path
        try:
            logger1 = log.logger.logger
        except:
            logger1 = log.logger
        old_log_path = switchLogPath(logger1,path)
        if not isSamePath(path, old_log_path) and os.path.exists(old_log_path):
            os.remove(old_log_path)
        
    def initLayout(self):
        if not self.cell:
            log.exception("cell is null, please open aedb file first.")
        self._info.update("SIwaveOptions", EdbSIwaveOptions(self))
        self._info.update("Layers", EdbLayers(self))
        self._info.update("PinGroups", EdbPinGroups(self))
        self._info.update("Components", EdbComponents(self))
        self._info.update("Vias", EdbVias(self))
        self._info.update("Primitives", EdbPrimitives(self))
        self._info.update("Objects", EdbPrimitives(self))
        self._info.update("Layers", EdbLayers(self))
        self._info.update("Nets", EdbNets(self))
        self._info.update("NetClass", EdbNetClasses(self))
        

        self._info.update("edbPath", os.path.abspath(self.db.GetDirectory()))
        split = os.path.split(self._info.edbPath)
        self._info.update("ProjectName",split[1][:-5])
        self._info.update("projectDir",split[0])
        self._info.update("ProjectPath", split[0])
        self._info.update("ResultsPath", os.path.join(self._info.projectDir,self._info.projectName+".aedtresults"))
        self._info.update("AedtPath", os.path.join(self._info.projectDir,self._info.projectName+".aedt"))
        self._info.update("DesignName",self.cell.GetName())

        if not self.installDir:
            self._info.update("installDir", os.path.dirname(self.edb.__file__))
        
        if not self.LogPath:
            #intial log with design
            path = os.path.join(self._info.projectDir,"%s_edb.log"%(self._info.projectName))
            try:
                logger1 = log.logger.logger
            except:
                logger1 = log.logger
            
            switchLogPath(logger1, path)
            log.info("Simulation log recorded in: %s"%path)

    def open(self,edbPath=None):

        """
        Open and initialize from edbFN.
        First of db.TopCircuitCells is set active in this object
        """
        if not edbPath:
            edbPath = self.edbPath
        else:
            self.edbPath = edbPath
        if not os.path.exists(edbPath):
            log.exception('Edb could not be found at "{0}"'.format(edbPath))
            return False
        log.info("Open Edb: %s"%edbPath)
        self.Edb.Database.SetRunAsStandAlone(True)
        self.db = self.Edb.Database.Open(edbPath, False)
        if self.db.IsNull():
            log.exception('Edb could not be opened at "{0}"'.format(edbPath))
            return False
        cells = list(self.db.TopCircuitCells)
        if cells:
            self.cell = cells[0]
        if self.cell and self.cell.IsNull():
            log.exception('TopCircuitCell could not be found'.format(edbPath))
            return False
        self.layout = self.cell.GetLayout()
        self.initLayout()

        return True  
    

    def attachEdb(self,hdb=None):
        '''
        not work @ list(self.db.TopCircuitCells) ...
        '''
        if is_linux:
            try:
                from ansys.aedt.core.generic.clr_module import _clr # @UnresolvedImport 
            except:
                log.info("Make sure pyaedt have installed on linux: pip install pyaedt")
                from ansys.aedt.core.internal.clr_module import _clr # @UnresolvedImport
        else:
            #for windows
            import clr as _clr # @UnresolvedImport
        
        from System import Convert

        try:
            self.Edb.Database.SetRunAsStandAlone(False)
            hdl = Convert.ToUInt64(hdb)
            self.db = self.Edb.Database.Attach(hdl)
        except:
            log.exception("attach edb error.")
            return False

        if self.db.IsNull():
            log.exception('Edb could not be opened')
            return False
        cells = list(self.db.TopCircuitCells)
        if cells:
            self.cell = cells[0]
        if self.cell and self.cell.IsNull():
            log.exception('TopCircuitCell could not be found')
            return False

        return True  



    def loadLayout(self,layoutPath ,edbOutPath = None,controlFile = "", layoutType = None, extractExePath = None):
        '''
        doc
        '''
   
        if not layoutType:
            if layoutPath[-4:].lower() in [".brd",".mcm",".sip"]:
                layoutType = "Cadence"
            elif layoutPath[-4:].lower() in [".siw"]:
                layoutType = "SIwave"
            elif layoutPath[-5:].lower() in [".aedt","aedtz"]:
                layoutType = "AEDT"
            elif layoutPath[-5:].lower() in [".aedb"]:
                layoutType = "EDB"
            elif layoutPath[-7:].lower() in ["edb.def"]:
                layoutType = "EDB"
                
            elif layoutPath[-4:].lower() in [".tgz"]:
                layoutType = "ODB++"
                
            elif layoutPath[-4:].lower() in [".gds"]:
                layoutType = "GDS"
                
            else:
                raise Exception("Layout type must be specified")
        
        if extractExePath:
            if extractExePath[-4:].lower() == ".exe":
                extractExePath = os.path.dirname(extractExePath)
                
            if extractExePath not in os.environ['PATH']:
                os.environ['PATH'] = os.pathsep.join([extractExePath,os.environ['PATH']])
                log.debug(os.environ['PATH'])
        
        
        if layoutType.lower() == "aedt":
            self.open(layoutPath[:-4]+"aedb")
        elif layoutType.lower() == "edb":
            self.open(layoutPath)
        elif layoutType.lower() == "cadence":
            if not edbOutPath:
                edbOutPath = layoutPath[:-4] + ".aedb"
            if not controlFile:
                controlFile = ""
            # self.importBrd(layoutPath,edbOutPath,controlFile)
        elif layoutType.lower() == "odb++":
            if not edbOutPath:
                edbOutPath = layoutPath[:-4] + ".aedb"
            if not controlFile:
                controlFile = ""
            # self.importODB(layoutPath,edbOutPath,controlFile)

        elif layoutType.lower() == "siwave":
            self.importSIwave(layoutPath)

        else:
            raise Exception("Unknow layout type")
    
        
    def findObjById(self,id):
        return EdbDefinition(self.edb.Cell.Connectable.FindById(self.layout,id),type="Connectable",edbApp=self)

    def hasObj(self,obj,objs):
        id1 = obj.GetId()
        for each in objs:
            if each.GetId() == id1:
                return True
        return False

    #--- find objects features
    

    def removeObj(self,obj,objs):
        id1 = obj.GetId()
        flag = False
        for each in objs:
            if each.GetId() == id1:
                flag = True
                break
        if flag:
            objs.remove(each)
            return objs
        else:
            log.info("Object %s not found."%id1)
            return objs

    def save(self):
        if self.db and not self.db.IsNull():
            self.db.Save()
        else:
            log.error("Database not valid.")
    
    def close(self):
        if self.db and not self.db.IsNull():
            self.db.Close()
        else:
            log.error("Database not valid.")
    
    def removeAllSimSetup(self):
        setups = [x for x in self.cell.SimulationSetups]
        for setup in setups:
            self.cell.DeleteSimulationSetup(setup.GetName())

    def importSIwave(self,path,edbPath = None):
        if edbPath == None:
            edbPath = os.path.splitext(path)[0]+".aedb"

        execPath = os.path.join(os.path.dirname(path), "SaveSiw.exec")
        with open(execPath,"w+") as f:
            f.write("SaveEdb %s"%edbPath)
            f.close()

        installDir = self.installDir or os.path.dirname(self.Edb.__file__)

        if installDir not in os.environ['PATH']:
            os.environ['PATH'] = os.pathsep.join([installDir,os.environ['PATH']])
            log.debug(os.environ['PATH'])

        cmd = '"{0}" {1} {2} -formatOutput'.format("siwave_ng",path,execPath)
        log.info("Import Siwave to Aedt: %s"%path)
        with os.popen(cmd,"r") as output:
            for line in output:
                log.info(line)
            output.close()
        self.open(edbPath)

    def exportSiwave(self,edbPath=None,path=None):
        edbPath = edbPath or self.edbPath
        return edbToSIwave(edbPath, path,self.installDir)
    
    def deleteFromDisk(self):
        if self.db and not self.db.IsNull():
            self.db.Close()
        if os.path.exists(self.edbPath):
            log.info("delete EDB from disk: %s"%self.edbPath)
            shutil.rmtree(self.edbPath)
            
        if os.path.exists(self.resultsPath):
            log.info("delete project from disk: %s"%self.resultsPath)
            shutil.rmtree(self.resultsPath)
            
        if os.path.exists(self.AedtPath):
            log.info("delete project from disk: %s"%self.AedtPath)
            os.remove(self.AedtPath)
    
    def copyAs(self,target):
        return self.copyEdb(self.edbPath,target)
    
    @classmethod
    def copyEdb(cls,source,target):
        '''
        copy aedb,aedt
        '''
        #source = (source,source+".aedt")(".aedt" in source)
        if os.path.splitext(source)[-1].lower() != ".aedb":
            print("source must .aedb file: %s"%source)
            return
        if not os.path.exists(source):
            print("source file not found: %s"%source)
            return
        
        if not os.path.exists(target):
            print("make dir: %s"%target)
            os.mkdir(target)
        
#         copy(source,target)
        
        edbSource = os.path.join(source,"edb.def") 
        edbTarget = os.path.join(target,"edb.def") 
        shutil.copy(edbSource,edbTarget)
        return target


# C:\Program Files\ANSYS Inc\v252\AnsysEM\syslib\Toolkits\Lib\EdbUtils.py
# from System import Convert
# 
# #---------------------------------------------------------
# 
# def GetEdbHandle(oProject):
#     hdl = Convert.ToUInt64(oProject.GetEDBHandle())
#     db = edb.Database.Attach(hdl)
#     return db
# 
# #---------------------------------------------------------
#     
# def GetCellFromDesignIDispatch(db, oDesign):
#     activeCellName = oDesign.GetName().rsplit(';')[1]    
#     cell = edb.Cell.Cell.FindByName(db, edb.Cell.CellType.CircuitCell, activeCellName)
#     return cell
#     
# #---------------------------------------------------------
# 
# class CellHandles:
#     def __init__(self, oDesktop):
#         self.oProject = oDesktop.GetActiveProject()
#         if not self.oProject:
#             raise Exception("Could not get active Project")
#             
#         self.oDesign = self.oProject.GetActiveDesign()
#         if not self.oDesign:
#             raise Exception("Could not get active Design")
#             
#         self.db = GetEdbHandle(self.oProject)
#         self.cell = GetCellFromDesignIDispatch(self.db, self.oDesign)
#         if self.cell.IsNull():
#             raise Exception("Edb cell is null")
#             
#         self.layout = self.cell.GetLayout()
#         if self.layout.IsNull():
#             raise Exception("Edb layout is null: {0}".format(self.cell.GetName()))
# 
#         self.linst = self.layout.GetLayoutInstance()
#         self.linst.Refresh() # force a refresh to ensure everything is up-to-date
#         



if __name__ == "__main__":
    pass
#     from ansys.aedt.core import Edb
#     edbapp = Edb(edbPath=r"C:\work\Project\AE\Script\PSI\PSI_automation_testCase\edb\SIWAVE_PDN_TEST_0716_group1.aedb", 
#         edbversion="2024.2")
#     siwave_id = edbapp.edb_api.ProductId.SIWave
#     cell = edbapp.active_cell._active_cell
#     cell.SetProductProperty(siwave_id, 515, '1')
#     edbapp.save_edb()
    
    
#     self.cell.SetProductProperty(edb.ProductId.SIWave, kSIwaveProperties.PSI_SIMULATION_PREFERENCE, self.m_simConfig.m_simulationPreference)