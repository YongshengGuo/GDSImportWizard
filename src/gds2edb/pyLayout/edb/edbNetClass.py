
#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-15

'''
pingroup for edb function
'''
import os,sys,re
from ..common.common import *
from ..common.complexDict import ComplexDict
from ..primitive.geometry import Point,Polygen
from .edbDefinition import EdbDefinition,EdbDefinitions
from .edbPrimitive import EdbPrimitive
from .edbVia import EdbVia

try:
    _clr = initClr()
    from System import String
except:
    log.warning("CLR initialization failed in child process (likely duplicate init). Ignoring if not needed.")  
# from System import String

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class EdbNetClass(EdbDefinition):
    def __init__(self,obj,edbApp=None):
        super(EdbNetClass,self).__init__(obj,type="EdbNet",edbApp=edbApp)

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return

        maps = {
            "Name":{"Key":"self","Get":lambda s:s.GetName(),"Set":lambda s,x:s.SetName(x)},
            "ID":{"Key":"self","Get":lambda s:s.obj.GetId()},
            "ObjType":{"Key":"self","Get":lambda s:s.obj.GetObjType().ToString()},
        }

        self.maps.update(maps)
        self._info.update("self", self)
        self._info.setMaps(self.maps)
        self.parsed = True

    def GetName(self):
        return self.obj.GetName()


class EdbNetClasses(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(EdbNetClasses,self).__init__(edbApp,type="NetClasses",definitionClass=EdbNetClass)

    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            if hasattr(self.edbApp.layout,self.type):
                objs = getattr(self.edbApp.layout,self.type)
                self._definitionDict  = ComplexDict(dict([(p.GetName(),self.definitionClass(p,self.edbApp)) for p in objs]))
            else:
                self._definitionDict = {}
        return self._definitionDict
    
    def disjointNets(self):

        for net in list(self.All):
            if net.Name in  ["----","<NO-NET>"]:
                continue
            net.disjoint()
    
