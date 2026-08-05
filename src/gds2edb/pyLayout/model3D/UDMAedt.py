#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-06-26
import os,sys,re
import importlib
from ..common.common import *

# UDMInfo = None
# IUDMExtension = None

def initUDM(installDir=None):

    Module = sys.modules['__main__']
    if hasattr(Module, "oDesktop"):
        oDesktop = getattr(Module, "oDesktop")
        return oDesktop
    else:
        oDesktop = None
    
    aedtInstallDir = None
    #set installDir
    if oDesktop:
        aedtInstallDir = oDesktop.GetExeDir()
    elif installDir != None:
        aedtInstallDir = installDir.strip("/").strip("\\")
#         print("AEDT InstallDir: %s"%aedtInstallDir)
    else:
        #environ ANSYSEM_ROOTxxx, set installDir from version
        
        if installDir:
            aedtInstallDir = installDir

        
        if aedtInstallDir:
            os.environ["ANSYSEM_ROOT"] = aedtInstallDir
        elif "ANSYSEM_ROOT" in os.environ and os.environ["ANSYSEM_ROOT"].strip():
            aedtInstallDir = os.environ["ANSYSEM_ROOT"]
        else:
            ANSYSEM_ROOTs = list(
                filter(lambda x: "ANSYSEM_ROOT" in x, os.environ))
            if ANSYSEM_ROOTs:
                log.debug("Try to initialize Desktop in latest version")
                ANSYSEM_ROOTs.sort(key=lambda x: x[-3:])
                aedtInstallDir = os.environ[ANSYSEM_ROOTs[-1]]
         
    if aedtInstallDir: 
        print("AEDT InstallDir: %s"%aedtInstallDir)
    else:
        log.exception("please set environ ANSYSEM_ROOT=Ansys EM install path...")

    if aedtInstallDir: 
        
        print("AEDT InstallDir: %s"%aedtInstallDir)
        sys.path.insert(0,aedtInstallDir)
        sys.path.insert(0,os.path.join(aedtInstallDir,r"syslib\UserDefinedModels\Lib"))
        sys.path.insert(0,os.path.join(aedtInstallDir,r"PythonFiles\Geometry3DPlugin"))
        sys.path.insert(0,os.path.join(aedtInstallDir,r"syslib\ACT\ATKDesign\Lib\UDMScript"))
        sys.path.insert(0,os.path.join(aedtInstallDir,r"common\Framework\bin\Win64"))


    else:
        log.exception("please set environ ANSYSEM_ROOT=Ansys EM install path...")

    #for python
    # if not isPython or is_linux:
    if is_linux:
        try:
            from ansys.aedt.core.generic.clr_module import _clr # @UnresolvedImport 
        except:
            log.info("Make sure pyaedt have installed on linux: pip install pyaedt")
            from ansys.aedt.core.internal.clr_module import _clr # @UnresolvedImport
    else:
        #for windows
        import clr as _clr # @UnresolvedImport
        
    if isPython:
    
#         _clr.AddReference("System.Core")
        _clr.AddReference('Ansys.Ansoft.Geometry3DPluginDotNet')

    else:
        _clr.AddReference('Ansys.Ansoft.Geometry3DPluginDotNet.dll')


class UDM(object):
    def __init__(self,path):
        self.path = path
    
    def create(self):
        initUDM()
        dirName = os.path.dirname(self.path)
        if dirName not in sys.path:
            sys.path.insert(0,dirName)
#         global UDMInfo,IUDMExtension
#         from Ansys.Ansoft.Geometry3DPluginDotNet.UDM.API.Data import UDMInfo,UDMOption
#         from Ansys.Ansoft.Geometry3DPluginDotNet.UDM.API.Interfaces import IUDMBaseExtension as IUDMExtension
# 
# #         Geometry3DPluginDotNet = __import__("Ansys.Ansoft.Geometry3DPluginDotNet.UDM.API.Data")
# #         UDMInfo = Geometry3DPluginDotNet.UDMInfo
# #         IUDMExtension = Geometry3DPluginDotNet.UDM.API.Interfaces.IUDMBaseExtension
        moduleName = os.path.basename(self.path)[:-3]
        module = importlib.import_module(moduleName)
        udm = module.UDMExtension()
        udm._CreateParameters()
        udmParams = []
        for udmParam in udm._udmParamList:
            '''
            PropType2 can be any of the following:
            
            0 - Property takes a string value.
            1 - Property is a menu option.
            2 - Property takes a number (integer or double).
            3 - Property takes a value (numbers, variables, or expressions).
            4 - Property is a file name.
            5 - Property corresponds to a check box.
            6 - Property specifies a 3D position.
            PropFlag2 can be any of the following:
            
            0 - No flags
            1 - Read-only
            2 - Must be integer
            4 - Must be real
            8 - Hidden
            '''
            
            
            Name = udmParam.ParamName
            Value = udmParam.ParamValue.Data
            unitType = int(udmParam.UnitType)
            PropType2 = int(udmParam.PropType)
            PropFlag2 = int(udmParam.PropFlag)
            if unitType == 2: 
                #UnitType: AngleUnit
                Value = str(Value)
            elif unitType == 1: 
                #UnitType: LengthUnit
                Value = str(Value) + udm._lengthUnits
            elif unitType == 0: 
                #UnitType: NoUnit
                Value = str(Value)
            else:
                Value = str(Value)
            
            if PropType2 == 1:
                #1 - Property is a menu option.
                Value = '"%s"'%Value
            else:
                pass
            
            udmParams.append({"Name":Name,
                            "Value":Value,
                            "PropType2":PropType2,
                            "PropFlag2":PropFlag2
                            })
        
        
        vArgParamVector = ["NAME:GeometryParams"]
        for pair in udmParams:
            vArgParamVector.append(["NAME:UDMParam", 
                                    "Name:=", pair["Name"], 
                                    "Value:=", pair["Value"],
                                    "PropType2:=", pair["PropType2"],
                                    "PropFlag2:=", pair["PropFlag2"]
                                    ])
        pass

