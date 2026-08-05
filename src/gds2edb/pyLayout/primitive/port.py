#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2023-04-24

'''
Ports manager module
'''

import re
from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log

from .primitive import Primitive,Primitives
from .geometry import Point


# def sortBus(net):
    
    
# #     sums = sum([float(i) for i in nums]) if nums else 1e9
# #     return residual.upper(),net.upper().count("R"),sums,net.upper().count("N")+net.count("-")+net.count("#")
#     nums = re.findall(r"\d+",net,re.I) #number
#     numsList = [0]*10
#     for i in range(len(nums)):
#         numsList[i] = int(nums[i])

#     residual = re.sub(r"[\dPNTRC#+-]+", "", net)
#     return [residual.upper(),net.upper().count("R")] + numsList + [net.upper().count("N")+net.count("-")+net.count("#")++net.count("C")]
#     #R: Tx, Rx, N: P/N +/- # T/C

def sortBus(net):
    """
    解析信号名以生成排序键。
    旨在正确处理如 CK, CS, DQS, RDQS, DQ0-63, Tx0P, TXN 等信号。
    支持极性标识位于中间或末尾。
    """
    if not net:
        return ["", 0] + [0] * 10 + [0]

    # 1. 预处理：移除极性/类型标识 (P, N, T, C, R)
    # 规则：移除紧跟在分隔符(_,-,#)后或数字后，且位于单词边界或结尾的 P/N/T/C/R
    # 例如: Tx0P -> Tx0, CK_T -> CK, DQS_N -> DQS, RDQS -> RDQS (R不在末尾且非分隔符后，保留? 不，RDQS的R是Read，应保留)
    # 下面的正则会移除 _P, -N, _T 等，以及末尾的 P/N (如 DQ0P)
    # 注意：RDQS 中的 R 不会被移除，因为它前面是 D(字母) 且不是分隔符，也不在末尾(如果后面有QS)
    # 但如果信号叫 DRAM_R, 这里的 R 会被移除吗？ (?<=[\d_\-#]) 要求前面是数字或分隔符。
    
    # # 更简单的策略：移除所有 _P, _N, _T, _C, _R, -P... 以及末尾的 P,N,T,C,R (如果前面是数字)
    # temp_net = re.sub(r"[_\-#x](P|N|T|C|R)\b", "", net, flags=re.IGNORECASE) # 移除分隔符+极性,考虑Txp/n
    # temp_net = re.sub(r"(\d)(P|N|T|C|R)\b", r"\1", temp_net, flags=re.IGNORECASE) # 移除数字+极性 (DQ0P -> DQ0)

    temp_net = re.sub(r"(P|N|T|C)", "", net, flags=re.IGNORECASE) # 移除极性,考虑Txp/n
    # temp_net = re.sub(r"(\d)(P|N|T|C|R)\b", r"\1", temp_net, flags=re.IGNORECASE) # 移除数字+极性 (DQ0P -> DQ0)
    
    # 2. 提取数字
    nums = re.findall(r"\d+", temp_net)
    numsList = [0] * 10
    for i in range(min(len(nums), 10)):
        numsList[i] = int(nums[i])
        
    # 3. 提取残差 (移除所有数字和常见分隔符)
    residual = re.sub(r"[\d_\-#\[\]]+", "", temp_net)
    
    # 清理可能产生的多余空字符或纯空白
    residual = residual.strip()
    
    if not residual:
        # Fallback: 如果全被移除了，尝试从原名提取纯字母
        residual = re.sub(r"[\d_\-#\[\]]+", "", net)
        if not residual:
            residual = net

    # 4. 其他因子
    has_Rx = net.upper().count("R")
    complexity = net.upper().count('N') + net.count('-') + net.count('#') + net.upper().count('C')

    return [residual.upper(), has_Rx] + numsList + [complexity]



class Port(Primitive):

        
    def parse(self, force = False):
        if self.parsed and not force:
            return
        
        super(self.__class__,self).parse(force) #initial component properties
        
        maps = self.maps
        EMProperties = self.layout.oEditor.GetProperties("EM Design","Excitations:%s"%self.Name)
        self._info.update("EMProperties",EMProperties)
        for prop in EMProperties:
            self._info.update(prop,None) #here give None value. get property value when used to improve running speed
            maps.update({prop.replace(" ",""):prop}) #map property with space characters

        #---prot infomation
        for item in self.layout.oEditor.GetPortInfo(self.name):
            splits = item.split("=",1)
            if len(splits) == 2:
                self._info.update(splits[0].strip(),splits[1].strip())
            else:
                log.debug("ignor port information: %s"%item)
        
        self._info.setMaps(maps)
        
    def get(self, key):
        
        if not self.parsed:
            self.parse()
        
        realKey = key
        
        if realKey in self._info.EMProperties:  #value is None
            self._info.update(realKey, self.layout.oEditor.GetPropertyValue("EM Design","Excitations:%s"%self.Name,realKey))
            return self._info[realKey]
        
        return super(self.__class__,self).get(realKey)
    
    
    
    def set(self,key,value):
        '''
        mapping key must not have same value with maped key.
        '''
        
        
        if not self.parsed:
            self.parse()
        
        realKey = self._info.getReallyKey(key)
            
        if realKey in self._info.EMProperties: 
            self.layout.oEditor.SetPropertyValue("EM Design", "Excitations:" + self.Name, realKey, value)
            self._info[realKey] = value
            if realKey == "Port": #Remane port name
                self.layout.Ports.refresh()
            return 1
#             self.parsed = False #refresh

        return super(self.__class__,self).set(key,value)
     
    def setPortImpedance(self,value):
        self.set("Impedance", str(value))
        
        if self.layout.isVersionAfter("2024.2"):
            self.set("Renormalize Impedance", str(value))
            return
        
        try:
            self.set("Renormalize Impedance", str(value)) #last then 2024.R2
        except:
            self.set("Renormalize Impedence", str(value)) #before Impedence
        
    def setSIwavePortRefNet(self,value):
        self.set("Reference Net", str(value))
        
        
    def autoRename(self):
        if "." in self.Name:
            log.info("skip port: %s"%self.Name)
            return
            
        ConnectionPoints = self.ConnectionPoints #0.000400 0.073049 Dir:270.000000 Layer: BOTTOM    
        if not ConnectionPoints or ConnectionPoints=='NONE':
            log.info("Port %s not a 3DL port, skip."%self.Name)
            return 
        
        splits = ConnectionPoints.split() #['0.000400', '0.073049', 'Dir:270.000000', 'Layer:', 'BOTTOM']
        X = float(splits[0])
        Y = float(splits[1])
        layer = splits[-1]
        posObjs = list(self.layout.getObjectByPoint([X,Y],layer = layer,radius="2mil"))
#         print(self.Name,posObjs,layer)
        
        if not posObjs:
            log.info("Not found objects on port '%s' position, skip."%self.Name)
            return

        if self.Name in posObjs:
            posObjs.remove(self.Name)
            
        if not posObjs:
            log.info("Not found objects on port '%s' position, skip."%self.Name)
            return
#             
#         posObj = posObjs[0]
        posObj = None
        for obj in posObjs:
            if obj in self.layout.Pins:
                posObj = obj
                break
            
        if not posObj:
            posObj = posObjs[0]
            
        if posObj in self.layout.Pins:   
            tempList = list(posObj.split("-"))+[self.layout.Pins[posObj].Net]
            newName = ".".join(tempList)
    #         print(newName,port)
            log.info("Rename %s to %s"%(self.Name,newName))
            self.Port = newName
        else:
            newName = self.layout[posObj].Net
            log.info("Rename %s to %s"%(self.Name,newName))
            self.Port = newName
        
    def delete(self):
        
        self.Collection.pop(self.Name)
        oModule = self.layout.oDesign.GetModule("Excitations")
        oModule.DeleteExcitation([self.Name])

class Ports(Primitives):
    
    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="port",primitiveClass=Port) #port not get by FindObjects

    @property
    def ObjectDict(self):
        '''
        get all port by oDesign.GetModule("Excitations").GetAllPortsList()
        '''

        if self._objectDict is None:
            self._objectDict = ComplexDict(dict([(port,Port(port,layout=self.layout)) for port in self.layout.oDesign.GetModule("Excitations").GetAllPortsList()]))
        return self._objectDict 

    def _portOrderRule(self,port,compOrder=[],netOrder=[]):
        
        if not compOrder:
            compOrder = []
            
        if not netOrder:
            netOrder = []
        
        # X: comp.pin.net
        rules = []
        comp,pin,net = port.split('.')
        #if compOrder:
        rules.append(compOrder.index(comp) if comp in compOrder else comp)
        
        if net in netOrder:
            rules.append(netOrder.index(net))
        else:
            rules += sortBus(net)
        
        return rules

    def _getMatchPortNames(self,name):
        '''
        name: support regex
        '''
        name ="^" + name.replace("*",".*?") + "$" #.replace(".","\.") 
        return list(filter(lambda x:re.match(name, x,re.I), self.NameList))

    def reorder(self,compOrder=[],netOrder=[],portOrder = []):
        '''
        assume port is generated by 3dlayout in rules: comp.pin.net
        compOrder is None will order by alphabet
        netOrder is none will order by bus 
        portOrder: comp.pin.net, comp.*.net, *.*.net, comp.pin.*  "*" is regex
        
        if portOrder have valid value, compOrder and netOrder will be ignored.
        '''
        log.info("order ports:")
        names = self.NameList
        
        #---portOrder first
        if portOrder:
            origNames = names[:]
            orderNames = []
            for p in portOrder:
                mports = self._getMatchPortNames(p)
                for p in mports:
                    orderNames.append(p)
                    origNames.remove(p)
            
            log.info("reorder port by portOrder: %s"%(", ".join(orderNames+origNames)))
            oModule = self.layout.oDesign.GetModule("Excitations")         
            oModule.ReorderMatrix(orderNames+origNames) #add residual ports     
            return orderNames+origNames
        
        
        #---compOrder and netOrder
        rulePorts = []
        unRulePorts = []
        for name in names:
            splits = name.split(".")
            if len(splits) ==3:
                rulePorts.append(name)
            else:
                log.info("unrule ports found:%s"%name)
                unRulePorts.append(name)
        
        rulePorts.sort(key= lambda p:self._portOrderRule(p, compOrder, netOrder))
        log.info("re order port %s"%(", ".join(rulePorts+unRulePorts)))
        oModule = self.layout.oDesign.GetModule("Excitations")
        oModule.ReorderMatrix(rulePorts+unRulePorts)
        return rulePorts+unRulePorts
    
    def add(self,netNames,compNames=None):
        return self.layout.Nets.createPortsOnNets(netNames,compNames,ignorRLC = True)

    def addPinGroupPort(self,posPins=None,refPins=None,compName=None,posNet=None,negNet=None,name=None,portZ0=0.1):

        if not posPins:
            if compName and posNet: 
                posPins = [pin.Name for pin in self.layout.Components[compName].Pins if pin.Net.lower() == posNet.lower()]
            else:
                log.exception("posPins or compName,posNet should be specified one")
        else:
            #remove pins not in layout
            PinNames = self.layout.Components[compName].PinNames
            
            if compName and not posPins[0].startswith(compName):
                # short Pin Name
                posPins = ["%s-%s"%(compName,p) for p in posPins]
            else:
                # full Pin Name
                pass
            
            tempPins = []
            for pin in posPins:
                if pin in PinNames:
                    tempPins.append(pin)
                else:
                    log.info("Pin %s not in Component %s, will be remove."%(pin,compName))
            posPins = tempPins

        if not refPins:
            if compName and negNet: 
                refPins = [pin.Name for pin in self.layout.Components[compName].Pins if pin.Net.lower() == negNet.lower()]
            else:
                log.exception("refPins or compName,negNet should be specified one")
        else:
            #remove pins not in layout
            PinNames = self.layout.Components[compName].PinNames
            if compName and not refPins[0].startswith(compName):
                # short Pin Name
                refPins = ["%s-%s"%(compName,p) for p in refPins]
            else:
                # full Pin Name
                pass
            
            
            tempPins = []
            for pin in refPins:
                if pin in PinNames:
                    tempPins.append(pin)
                else:
                    log.info("Pin %s not in Component %s, will be remove."%(pin,compName))
            refPins = tempPins
        
        if len(posPins)<1:
            log.info("PinGroup posPins have no pin. skip.")
            return
            
        if len(refPins)<1:
            log.info("PinGroup refPins have no pin. skip.")
            return
        
        posPin1 = self.layout.Pins[posPins[0]]
        posNet = posPin1.Net
        posPortName = posPins[0]+"_"+posNet
        
        refPin1 = self.layout.Pins[refPins[0]]
        refNet = refPin1.Net
        refPortName = refPins[0]+"_"+refNet
        
#         if not name:
#             name = posPortName
        
        if posPortName in self.layout.Ports:
            log.warning("port '%s' already exist, will be delete."%name)
            self.layout.Ports[posPortName].delete()
            
        if name and name in self.layout.Ports:
            log.warning("port '%s' already exist, will be delete."%name)
            self.layout.Ports[name].delete()
                        

        self.layout.oEditor.CreatePinGroups([
                "NAME:PinGroupDatas",
                ["NAME:%s"%posPortName]+posPins,
                ["NAME:%s"%refPortName]+refPins
            ])
            
        self.layout.PinGroups.push("%s"%posPortName,self.layout.PinGroups.definitionCalss("%s"%posPortName,posPins,self.layout))
        self.layout.PinGroups.push("%s"%refPortName,self.layout.PinGroups.definitionCalss("%s"%refPortName,refPins,self.layout))
        
        self.layout.oEditor.CreatePinGroupPort(
            [
                "Port:="        , posPortName,
                "Ref:="            , refPortName,
                "Magnitude:="        , "0"
            ])
        
        self.layout.Ports.push(posPortName)
        self.layout.Ports[posPortName].setPortImpedance(portZ0)
    
        if name:
            self.layout.Ports[posPortName]["Port"] = name
        else:
            name = posPortName

        return  self[name]
        
