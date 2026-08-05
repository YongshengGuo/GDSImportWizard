#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230410

"""
    Examples:
        >>>allSignalLayers = LayerDict['C*']
        返回所有信号层对象的列表
        >>>signalLayer1 = LayerDict['C:1']
        返回第一层信号层对象
       >>> signalLayer2 = LayerDict['C:2']
        返回第二层信号层对象 
        >>>allDielecLayers = LayerDict['D:*]
        返回所有介质层对象
        >>>sigLayer1.Layername
        返回层名
        >>>sigLayer1.Thickness()
        返回层厚度   

  layer["IsVisible"]
  layer["Thickness"] = "10mil"
  _definitionDict["Top"]["Thickness"] = 10mil
  _definitionDict["Top.Thickness"] = 10mil
  
    _definitionDict[0]  或 _definitionDict[“:0”] 返回叠层的第一层 (金属+介质)
    
    _definitionDict["C0"] 返回金属的第一层
    _definitionDict["D0"] 返回介质的第一层
    
    _definitionDict["C"] 或者 _definitionDict["C:*"] 返回所有金属
    _definitionDict["D"] 或者 _definitionDict["D:*"] 返回所有介质
    

  
get component information from oEditor.GetComponentInfo API

"layerInfo":['Type: signal', 'TopBottomAssociation: Neither', 'Color: 16711680d', 'IsVisible: true', '  IsVisibleShape: true',
 '  IsVisiblePath: true', '  IsVisiblePad: true', '  IsVisibleHole: true', '  IsVisibleComponent: true', 'IsLocked: false', 
 'LayerId: 1', 'Index: 1', 'LayerThickness: 3.556e-05', 'IsIgnored: false', 'NumberOfSublayers: 1', 'Material0: copper', 'FillMaterial0: air', 
 'Thickness0: 3.556e-05meter', 'LowerElevation0: 0.0016256']
"""


import re,os
import math
from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,loadCSV,writeCSV,writeData
from .definition import Definitions,Definition
from ..common.common import DisableAutoSave,ProcessTime


class Layer(Definition):
    '''
    
    >>> oEditor.GetLayerInfo:
    ['Type: signal', 'TopBottomAssociation: Neither', 'Color: 6599935d', 'IsVisible: true', '  IsVisibleShape: true', '  IsVisiblePath: true', 
    '  IsVisiblePad: true', '  IsVisibleHole: true', '  IsVisibleComponent: true', 'IsLocked: false', 'LayerId: 1', 'Index: 1', 
    'LayerThickness: 4.826e-05', 'EtchFactor: -2.5', 'IsIgnored: false', 'NumberOfSublayers: 1', 'Material0: copper', 'FillMaterial0: TOP_FILL', 
    'Thickness0: 0.04826mm', 'LowerElevation0: 1.98628mm', 'Roughness0 Type: Groiss', 'Roughness0: 1um', 'BottomRoughness0 Type: Groiss', 
    'BottomRoughness0: 1um', 'SideRoughness0 Type: Huray', 'SideRoughness0: 0.5um, 2.9']
    
    ['Type: dielectric', 'TopBottomAssociation: Neither', 'Color: 12632256d', 'IsVisible: false', '  IsVisibleShape: false', '  IsVisiblePath: false', '  
    IsVisiblePad: false', '  IsVisibleHole: false', '  IsVisibleComponent: false', 'IsLocked: false', 'LayerId: 2', 'Index: 2', 'LayerThickness: 6.731e-05', 
    'IsIgnored: false', 'NumberOfSublayers: 1', 'Material0: FR-4_3', 'FillMaterial0: ', 'Thickness0: 0.06731mm', 'LowerElevation0: 1.91897mm']
    
    ['Type: measures', 'TopBottomAssociation: Neither', 'Color: 4144959d', 'IsVisible: true', 'IsLocked: false', 'LayerId: 15']
    
    '''
    
#     signalLayer = ['Type: signal', 'TopBottomAssociation: Neither', 'Color: 6599935d', 'IsVisible: true', '  IsVisibleShape: true', '  IsVisiblePath: true', 
#     '  IsVisiblePad: true', '  IsVisibleHole: true', '  IsVisibleComponent: true', 'IsLocked: false', 'LayerId: 1', 'Index: 1', 
#     'LayerThickness: 4.826e-05', 'EtchFactor: -2.5', 'IsIgnored: false', 'NumberOfSublayers: 1', 'Material0: copper', 'FillMaterial0: TOP_FILL', 
#     'Thickness0: 0.04826mm', 'LowerElevation0: 1.98628mm', 'Roughness0 Type: Groiss', 'Roughness0: 0um', 'BottomRoughness0 Type: Groiss', 
#     'BottomRoughness0: 0um', 'SideRoughness0 Type: Huray', 'SideRoughness0: 0.5um, 2.9']
    
 
    
    _enableUpdate = True

    def __init__(self, name = None,array = None,layout = None):
        super(self.__class__,self).__init__(name,type="Layer",layout=layout)
        self.maps = {
                "LayerName":"Name",
                "T":"Thickness0",
                "Thickness":"Thickness0",
                "H":"LowerElevation0",
                "Height":"LowerElevation0",
                "Material":"Material0",
                "ID":"LayerId",
                "FillMaterial":"FillMaterial0",
                "LowerElevation":"LowerElevation0",
                "Lower":"LowerElevation0",
                "Upper": {"Key":("LowerElevation0","Thickness0"),"Get": lambda L,T:(Unit(L)+T)[Unit(L).U]},
                "UpperElevation": {"Key":("LowerElevation0","Thickness0"),"Get": lambda L,T:(Unit(L)+T)[Unit(L).U]},
                "TopRoughnessType":"Roughness0 Type",
                "TopRoughness":"Roughness0",
                "BottomRoughnessType":"BottomRoughness0 Type",
                "BottomRoughness":"BottomRoughness0",
                "SideRoughnessType":"SideRoughness0 Type",
                "SideRoughness":"SideRoughness0",
                "UseRoughness":"UseR",
                "Roughness":{"Key":("Roughness0","BottomRoughness0","SideRoughness0"),"Get": lambda T,B,S: T,"Set": lambda x: [x]*3},
                "RoughnessType":{"Key":("Roughness0 Type","BottomRoughness0 Type","SideRoughness0 Type"),"Get": lambda T,B,S: T,"Set": lambda x: [x]*3},
                "EtchAngle":{"Key":"EtchFactor","Get": lambda x: math.degrees(math.atan(float(x))),"Set": lambda x: math.tan(math.radians(float(x)))},
                }
        self._info.update("autoUpdate",True)
    

    def __setitem__(self, key,value):
        self.Info[key] = value
            
        if self.autoUpdate:
            log.debug("layer '%s' auto update :%s->%s."%(self.name,key,value))
            self.update()


    def __repr__(self):
        return "Layer Object: Layer(name={}, layer_type={}, index={}, thickness={})".format(self.name, self["Type"], self["LayerId"], self["LayerThickness"])
    

    @property
    def ArrayDatas(self):
        if self.Info["Type"].lower() in ["signal","conductor"]:
            ary = ArrayStruct(hfss3DLParameters.signalLayer).copy()
            ary["Name"] = self.name
            ary["ID"] = int(self.Info["LayerId"])
            ary["Color"] = int(self.Info["Color"].replace("d",""))
            
            #20231020
            #ary["VisFlag"] = 127 if self.Info["IsVisible"] else 0
            #[self.IsVisibleShape,self.IsVisiblePath,self.IsVisiblePad,self.IsVisibleHole,self.IsVisibleComponent]
            ary["VisFlag"] = self.Info["IsVisibleShape"]*1 +  self.Info["IsVisiblePath"]*2 +  self.Info["IsVisiblePad"]*4 + \
                self.Info["IsVisibleHole"]*8 +  self.Info["IsVisibleComponent"]*16
            
            
            ary["Sublayer/Thickness"] = self.Info["Thickness"]
            ary["Sublayer/LowerElevation"] = self.Info["LowerElevation"]
            ary["Sublayer/Material"] = self.Info["Material"]
            ary["Sublayer/FillMaterial"] = self.Info["FillMaterial"]
            
            if self.Info["UseRoughness"]:
                ary["UseR"] = bool(self.Info["UseRoughness"])
                TopRoughness = re.split(r"[,;]", self.Info["TopRoughness"] or "0.5um")
                ary["RMdl"] = "Groiss" if len(TopRoughness) == 1 else "Huray"
                ary["NR"] = TopRoughness[0]
                ary["HRatio"] = TopRoughness[-1]
                
                BottomRoughness = re.split(r"[,;]", self.Info["BottomRoughness"]  or "0.5um")
                ary["BRMdl"] = "Groiss" if len(BottomRoughness) == 1 else "Huray"
                ary["BNR"] = BottomRoughness[0]
                ary["BHRatio"] = BottomRoughness[-1]
                
                SideRoughness = re.split(r"[,;]", self.Info["SideRoughness"]  or "0.5um")
                ary["SRMdl"] = "Groiss" if len(SideRoughness) == 1 else "Huray"
                ary["SNR"] = SideRoughness[0]
                ary["SHRatio"] = SideRoughness[-1]
                
                ary["Sublayer/Roughness"] = ary["NR"]
                ary["Sublayer/BotRoughness"] = ary["BNR"]
                ary["Sublayer/SideRoughness"] = ary["SNR"]
                
            if self.Info["UseEtch"]:
                ary["UseEtch"] =  bool(self.Info["UseEtch"])
                ary["Etch"] = str(self.Info["EtchFactor"])

        elif self.Info["Type"].lower()  == "dielectric":
            ary = ArrayStruct(hfss3DLParameters.dielectricLayer).copy()
            ary["Name"] = self.name
            ary["ID"] = int(self.Info["LayerId"])
            ary["Color"] = int(self.Info["Color"].replace("d",""))
            ary["VisFlag"] = 127 if self.Info["IsVisible"] else 0
            ary["Sublayer/Thickness"] = self.Info["Thickness"]
            ary["Sublayer/LowerElevation"] = self.Info["LowerElevation"]
            ary["Sublayer/Material"] = self.Info["Material"]
            

        else:
            ary = ArrayStruct(hfss3DLParameters.otherLayer).copy()
            ary["Name"] = self.name
            ary["ID"] = int(self.Info["LayerId"])
            ary["Color"] = int(self.Info["Color"].replace("d",""))
            ary["Type"] = self.Info["Type"]
            ary["VisFlag"] = 127 if self.Info["IsVisible"] else 0
        
        return ary.Datas
        
#     def XML(self):
#         '''
#         layer:
#         <Layer Color="#ffb464" EtchFactor="0" FillMaterial="TOP_FILL" Material="copper" Name="TOP" Thickness="0.04826" Type="conductor"/>
#         <Layer Color="#c0c0c0" Material="FR-4_3" Name="UNNAMED_002" Thickness="0.06730999999999999" Type="dielectric"/>
#         '''
#         
#         if self.Info["Type"] == "signal":
#             xml = ""
#             
#         elif self.Info["Type"]  == "dielectric":
#             xml = ""
#         
#         else:
#             return None
#         
#         raise Exception("bad layer type: %s"%self.Info("Type")) 
    
    def parse(self,force = False):
        
        if self.parsed and not force:
            return
        
        maps = self.maps
        info = ComplexDict(dict(filter(lambda x: len(x) == 2, [p.lstrip().split(": ", 1) for p in self.layout.oEditor.GetLayerInfo(self.name)])))
        
        
#         info.setMaps(self.maps)
        if info["Type"] == "signal":
            if "Roughness0" in info:
                info.update("UseR",True)
            else:
                info.update("UseR",False)
                info.update("Roughness0","0.5um")
                info.update("BottomRoughness0","0.5um")
                info.update("SideRoughness0","0.5um")
                info.update("Roughness0 Type","Groiss")
                info.update("BottomRoughness0 Type","Groiss")
                info.update("SideRoughness0 Type","Groiss")

            if "EtchFactor" in info:
                info.update("UseEtch",True)
            else:
                info.update("UseEtch",False)
                info.update("EtchFactor",0)
                
                
        for key in info.Keys:
            if info[key] == "true":
                info[key] = True
            if info[key] == "false":
                info[key] = False

        maps.update({"indexIntra":{
            "Key":"self",
            "Get":lambda s: s._getIndexIntra()
            }})
        
        maps.update({"HalfStackup":{
            "Key":"self",
            "Get":lambda s: s._halfStack()
            }})
                
    
        maps.update({"Objects":{
            "Key":"self",
            "Get":lambda s:s._getObjects()
            }})
            
        
        #FillMaterial 'Type: dielectric'  'Type: signal'
        maps.update({"LayerDK":{
            "Key":"self",
            "Get":lambda s:s.layout.Materials[s.Material].DK if self.Type == "dielectric" else (s.layout.Materials[s.FillMaterial].DK if s.FillMaterial else "")
            }})
        
        
        maps.update({"LayerDF":{
            "Key":"self",
            "Get":lambda s:s.layout.Materials[s.Material].DF if self.Type == "dielectric" else (s.layout.Materials[s.FillMaterial].DF if s.FillMaterial else "")
            }})
        
        maps.update({"LayerCond":{
            "Key":"self",
            "Get":lambda s:s.layout.Materials[s.Material].Cond
            }})
        
    
        if self._info:
            self._info.updates(info)
        else:
            self._info = info
        
        _array = ArrayStruct([])
        self._info.update("Name",self.name)
        self._info.update("Array", _array)
        self._info.update("self", self) 
        self._info.setMaps(maps)

        self.parsed = True
        
        
    def _getIndexIntra(self):
        if self["Type"] == "signal":
            layerNames = self.layout.Layers.ConductorLayerNames
            idx = layerNames.index(self.Name)

        elif self["Type"]  == "dielectric":
            layerNames = self.layout.Layers.DielectricLayerNames
            idx = layerNames.index(self.Name)
        else:
            idx = -1
        
        return idx
    
    
    def _halfStack(self):
        if self["Type"] == "signal":
            layerNames = self.layout.Layers.ConductorLayerNames 
        elif self["Type"]  == "dielectric":
            layerNames = self.layout.Layers.DielectricLayerNames
 
        else:
            return -1
        
        idx = layerNames.index(self.Name)
        return 1 if idx<len(layerNames)/2.0 else 0
    
    
    def _getObjects(self):
        objectCDicts = ComplexDict()
        maps = {}
        objectCDicts.update("Layer", self.name)
        objectCDicts.update("self", self)
        for type in self.layout.primitiveTypes:
            objectCDicts.update(type+"s",type)
            fxDict = {
                "Key":("self",type+"s"),
                "Get":lambda s,k:s.getObjectsbyLayer(k) 
                }
            maps.update({type+"s":fxDict})
        
        objectCDicts.update("All","*")
        maps.update({"All":{
            "Key":("self","All"),
            "Get":lambda s,k:s.getObjectsbyLayer(k)
            }})
        objectCDicts.setMaps(maps)
        return objectCDicts
    
    def getObjectsbyLayer(self,typ = "*"):
        return self.layout.getObjectsbyLayer(self.Name,typ)
    
    
    def enableUpdate(self,enable = True):
        self.__class__._enableUpdate = enable
    
    def update(self):
        
        if self.__class__._enableUpdate:
            self.layout.oEditor.ChangeLayer(self.ArrayDatas)
            self.parse(force=True)
        else:
            log.debug("layer '%s' update is disabled."%self.name)
        
    def setData(self,layerDict):
        '''
        - {Name: SURFACE,Type: conductor, Material: copper, FillMaterial: M4 ,Thickness: 3.556e-05, Roughness: 0.5um,2.9 ,DK: 4,DF: 0.02, Cond: 5.8e7, EtchFactor: 2.5}
        - {Name: SURFACE,Type: dielectric, Material: M4 ,Thickness: 3.556e-05,DK: 4,DF: 0.02}
        
        "T":"Thickness0",
        "Thickness":"Thickness0",
        "Material":"Material0",
        "ID":"LayerId",
        "FillMaterial":"FillMaterial0",
        "LowerElevation":"LowerElevation0",
        "Lower":"LowerElevation0",
        "TopRoughnessType":"Roughness0 Type",
        "TopRoughness":"Roughness0",
        "BottomRoughnessType":"BottomRoughness0 Type",
        "BottomRoughness":"BottomRoughness0",
        "SideRoughnessType":"SideRoughness0 Type",
        "SideRoughness":"SideRoughness0",
        
        '''
        
        info = ComplexDict(layerDict)
        
        if self["Type"].lower() in ["signal","conductor"]:
        
            if "Roughness" in info and info["Roughness"]:
                Roughness = info["Roughness"]
                RoughnessType = "Huray" if len(Roughness.split(",")) == 2 else "Groiss"
                layerDict["UseR"] = True
                layerDict["TopRoughnessType"] = RoughnessType
                layerDict["TopRoughness"] = Roughness
                layerDict["BottomRoughnessType"] = RoughnessType
                layerDict["BottomRoughness"] = Roughness
                layerDict["SideRoughnessType"] = RoughnessType
                layerDict["SideRoughness"] = Roughness
                
            if "TopRoughness" in info and info["TopRoughness"]:
                layerDict["UseR"] = True
                Roughness = info["TopRoughness"]
                RoughnessType = "Huray" if len(Roughness.split(",")) == 2 else "Groiss"
                layerDict["TopRoughnessType"] = RoughnessType
                layerDict["TopRoughness"] = Roughness
                
            if "BottomRoughness" in info and info["BottomRoughness"]:
                layerDict["UseR"] = True
                Roughness = info["BottomRoughness"]
                RoughnessType = "Huray" if len(Roughness.split(",")) == 2 else "Groiss"
                layerDict["BottomRoughnessType"] = RoughnessType
                layerDict["BottomRoughness"] = Roughness
                
            if "SideRoughness" in info and info["SideRoughness"]:
                layerDict["UseR"] = True
                Roughness = info["SideRoughness"]
                RoughnessType = "Huray" if len(Roughness.split(",")) == 2 else "Groiss"
                layerDict["SideRoughnessType"] = RoughnessType
                layerDict["SideRoughness"] = Roughness
                
            if "Cond" in info  and info["Cond"]:
                if "Material" not in info or not info["Material"].strip():
                    layerDict["Material"] = "Cond_%s"%str(info["Cond"])
                if info["Material"] not in self.layout.Materials:
                    material = self.layout.Materials.add({"Name":info["Material"],
                                                      "Cond": info["Cond"]
                                                      })
                    layerDict["Material"] = material.Name
                    
            #if DK,DF have value, it will have higher priority the materail in definitions
            if "DK" in info and info["DK"]:
                if "DF" not in info or not info["DF"]: #set df=0
                    layerDict["DF"] = 0
                
                #consider DK,df maybe not same with material in project, alway update #20240314
                layerDict["FillMaterial"] = "DK%sDF%s"%(info["DK"],info["DF"])
                material = self.layout.Materials.add({"Name":info["FillMaterial"],
                                                  "DK": info["DK"],
                                                  "DF": info["DF"],
                                                  "Freq":info["Freq"] if "Freq" in info else None
                                                  })
                layerDict["FillMaterial"] = material.Name
                
            elif "FillMaterial" in info and info["FillMaterial"]:
                if info["FillMaterial"] not in self.layout.Materials:
                    log.exception("FillMaterial and DK/DF must have one to difinited on layer:%s"%info["Name"])
            else:
                layerDict["FillMaterial"] = "FR4_epoxy"
                    
            self.Info.updates(layerDict)
            self.update()
                    
        elif self["Type"] == "dielectric":
            #if DK,DF have value, it will have higher priority the materail in definitions
            if "DK" in info:
                if "DF" not in info or not str(info["DF"]).strip(): #set df=0
                    layerDict["DF"] = 0

                #consider DK,df maybe not same with material in project, alway update #20240314
                layerDict["Material"] = "DK%sDF%s"%(info["DK"],info["DF"])
                material = self.layout.Materials.add({"Name":info["Material"],
                                                  "DK": info["DK"],
                                                  "DF": info["DF"],
                                                  "Freq":info["Freq"] if "Freq" in info else None
                                                  })
                layerDict["Material"] = material.Name
                
            elif "Material" in info and info["Material"].strip():
                if info["Material"] not in self.layout.Materials:
                    log.exception("Material and DK/DF must have one to difinited on layer:%s"%info["Name"])
            else:
                layerDict["FillMaterial"] = "FR4_epoxy"
                        
                
            self.Info.updates(layerDict)
            self.update()
        

        else:
            self.Info.updates(layerDict)
            self.update()
        
    def setRoughness(self,value):
        '''
        str: '0.5um', '0.5um:2.9'
        list: ['0.5um', '0.5um', '0.5um']
        '''
        if isinstance(value, str):
            self._info.update("Roughness0", value)
            self._info.update("BottomRoughness0", value)
            self._info.update("SideRoughness0", value)
        elif isinstance(value, (list,tuple)) and len(value)==3:
            self._info.update("Roughness0", value[0])
            self._info.update("BottomRoughness0", value[1])
            self._info.update("SideRoughness0", value[2])
        else:
            log.exception("routhness input msut be as '0.5um' or '0.5um:2.9' or ['0.5um','0.5um','0.5um']")           
            

    def offLayer(self,offset = 0, type = "signal"):
        if type.lower() in ["signal","conductor"]:
            layerNames = self.layout.Layers.ConductorLayerNames
            idx = layerNames.index(self.Name)
            if idx+offset<0: #return bottom
                return self.layout.Layers["CB1"]
            if idx+offset>len(layerNames)-1: #return top
                return self.layout.Layers["C1"]
            
            name = layerNames[idx+offset]
            return self.layout.Layers.DefinitionDict[name]
        elif type.lower() == "dielectric":
            layerNames = self.layout.Layers.DielectricLayerNames
            idx = layerNames.index(self.Name)
            
            if idx+offset<0: #return bottom
                return self.layout.Layers["CD1"]
            if idx+offset>len(layerNames)-1: #return top
                return self.layout.Layers["D1"]
            
            name = layerNames[idx+offset]
            return self.layout.Layers.DefinitionDict[name]
        
        elif type is None or type.lower() == "all":
            layerNames = self.layout.Layers.LayerNames
            idx = layerNames.index(self.Name)
            if idx+offset<0: #return bottom
                return self.layout.Layers["SB1"]
            if idx+offset>len(layerNames)-1: #return top
                return self.layout.Layers["S1"]
            
            if idx+offset<0 or idx+offset>len(layerNames)-1:
                return None
            name = layerNames[idx+offset]
            return self.layout.Layers.DefinitionDict[name]
        else:
            log.exception("offLayer type must be signal,dielectric or None : %s"%type)
            return None
    
    def rename(self,newName):
        self["Name"] = newName
        self.update()
    
    # def remove(self):
    #     objs = self.layout.oEditor.FindObjects('Layer',self.name)
    #     vias = self.layout.oEditor.FilterObjectList('Layer', self.name, self.layout.oEditor.FindObjects('Type',"via"))
    #     pins = self.layout.oEditor.FilterObjectList('Layer', self.name, self.layout.oEditor.FindObjects('Type',"pin"))
    #     self.layout.oEditor.RemoveLayer(self.Name)
    #     self.layout.Layers.refresh()
    
    def delete(self):
        if self.isConductor():
            log.info("delete conductor layer %s"%self.name)
            objs = set(self.layout.oEditor.FindObjects('Layer',self.name))
            objs = objs - set(self.layout.oEditor.FilterObjectList('Layer', self.name, self.layout.oEditor.FindObjects('Type',"via")))
            objs = objs - set(self.layout.oEditor.FilterObjectList('Layer', self.name, self.layout.oEditor.FindObjects('Type',"pin")))
            self.layout.oEditor.Delete(list(objs))
            self.layout.refresh()
            
        self.layout.oEditor.RemoveLayer(self.name)
        self.layout.Layers.refresh()
        

    
    
    def addLayerAbove(self,name,typ = "signal", copy = None):
        '''
        Args:
            typ: signal or dielectric
            copy (Layer): copy data from Layer object
        '''
        ary = []
        if copy:
            ary = ArrayStruct(copy.Array).copy()
        elif typ.lower() in ["signal","conductor"]:
            ary = ArrayStruct(hfss3DLParameters.signalLayer).copy()
        elif typ.lower().startswith("d"):
            ary = ArrayStruct(hfss3DLParameters.dielectricLayer).copy()
        else:
            pass
        
        ary["Name"] = name
        del ary["ID"]

        ary["Sublayer/LowerElevation"] = self.Upper
        
        self.layout.oEditor.AddStackupLayer(ary.Array)
        self.layout.Layers.refresh()
        
    def addLayerBelow(self,name,typ = "signal", copy = None):
        '''
        Args:
            typ: signal or dielectric
        '''
        ary = []
        if copy:
            ary = copy.Array    
        elif typ.lower() in ["signal","conductor"]:
            ary = ArrayStruct(hfss3DLParameters.signalLayer).copy()
        elif typ.lower().startswith("d"):
            ary = ArrayStruct(hfss3DLParameters.dielectricLayer).copy()
        else:
            pass
        ary["Name"] = name
        del ary["ID"]
        ary["Sublayer/LowerElevation"] = (Unit(self.Lower) - ary["Sublayer/Thickness"])["mm"]
        self.layout.oEditor.AddStackupLayer(ary.Array)
        self.layout.Layers.refresh()
        

    def getObjects(self,type="*"):
        '''
        "Type" to search by object type.
        Valid <value> strings for this type include: 'pin', 'via', 'rect', 'arc', 'line', 'poly', 'plg', 'circle void', 
        'line void', 'rect void', 'poly void', 'plg void', 'text', 'cell', 'Measurement', 'Port', 'Port Instance', 
        'Port Instance Port', 'Edge Port', 'component', 'CS', 'S3D', 'ViaGroup'
        '''
        return self.layout.oEditor.FilterObjectList('Layer', self.Name, self.layout.oEditor.FindObjects('Type',type))
        
    
    def isVisible(self):
        '''
        self.IsVisible not alway right
        '''
        return True in [self.IsVisibleShape,self.IsVisiblePath,self.IsVisiblePad,self.IsVisibleHole,self.IsVisibleComponent]
    
    def isConductor(self):
        return self["Type"] == "signal"

class Layers(Definitions):

        
    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Layer",definitionCalss=Layer)
        

    def __getitem__(self, key):
        
        key = self.DefinitionDict[key].name
        return super(self.__class__,self).__getitem__(key)

    def __setitem__(self, key,value):
        
        key = self.DefinitionDict[key].name
        return super(self.__class__,self).__setitem__(key,value)

    @property
    def DefinitionDict(self):
        if not self._definitionDict:
            self._definitionDict = ComplexDict(dict([(name,Layer(name,layout = self.layout)) for name in self.getAllLayerNames()]))
            maps = {}
            ConductorLayerNames = [layer for layer in self.LayerNames if self._definitionDict[layer]["Type"] == "signal"]
            DielectricLayerNames = [layer for layer in self.LayerNames if self._definitionDict[layer]["Type"]  == "dielectric"]
            
            #short name for signal
            count = len(ConductorLayerNames)
            for i,v in enumerate(ConductorLayerNames):
                maps.update({"C%s"%(i+1):v})
                maps.update({"CB%s"%(count-i):v})
                maps.update({"L%s"%(i+1):v})
                maps.update({"LB%s"%(count-i):v})

            #short name for dielectric
            count = len(DielectricLayerNames)
            for i,v in enumerate(DielectricLayerNames):
                maps.update({"D%s"%(i+1):v})
                maps.update({"DB%s"%(count-i):v})
            
            #short name for all stackup layer
            count = len(self.LayerNames)
            for i,v in enumerate(self.LayerNames):
                maps.update({"S%s"%(i+1):v})
                maps.update({"SB%s"%(count-i):v})
                maps.update({"Stk%s"%(i+1):v})
                maps.update({"StkB%s"%(count-i):v})
                
            self._definitionDict.setMaps(maps)
        return self._definitionDict
    
    @property
    def LayerNames(self):
        return self.layout.oEditor.GetStackupLayerNames()
    
    @property
    def ConductorLayerNames(self):
        return [layer for layer in self.LayerNames if self.DefinitionDict[layer]["Type"] == "signal"]

    @property
    def DielectricLayerNames(self):
        return [layer for layer in self.LayerNames if self.DefinitionDict[layer]["Type"]  == "dielectric"]
    
    
    def refresh(self):
        self._definitionDict = None
        #re-calculate LowerElevation0 for add or delete layer
#         elevation = Unit(0)
#         for layerName in self.LayerNames[::-1]:
#             layer = self.DefinitionDict[layerName]
#             layer.LowerElevation = elevation[self.layout.unit]
#             elevation += Unit(layer.Thickness)

    def getLayer(self,key):
        '''
        Args:
            key(int):
            key(LayerName):
            key("C:LayerIndex"):
            key("D:LayerIndex"):
            key("C:"):
            key("D:"):
        '''
        
        #for loop
        if isinstance(key, (int)):
            return self.DefinitionDict[self.LayerNames[key]]
        
        if isinstance(key, (slice)):
            return [self[l] for l in self.LayerNames[key]]
        
        if not isinstance(key, str):
            raise Exception("key error %s"%str(key))
        
        if key in self.DefinitionDict:
            return self._definitionDict[key]
        
        #support multi-level key
        keyList = re.split(r"[\\/]", key,maxsplit = 1)
        keyList = list(filter(lambda k:k.strip(),keyList)) #filter empty key
        if len(keyList)>1:
            return self[keyList[0]][keyList[1]]
        
        
        if ":" not in key:
            '''
            "Top" or "0"
            '''
            try:
                return self[int(key)]
            except Exception:
                return self._definitionDict[key]
        
        key = key.replace("*","")
        key1,key2 = key.split(":",1)
        
        if key1 == "":
            if key2 == "":
                #":"
                return self._definitionDict
            else:
                #":Top"
                return self[key2]
        elif key1.lower() == "c":
            if key2 == "":
                return [self[l] for l in self.ConductorLayerNames]
            else:
                try:
                    return self[self.ConductorLayerNames[int(key2)]]
                except Exception:
                    return self._definitionDict[key2]
                
        elif key1.lower() == "d":
            if key2 == "":
                return [self[l] for l in self.DielectricLayerNames]
            else:
                try:
                    return self[self.DielectricLayerNames[int(key2)]]
                except Exception:
                    return self._definitionDict[key2]
        else:
            if key2 in self.DefinitionDict:
                return self._definitionDict[key2]
 
        raise Exception("Unknown key :%s"%key)
    
    def getStackLayerNames(self):
        return self.layout.oEditor.GetStackupLayerNames()
    
    def getRealLayername(self,name):
        return self.layout.Layers[name].name
    
    def getAllLayerNames(self):
        return self.layout.oEditor.GetAllLayerNames()
    
    def update(self):
        '''
        update layers modify to layout
        '''
        for name in self._definitionDict:
            self._definitionDict[name].update()
    
    def getUniqueName(self,prefix="layer"):
        for i in range(1,10000):
            name = "%s%s"%(prefix,i)
            names = self.getAllLayerNames()
            if name in names:
                i += 1
            else:
                break
        return name
    
    
    def addLayer(self,name,type = "signal", height = None, refLayer= "S1", direction = "above",refresh = True):
        '''
        Args:
            type: signal(or conductor) or dielectric
            refLayer:  layerName
            direction: above or below
        '''
        log.info("add layer: %s"%name)
        
        ary = []
        if type.lower() in ["signal","conductor"]:
            ary = ArrayStruct(hfss3DLParameters.signalLayer).copy()
        elif type.lower().startswith("d"):
            ary = ArrayStruct(hfss3DLParameters.dielectricLayer).copy()
        else:
            pass
        
        if name in self.getAllLayerNames(): #avoid same layer name #20240324
            ary["Name"] = self.getUniqueName(name)
            log.info("layer exist, use new layer name: %s"%ary["Name"])
        else:
            ary["Name"] = name
            
        del ary["ID"]
        
        if height is not None:
            ary["Sublayer/LowerElevation"] = height  
        elif not self.layout.Layers.LayerNames: #20231018, for empty stackup
            ary["Sublayer/LowerElevation"] = 0            
        elif "above" in direction.lower():
            ary["Sublayer/LowerElevation"] = self[refLayer.strip()].Upper
        elif "below" in direction.lower():
            ary["Sublayer/LowerElevation"] = (Unit(self[refLayer.strip()].Lower) - ary["Sublayer/Thickness"])["mm"]
        else:
            log.exception("add layer argument 'positon' should have format: above:layerName or below:layerName")
        
        self.layout.oEditor.AddStackupLayer(ary.Array)
        if refresh:
            self.refresh()
            
    def removeLayer(self,layerName,refresh = True):
        self[layerName].delete()
        # self.layout.oEditor.RemoveLayer(layerName)
        # if refresh:
        #     self.refresh()

    def deleteLayer(self,fromLayer,toLayer):
        #fromLayer.必须大于toLayer.Lower，否则进行交换
        if self[fromLayer].Lower < self[toLayer].Lower:
            fromLayer,toLayer = toLayer,fromLayer
        fromH = Unit(self[fromLayer].Lower)
        toH = Unit(self.layout.Layers[toLayer].Lower)
        for layer in self.getStackLayerNames():
            layerH = Unit(self.layout.Layers[layer].Lower)
            if layerH <= fromH and layerH >= toH:
                print("delete layer: ",layer)
                self.layout.Layers[layer].delete()

    def setLayerDatas(self,layersInfo,mode = 0):
        '''
        layersInfo:
        - {Name: SURFACE,Type: signal, Material: copper, FillMaterial: M4 ,Thickness: 3.556e-05, Roughness: 0.5um,2.9 ,DK: 4,DF: 0.02,Freq: 1Ghz, Cond: 5.8e7, EtchFactor: 2.5}
        - {Name: SURFACE,Type: dielectric, Material: M4 ,Thickness: 3.556e-05,DK: 4,DF: 0.02,Freq: 1Ghz}
        
        mode:
        0(Auto): automatic, if signal layers and dielectric Layers have same count, will be update by index. else will update by name and will be ignore if layer name not in layout
        1(byIndex): by index, signal layers and dielectric Layers must have same count
        2(byName): by layer name, if layer name not in layout will be ignore
        3(force): force the layers same as layersInfo, signal layers count must have same count, dielectric Layers will override by layersInfo
        '''
        
        condLayersInfo = [layer for layer in layersInfo if ComplexDict(layer)["Type"].lower() in ["signal","conductor"]]
        dielectricLayersInfo = [layer for layer in layersInfo if ComplexDict(layer)["Type"].lower() in ["dielectric"]]
        otherLayersInfo = [layer for layer in layersInfo if ComplexDict(layer)["Type"].lower() not in ["dielectric","signal","conductor"]]
        
        ConductorLayerNames = self.ConductorLayerNames
        DielectricLayerNames = self.DielectricLayerNames
        AllLayerNames = self.getAllLayerNames()
        
        #--- byindex=1
        if mode == 1 or str(mode).lower() == "byindex":
#             1: by index, signal layers and dielectric Layers must have same count
            
            Layer._enableUpdate = False
            #set  layer datas
            if len(dielectricLayersInfo)>0:
                if len(dielectricLayersInfo) == len(DielectricLayerNames):
                    log.info("update dielectric layers data by index.")
                    for i in range(len(dielectricLayersInfo)): #[::-1] 20260612
                        log.info("update dielectric layers data by index: %s"%DielectricLayerNames[i])
                        self[DielectricLayerNames[i]].setData(dielectricLayersInfo[i])
                else:
                    log.exception("update layers by index, Dielectric layer count (%s) not same with layout count (%s)."%(len(dielectricLayersInfo),len(DielectricLayerNames)))
            else:
                log.debug("Input dielectricLayersInfo length is 0, skip.")
            
            if len(condLayersInfo)>0:
                if len(condLayersInfo) == len(ConductorLayerNames):
                    log.info("update Conductor layers data by index.")
                    for i in range(len(condLayersInfo)): #[::-1] 20260612
                        log.info("update Conductor layers data by index: %s"%ConductorLayerNames[i])
                        self[ConductorLayerNames[i]].setData(condLayersInfo[i])
                else:
                    log.exception("update layers by index, Conductor layer count (%s) not same with layout count (%s)."%(len(condLayersInfo),len(ConductorLayerNames)))

            else:
                log.debug("Input ConductorLayerNames length is 0, skip.")
            #continue executing
#             self.refresh()

            layerArrayDatas = []
            for layer in self.All:
                layerArrayDatas.append(layer.ArrayDatas)
    
            self.layout.oEditor.ChangeLayers([
                "NAME:layers",
                "Mode:=", "Laminate",
                [
                    "NAME:pps"
                ]]+layerArrayDatas)
            
            Layer._enableUpdate = True
            self.refresh()
            return
        
        
        #--- byname=2
        if mode == 2 or str(mode).lower() == "byname":
            log.info("update layers by name")
#             lowerLayerName = [name.lower() for name in self.getAllLayerNames()]
            for inputLayer in layersInfo:
                inputDict = ComplexDict(inputLayer)
                if "Name" not in inputDict:
                    log.debug("Mode by name, layer not with name will be ignore: %s"%str(inputLayer))
                    continue
                flag = False
                for layer in AllLayerNames:
                    if inputDict["Name"].lower() == layer.lower():
                        self._definitionDict[layer].setData(inputLayer)
                        flag = True
                
                if not flag:
                    log.info("layer name: '%s' not found, ignore."% inputDict["Name"])   
            
            self.refresh()
            
        #--- force=3
        if mode == 3 or str(mode).lower() == "force":
            if len(condLayersInfo) != len(ConductorLayerNames):
                if len(ConductorLayerNames)!=0:
                    log.exception("in force mode, Conductor layers input must have same count with stackup layers.")
                
            #set layer Thickness value
            h = Unit(0)
            for layer in layersInfo[::-1]:
                if "Type" not in layer:
                    continue
                
                layer["Height"] = h["mm"]
                h += layer["Thickness"]
            
            # if ConductorLayerNames len is 0, add all conductor layer to design #20231018
            if len(ConductorLayerNames)==0:
                for layer in condLayersInfo[::-1]:
                    self.addLayer(layer["Name"], type="conductor",height=layer["Height"],refresh=False)
                self.refresh()
            if len(dielectricLayersInfo) != len(DielectricLayerNames):
                #delete original dielectricLayers
                for layerName in DielectricLayerNames:
                    self.removeLayer(layerName,refresh=False)
                    self.layout.layers._definitionDict = None
                # replace dielectricLayers with new layer
                for layer in dielectricLayersInfo[::-1]:
                    self.addLayer(layer["Name"],type="dielectric",height=layer["Height"],refresh=False)
                self.refresh()
                    
            #set layer thickness
            self.layout.layers._definitionDict = None
            self.setLayerDatas(layersInfo, mode = "byindex")  
            self.refresh()

            #set layer thickness
#             self.layout.layers._definitionDict = None
#             self._quickUpdateLayers(layersInfo)

            return

        #--- auto=0      
        if mode == 0 or str(mode).lower() == "auto":
            #continue executing
            if len(condLayersInfo) == len(ConductorLayerNames):
                self.setLayerDatas(condLayersInfo, mode = "byindex")
            else:
                self.setLayerDatas(condLayersInfo, mode = "byname")
                
            if len(dielectricLayersInfo) == len(DielectricLayerNames):
                self.setLayerDatas(dielectricLayersInfo, mode = "byindex")
            else:
                self.setLayerDatas(dielectricLayersInfo, mode = "byname")
   
        #--- Unspecified type layers      
        log.info("update Unspecified type layers data by name.")

        for inputLayer in otherLayersInfo:
            inputDict = ComplexDict(inputLayer)
            if "Name" not in inputDict:
                log.debug("Mode by name, layer not with name will be ignore: %s"%str(layer))
                continue
            flag = False
            for layer in AllLayerNames:
                if inputDict["Name"].lower() == layer.lower():
                    self._definitionDict[layer].setData(inputLayer)
                    flag = True
            
            if not flag:
                log.info("layer name: '%s' not found, ignore."% inputDict["Name"])   
    
    @ProcessTime
    def loadFromDict(self,layersInfo,mode=3):
        '''
        mode=3 强制更新,给定全部信息
        layersInfo:
        - {Name: SURFACE,Type: signal, Cond:5.8e7 ,Thickness: 3.556e-05, Roughness: 0.5um,2.9um, 
            DK: 4,DF: 0.02,Freq: 1Ghz, Cond: 5.8e7, EtchFactor: 2.5,EtchAngle:75}
        
        mode: 
        0(Auto): automatic, if signal layers and dielectric Layers have same count, will be update by index. else will update by name and will be ignore if layer name not in layout
        1(byIndex): by index, signal layers and dielectric Layers must have same count
        2(byName): by layer name, if layer name not in layout will be ignore
        3(force): force the layers same as layersInfo, signal layers count must have same count, dielectric Layers will override by layersInfo

        更新一个或者多个层的信息用mode=2 byName
        - 更新SURFACE层的厚度和Roughness信息 {Name: SURFACE,Thickness: 3.556e-05, Roughness: 0.5um,2.9um}
        强制更新所有的金属层和介质层信息使用 mode=3 force，此时需要提供所有层的信息，当提供的金属层数量和当前设计中的金属层数量不一致时会报错，介质层会被强制覆盖。
 
        '''
        layersInfoTemps = []
        index = 0
        for layerDict in layersInfo:
            index += 1
            cpLayerDict = ComplexDict(layerDict)
            
            if "Type" not in cpLayerDict:
                log.exception("Layer input must have 'Type' attribule.")
            
            if cpLayerDict["Type"].lower() in ["signal","conductor"] or cpLayerDict["Type"].lower().startswith("c"):
                layerDict["UseEtch"] = False
                layerDict["UseR"] = False
                if "Cond" not in cpLayerDict:
                    layerDict["Material"] = "Copper"
            elif cpLayerDict["Type"].lower() in ["dielectric"] or cpLayerDict["Type"].lower().startswith("d"):
                if "DK" not in cpLayerDict:
                    layerDict["Material"] = "FR4_epoxy"
            else:
                continue #Type not give
            

            #remove empty value in layerDict , 20231123
            
            for key in list(layerDict.keys()): #copy keys
                if str(layerDict[key]).strip() == "":
                    log.info("del key with empty value: %s"%key)
                    del layerDict[key]
                    continue
                
                if key.lower() == "etchangle":
                    layerDict["UseEtch"] = True
                    layerDict["EtchFactor"] = math.tan(math.radians(float(layerDict[key])))
                    continue

                if key.lower() == "etchfactor":
                    layerDict["UseEtch"] = True
                    continue
                
                if key.lower() == "roughness" and layerDict[key]:
                    layerDict["UseR"] = True
                    layerDict[key] = re.sub(r"[,;:]",",",layerDict[key])
                    continue
                
                # Thickness(um)
                if "thickness" in key.lower() and layerDict[key]:
                    if not layerDict[key].strip(): #break if Thickness not have value
                        layerDict["Thickness"] = ""
                        continue
                    
                    rst = re.match(r".*\((.*)\)",key)
                    if rst:
                        unit = rst.groups()[0]
                        try: 
                            float(layerDict[key]) #if thickness is flaot
                            layerDict["Thickness"] = layerDict[key]+unit
                        except Exception:
                            log.debug("thickness have unit: %s"%layerDict[key])
                            layerDict["Thickness"] = layerDict[key]
                            pass
                    else:
                        pass
                    continue
                
                #for layer Name
                if key.lower() in ["name","layer","layername","layer name"]:
                    layerDict["Name"] = layerDict[key]
                    continue
                
            
            # if "Name" in cpLayerDict and cpLayerDict["Name"].strip() and \
            # "Thickness" in cpLayerDict and cpLayerDict["Thickness"].strip(): # remove if Thickness not have value
            if "Thickness" in cpLayerDict and cpLayerDict["Thickness"].strip(): # 20260401
                if "Name" not in cpLayerDict or not cpLayerDict["Name"].strip(): # remove if Name not have value
                    # cpLayerDict["Name"] = "%s_%s"%(cpLayerDict["Type"],index)  
                    cpLayerDict.update("Name","%s_%s"%(cpLayerDict["Type"],index))
                layersInfoTemps.append(layerDict)
            else:
                log.info("Remove layer with not valid input: %s"%str(layerDict))
                
        self.setLayerDatas(layersInfoTemps, mode=mode)
    
            
    def loadFromCSV(self,csvPath):
        layersInfo = loadCSV(csvPath, fmt="dict")
#         log.messageBox(layersInfo)
        self.loadFromDict(layersInfo)
        
    def exportCsv(self,csvPath):
        header = ["Layer","Type","Thickness(mil)","DK","DF","Roughness"]
        layerList = []
        for name in self.LayerNames:
            row = []
            layer = self[name]
            row.append(layer.name)
            row.append(layer.Type)
            row.append(layer.Thickness)
            row.append(layer.LayerDK)
            row.append(layer.LayerDF)
            row.append(layer.Roughness.replace(",",";") if layer.Type == "signal" and layer.UseRoughness else "")
            layerList.append(row)
        
        writeCSV(csvPath,layerList,header=header)
            
            
    def exportXml(self,path):
        log.info("Export stackup xml to %s"%path)
        self.layout.oEditor.ExportStackupXML(path)
        
    def importXml(self,path):
        log.info("Import stackup xml from %s"%path)
        self.layout.oEditor.ImportStackupXML(path)
        
    def reversedStakup(self):
        log.info("reversed stakcup ...")
        stackupH = Unit(self["S1"].Upper)
        for layer in self.LayerNames:
            self[layer].Lower = (stackupH - self[layer].Upper)["mm"]
        
        self._definitionDict = None
        
    def getLayerByHeight(self,height,type="Conductor",adjust = "Near"):
        '''
        adjust: above,below,Near,Inner, Outer
        '''
        flayer = None
        distance = 1e9 #max enough
        
        height = Unit(height)
        if type[0].lower() == "c" or type[0].lower() == "s":
            for name in self.layout.layers.ConductorLayerNames[::-1]:
                layer = self.layout.layers[name]
                if height> layer.Upper: #above the layer
                    distance1 = height - layer.Upper
                elif height<layer.Lower:
                    distance1 = height - layer.Lower
                else:
                    distance = 0
                    flayer = name
                    break
                
                if abs(distance1)<abs(distance):
                    distance = distance1
                    flayer = name
                    
            if distance == 0:
                return flayer
            
            if adjust == "Near":
                return flayer
            
            if adjust == "Inner": #HalfStackup 0,1
                adjust = "below" if self[flayer].HalfStackup else "above"
                 
            if adjust == "Outer":
                adjust = "above" if self[flayer].HalfStackup else "below"              
            
            if adjust == "above":
                flayer = self.layout.layers[flayer].offLayer(1 if distance>0 else 0,type=type).Name
            if adjust == "below":
                flayer = self.layout.layers[flayer].offLayer(0 if distance>0 else -1,type=type).Name
            
#            #for 2025.2 'Zone1;signal_3'
#             flayer = flayer.split(";")[-1]
            return flayer
                    
        
        elif type[0].lower() == "d":
            pass
        else:
            log.exception("unknown layer type: %s"%type)
    
    def getVisibleConductorLayers(self):
        ConductorLayerNames = self.ConductorLayerNames
        return [self[name] for name in ConductorLayerNames if self[name].isVisible()]
    
    
        