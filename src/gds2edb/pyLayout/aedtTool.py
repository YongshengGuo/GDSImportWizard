#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20260702



import os,sys,re
import shutil
import time

from .desktop import initializeDesktop,releaseDesktop

#---library
from .definition.padStack import PadStacks
from .definition.componentLib import ComponentDefs
from .definition.material import Materials
#---natural
from .definition.setup import Setups
from .definition.variable import Variables

from .common.complexDict import ComplexDict
from .common.arrayStruct import ArrayStruct
from .common.licenseChecker import LicenseChecker
# from .lib.common.common import *
from .common.common import log,isIronpython #log is a globle variable
from .common.unit import Unit
from .common.common import DisableAutoSave,ProcessTime
from .pyLayout import Layout
from .model3D.Aedt3DToolBase import Aedt3DToolBase
from .edb.edbApp import EdbApp,EdbSIwaveOptions,edbToSIwave

class AedtTool(Layout):
    '''
    classdocs
    '''
    def __init__(self,toolType=None, version=None, installDir=None,nonGraphical=False,newDesktop=False,usePyAedt=False,oDesktop = None):
        super(AedtTool,self).__init__(version=version, installDir=installDir,nonGraphical=nonGraphical,
                                          newDesktop=newDesktop,usePyAedt=usePyAedt,oDesktop = oDesktop)
        self._info.update("ToolType",toolType)
        
    def __getitem__(self, key):
        
        if not isinstance(key, str):
            log.exception("key for layout must be str: %s"%key)
        
        if key in self._info:
            return self._info[key]
        
        if not self._oDesign:
            log.exception("%s should be intial use initDesign()" % self.ToolType)
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
            return super(self.__class__,self).__getattribute__(key)
        except:
            # log.info("Layout __getattribute__ from info: %s"%str(key))
            return self[key]
        
    def __setattr__(self, key, value):
        if key in ["_oDesktop","_oProject","_oDesign","_oEditor","_info","maps"]:
            object.__setattr__(self,key,value)
        else:
            self[key] = value
        
    def __dir__(self):
#         return object.__dir__(self)  + self.Props
        return dir(self.__class__) + list(self.__dict__.keys()) + self.Props
    
    def __repr__(self):
        return "%s Object"%self.__class__.__name__
    
    def initDesign(self,projectName = None,designName = None, initObjects = True):
        super(AedtTool,self).initDesign(projectName,designName, False)
        if initObjects:
            if self.designtype == 'HFSS 3D Layout Design':
                tool = Layout(oDesktop = self.oDesktop)
                tool.initDesign(projectName,designName)
                return tool
            else:
                tool = Aedt3DToolBase(oDesktop = self.oDesktop)
                tool.initDesign(projectName,designName)
                return tool