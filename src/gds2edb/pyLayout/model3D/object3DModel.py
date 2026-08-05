#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20240317

import re

from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log


class Object3DModle(object):
    '''_summary_

    Args:
        object (_type_): _description_
    '''

    appTemp = None
    
    
    def __init__(self, name, app=None):
        '''
        '''
        self.name = name
        if app:
            self.__class__.appTemp = app
            self.app = app
        else:
            self.app = self.__class__.appTemp

        self._info = None
        self.maps = {}
        self.parsed = False

    def __getitem__(self, key):
        """
        key: str
        """
        return self.get(key)


    def __setitem__(self,key,value):
        self.set(key,value)

        

    def __getattr__(self,key):

        if key in ["app","name","_info","maps","parsed"]:
            return object.__getattribute__(self,key)
        else:
            log.debug("__getattr__ from _dict: %s"%key)
            return self[key]
        

    def __setattr__(self, key, value):
        if key in ["app","name","_info","maps","parsed"]:
            object.__setattr__(self,key,value)
        else:
            log.debug("get property '%s' from dict."%key)
            self[key] = value

    def __contains__(self,key):
        return key in self.Info

    def __repr__(self):
        return "%s Object: %s"%(self.__class__.__name__,self.Name)
    
    def __dir__(self):
        return list(dir(self.__class__)) + list(self.__dict__.keys()) + list(self.Props)

    @property
    def Info(self):
        if not self._info:
            self.parse()
            
        return self._info

    @property
    def Props(self):
        propKeys = list(self.Info.Keys)
        if self.maps:
            propKeys += list(self.maps.keys())
        
        return propKeys
    
    @property
    def Name(self):
        return self.name
    
    
    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        
        log.debug("parse primitive: %s"%self.name)
        self._info = ComplexDict()
        maps = self.maps
        self._info.update("Name",self.name) #add name to Info
        self._info.update("self",self) #add name to Info
        
        #--- for BaseElementTab peoperty
        properties = self.app.oEditor.GetProperties("Geometry3DAttributeTab",self.name)
        self._info.update("Properties",properties)
        for prop in properties:
            self._info.update(prop,None) #here give None value. get property value when used to improve running speed
            if " " in prop:
                maps.update({prop.replace(" ",""):prop}) #map property with space characters
        
        maps.update({"Vertexs":{
                          "Key":"self",
                          "Get": lambda s: s._getVertexsPositionDict(s.app.oEditor.GetVertexIDsFromObject(s.name))
                          }})
        
        maps.update({"Faces":{
                          "Key":"self",
                          "Get": lambda s: s.app.oEditor.GetFaceIDs(s.name)
                          }})

        
        maps.update({"Edges":{
                          "Key":"self",
                          "Get": lambda s: s.app.oEditor.GetEdgeIDsFromObject(s.name)
                          }})
        
        self._info.setMaps(maps)
        self.parsed = True


    def get(self,key):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if not self.parsed:
            self.parse()
  

        
        if key in self._info and self._info[key] != None: # Map value or already have value
            return self._info[key]
        
        
        realKey = self._info.getReallyKey(key)

        if realKey in self._info.Properties:  #value is None
            self._info.update(realKey,self.getProp(realKey))
            return self._info[realKey]
        else:
            log.exception("Property error: %s->%s"%(self.name,key))
    
    def set(self,key,value):
        '''
        mapping key must not have same value with maped key.
        
        oEditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:Geometry3DAttributeTab",
                    [
                        "NAME:PropServers", 
                        "via_967_2"
                    ],
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Color",
                            "R:="            , 0,
                            "G:="            , 255,
                            "B:="            , 0
                        ]
                    ]
                ]
            ])
        
        
        '''

        if not self.parsed:
            self.parse()
        
#         realKey = self._info.getReallyKey(key) #don't use mapkey
        realKey = key  #don't use mapkey
           
        if key in self._info.Properties: 
            self.setProp(realKey, value)
            self._info[realKey] = value
#             self.parsed = False #refresh
            
        elif key in self._info:
            log.warning("Attribute values will not take effect in app: %s:%s"%(key,value))
            self._info[realKey] = value
        
        else:
            log.exception("Property error: %s->%s"%(self.name,key))

    def getProp(self,prop):
        value = self.app.oEditor.GetPropertyValue("Geometry3DAttributeTab",self.Name,prop)
        value = value.replace('"',"") #fix material name with ""
        return value

    def setProp(self,prop,value):
        self.app.oEditor.SetPropertyValue("Geometry3DAttributeTab",self.name, prop,value)

    def delete(self):
        self.app.oEditor.Delete(
            [
                "NAME:Selections",
                "Selections:="        , self.name
            ])

        self.app.Objects.pop(self.name)

    def update(self):
        self._info = None #delay update
#         self.parse()

    def _getVertexsPositionDict(self,vertexIds):
        postions = []
        for vertexId in vertexIds:
            postions.append(self.app.oEditor.GetVertexPosition(vertexId))
        return dict(zip(vertexIds,postions))
    
    def getVertexPosition(self,vertexId):
        return self.app.oEditor.GetVertexPosition(vertexId)


class Objects3DModle(object):
    

    def __init__(self,app=None):
        self._objectDict = None #ComplexDict component buffer
        self.app = app

    def __getitem__(self, key):
        """
        key: str, regex, list, slice
        """
        
        if isinstance(key, int):
            return self.ObjectDict[key]
        
        if isinstance(key, slice):
            return self.ObjectDict[key]
        
        if isinstance(key, str):
            if key in self.ObjectDict:
                return self.ObjectDict[key]
            else:
                #find by 正则表达式
                lst = [name for name in self.ObjectDict.Keys if re.match(r"^%s$"%key,name,re.I)]
                if not lst:
                    raise Exception("not found component: %s"%key)
                else:
                    #如果找到多个器件（正则表达式），返回列表
                    return self[lst]

        if isinstance(key, (list,tuple)):
            return [self[i] for i in list(key)]
    
    def __getattr__(self,key):
        if key in ['__get__','__set__']:
            #just for debug run
            return None
        if key in ["app","_objectDict"]:
            return object.__getattribute__(self,key)
        else:
            log.debug("__getattr__ from _dict: %s"%key)
            return self[key]
    
    def __contains__(self,key):
        return key in self.ObjectDict
    
    def __len__(self):
        return len(self.ObjectDict)
    
    @property
    def Count(self):
        return len(self)
    
    
    @property
    def ObjectDict(self):
        '''
        oEditor.GetChildNames("AllParts")
        Name    Type    Description
        <category>    String    
        Optional. Passing no input returns the list of possible strings:
        
        "AllParts" – Returns the names of all parts.
        "CoordinateSystems" – Returns the names of all coordinate systems.
        "Groups" – Returns the names of all groups.
        "Lists" – Returns the names of all lists.
        "ModelParts" – Returns names of model parts.
        "NonModelParts" – Returns the names of non-model parts.
        "Planes" – Returns the names of all planes.
        "Points" – Returns the names of all points.
        "SubmodelDefinitions" – Returns the names of submodel definitions.
        
        
        '''
        
        if self._objectDict is None:
            self._objectDict  = ComplexDict(dict([(p,Object3DModle(p,app=self.app)) for p in self.app.oEditor.GetChildNames("AllParts")]))
        return self._objectDict 
    
    @property
    def All(self):
        return self.ObjectDict
    
    @property
    def NameList(self):
        return self.ObjectDict.Keys
    
    def filter(self, func):
        return dict(filter(func,self.ObjectDict.items()))
    
        
    def refresh(self):
        self._objectDict  = None

        
    def push(self,name):
        if self._objectDict is None:
            self._objectDict = ComplexDict()
        self._objectDict.update(name,Object3DModle(name,app=self.app))
    
    def pop(self,name):
        if self._objectDict is None:
            return
        del self._objectDict[name]
        

    def getByName(self,name):
        '''
        Args:
            name (str): component name in app, ingor case
        Returns:
            (Component): Component object of name
             
        Raises:
            name not found on app
        '''
        if name in self.ObjectDict:
            return self.ObjectDict[name]
        
        log.info("not found component: %s"%name)
        return None
    
    def getUniqueName(self,prefix=""):
        
        if prefix is None:
            prefix = "Object_"
            
        for i in range(1,100000):
            name = "%s%s"%(prefix,i)
            names = self.NameList
            if name in names:
                i += 1
            else:
                break
        return name