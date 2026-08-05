#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20240317

import re

try:
    from collections import Iterable
except Exception:
    from collections.abc import Iterable

from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log

from .geometry import Point

'''
this a base class for privitives of : 
        'pin', 'via', 'rect', 'arc', 'line', 'poly', 
        'plg', 'circle void', 'line void', 'rect void', 'poly void', 'plg void', 'text', 'cell', 
        'Measurement', 'Port', 'Port Instance', 'Port Instance Port', 'Edge Port', 'component', 'CS', 'S3D', 'ViaGroup'
        
It 's not recommand to initial Primitive or Primitives object redirect.
'''


class Primitive(object):
    '''_summary_

    Args:
        object (_type_): _description_
    '''

    def __init__(self, name, layout=None):
        '''Initialize Pin object
        Args:
            name (str): poly name in layout
            layout (PyLayout): PyLayout object, optional
        '''
        self.name = name
        self.layout = layout
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

        if key in ["layout","name","_info","maps","parsed"]:
            return object.__getattribute__(self,key)
        else:
            log.debug("__getattr__ from _dict: %s"%key)
            return self[key]
        

    def __setattr__(self, key, value):
        if key in ["layout","name","_info","maps","parsed"]:
            object.__setattr__(self,key,value)
        else:
            log.debug("get property '%s' from dict."%key)
            self[key] = value

    def __repr__(self):
        return "%s Object: %s"%(self.__class__.__name__,self.Name)
    
    def __contains__(self,key):
        return key in self.Info
    
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
        if self.Info.maps:
            propKeys += list(self.Info.maps.keys())
        
        return propKeys
    
    @property
    def Name(self):
        return self.name
    
#     @property
#     def Type(self):
#         return self.getProp("Type")
    
    @property
    def Collection(self):
        typ = self.getProp("Type")
        
        if self.__class__.__name__ == 'Port':
            typ = "Port"
    
        return self.layout[typ+"s"]
    
    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        
        log.debug("parse primitive: %s"%self.name)
        self._info = ComplexDict()
        maps = self.maps
#         self._info.update("Name",self.name) #add name to Info
        
        #--- for BaseElementTab peoperty
        properties = self.layout.oEditor.GetProperties("BaseElementTab",self.Name)
        self._info.update("Properties",properties)
        for prop in properties:
            self._info.update(prop,None) #here give None value. get property value when used to improve running speed
            if " " in prop:
                maps.update({prop.replace(" ","").replace("-","_"):prop}) #map property with space characters
                
            if re.match(r"Pt(\d+|s)$",prop,re.IGNORECASE): 
                self._info.update("Pts",None)
        
        #change 20240703
        self._info.update("Name",self.name) #add name to Info, override name Properties
        self._info.update("self", self)
        
        #for Polygon Object
        maps.update({"Polygon":{
            "Key":"self", #should use name, not Name
            "Get":lambda s: s.layout.oEditor.GetPolygon(s.name)
            }})
        
        #for Polygon Object
        def __area(self):
            polygon = self.layout.oEditor.GetPolygon(self.name)
            return polygon.Area() if polygon else None
        
        maps.update({"Area":{
            "Key":"self",
            "Get":lambda s: __area(s)
            }})
        
        #for bbox
        def __GetBBox(self):
            bbox = self.layout.oEditor.GetBBox(self.name)
            if bbox:
                LL = bbox.BBoxLL()
                UR = bbox.BBoxUR()
                return [Point(LL),Point(UR)] 
            else:
                return None

        maps.update({"BBox":{
            "Key":"self",
            "Get":lambda s: __GetBBox(s)
            }})

        self.maps = maps
        self._info.setMaps(maps)
        self.parsed = True


#     def __area(self,name):
#         polygon = self.layout.oEditor.GetPolygon(self.name)
#         return polygon.Area() if polygon else None

    def get(self,key):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if not self.parsed:
            self.parse()
  
        
        if key in self._info and self._info[key] is not None: # Map value or already have value
            return self._info[key]
        
        if not isinstance(key, str): #key must string
            log.exception("Property error: %s->%s"%(self.name,str(key)))
        
        realKey = self._info.getReallyKey(key) #realKey for mapping
        if re.match(r"Pt(\d+|s)$",realKey,re.IGNORECASE) or realKey in ["Center","Pt A","Pt B","Location"]: 
            self._info.update(realKey,self.getPoint(realKey))
            return self._info[realKey]
        
        if realKey in self._info.Properties:  #value is None
            self._info.update(realKey,self.getProp(realKey))
            return self._info[realKey]
        else:
            log.exception("Property error: %s->%s"%(self.name,key))
    
    def set(self,key,value):
        '''
        mapping key must not have same value with maped key.
        '''
        
        
        if not self.parsed:
            self.parse()
        
        if not isinstance(key, str): #key must string
            log.exception("Property error: %s->%s"%(self.name,str(key)))
        
        realKey = self._info.getReallyKey(key) #don't use mapkey
#         realKey = key  #don't use mapkey
           
        if re.match(r"Pt(\d+|s)$",realKey,re.IGNORECASE) or realKey in ["Center","Pt A","Pt B","Location"]: 
            self.setPoint(realKey, value)
            self.parsed = False #refresh
            
        elif realKey in self._info.Properties: 
            self.setProp(realKey, value)
            self._info[realKey] = value
#             self.parsed = False #refresh
            
        elif key in self._info:
            log.warning("Attribute values will not take effect in layout: %s:%s"%(key,value))
            self._info[key] = value
        
        else:
            log.exception("Property error: %s->%s"%(self.name,key))

    def getProp(self,prop):
        return self.layout.oEditor.GetPropertyValue("BaseElementTab",self.Name,prop)

    def setProp(self,prop,value):
        
        if re.match(r"Pt\s*[\dAB]+$",prop): #set Points: Pt0,Pt1, Pt A, Pt B, support expression
            self.setPoint(prop, value)
        else:
            self.layout.oEditor.SetPropertyValue("BaseElementTab",self.name, prop,value)

        
    def setPoint(self,ptName,value):
        '''
        value: list,tuple,"x,y",Point, 3DL Point
        '''
#         key = self._info.getReallyKey(ptName)
        
        key = ptName
        if re.match(r"Pt\d+$",key) or key in ["Center","Pt A","Pt B","Location"]:
            pt = Point(value)
            self.layout.oEditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:BaseElementTab",
                        [
                            "NAME:PropServers", 
                            self.Name
                        ],
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:%s"%ptName,
                                "X:=", pt.X,
                                "Y:=", pt.Y
                            ]
                        ]
                    ]
                ])
            return None
        
        if key.lower() == "pts" and isinstance(value, (list,tuple)):
            for i in range(len(value)):
                self.setPoint("Pt%s"%i, value[i])
                
            return None             
        
        log.exception("property or value error: %s %s"%(ptName,str(value)))
        
    def getPoint(self,ptName):
        #add unit for pt\d+ or pt [AB]
        
        key = self._info.getReallyKey(ptName)
        if re.match(r"Pt\d+$",key) or key in ["Center","Pt A","Pt B","Location"]:
            ptValue = self.layout.oEditor.GetPropertyValue("BaseElementTab",self.Name,key)
            return Point(["%s%s"%(c.strip(),self.layout.unit) for c in ptValue.split(",")])
        
        if re.match(r"ArcHeight.*$",key):
            ptValue = self.layout.oEditor.GetPropertyValue("BaseElementTab",self.Name,key)
            return ptValue
#             return "%s%s"%(ptValue.strip(),self.layout.unit)
        
        if key.lower() == "pts":
            pts = []
            for p in self._info.Keys:
                if re.match(r"Pt\d+$", p) or re.match(r"ArcHeight.*$", p):
                    pts.append(self.getPoint(p))
            return pts
        
        log.exception("property error: %s"%ptName)
  
    def getConnectedObjs(self,type="*"):
        if not self.Net:
            log.info("via not have net name")
            return []
        
        objs1 = self.layout.oEditor.FilterObjectList('Type',type, self.layout.oEditor.FindObjects('Net', self.Net))
        objs2 = self.layout.oEditor.FindObjectsByPolygon(self.layout.oEditor.GetBBox(self.name), '*') # * for all layers
        objs3 = set(objs1).intersection(set(objs2))
        return list(objs3)

    def getPhysicallyConnected(self):
        self.layout.oEditor.UnselectAll()
        try:
            self.layout.oEditor.SelectPhysicallyConnected(
                [
                    "NAME:elements", 
                    self.name
                ])
            objs2 = self.layout.oEditor.GetSelections()
        except Exception:
            return []
        self.layout.oEditor.UnselectAll()
        return list(objs2)

    def delete(self):
        
        self.Collection.pop(self.Name)
        self.layout.oEditor.Delete([self.Name])
        

    def update(self):
        self._info = None 
        self.parsed = False #delay update



class Primitives(object):
    

    def __init__(self,layout=None,type="*",primitiveClass=Primitive):
        self._objectDict = None #ComplexDict component buffer
        self.layout = layout
        self.type = type
        self.primitiveClass = primitiveClass
        
#         #for port objects, PlanarEM Type
#         if type in ["Circuit","Single Strip Gap Source"]: 
#             self.type = "Port"
   
            
    def __getitem__(self, key):
        """
        key: str, regex, list, slice
        """
        
        if isinstance(key, int):
            return self.ObjectDict[self.NameList[key]]
        
        if isinstance(key, slice):
            return self.ObjectDict[self.NameList[key]]
        
        if isinstance(key, str):
            if key in self.ObjectDict:
#                 return self.primitiveClass(key,layout=self.layout)
                return self.ObjectDict[key]
            
            elif re.match(r".*[\*\.\?\+\{\}\|].*",key,re.I): #正则表达式
                #find by 正则表达式
                lst = [name for name in self.NameList if re.match(r"^%s$"%key,name,re.I)]
                if not lst:
                    return []
#                     raise Exception("not found component: %s"%key)
                else:
                    #如果找到多个器件（正则表达式），返回列表
                    return self[lst]
            else:
                raise Exception("not found %s: %s"%(self.type,key))

        if isinstance(key, (list,tuple,Iterable)):
            return [self[i] for i in list(key)]
    
    def __getattr__(self,key):
        if key in ['__get__','__set__']:
            #just for debug run
            return None
        if key in ["layout","_objectDict","type","primitiveClass"]:
            return object.__getattribute__(self,key)
        else:
            log.debug("__getattr__ from _dict: %s"%key)
            return self[key]
    
    def __contains__(self,key):
        return key in self.ObjectDict
    
    def __len__(self):
        return len(self.ObjectDict)
    
    def __repr__(self):
        return "%s Objects collection: %s Objects"%(str(self.type),len(self.ObjectDict))
    
    def __add__(self,prim2):
        if isinstance(prim2, Primitives):
            _objectDict = ComplexDict()
            _objectDict.append(self.ObjectDict)
            _objectDict.append(prim2.ObjectDict)
            primObject = Primitives(layout=self.layout,type="MixedObjects",primitiveClass=object)
            primObject._objectDict = _objectDict
            return primObject
        else:
            log.exception("Only Primitive Class can be __add__")
    
    @property
    def oProject(self):
        return self.layout.oProject
    
    @property
    def oDesign(self):
        return self.layout.oDesign

    @property
    def oEditor(self):
        return self.layout.oEditor
    
    
    @property
    def ObjectDict(self):
        '''
        FindObjects
        "Type" to search by object type.
        Valid <value> strings for this type include: 'pin', 'via', 'rect', 'arc', 'line', 'poly', 
        'plg', 'circle void', 'line void', 'rect void', 'poly void', 'plg void', 'text', 'cell', 
        'Measurement', 'Port', 'Port Instance', 'Port Instance Port', 'Edge Port', 'component', 'CS', 'S3D', 'ViaGroup'
        '''
        
        if self._objectDict is None:
            objs = self.layout.oEditor.FindObjects('Type', self.type)
            if objs:
                self._objectDict  = ComplexDict(dict([(p,self.primitiveClass(p,layout=self.layout)) for p in objs]))
            else:
                self._objectDict  = ComplexDict()
                
        return self._objectDict
    
    @property
    def All(self):
        return self.ObjectDict.Values
    
    @property
    def Count(self):
        return len(self)
    
    @property
    def Type(self):
        return self.type
    
    @property
    def NameList(self):
        return list(self.ObjectDict.Keys)
    
    def filter(self, func):
        return dict(filter(func,self.ObjectDict.items()))
    

    def filterName(self, func):
        if isinstance(func, str):
            return list(filter(lambda x:re.match(func+"$", x, re.I),self.NameList))
        else:
            return list(filter(func,self.NameList))

    def filterByLayer(self,layerName):
        '''
        type: [] or Poly Object
        '''
        objsLayerAll = self.layout.oEditor.FindObjects('Layer',self.layout.layers.getRealLayername(layerName))
        return self.filter(lambda kv: kv[0] in objsLayerAll)
        
        
#         objsLayer = []
#         objsLayerAll = self.layout.oEditor.FindObjects('Layer',self.layout.layers.getRealLayername(layerName))
#         objsLayerNames = list(filter(lambda x:x in objsLayerAll, self.NameList))
#         return self[objsLayerNames]
    
        
    def refresh(self):
        if self._objectDict:
            self._objectDict.clear()
#             del self._objectDict
            
        self._objectDict  = None

        
    def push(self,name,obj=None):
        if self._objectDict is None:
            self._objectDict = ComplexDict()
        if obj:
            self._objectDict.update(name,obj)
        else:
            self._objectDict.update(name,self.primitiveClass(name,layout=self.layout))
    
    def pop(self,name):
        if self._objectDict is None:
            return
        del self._objectDict[name]
        
    def get(self, key):
        return self.getByName(key)

    def getByName(self,name):
        '''
        Args:
            name (str): component name in layout, ingor case
        Returns:
            (Component): Component object of name
             
        Raises:
            name not found on layout
        '''
        if name in self.ObjectDict:
            return self.ObjectDict[name]
        
        log.info("not found component: %s"%name)
        return None
    
    def getUniqueName(self,prefix=""):
        
        if prefix is None:
            prefix = "%s_"%self.type
            
        for i in range(1,100000):
            name = "%s%s"%(prefix,i)
            names = self.NameList
            if name in names:
                i += 1
            else:
                break
        return name

class Objects3DL(Primitives):

    def __init__(self,layout=None,types=".*"):
        super(Objects3DL,self).__init__(layout, type=types,primitiveClass=None)

    @property
    def ObjectDict(self):
        '''
        alway return new object list.
        
        FindObjects
        "Type" to search by object type.
        Valid <value> strings for this type include: 'pin', 'via', 'rect', 'arc', 'line', 'poly', 
        'plg', 'circle void', 'line void', 'rect void', 'poly void', 'plg void', 'text', 'cell', 
        'Measurement', 'Port', 'Port Instance', 'Port Instance Port', 'Edge Port', 'component', 'CS', 'S3D', 'ViaGroup'
        '''
        types = []
        if isinstance(self.type, str):
            types = [self.type]
        elif isinstance(self.type,(list,tuple)):
            types = list(self.type)
        else:
            log.exception("type error %s"%str(self.type))
        
        objTypes = []
        for t in types:
            for t2 in self.layout.primitiveTypes:
                if re.match(r"^%s$"%t,t2,re.I):
                    objTypes.append(t2)

        if len(objTypes)<1:
            self._objectDict = ComplexDict()
            return self._objectDict
        
        objectPrimitives = None
        for typ in objTypes:
            try:
                if objectPrimitives is None:
                    objectPrimitives = self.layout[typ+"s"]
                else:
                    objectPrimitives += self.layout[typ+"s"]
            except Exception:
                log.exception("%s not in layout deifiniton"%typ)

        if objectPrimitives is None:
            self._objectDict = ComplexDict()
            return self._objectDict

        self._objectDict = objectPrimitives._objectDict
        return self._objectDict
