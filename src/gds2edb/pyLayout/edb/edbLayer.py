
#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-15

'''
pingroup for edb function
'''
import os,sys,re
from ..common.common import *
from ..common.complexDict import ComplexDict

from .edbDefinition import EdbDefinition,EdbDefinitions

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class EdbLayer(EdbDefinition):
    def __init__(self,layer,edbApp=None):
        super(self.__class__,self).__init__(layer,type="EdbLayer",edbApp=edbApp)

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return

        maps = {
            "Name":{"Key":"self","Get":lambda s:s.GetName()},
            "ID":{"Key":"self","Get":lambda s:s.GetId()},
            "LayerId":{"Key":"self","Get":lambda s:s.obj.GetLayerId()},
            "Color":{"Key":"self","Get":lambda s:s.obj.GetColor()},
            "LayerType":{"Key":"self","Get":lambda s:s.obj.GetLayerType().ToString()},
            "Locked":{"Key":"self","Get":lambda s:s.obj.GetLocked()},
            "LowerElevation":{"Key":"self","Get":lambda s:s.obj.GetLowerElevation()},
            "Material":{"Key":"self","Get":lambda s:s.obj.GetMaterial()},
            "Thickness":{"Key":"self","Get":lambda s:s.obj.GetThicknessValue()},
            "UpperElevation":{"Key":"self","Get":lambda s:s.obj.GetUpperElevation()},
            "ObjType":{"Key":"self","Get":lambda s:s.obj.GetObjType().ToString()},
        }

        self.maps.update(maps)
        self._info.update("self", self)
        self._info.setMaps(self.maps)
        self.parsed = True

    def GetName(self):
        return self.obj.GetName()

class EdbLayers(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(self.__class__,self).__init__(edbApp,type="EdbLayer",definitionClass=EdbLayer)
        self.conductorLayerNames = None
        self.dielectricLayerNames = None
        self.allLayerNames = None
        self.stackupLayerNames = None
        self.nonStackupLayerNames = None
        

    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            layers = self.edbApp.layout.GetLayerCollection().Layers(self.edbApp.Edb.Cell.LayerTypeSet.AllLayerSet)
            self._definitionDict  = ComplexDict(dict([(l.GetName(),self.definitionClass(l,self.edbApp)) for l in layers]))
            
            self.conductorLayerNames = [l.GetName() for l in self.edbApp.layout.GetLayerCollection().Layers(self.edbApp.Edb.Cell.LayerTypeSet.SignalLayerSet)]
            self.dielectricLayerNames = [l.GetName() for l in self.edbApp.layout.GetLayerCollection().Layers(self.edbApp.Edb.Cell.LayerTypeSet.DielectricLayerSet)]
            self.allLayerNames = [l.GetName() for l in self.edbApp.layout.GetLayerCollection().Layers(self.edbApp.Edb.Cell.LayerTypeSet.AllLayerSet)]
            self.stackupLayerNames = [l.GetName() for l in self.edbApp.layout.GetLayerCollection().Layers(self.edbApp.Edb.Cell.LayerTypeSet.StackupLayerSet)]
            self.nonStackupLayerNames = [l.GetName() for l in self.edbApp.layout.GetLayerCollection().Layers(self.edbApp.Edb.Cell.LayerTypeSet.NonStackupLayerSet)]
            
            maps = {}
            #short name for signal
            count = len(self.conductorLayerNames)
            for i,v in enumerate(self.conductorLayerNames):
                maps.update({"C%s"%(i+1):v})
                maps.update({"CB%s"%(count-i):v})
                maps.update({"L%s"%(i+1):v})
                maps.update({"LB%s"%(count-i):v})

            #short name for dielectric
            count = len(self.dielectricLayerNames)
            for i,v in enumerate(self.dielectricLayerNames):
                maps.update({"D%s"%(i+1):v})
                maps.update({"DB%s"%(count-i):v})
            
            #short name for all stackup layer
            count = len(self.stackupLayerNames)
            for i,v in enumerate(self.stackupLayerNames):
                maps.update({"S%s"%(i+1):v})
                maps.update({"SB%s"%(count-i):v})
                maps.update({"Stk%s"%(i+1):v})
                maps.update({"StkB%s"%(count-i):v})

            self._definitionDict.setMaps(maps)
        return self._definitionDict