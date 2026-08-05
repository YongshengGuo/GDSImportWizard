
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
from .edbVia import EdbVia,getViaName

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class EdbComponent(EdbDefinition):
    def __init__(self,component,edbApp=None):
        super(self.__class__,self).__init__(component,type="EdbComponent",edbApp=edbApp)

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return

        maps = {
            "Name":{"Key":"self","Get":lambda s:s.GetName()},
            "ID":{"Key":"self","Get":lambda s:s.obj.GetId()},
            "Net":{"Key":"self","Get":lambda s:s.obj.GetNet()},
            "NetName":{"Key":"self","Get":lambda s:s.obj.GetNet().GetName()},
            "Group":{"Key":"self","Get":lambda s:s.obj.GetGroup()},
            "GroupName":{"Key":"self","Get":lambda s:s.obj.GetGroup().GetName()},
            "Component":{"Key":"self","Get":lambda s:s.obj.GetComponent()},
            "ComponentName":{"Key":"self","Get":lambda s:s.obj.GetComponent().GetName()},
            "PlacementLayer":{"Key":"self","Get":lambda s:s.obj.GetPlacementLayer()},
            "PlacementLayerName":{"Key":"self","Get":lambda s:s.obj.GetPlacementLayer().GetName()},
            "Layer":{"Key":"self","Get":lambda s:s.obj.GetPlacementLayer().GetName()},
            "Pins":{"Key":"self","Get":lambda s:[EdbVia(p,self.edbApp) for p in s.obj.LayoutObjs if p.GetObjType() == s.edbApp.Edb.Cell.LayoutObjType.PadstackInstance] },
            "PinNames":{"Key":"self","Get":lambda s:[getViaName(p) for p in s.obj.LayoutObjs if p.GetObjType() == s.edbApp.Edb.Cell.LayoutObjType.PadstackInstance] },
            "PinCount":{"Key":"self","Get":lambda s: s.obj.GetNumberOfPins() },
            "LayerName":{"Key":"self","Get":lambda s:[getViaName(p) for p in s.obj.LayoutObjs if p.GetObjType() == s.edbApp.Edb.Cell.LayoutObjType.PadstackInstance]},
            "Part":{"Key":"self","Get":lambda s:s.obj.GetComponentDef()},
            "PartName":{"Key":"self","Get":lambda s:s.obj.GetComponentDef().GetName()},
            "PartType":{"Key":"self","Get":lambda s:s.obj.GetComponentType().ToString()},
            "Location":{"Key":"self","Get":lambda s:s.getLocation()},
            "ObjType":{"Key":"self","Get":lambda s:s.obj.GetObjType().ToString()},
        }

        self.maps.update(maps)
        self._info.update("self", self)
        self._info.setMaps(self.maps)
        self.parsed = True

#         maps.update({"Pins":{
#             "Key":"self",
# #             "Get":lambda s:[getViaName(p) for p in s.obj.LayoutObjs] #PadstackInstance 1 
#             "Get":lambda s:[s.edbApp.Vias[getViaName(p)] for p in s.obj.LayoutObjs if p.GetObjType() == s.edbApp.Edb.Cell.LayoutObjType.PadstackInstance] #PadstackInstance 1 
#             }})

#         maps.update({"PinNames":{
#             "Key":"self",
#             "Get":lambda s:[getViaName(p) for p in s.obj.LayoutObjs if p.GetObjType() == s.edbApp.Edb.Cell.LayoutObjType.PadstackInstance]
#             }})

        # Other 0 Other component type.  
        # Resistor 1 Resistor type.  
        # Inductor 2 Inductor type.  
        # Capacitor 3 Capacitor type.  
        # IC 4 IC type.  
        # IO 5 IO type.  

    def GetName(self):
        return self.obj.GetName()
  
  
    def getLocation(self):
        rst = self.obj.GetLocation()
        if rst[0]:
            return Point(rst[1:])
        else:
            return None

class EdbComponents(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(EdbComponents,self).__init__(edbApp,type="Groups",definitionClass=EdbComponent)
        

    
    # @property
    # def DefinitionDict(self):
    #     if self._definitionDict == None:
    #         component = [g for g in list(self.edbApp.layout.Groups) if g.ToString() == "Ansys.Ansoft.Edb.Cell.Hierarchy.Component"]
    #         self._definitionDict  = ComplexDict(dict([(g.GetName(),self.definitionClass(g,self.edbApp)) for g in component]))
    #     return self._definitionDict