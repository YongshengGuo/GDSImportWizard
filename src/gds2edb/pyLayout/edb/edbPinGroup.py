
#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-15

'''
pingroup for edb function
'''
import os,sys,re
from itertools import groupby
from ..common.common import *
from ..common.complexDict import ComplexDict

from .edbDefinition import EdbDefinition,EdbDefinitions
from .edbVia import EdbVia
from .edbComponent import EdbComponent

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class EdbPinGroup(EdbDefinition):
    def __init__(self,pinGroup,edbApp=None):
        super(__class__,self).__init__(pinGroup,"EdbPinGroup",edbApp)


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
            "Pins":{"Key":"self","Get":lambda s:[EdbVia(p,self.edbApp) for p in  s.obj.GetPins()]},
            "PinNames":{"Key":"self","Get":lambda s:["%s-%s"%(p.GetComponent().GetName(),p.GetName()) for p in  s.obj.GetPins()]},
            "Component":{"Key":"self","Get":lambda s:s.obj.GetComponent()},
            "ComponentName":{"Key":"self","Get":lambda s:s.obj.GetComponent().GetName()},
            "ObjType":{"Key":"self","Get":lambda s:s.obj.GetObjType().ToString()},
            "PrimitiveType":{"Key":"self","Get":lambda s:s.obj.GetPrimitiveType()},
            "Layer":{"Key":"self","Get":lambda s:s.obj.GetLayer()},
            "LayerName":{"Key":"self","Get":lambda s:s.obj.GetLayer().GetName()},
        }

        self.maps.update(maps)
        self._info.update("self", self)
        self._info.setMaps(self.maps)
        self.parsed = True
        
        
    def GetName(self):
        return self.obj.GetName()

class EdbPinGroups(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(self.__class__,self).__init__(edbApp,type="PinGroups",definitionClass=EdbPinGroup)

    def createByPins(self,pinList=None,compName=None,groupName = None):
        
        if not pinList:
            log.info("pinList is empty,skip")
            return ""

        if not compName:
            log.info("Component Name must give, skip")
            return ""

        if compName not in self.edbApp.Components:
            log.info("Component not found in layout, skip")
            return ""
        
        comp = self.edbApp.Components[compName]
        compPinNames = [p for p in comp.Pins if p.GetName()]


    def createByGrid(self,pinList,compName,nets=None,groupName = None,rows = 1,cols = 1):
        
        if not compName:
            log.exception("CompName must definition before create pingroup.")
        
        if isinstance(nets, str):
            nets = self.edbApp.Nets.getRegularNetNames(nets)

        selected_pins = list(pinList) if pinList else []
        if nets:
            selected_pins = []
            pins = self.edbApp.Components[compName].Pins
            for net in nets:
                net_pins = [p for p in pins if p.NetName.lower() == net.lower()]
                if net_pins:
                    selected_pins.extend(net_pins)

        if not selected_pins:
            log.info("No pins found for grid pin group on %s" % compName)
            return

        if not hasattr(self, "_gridPins"):
            log.exception("_gridPins method not implemented for EdbPinGroups")

        grid_assignment = self._gridPins(selected_pins,int(rows),int(cols))

        for k,v in grid_assignment.items():
            sorted_data = sorted(v, key=lambda x: x.Net)
            grouped_data = groupby(sorted_data, key=lambda x: x.Net) 
            for netName, netPins in grouped_data:
                if not groupName:
                    groupName = "PinGroup_%s_%s"%(netName,compName)
                pinNames = [p.Name for p in netPins]
                log.info("Create PinGroup, component:%s Net:%s Grid:%s pinCount:%s"%(compName,netName,k,len(pinNames)))
                self.createByPins(pinNames, compName=compName, groupName = groupName+"_"+k)