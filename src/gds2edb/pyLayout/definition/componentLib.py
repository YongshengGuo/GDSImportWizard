#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230828


'''
used to get padstak information

'''

import os,re
from .definition import Definitions,Definition
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common import hfss3DLParameters
from ..common.common import log,tuple2list

class ComponentDef(Definition):
    '''

    Args:
    '''
    
    def __init__(self, name = None,array = None,layout = None):
        super(self.__class__,self).__init__(name,type="Component",layout=layout)
    

    def rename(self,newName):
        self.Info.Array[0] = "NAME:%s"%newName
        self.update()
        self.layout.ComponentDefs.refresh()
        return
    
    

class ComponentDefs(Definitions):
    

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Component",definitionCalss=ComponentDef)

    def add(self,name):
        oDefinitionManager = self.layout.oProject.GetDefinitionManager()
        oComponentManager = oDefinitionManager.GetManager("Component")
        oComponentManager.Add(["NAME:%s"%name])
        self.push(name)
        
#     def addSNPDef(self,path,name=None):
        #"CosimulatorType:=", 102 for spice model
    def addSNPDef(self,part,modelName,pinMap=None):
#         if not name:
#             name = os.path.split(path)[-1] 
#         name = re.sub("[\.\s#]","_",name)
        nodes,pinNames = [],[]
        if pinMap:
            nodes,pinNames = pinMap
        if not nodes:
            nodes = self.layout.ModelDefs[modelName].PortNames
        if not pinNames:
            comps = self.layout.Components.getComponentsByPart(part)
            if comps:
                pinNames = comps[0].ShortPinNames
        
        oDefinitionManager = self.layout.oProject.GetDefinitionManager()
        oComponentManager = oDefinitionManager.GetManager("Component")
        
        if modelName in self.NameList:
            log.info("%s exist in model definition,skip."%modelName)
        else:
            ary = ArrayStruct(tuple2list(hfss3DLParameters.componentLib_snp)).copy()
            ary.Array[0] = "NAME:%s"%modelName
            ary.Info.DataSource = self.layout.ModelDefs[modelName].filename
            ary.Info.NumTerminals = len(nodes)
#             ary.ModelDefName = modelName
#             ary.CosimDefinitions.CosimDefinition.CosimDefName = modelName
            ary.CosimDefinitions.CosimDefinition.ModelDefinitionName = modelName
#             ary.CosimDefinitions.DefaultCosim = modelName
            oComponentManager.Add(ary.Array)
            self.push(modelName)
            self[modelName].parse()
        
        
        if not part:
            return self[modelName]
        
        #---AddSolverOnDemandModel
        oComponentManager.AddSolverOnDemandModel(part, 
            [
                "NAME:CosimDefinition",
                "CosimulatorType:="    , 102,
                "CosimDefName:="    , modelName,
                "IsDefinition:="    , True,
                "Connect:="        , True,
                "ModelDefinitionName:="   , modelName,
                "ShowRefPin2:="        , 2,
                "LenPropName:="        , ""
            ])

        
        #---add part model
#         oDefinitionManager = self.layout.oProject.GetDefinitionManager()
#         oComponentManager = oDefinitionManager.GetManager("Component")
        
        ary = ArrayStruct(tuple2list(hfss3DLParameters.componentLib_snp)).copy()
        ary.Array[0] = "NAME:%s"%part
        ary.Refbase = "U",
        ary.Info.DataSource = self.layout.ModelDefs[modelName].filename
        ary.Info.Type = 0
        ary.Info.Symbol = part
        ary.Info.NumTerminals = len(nodes)
        ary.ModSinceLib = True
        ary.CompExtID = 1
        ary.ModelDefName = modelName
        ary.CosimDefinitions.CosimDefinition.CosimDefName = modelName
        ary.CosimDefinitions.CosimDefinition.ModelDefinitionName = modelName
        ary.CosimDefinitions.DefaultCosim = modelName
        for i in range(len(pinNames)):
            ary.append("Terminal:=")
            ary.append([pinNames[i],pinNames[i],"A",False,2+i,1,"","Electrical","0"])
        return self[modelName]
#         <TerminalInfo>:
#         
#         Array(<string>, // symbol pin
#         
#         <string> // footprint pin
#         
#         <string >, // gate name
#         
#         <bool>, // shared
#         
#         <int>, // equivalence number
#         
#         <int>, // what to do if unconnected: flag as error:0, ignore:1
#         
#         <string>, // description
#         
#         <Nature>)

        
    

    def addSpiceDef(self,name):
        if name in self.NameList:
            log.info("%s exist in model definition,skip"%name)
            return
        
        oDefinitionManager = self.layout.oProject.GetDefinitionManager()
        oComponentManager = oDefinitionManager.GetManager("Component")
        #"CosimulatorType:=", 112 for spice model
        
        ary = ["NAME:%s"%name,["NAME:CosimDefinitions",["NAME:CosimDefinition","CosimulatorType:=", 112,"CosimDefName:=", "Default",
                 "IsDefinition:=", True,"Connect:=", True,"ModelDefinitionName:=", name],
                "DefaultCosim:=", "Default"]]
        
        oComponentManager.Add(ary)
        self.push(name)
        self[name].parse()
        return self[name]
            