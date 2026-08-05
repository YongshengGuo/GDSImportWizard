#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230828


'''
used to get padstak information

'''



import re

from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,tuple2list
from .definition import Definitions,Definition
from ..primitive.geometry import Point,Polygen

class PadStack(Definition):
    '''

    Args:
    '''
    #variable not in info
    mapsPDS = {
        "PadSize":{"Key":"pad/Szs","Get":lambda x:x[0] if len(x) else None},
        "AntipadPadSize":{"Key":"ant/Szs","Get":lambda x:x[0] if len(x) else None},
        "ThermalPadSize":{"Key":"thm/Szs","Get":lambda x:x[0] if len(x) else None}
        }
    
    
    def __init__(self, name = None,layout = None):
        super(self.__class__,self).__init__(name,type="Padstack",layout=layout)
        self.maps = {
            "DrillSize":{"Key":"psd/hle/Szs","Get":lambda x:x[0] if len(x) else None},
            "PlatingPercent":"psd/plt",
            "Material":"mat"
            }

    def parse(self,force = False):
        super(self.__class__,self).parse(force)
        
        pds = self._info.Array["psd/pds"]
        for pd in pds.Datas:
            if not isinstance(pd, list):
                continue
            lgm = ArrayStruct(pd,maps=self.mapsPDS)
            self._info.update(lgm.lay, lgm)

    def appendLayer(self,layerName,update=True):
        self.Info.append("psd/pds",
            [
                "NAME:lgm",
                "lay:=", layerName,
                "id:=", 1, #self.layout.layers[layerName].ID,
                "pad:=", ["shp:=", "No","Szs:=", [],"ply:=", [],"X:=", "0mil","Y:=", "0mil","R:=", "0deg"],
                "ant:=", ["shp:=", "No","Szs:=", [],"ply:=", [],"X:=", "0mm","Y:=", "0mm","R:=", "0deg"],
                "thm:=", ["shp:=", "No","Szs:=", [],"ply:=", [],"X:=", "0mm","Y:=", "0mm","R:=", "0deg"],
                "X:=", "0",
                "Y:=", "0",
                "dir:=", "No"
            ])
        if update:
            self.update()
    
    def appendSignalLayers(self):
        if len(self["psd/pds"])>1:
            self["psd/pds"] = ["NAME:pds"]
        
        for layerName in self.layout.Layers.ConductorLayerNames:
            self.appendLayer(layerName,update=False) 
        self.update()
        
    # def setPlatingPercent(self,platingPercent):
    #     self["psd/plt"] = str(platingPercent)
    #     self.update()

    def place(self,position,upperLayer,lowerLayer,isPin = False):
        '''
        Center: [x,y], str value
        #Return Value: Returns the name of the created via
        '''
        
        self.layout.addVia(self,position,upperLayer,lowerLayer,isPin)
        

class PadStacks(Definitions):
    
    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Padstack",definitionCalss=PadStack)

     
    def add(self,name,padSize="16mil",dirll="8mil"):
        oDefinitionManager = self.layout.oProject.GetDefinitionManager()
        oPadstackManager = oDefinitionManager.GetManager("Padstack")
        oPadstackManager.Add(["NAME:%s"%name])
        self.DefinitionDict[name].appendSignalLayers() #添加默认padstack叠层信息
        self.push(name)
        
        
        