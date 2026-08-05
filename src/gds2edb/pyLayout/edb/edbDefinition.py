#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20250516

'''_summary_
Note: "This file defines a parent class, which cannot be used independently and must be implemented through a subclass." 
'''

import re

from ..common.complexDict import ComplexDict
from ..common.common import *

try:
    _clr = initClr()
    from System import String
except:
    log.warning("CLR initialization failed in child process (likely duplicate init). Ignoring if not needed.")

# from System import String

class EdbDefinition(object):
    '''
    '''
    
    def __init__(self,obj,type,edbApp=None):
        '''Initialize Pin object
        Args:
            name (str): Via name in edbApp
            edbApp (PyedbApp): PyedbApp object, optional
        '''

        self.edbApp = edbApp
        if isinstance(obj, EdbDefinition):
            self.obj = obj.obj
        elif isinstance(obj, int): #ID
            self.obj = self.edbApp.findObjById(obj)
        else:
            self.obj = obj
        self.type = type
        
        self._info = ComplexDict()
        self.maps = {}
        self.parsed = False

    def __getitem__(self, key):
        """
        key: str
        """
        self.parse()
        
        #for multi-level key
        keyList = re.split(r"[\\/]", key,maxsplit = 1)
        keyList = list(filter(lambda k:k.strip(),keyList)) #filter empty key
        if len(keyList)>1:
            return self[keyList[0]][keyList[1]]

        if key in self._info:
            return self._info[key]
        else:
            log.exception("key error for %s: %s"%(self.type,key))       
        

    def __setitem__(self, key,value):
        self.parse()
        
        #for multi-level key
        keyList = re.split(r"[\\/]", key,maxsplit = 1)
        keyList = list(filter(lambda k:k.strip(),keyList)) #filter empty key
        if len(keyList)>1:
            self[keyList[0]][keyList[1]] = value
            return

        if key in self._info:
            self._info[key] = value
        else:
            log.exception("key error for %S: %s"%(self.type,key))       
        

    def __getattr__(self,key):

        if key in ["edbApp","obj","_info","parsed","type","maps"]:
            return object.__getattribute__(self,key)
        elif key in self.Info:
            return self[key]
        elif hasattr(self.obj,key):
            return getattr(self.obj,key)
        else:
            log.info("__getattr__ from _dict: %s"%key)
            
    def __setattr__(self, key, value):
        if key in ["edbApp","obj","_info","parsed","type","maps"]:
            object.__setattr__(self,key,value)
        elif key in self.Info:
            self[key] = value
        elif hasattr(self.obj,key):
            setattr(self.obj,key,value)
        else:
            log.info("__getattr__ from _dict: %s"%key)

    def __contains__(self,key):
        return key in self.Props

    def __repr__(self):
        return "%s %s Object: %s"%(self.__class__.__name__ ,self.obj.GetObjType(),self.GetName())
    
    def __dir__(self):
        return list(dir(self.__class__)) + list(self.__dict__.keys()) + list(self.Props)


    @property
    def Props(self):
        propKeys = list(self.Info.Keys)
        propKeys += list(dir(self.obj))
        if self.Info.maps:
            propKeys += self.Info.maps.keys()
    
        return propKeys

    @property
    def Info(self):
        self.parse()
        return self._info
    
        
    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return

        maps = {
            "Name":{"Key":"self","Get":lambda s:s.GetName()},
            "ID":{"Key":"self","Get":lambda s:s.obj.GetId()},
            "ObjType":{"Key":"self","Get":lambda s:s.obj.GetObjType().ToString()},
        }

        self.maps.update(maps)
        self._info.update("self", self)
        self._info.setMaps(self.maps)
        self.parsed = True

    def getViaName(self):
        if self.IsLayoutPin():
            return "%s-%s"%(self.GetComponent().GetName(),self.obj.GetName())
        else:
            name = ""
            if isIronpython:
                val = _clr.StrongBox[str]()
                rst = self.GetProductProperty(self.edbApp.Edb.ProductId.Designer, 11, val)
                if rst:
                    name = val.Value
            else:
                val = String("")
                #edbApp.Edb.ProductId.Designer  0 Deprecated. use Hfss3DLayout instead.  
                _, name = self.GetProductProperty(self.edbApp.Edb.ProductId.Designer, 11, val)
            
            name = str(name).strip("'")
    
    #         edbApp.SetProductProperty(edbApp.Edb.ProductId.Designer, 11, name)
            return name

    def getPrimitiveName(self):
        
        
        name = ""
        if isIronpython:
            val = _clr.StrongBox[str]()
            rst = self.GetProductProperty(self.edbApp.Edb.ProductId.Designer, 1, val)
            if rst:
                name = val.Value
        else:
            val = String("")
            #edbApp.Edb.ProductId.Designer  0 Deprecated. use Hfss3DLayout instead.  
            _, name = self.GetProductProperty(self.edbApp.Edb.ProductId.Designer, 1, val)
            
        name = str(name).strip("'")
        PrimitiveType = str(self.GetPrimitiveType()).lower()
        if name == "":
            if PrimitiveType == "path":
                ptype = "line"
            elif PrimitiveType == "rectangle":
                ptype = "rect"
            elif PrimitiveType == "polygon":
                ptype = "poly"
            elif PrimitiveType == "bondwire":
                ptype = "bwr"
            else:
                ptype = PrimitiveType
                
            name = "{}__{}".format(ptype, self.GetId())
    #             self.edbApp.SetProductProperty(self._pedb._edb.ProductId.Designer, 1, name)
        return name


    def GetName(self):
        if self.GetObjType() == self.edbApp.Edb.Cell.LayoutObjType.Primitive:
            return self.getPrimitiveName()
        elif self.GetObjType() == self.edbApp.Edb.Cell.LayoutObjType.PadstackInstance:
            return self.getViaName()
        else:
            try:
                return self.obj.GetName()
            except:
                return "UnKnown"


    def getPhysicallyConnected(self):
        '''
        only for primitive and via
        Issue to get all connected objects....
        '''
#         log.exception("Issue to get all connected objects....") #not fixed
        layoutInst = self.edbApp.layout.GetLayoutInstance()
        layoutObjInst = layoutInst.GetLayoutObjInstance(self.obj, None)
        objs = [EdbDefinition(obj.GetLayoutObj(),type="Connectable",edbApp=self.edbApp) for obj in layoutInst.GetConnectedObjects(layoutObjInst).Items]
#         objs = [o for o in objs if o.ObjType in ["Primitive","PadstackInstance"]]
        objs2 = []
        for obj in objs:
            typ = obj.ObjType
            if typ == "Primitive" and not obj.IsVoid():
                objs2.append(obj)
            elif typ == "PadstackInstance":
                objs2.append(obj)
            else:
                pass
                
        return objs2 + [self]
    
    
class EdbDefinitions(object):

    def __init__(self,edbApp = None,type=None,definitionClass = None):
        self.edbApp = edbApp
        self.definitionClass = definitionClass
        self.type = type
        self._definitionDict = None
            
    def __getitem__(self, key):
        
        if isinstance(key, int):
            names = list(self.DefinitionDict.Keys)
            if key < 0 or key >= len(names):
                raise IndexError("index out of range: %s" % key)
            return self.DefinitionDict[names[key]]
        
        if isinstance(key, slice):
            names = list(self.DefinitionDict.Keys)[key]
            return [self.DefinitionDict[name] for name in names]
        
        if isinstance(key, str):
            if key in self.DefinitionDict:
                return self.DefinitionDict[key]
            else:
                #find by 正则表达式
                lst = [name for name in self.DefinitionDict.Keys if re.match(r"^%s$"%key,name,re.I)]
                if not lst:
                    raise Exception("not found %s: %s"%(self.type,key))
                else:
                    #如果找到多个器件（正则表达式），返回列表
                    return self[lst]

        if isinstance(key, (list,tuple,Iterable)):
            return [self[i] for i in list(key)]
        
        if "Ansys.Ansoft.Edb.Cell" in str(key): #for edb object
            if hasattr(key, "GetName"):
                return self[key.GetName()]

        raise Exception("not found %s: %s"%(self.type,key))
        
            
    def __contains__(self,key):
        if isinstance(key, str):
            return key in self.DefinitionDict
        else:
            try:
                key2 = key.GetName()
                return key2 in self.DefinitionDict
            except:
                return False
    
    def __len__(self):
        return len(self.DefinitionDict)
    
    def __repr__(self):
        return "%s Definition Objects"%(self.type+"s")
            
    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            if hasattr(self.edbApp.layout,self.type):
                #self.type: CellInstances DifferentialPairs  EDBHandle Groups NetClasses Nets PadstackInstances  PinGroups  Primitives Terminals VoltageRegulators
                objs = getattr(self.edbApp.layout,self.type)
                self._definitionDict = {}
                self._definitionDict  = ComplexDict(dict([(p.GetName(),self.definitionClass(p,self.edbApp)) for p in objs]))
            else:
                self._definitionDict = {}
        return self._definitionDict
    @property
    def All(self):
        return self.DefinitionDict.Values
    
    @property
    def Count(self):
        return len(self)
    
    @property
    def Type(self):
        return self.type
    
    @property
    def NameList(self):
        return list(self.DefinitionDict.Keys)
    
    def filter(self, func):
        return dict(filter(func,self.DefinitionDict.items()))
    
    def refresh(self):
        self._definitionDict  = None
        
    def push(self,name):
        self.DefinitionDict.update(name,self.definitionClass(name,edbApp=self.edbApp))
    
    def pop(self,name):
        del self.DefinitionDict[name]
        
        
    def getByName(self,name):
        '''
        Args:
            name (str): component name in edbApp, ingor case
        Returns:
            (Component): Component object of name
             
        Raises:
            name not found on edbApp
        '''
        if name in self.DefinitionDict:
            return self.DefinitionDict[name]
        
        log.info("not found %s: %s"%(self.type,name))
        return None
    
    def getUniqueName(self,prefix=""):
        
        if prefix == None:
            prefix = "%s_"%self.type
            
        for i in range(1,100000):
            name = "%s%s"%(prefix,i)
            names = self.NameList
            if name in names:
                i += 1
            else:
                break
        return name
        