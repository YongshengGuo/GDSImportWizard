#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230828


'''
used to get padstak information

'''
import os
import re

from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,tuple2list
from .definition import Definitions,Definition

class ModelDef(Definition):
    '''

    Args:
    '''
    
    def __init__(self, name = None,array = None,layout = None):
        super(self.__class__,self).__init__(name,type="Model",layout=layout)


class ModelDefs(Definitions):
    

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Model",definitionCalss=ModelDef)

        

    def addSnpModel(self,path,name=None,pinMap=None):
        
        if not name:
            name = os.path.split(path)[-1] 
            name = re.sub("[\.\s#]","_",name)
        
        if name in self.NameList:
            log.info("%s exist in model definition,skip"%name)
            return
        
        try:
            portCount = int(re.sub(r"[A-Za-z]","",path.split(".")[-1]))
        except:
            log.exception(r"not a vaild snp file: %s"%path)
            

        
        nodes,pinNames = [],[]
        if pinMap:
            nodes,pinNames = pinMap
        if not nodes:
            nodes = ["Port%s"%(i+1) for i in range(portCount)] #["Port1","Port2"]

        oDefinitionManager = self.layout.oProject.GetDefinitionManager()
        oModelManager = oDefinitionManager.GetManager("Model")
        
        ary = ArrayStruct(tuple2list(hfss3DLParameters.model_snp)).copy()
        ary.Array[0] = "NAME:%s"%name
        ary.Name = name
        ary.ModelType = "nport"
        ary.filename = path
        ary.numberofports = portCount
        ary.PortNames = nodes #["Port1","Port2"]
 

        oModelManager.Add(ary.Array)
        self.push(name)
        self[name].parse()    
        return self[name]
        
    def addSpiceModel(self,path,name=None):
        
        if not name:
            name = os.path.split(path)[-1] 
            name = re.sub("[\.\s#]","_",name)
        
        if name in self.NameList:
            log.info("%s exist in model definition,skip"%name)
            return
        
        oDefinitionManager = self.layout.oProject.GetDefinitionManager()
        oModelManager = oDefinitionManager.GetManager("Model")


        oModelManager.Add(["NAME:%s"%name,"Name:=", name,"ModelType:=", "dcirspice",
                           "filename:=", path,"modelname:=", name]) 
            
        self.push(name)
        self[name].parse()
        return self[name]
