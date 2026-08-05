#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20250509

import re

try:
    from collections import Iterable
except:
    from collections.abc import Iterable
import json

from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,tuple2list


class SolutionData(ComplexDict):
    
    def __init__(self,name = None,solution = None):
        
        super(self.__class__,self).__init__()
        self.update("name", name)
        self.update("solution", solution)
        self.update("DataObj", None)
        self.update("parsed", False)
        if name:
            self.parse()
    

    def __del__(self):
        self.release()                
    
    def parse(self,force = False):
        
        if self.parsed and not force:
            return

        oModule = self.solution.layout.oDesign.GetModule("ReportSetup")
        
        variablesKey = []
        for v in self.solution.layout.oProject.GetVariables() + self.solution.layout.oDesign.GetOutputVariables():
            variablesKey.append("%s:="%v)
            variablesKey.append(["All"])
        
        try:
            DataObjs = oModule.GetSolutionDataPerVariation("Standard", self.solution.name,
                ["NAME:Context","SimValueContext:=", self.solution.SimValueContext],
                ["Index:=", ["All"] ] + variablesKey,self.name)
        except:
            log.exception("Error when get expression value: %s"%self.name)
        
        self.update("DataObj", DataObjs[0])
        self.update("XName", DataObjs[0].GetSweepNames()[0])
        self.update("YName", DataObjs[0].GetDataExpressions()[0])
        self.update("X", list(DataObjs[0].GetSweepValues(self.XName,True)))
        self.update("Y", list(DataObjs[0].GetRealDataValues(self.name, True))) # SI unit
        self.update("YUnit", DataObjs[0].GetDataUnits(self.name))
        self.update("XUnit", DataObjs[0].GetSweepUnits(DataObjs[0].GetSweepNames()[0]))
        self.parsed = True
    
    def toDict(self):
        """
        dataDict->{Datas:[x,ys list],Header:[data lables],"key":VariationKey}
        first of Header element is X values, others is Y values
        """
        datas = {
            "Name":self.name,
            "X":self.X,
            "Y":self.Y
            }
        return datas

    def writeJson(self,path=None):
        print("export Json file %s"%path)
        with open(path,"w+") as f:
            json.dump(self.toDict(),f,indent=4, separators=(',', ': '))
            f.close()
            

    def release(self):
        
        if self.DataObj:
            self.DataObj.ReleaseData()        
        
        

class Solution(object):
    """
    DCSolution Object
    """

    def __init__(self,solutionName = None,type=None,layout = None):
        self.layout = layout
        self.name = solutionName
        self._type = type
        self._quantitys = None
            
    def __getitem__(self, key):
        
        if isinstance(key, str):
            return self.getData(key)

        if isinstance(key,Iterable):
            return [self[i] for i in list(key)]

        raise Exception("not found %s: %s"%(self.type,key))
        
    def __repr__(self):
        return "%s Solution Objects: %s"%(self.type,self.name)
    
    @property
    def Type(self):
        return self._type

    @property
    def SimValueContext(self):
        if self.Type == "Transient":
            return [1,0,2,0,False,False,-1,1,0,1,1,"",0,0,"NUMLEVELS",False,"0"]
        elif self.Type == "DC":
            return [9,0,2,0,False,False,-1,1,0,1,1,"",0,0] 
        else:
            log.exception("Solution type not support： %s"%str(self.Type))

            
    @property
    def QuantityList(self):
        if self._quantitys == None:
            oModule = self.layout.oDesign.GetModule("ReportSetup")
            solutionName = self.name or self.layout.DefaultSolution
            self._quantitys = oModule.GetAllQuantities("Standard", "Rectangular Plot", solutionName, ["Index:=", ["All"]], "Voltage")
        return self._quantitys
    
    def getData(self,expression):
        try:
            obj = SolutionData(expression,self)
            return obj
        except:
            log.info("%s definition maybe error, or the %s not be solved"%(expression,self.name))
            return None

#     def getType(self):
#         oModule = self.layout.oDesign.GetModule("SimSetup")
#         setupData = oModule.GetSetupData(setup)
#         if self.getSetupValue(setupData, "TransientData:="):
#             typ = "Transient"
#         elif self.getSetupValue(setupData, "LinearFrequencyData:="):
#             typ = "LinearNetworkAnalysis"
#         elif self.getSetupValue(setupData, "VerifEyeAnalysis:="):
#             typ = "VerifEyeAnalysis"
#         elif self.getSetupValue(setupData, "QuickEyeAnalysis:="):
#             typ = "QuickEyeAnalysis"     
#         elif self.getSetupValue(setupData, "AMIAnalysis:="):
#             typ = "AMIAnalysis"
#         else:
#             self.message("setup type not set: %s"%setup)
#             return None
#         return typ




    
# class Solutions(object):

#     def __init__(self,layout = None):
#         self.layout = layout

#     def __getitem__(self, key):
        
#         if isinstance(key, int):
#             return self.DefinitionDict[key]
        
#         if isinstance(key, slice):
#             return self.DefinitionDict[key]
        
#         if isinstance(key, str):
#             if key in self.DefinitionDict:
#                 return self.DefinitionDict[key]
#             else:
#                 #find by 正则表达式
#                 lst = [name for name in self.DefinitionDict.Keys if re.match(r"^%s$"%key,name,re.I)]
#                 if not lst:
#                     raise Exception("not found %s: %s"%(self.type,key))
#                 else:
#                     #如果找到多个器件（正则表达式），返回列表
#                     return self[lst]

#         if isinstance(key, (list,tuple,Iterable)):
#             return [self[i] for i in list(key)]
        
#         raise Exception("not found %s: %s"%(self.type,key))
        
            
#     def __getattr__(self,key):
#         if key in ['__get__','__set__']:
#             #just for debug run
#             return None
# #         print("%s  __getattribute__ from _info: %s"%str(self.__class__.name,key))
#         try:
#             return super(self.__class__,self).__getattribute__(key)
#         except:
#             log.debug("%s  __getattribute__ from _info: %s"%(self.__class__.__name__,key))
#             return self[key]
            
#     def __contains__(self,key):
#         return key in self.DefinitionDict
    
#     def __len__(self):
#         return len(self.DefinitionDict)
    
#     def __repr__(self):
#         return "%s Definition Objects"%(self.type)
            
            
#     @property
#     def DefinitionDict(self):
#         if self._definitionDict == None:
#             oModule = oDesign.GetModule("ReportSetup")
#             # oModule.GetAvailableSolutions("Standard")
            
#             self._definitionDict  = ComplexDict(dict([(name,self.Solution(name,layout=self.layout)) for name in oManager.GetNames()]))
#         return self._definitionDict
    
#     @property
#     def All(self):
#         return self.DefinitionDict.Values
    
#     @property
#     def Count(self):
#         return len(self)
    
#     @property
#     def Type(self):
#         return self.type
    
#     @property
#     def NameList(self):
#         return list(self.DefinitionDict.Keys)
    
#     def filter(self, func):
#         return dict(filter(func,self.ObjectDict.items()))
    
#     def refresh(self):
#         self._definitionDict  = None
        
#     def push(self,name):
#         self.DefinitionDict.update(name,self.definitionClass(name,layout=self.layout))
    
#     def pop(self,name):
#         del self.DefinitionDict[name]
        
        
#     def getByName(self,name):
#         '''
#         Args:
#             name (str): component name in layout, ingor case
#         Returns:
#             (Component): Component object of name
             
#         Raises:
#             name not found on layout
#         '''
#         if name in self.DefinitionDict:
#             return self.DefinitionDict[name]
        
#         log.info("not found %s: %s"%(self.type,name))
#         return None
    
#     def getUniqueName(self,prefix=""):
        
#         if prefix == None:
#             prefix = "%s_"%self.type
            
#         for i in range(1,100000):
#             name = "%s%s"%(prefix,i)
#             names = self.NameList
#             if name in names:
#                 i += 1
#             else:
#                 break
#         return name