#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230611

"""
    Examples:
        >>> via = Via()
        >>> via["via1"]
        返回via1的Via对象
                
        >>> cmp[["via1","via2"]]
        返回via1,via2的Via对象List
        
        >>> for v in via():
        >>>     log.debug(v.Name)
        打印PCB上所有的Via名字  
        
        >>> backDrill(self,viaName=None,startLayer=None,stopLayer=None,
                  BackdrillTop=None,BackdrillTopOffset=0,BackdrillTopDiameter=0,
                  BackdrillBot=None,BackdrillBotOffset=0,BackdrillBotDiameter=0):
    backdrill：可以设置通过Layer背钻，或者通过Length（2023R1版本及以上）
"""


import re
from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,tuple2list


from .geometry import Point
from .primitive import Primitive,Primitives

class Via(Primitive):
    '''

    Args:
    '''

    def __init__(self, name, layout=None):
        '''Initialize Pin object
        Args:
            name (str): Via name in layout
            layout (PyLayout): PyLayout object, optional
        '''
        super(self.__class__,self).__init__(name,layout)

    def parse(self, force = False):
        if self.parsed and not force:
            return
        
        super(self.__class__,self).parse(force) #initial component properties
        maps = self.maps
        
        #add X,Y location property
        maps.update({"X":{
            "Key":"Location",
            "Get":lambda v:v.X 
            }})
        maps.update({"Y":{
            "Key":"Location",
            "Get":lambda v:v.Y
            }})
        
        self._info.setMaps(maps)

#         self._info.update("PadStack",self.layout.PadStacks[self._info["Padstack Definition"]])



    def getPadSize(self,layer="C1"):
        PadStack = self.layout.PadStacks[self._info["Padstack Definition"]]
        return PadStack[layer]["PadSize"]
    
#     def getConnectedObjs(self,type="*"):
#         if not self.Net:
#             log.info("via not have net name")
#             return []
#         
#         objs1 = self.layout.oEditor.FilterObjectList('Type',type, self.layout.oEditor.FindObjects('Net', self.Net))
#         objs2 = self.layout.oEditor.FindObjectsByPolygon(self.layout.oEditor.GetBBox(self.name), '*') # * for all layers
#         objs3 = set(objs1).intersection(set(objs2))
#         return list(objs3)
    

    def backdrill(self,stub = None):
        '''
        this function only support 2023.1 or later versions 
        stub: str or dict {layerName:"stubTop,stubTop",
        defalut:stubTop,stubBottom,"Tail":top,bottom} 
        '''
        
        if isinstance(stub,str):
            stubs = re.split("[,;]",stub)
            if len(stubs)==1:
                stub = {"default":[stubs[0],stubs[0]]}
            elif len(stubs)==2:
                stub = {"default":stubs}
            else:
                log.exception("stub format error %s " % str(stub))
        
        if isinstance(stub,(dict,ComplexDict)):
            for layer,stubs in stub.items():
                if isinstance(stubs,str):
                    stubs = re.split("[,;]",stubs)
                
                if not isinstance(stubs,(list,tuple)):
                    log.exception("stub format error %s " % str(stub))
                
                if len(stubs)==1:
                    stub[layer] = [stubs[0],stubs[0]]
                elif len(stubs)==2:
                    stub[layer] = stubs
                else:
                    log.error("stub format error %s " % str(stub))
            if "default" not in stub:
                stub["default"] = [self.layout.options["H3DL_backdrillStub"],self.layout.options["H3DL_backdrillStub"]] #last layer
        stub = ComplexDict(stub)
        layers = []
        #for lines
        names = self.getConnectedObjs('line')
        for name in names:
            line = self.layout.lines[name]
            layers.append(line["PlacementLayer"])
        

        #for pins
        names = self.getConnectedObjs('pin')
        for name in names:
            pin = self.layout.pins[name]
            CompName = pin.CompName
            if CompName in self.layout.components:
                layers.append(self.layout.components[CompName]["PlacementLayer"])
        
        if len(layers)<2: #small then two layers
            return
        
        layers.sort(key = lambda x: Unit(self.layout.layers[x].Lower).V,reverse = True)
        #---backdrill Top
        if layers[0] != self.layout.layers["C1"].Name:
            stubLen = stub[layers[0]][0] if layers[0] in stub else stub["default"][0]
            #Tail only for pins
            # if "Tail" in stub and stub["Tail"]:
            #     disBot = Unit(self.layout.layers[layers[0]].Lower)-Unit(self.layout.layers["CB1"].lower)
            #     if Unit(stub["Tail"][-1])>disBot:
            #         stubLen = (Unit(stub["Tail"][-1]) - disBot)["mil"]
            
            log.info("Backdrill vias : %s from Top to %s, stub:%s, net:%s, stub: %s"%(self.name,layers[0],stub,self.Net,stubLen))
            self.BackdrillTop = layers[0]
            self.TopOffset = stubLen
            self.update()
        #---backdrill bottom
        if layers[-1] != self.layout.layers["CB1"].Name:
            stubLen = stub[layers[0]][-1] if layers[0] in stub else stub["default"][-1]
            #Tail only for pins
            # if "Tail" in stub and stub["Tail"]:
            #     disTop = Unit(self.layout.layers["C1"].lower) - Unit(self.layout.layers[layers[-1]].Lower)
            #     if Unit(stub["Tail"][0])>disTop:
            #         stubLen = (Unit(stub["Tail"][0]) - disTop)["mil"]         
            log.info("Backdrill pin : %s from Bottom to %s, stub:%s, net:%s, stub: %s"%(self.name,layers[-1],stub,self.Net,stubLen))
            self.BackdrillBottom = layers[-1]
            self.BottomOffset = stubLen
            self.update()
            
    def clearBackdrill(self):
        
        if self.BackdrillTop != "----":
            log.info("clear backdrill vias Top: %s"%self.name)
            self.BackdrillTop = "----"
            self.update()
        if self.BackdrillBottom != "----" :
            log.info("clear backdrill vias Bottom: %s"%self.name)
            self.BackdrillBottom = "----"
            self.update()
    
class Vias(Primitives):
    
    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="via",primitiveClass=Via)
        