#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230410



'''Net Object quick access

Examples:
    Get Net using full Net Name
    
    >>> Net["DQ0"]
    Net object
    
    Get Net using regular
    
    >>> Net["DQ\d+"]
    Net object list

    
    Get Net using regular
    
    >>> Net["DQ\d+"]
    Net object list
    
    Get Net using bus
    
    >>> Net["DQ[7:0]"]
    Net object list
    
    Get Net using bus and regular
    
    >>> Net["CH\d+_DQ[7:0]"]
    Net object list
    
'''

import time
import re
from ..common.common import log
from ..common.unit import Unit
from ..common.complexDict import ComplexDict
from ..common.arrayStruct import ArrayStruct
from .definition import Definitions,Definition
from ..primitive.primitive import Primitive

class Net(Definition):
    '''_summary_
    '''
    def __init__(self, name = None,layout = None):
        super(self.__class__,self).__init__(name,type="Net",layout=layout)
    
    @property
    def IsPowerNet(self):
        if self.name in self.layout.nets.PowerNetNames:
            return True
        else:
            return False
    
    @property
    def IsNaming(self):
        return not re.match(r"(^N[^a-z]+)|(^UNNAMED.*)$",self.name,re.I)
    
    
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
        
        maps.update({"Objects":{
            "Key":"self",
            "Get":lambda s:s._getObjects()
            }})
            
        self._info.setMaps(maps)
        self._info.update("self", self)
        self.parsed = True
    
    def _getObjects(self):
        #Note: bad values for components 
        
        objectCDicts = ComplexDict()
        maps = {}
        objectCDicts.update("Net", self.name)
        objectCDicts.update("self", self)
        for type in self.layout.primitiveTypes:
            objectCDicts.update(type+"s",type)
            fxDict = {
                "Key":("self",type+"s"),
                "Get":lambda s,k:s.getConnectedObjs(k)
                }
            maps.update({type+"s":fxDict})
        
        objectCDicts.update("All","*")
        maps.update({"All":{
            "Key":("self",type+"s"),
            "Get":lambda s,k:s.getConnectedObjs(k)
            }})

        objectCDicts.setMaps(maps)
        return objectCDicts
    

    def getConnectedPins(self):
        return self.getConnectedObjs('pin')

    
    def getConnectedComponnets(self):
#         return self.getConnectedObjs('component') #return wrong values
        pins = self.getConnectedObjs('pin')
        compList = []
        for name in pins:
            pinObj = self.layout.Pins[name]
            if pinObj.CompName and pinObj.CompName not in compList:
                compList.append(pinObj.CompName)
        return compList

    
    def getConnectedPorts(self):
        return self.getConnectedObjs('Port')

    
    def getConnectedObjs(self,typ = "*"):
        return self.layout.getObjectsbyNet(self.Name,typ)
    
    def getLength(self,unit = None):
        '''
        powerNet: return None
        shape with no lines: return None
        have lines: return total length of lines
        unit: the unit of return value
        '''
        if self.IsPowerNet:
            return None
        
        lines = self.getConnectedObjs('line')
        if not lines:
            return None

        segLens = [Unit(self.layout.lines[o].TotalLength) for o in lines]
        if unit is None:
            return sum(segLens)
        else:
            return Unit(sum(segLens))[unit]

    def createPortOnNet(self,comps = None,ignorRLC = True):

        if comps is None:
            compNames = self.getConnectedComponnets()
            if ignorRLC:
                compNames = [c for c in compNames if self.layout.Components[c].Type not in ["Resistor","Inductor","Capacitor"]]
         
        elif isinstance(comps, str):
            compNames = [comps]
         
        else:
            #comps is list 
            compNames= list(comps)

        self.layout.oEditor.CreatePortsOnComponentsByNet(
            ["NAME:Components"]+compNames,["NAME:Nets",self.Name], "Port", "0", "0", "0")

    def backdrill(self,stub=None):
        
        if self.IsPowerNet:
            log.info("Skip Backdrill on power/GND net : %s"%self.name)
            return
            
        log.info("Backdrill net : %s"%self.name)
        
        viaNames = self.getConnectedObjs("via")
        for name in viaNames:
            self.layout.Vias[name].backdrill(stub = stub)
            
        pinNames = self.getConnectedObjs("pin")
        for name in pinNames:
            self.layout.Pins[name].backdrill(stub = stub)
            
    def rename(self,newNet):
        
        if newNet == self.Name:
            return
        
        objs = self.layout.oEditor.FindObjects('Net', self.Name)

        if len(objs)==0:
            log.info("not found objects on net %s"%self.Name)
            return
        
        self.layout.oEditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:BaseElementTab",
                    [
                        "NAME:PropServers"
                    ] + list(objs),
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Net",
                            "Value:=", newNet
                        ]
                    ]
                ]
            ])
    
    
    def getNetConnected(self):
        #SelectNetConnected
        
        obj = None
        objs = self.getConnectedObjs("poly")
        if objs:
            obj = objs[0]
        
        if not obj:
            objs = self.getConnectedObjs("line")
            if objs:
                obj = objs[0]
        
        if not obj:
            objs = self.getConnectedObjs("via")
            if objs:
                obj = objs[0]
                
        if not obj:
            objs = self.getConnectedObjs("pin")
            if objs:
                obj = objs[0]
        
        if not obj:
            log.warning("Net not found any objects: %s"%self.Name)
            return []
        
        
        self.layout.oEditor.UnselectAll()
        self.layout.oEditor.SelectNetConnected(
            [
                "NAME:elements", 
                obj
            ])
        objs2 = self.layout.oEditor.GetSelections()
        self.layout.oEditor.UnselectAll()
        return objs2
    
    
    def getPhysicallyConnected(self):
        #SelectNetConnected
        
        obj = None
        objs = self.getConnectedObjs("poly")
        if objs:
            obj = objs[0]
        
        if not obj:
            objs = self.getConnectedObjs("line")
            if objs:
                obj = objs[0]
        
        if not obj:
            objs = self.getConnectedObjs("via")
            if objs:
                obj = objs[0]
                
        if not obj:
            objs = self.getConnectedObjs("pin")
            if objs:
                obj = objs[0]
        
        if not obj:
            log.warning("Net not found any objects: %s"%self.Name)
            return []
        
        
        self.layout.oEditor.UnselectAll()
        self.layout.oEditor.SelectPhysicallyConnected(
            [
                "NAME:elements", 
                obj
            ])
        objs2 = self.layout.oEditor.GetSelections()
        self.layout.oEditor.UnselectAll()
        return objs2
    

    def disjoint(self):
        
        objs1 = self.getNetConnected()
        objs2 = self.getPhysicallyConnected()
        objs3 = list(set(objs1)-set(objs2))
        if not objs3:
            log.info("disjoint not found on net %s"%(self.name))
            return
        
        objList = [list(set(objs1)&set(objs2))]
        while len(objs3):
            objName = objs3.pop()
            objs4 = Primitive(objName,self.layout).getPhysicallyConnected()
            objList.append(list(objs4))
            objs3 = list(set(objs3)-set(objs4))
            
        objList.sort(key=len,reverse=True)
        log.info("%s will splite to %s part"%(self.name,len(objList)))
        
        i =1
        newName = self.name
        
        for each in objList[1:]:
#             each2 = [x for x in each if "Net" in Primitive(x,self.layout)]
            newName = "%s_%s"%(self.name,i)
            i += 1
            log.info("Rename %s to new net %s"%(str(each),newName))
            self.layout.oEditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:BaseElementTab",
                        [
                            "NAME:PropServers"
                        ]+each,
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:Net",
                                "Value:=", newName
                            ]
                        ]
                    ]
                ])
            time.sleep(1) #delay must>1s,bug for 2025R2
        self.layout.Nets.refresh() 
    
    
    def addToPwrGndNets(self):
        
        netList = self.PowerNetNames
        if self.Name not in netList:
            netList = self.PowerNetNames + [self.Name]
            log.info("Add power/Ground Nets: %s"%self.Name)
            self.layout.oEditor.ModifyNetClass("<Power/Ground>", "<Power/Ground>", "",netList)
            
    def removeFromPwrGndNets(self):
        netList = self.PowerNetNames
        if  self.Name in netList:
            netList.remove(self.Name)
            log.info("Remove power/Ground Nets: %s"%self.Name)
            self.layout.oEditor.ModifyNetClass("<Power/Ground>", "<Power/Ground>", "",netList)
        else:
            pass       
        
    def delete(self):
        self.layout.oEditor.DeleteNets([self.Name])

class Nets(Definitions):

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Net",definitionCalss=Net)

#     def _getDefinitionDict(self):
#         return  ComplexDict(dict([(name,Net(name,self.layout)) for name in self.layout.oEditor.GetNetClassNets('<All>')]))

    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            self._definitionDict  = ComplexDict(dict([(name,Net(name,self.layout)) for name in self.layout.oEditor.GetNetClassNets('<All>')]))
#             self._definitionDict  = self._getDefinitionDict()
        return self._definitionDict

    @property
    def SignalNetNames(self):
        allNets = self.layout.oEditor.GetNetClassNets('<All>')
        pwrNets = self.layout.oEditor.GetNetClassNets('<Power/Ground>')
        sigNets = [net for net in allNets if net not in pwrNets]
        if "<NO-NET>" in sigNets:
            sigNets.remove("<NO-NET>")
        return sigNets
        
    @property
    def PowerNetNames(self):
        return list(self.layout.oEditor.GetNetClassNets('<Power/Ground>')) 
            
    #--- for Nets
    
    def getComponentsOnNets(self,nets,ignorRLC = True):
        
        # if isinstance(nets, str):
        #     nets = [nets]
        nets = self.getRegularNets(nets)
        if not nets: return []
        compList = self.layout.Components.NameList
        temp = []
        for net in nets:
#             compNames = self.__class__(net).CompNames
            compNames = self.DefinitionDict[net].getConnectedComponnets()
            # compList = self.layout.Components.NameList
            compNames = [c for c in compNames if c in compList]  #ignor none type
            if ignorRLC:
                compNames = [c for c in compNames if self.layout.Components[c].PartType not in ["Resistor","Inductor","Capacitor"]]
            temp += compNames
            
        return list(set(temp))
    
    def createPortsOnNets(self,nets,comps = None,ignorRLC = True):


        nets = self.layout.nets.getRegularNets(nets)
        if not nets:
            log.info("No nets found, skip to create ports")
         
        if not comps:
            compNames = self.getComponentsOnNets(nets,ignorRLC)
         
        elif isinstance(comps, str):
            compNames = [comps]
         
        else:
            compNames= comps
        
        log.info("Create port on net: %s  Compoents: %s"%(",".join(nets),",".join(compNames)))
        self.layout.oEditor.CreatePortsOnComponentsByNet(
            ["NAME:Components"]+compNames,["NAME:Nets"]+nets, "Port", "0", "0", "0")

    def getRegularNets(self,regNets):
        '''_summary_

        Args:
            regNets (str,list): regular net. if space in regNets, will split to list.
            Signals: 需要保留的Signals, 支持多个信号，例如：“net1 net2”中间空格隔开，支持正则表达试，支持[7:0]总线写法”

        Returns:
            list: netNames list of regular input
        '''
        
        if not regNets:
            return []
        
        if type(regNets) == str:
#             regNets = [regNets]
            regNets = re.split(r"[,;\s]+", regNets.strip()) #regNets.strip().split()
            
        #[7:0]
        nets = []
        for regNet in regNets:
            #support vector [15:0]
            rm = re.match(r".*\[(\d+):(\d+)\].*",regNet,re.IGNORECASE)
            if rm:
                H,L = [int(i) for i in rm.groups()[:2]]
                nets += [re.sub(r"\[(\d+:\d+)\]",str(i),regNet) for i in range(L,H+1)]
            else:
                nets.append(regNet)
                     
        regNets = nets #if len(nets)>0 else regNets
        
        
        nets = []

        for regNet in regNets:
            #add full net name with '+'
            if regNet in self.NameList:
                nets.append(regNet)
                continue
            temp = None
            if regNet.endswith("$"):
                temp = regNet[:-1]
            temp = regNet.replace("$","\$").strip()
            nets += filter(lambda x: re.match(temp+"$",x,re.IGNORECASE),self.NameList)
        return list(set(nets))
    
    def getGNDRefNet(self,netList = None):
        nets = netList if netList is not None else self.NameList
        if "GND" in nets:
            return "GND"
        if "VSS" in nets:
            return "VSS"
        if "DGND" in nets:
            return "DGND"
        if "AGND" in nets:
            return "AGND"
        
        if "AVSS" in nets:
            return "AGND"

        #返回包含GND/VSS/DGND/AGND的net，优先级：完全匹配>开头匹配>包含匹配，忽略大小写
        for net in nets:
            if re.match(r"^(GND|VSS|DGND|AGND)$",net,re.IGNORECASE):
                return net
            
        for net in nets:
            if re.match(r"^(GND|VSS|DGND|AGND).*$",net,re.IGNORECASE):
                return net
            
        for net in nets:
            if re.match(r"^.*(GND|VSS|DGND|AGND).*$",net,re.IGNORECASE):
                return net
            
        return None
    
    
    
    def deleteNets(self,netList):
        if not isinstance(netList, (list,tuple)):
            log.info("deleteNets input is empty")
            return 
        
#         #移除No-Net
#         while "<NO-NET>" in netList:
#             netList.remove("<NO-NET>")
        
        if len(netList)<1:
            log.info("deleteNets input is empty")
            return 
        
        log.info("delete nets: %s"%(",".join(netList)))
        self.layout.oEditor.DeleteNets(netList)
        self.layout.initObjects()  #add 20250707
        
    def reNameXnetForce(self,regNets,tail="_C"):
        '''
        on: R or C or L or RC or RLC ... 
        '''
        
        nets = self.getRegularNets(regNets)
        i = 0
        pwrNets = self.PowerNetNames
        for net in nets:
            i += 1
#             for comp in self.layout.Nets[net].Objects.Components:
            for name in self.layout.Nets[net].getConnectedComponnets():
                comp = self.layout.Components[name]
                if len(comp.Pins) != 2: #must RLC
                    continue
                
                pnet,nnet = comp.NetNames
                if pnet in pwrNets or nnet in pwrNets: 
#                     log.debug("Component: %s, Pnet: %s, Nnet: %s %s"%(comp.Name,pnet,nnet,"................%s/%s"%(i,len(comps))))
                    continue

                
#                 log.debug("Component: %s, Pnet: %s, Nnet: %s %s"%(comp.Name,pnet,nnet,"................%s/%s"%(i,len(comps))))
                
                log.info(("Component: %s, Pnet: %s, Nnet: %s"%(comp.Name,pnet,nnet)).ljust(50,"-") + " %s/%s"%(i,len(nets)))
                if pnet == net:
                    log.info(comp.Name+" Nets: "+ pnet + " " + nnet + ": Rename "+ nnet + " to " + pnet+tail)
                    self.layout.Nets[nnet].rename(pnet+tail)
                    
                if nnet == net:    
                    log.info(comp.Name+" Nets: "+ nnet + " " + pnet+ ": Rename "+ pnet + " to " + nnet+tail)
                    self.layout.Nets[pnet].rename(nnet+tail)
                
        
    def autoRLCnet(self,on = "R"):
        '''
        on: R or C or L or RC or RLC ... 
        '''
        
        for each in on:
            if "r" == each.lower():
                reg = "R.*"
                tail = "_R"
            elif "l" == each.lower():
                reg = "L.*"
                tail = "_L"
            elif "c" == each.lower():
                reg = "C.*"
                tail = "_C"
            else:
                continue
            
            comps = self.layout.Components[reg]
            
            
            pwrNets = self.PowerNetNames
            i = 0
            for comp in comps:
#                 print("Process component: %s"%comp.Name)
                i += 1
                if len(comp.Pins) != 2:
                    continue
                
                pnet,nnet = comp.NetNames
    
                if pnet in pwrNets or nnet in pwrNets: 
#                     log.debug("Component: %s, Pnet: %s, Nnet: %s %s"%(comp.Name,pnet,nnet,"................%s/%s"%(i,len(comps))))
                    continue
                
#                 log.debug("Component: %s, Pnet: %s, Nnet: %s %s"%(comp.Name,pnet,nnet,"................%s/%s"%(i,len(comps))))
                
                log.info(("Component: %s, Pnet: %s, Nnet: %s"%(comp.Name,pnet,nnet)).ljust(50,"-") + "%s/%s"%(i,len(comps)))
                
                if re.match(r"^(N?\d+$)|(UNNAMED.*)|(\$.*)",pnet,re.I) and re.match(r"^N?[a-z0-9_]+[a-z]+",nnet,re.I): 
                    log.info(comp.Name+" Nets: "+ nnet + " " + pnet+ ": Rename "+ pnet + " to " + nnet+tail)
                    self.layout.Nets[pnet].rename(nnet+tail)
                if re.match(r"^(N?\d+$)|(UNNAMED.*)|(\$.*)",nnet,re.I) and re.match(r"^N?[a-z0-9_]+[a-z]+",pnet,re.I): 
                    log.info(comp.Name+" Nets: "+ pnet + " " + nnet + ": Rename "+ nnet + " to " + pnet+tail)
                    self.layout.Nets[nnet].rename(pnet+tail)
                    
    def mergePhysicallyConnectedNets(self):

        netObjectsList = []
        for net in self.All:
            if net.Name in ["----","<NO-NET>","OUTLINES"]:
                continue 
            log.info("Get Net Connected objects: %s"%net.Name)
            objs = net.getNetConnected()
            if not objs:
                continue
            netObjectsList.append([net,objs])
        
        netObjectsList.sort(key=lambda x:len(x[1]),reverse=True)  #sort by objs count
        
        while len(netObjectsList):
            net,objs1 = netObjectsList.pop(0)
            log.info("Check Physically Connected on Net: %s"%net.Name)
            objs2 = net.getPhysicallyConnected()
            objs3 = list(set(objs2)-set(objs1))
            if not objs3:
                continue
            
            #short object found
            netList4 = []
            objs4 = []
            for name in objs3:
                obj3 = Primitive(name,self.layout)
                if "Net" in obj3:
                    objs4.append(name)
                    netName3 = obj3.Net
                    if netName3 not in netList4: #and netName3 != "----"
                        netList4.append(netName3)
                else:
                    pass
                
            log.info("Rename objects on net %s: %s"%(net.Name,str(objs4)))
            self.layout.oEditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:BaseElementTab",
                        [
                            "NAME:PropServers"
                        ]+objs4,
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:Net",
                                "Value:=", net.Name
                            ]
                        ]
                    ]
                ])
            
            newObjectsList = []
            for obj in netObjectsList:
                if obj[0].Name not in netList4:
                    newObjectsList.append(obj)
                                
            netObjectsList = newObjectsList
            
        self.layout.Nets.refresh()
        
    def disjointNets(self):

        for net in list(self.All):
            if net.Name in ["----","<NO-NET>","OUTLINES"]:
                continue
            net.disjoint()
   
#         self.layout.Nets.refresh() 

    def addPwrGndNets(self,nets):
        netList = self.getRegularNets(nets)
        if netList:
            netList += self.PowerNetNames
            netList = list(set(netList))
            log.info("Add power/Ground Nets: %s"%str(netList))
            self.layout.oEditor.ModifyNetClass("<Power/Ground>", "<Power/Ground>", "",netList)
        else:
            log.warning("Nets not found in layout: %s"%str(nets))
            
    def removePwrGndNets(self,nets):
        netList = self.getRegularNets(nets)
        if netList:
            pwrGnds = self.PowerNetNames
            pwrGnds = [net for net in pwrGnds if net not in netList]
            log.info("Remove power/Ground Nets: %s"%str(pwrGnds))
            self.layout.oEditor.ModifyNetClass("<Power/Ground>", "<Power/Ground>", "",pwrGnds)
        else:
            log.warning("Nets not found in layout: %s"%str(nets))
            