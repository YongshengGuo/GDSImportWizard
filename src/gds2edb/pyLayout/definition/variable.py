#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2023-04-09

'''
变量管理模块
Examples:
    Add variable to active design
    >>> varbs = Variable(layout=layout)
    >>> varbs.add("len","10in")
    >>> varbs["len"].Value
    10in
    
    chang varbs["len"] Value
    >>> varbs["len"] = "20in"
    >>> varbs["len"].Value
    20in
    
    varbs["len"] could be convert to str implicitly 
    >>> log.debug(varbs["len"])
    20in
    
    if variable start with $, will add as project variable
    >>> varbs.add("$len2","5in")
    >>> log.debug(varbs["len"])
    5in
    
Raises:
    key error: varbs["len2"]variable name not in Project or design
        
'''

import re
from ..common.complexDict import ComplexDict
from ..common.common import log
from .definition import Definitions,Definition
from ..common.arrayStruct import ArrayStruct

class Variable(Definition):
    '''_summary_
    '''

    def __init__(self,name = None,layout=None):
        '''Initialize Component object
        Args:
            compName (str): refdes of component in PCB, optional
            layout (PyLayout): PyLayout object, optional
        '''
        super(self.__class__,self).__init__(name,type="Variable",layout=layout)

    def __setattr__(self, key, value):
        if key in ["layout","name","_info","parsed","type","maps"]:
            object.__setattr__(self,key,value)
        else:
            self.set(value)

    def __str__(self):
        return str(self.Value)

    def __repr__(self):
        return "Variable Object %s: %s"%(self.name,self.Value)
            

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        maps = self.maps
        _array = ArrayStruct([])
        self._info.update("Name",self.name)
        self._info.update("Array", _array)

        maps.update({"Value":{
            "Key":"self",
            "Get":lambda s: s.get(),
            "Set":lambda s,v: s.set(v)
            }})
        
        maps.update({"EvalValue":{
            "Key":"self",
            "Get":lambda s: s.getEvalValue()
            }})
        
        maps.update({"SIValue":{
            "Key":"self",
            "Get":lambda s: s.getSIValue()
            }})
        
        self._info.setMaps(maps)
        self._info.update("self", self)
        self.parsed = True
    
    def getEvalValue(self):
        '''
        Evaluated Value as string
        '''
        var = self.name
        obj = self.layout.oProject if var.startswith("$") else self.layout.oDesign
        return obj.GetPropEvaluatedValue("Variables/%s"%var)
        
    def getSIValue(self):
        '''
        Evaluated Value as string
        '''
        var = self.name
        obj = self.layout.oProject if var.startswith("$") else self.layout.oDesign
        return obj.GetPropSIValue("Variables/%s"%var)
    
    def set(self,val):    
        var = self.name
        obj = self.layout.oProject if var.startswith("$") else self.layout.oDesign
        obj.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:%s"%("ProjectVariableTab" if var.startswith("$") else "LocalVariableTab"),
                    [
                        "NAME:PropServers", 
                        "%s"%("ProjectVariables" if var.startswith("$") else "LocalVariables")
                    ],
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:%s"%var,
                            "Value:=", "%s"%str(val)
                        ]
                    ]
                ]
            ])
        
    def get(self):
        var = self.name
        obj = self.layout.oProject if var.startswith("$") else self.layout.oDesign
        val = obj.GetVariableValue(var)
        return val
    
    def delete(self):

        obj = self.layout.oProject if self.name.startswith("$") else self.layout.oDesign
        tabName = "ProjectVariableTab" if self.name.startswith("$") else "LocalVariableTab"
        propServers = "ProjectVariables" if self.name.startswith("$") else "LocalVariables"
        obj.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:%s"%tabName,
                    [
                        "NAME:PropServers", 
                        propServers
                    ],
                    [
                        "NAME:DeletedProps", 
                        self.name
                    ]
                ]
            ])
        
class Variables(Definitions):


    def __init__(self,layout=None):
        '''Initialize Variables object
        '''
        super(Variables,self).__init__(layout, type="Variable",definitionCalss=Variable)


    def __setitem__(self, key, value):
        self[key].Value = value
        
    def  __setattr__(self, key, value):
        if key in ["layout","definitionCalss","type","_definitionDict"]:
            object.__setattr__(self,key,value)
        elif key in self.DefinitionDict:
            self[key].Value = value
        else:
            log.error("%s not a variable"%key)
            
    @property
    def DefinitionDict(self):
        if self._definitionDict is None:
            ProjectVars,designVars = self.layout.oProject.GetVariables(),self.layout.oDesign.GetVariables()
            self._definitionDict  = ComplexDict(dict([(var,Variable(var,layout=self.layout)) for var in ProjectVars+designVars]))
            self._definitionDict.setMaps(dict([(re.sub(r'[$]','_',var),var) for var in ProjectVars]))
        return self._definitionDict
    

    def add(self,var,val = 0):
        
        obj = self.layout.oProject if var.startswith("$") else self.layout.oDesign
        if var in self.layout.oProject.GetVariables() + self.layout.oDesign.GetVariables():
            log.debug("change value for exist variable: %s"%var)
            obj.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:%s"%("ProjectVariableTab" if var.startswith("$") else "LocalVariableTab"),
                        [
                            "NAME:PropServers", 
                            "%s"%("ProjectVariables" if var.startswith("$") else "LocalVariables")
                        ],
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:%s"%var,
                                "Value:=", "%s"%val
                            ]
                        ]
                    ]
                ])
            
            
            
        else:
            log.info("add new variable: %s"%var)
            obj.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:%s"%("ProjectVariableTab" if var.startswith("$") else "LocalVariableTab"),
                        [
                            "NAME:PropServers", 
                            "%s"%("ProjectVariables" if var.startswith("$") else "LocalVariables")
                        ],
                        [
                            "NAME:NewProps",
                            [
                                "NAME:%s"%var,
                                "PropType:=", "VariableProp",
                                "UserDef:=", True,
                                "Value:=", "%s"%val
                            ]
                        ]
                    ]
                ])
        self._definitionDict = None
        return self.DefinitionDict[var]
        
    
    def evalExpression(self,expression = 0):
        if "Freq" in expression:
            log.info("Eval the '%s' at frequency 1Ghz"%expression)
            expression = expression.replace("Freq","1e9")
        
        var = self.add("EvalExpressionValue", expression)
        return var.SIValue
    
    def removeUnusedVariables(self):
        '''
        Remove the unused variables in project
        '''
        ProjectVars,designVars = self.layout.oProject.GetVariables(),self.layout.oDesign.GetVariables()
        self.layout.oProject.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:ProjectVariableTab",
                    [
                        "NAME:PropServers", 
                        "ProjectVariables"
                    ],
                    [
                        "NAME:DeletedProps", 
                    ] + list(ProjectVars)
                ]
            ])
    
        self.layout.oDesign.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:LocalVariableTab",
                    [
                        "NAME:PropServers", 
                        "LocalVariables"
                    ],
                    [
                        "NAME:DeletedProps", 
                    ] + list(designVars)
                ]
            ])
    
    def setByDict(self,varDict):
        for k,v in varDict.items():
            if k in self:
                self[k] = v
                log.info("Variable %s set to %s"%(k,v))
            else:
                log.info("Variable not found: %s"%k)
        
        
        
        
        