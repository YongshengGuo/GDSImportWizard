
#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-15

'''
pingroup for edb function
'''
import os,sys,re
from ..common.common import *
from ..common.complexDict import ComplexDict
from ..primitive.geometry import Point,Polygen
from .edbDefinition import EdbDefinition,EdbDefinitions
from .edbPrimitive import EdbPrimitive
from .edbVia import EdbVia

try:
    _clr = initClr()
    from System import String
except:
    log.warning("CLR initialization failed in child process (likely duplicate init). Ignoring if not needed.")


appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class EdbNet(EdbDefinition):
    def __init__(self,obj,edbApp=None):
        super(EdbNet,self).__init__(obj,type="EdbNet",edbApp=edbApp)

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return

        maps = {
            "Name":{"Key":"self","Get":lambda s:s.GetName(),"Set":lambda s,x:s.SetName(x)},
            "ID":{"Key":"self","Get":lambda s:s.obj.GetId()},
            "ObjType":{"Key":"self","Get":lambda s:s.obj.GetObjType().ToString()},
        }

        self.maps.update(maps)
        self._info.update("self", self)
        self._info.setMaps(self.maps)
        self.parsed = True

    def GetName(self):
        return self.obj.GetName()


    def getNetConnectedPrimitives(self):
        objs = list(self.obj.Primitives)
        return [EdbPrimitive(o,self.edbApp)  for o in objs if not o.IsVoid()] #remove void

    def getNetConnectedPadstackInstances(self):
        objs = list(self.obj.PadstackInstances)
        return [EdbVia(o,self.edbApp)  for o in objs]

    def getNetConnected(self):
        return self.getNetConnectedPrimitives() + self.getNetConnectedPadstackInstances()

    
    def disjoint(self):
        log.info("Get net %s connected objects "%self.Name)
        objs1 = self.getNetConnected()
        objs1_Ids = [o.GetId() for o in objs1]
        
#         objs2 = []
        objs2_Ids = [] #return objs

        #get net group
        while len(objs1_Ids):
            id1 = objs1_Ids[0]
            obj1 = self.edbApp.findObjById(id1)
            log.info("disjoint process net %s id %s"%(self.Name,obj1.Name))
            objs3 = EdbPrimitive(obj1,self.edbApp).getPhysicallyConnected()
            objs3_Ids = [o.GetId() for o in objs3]
            objs2_Ids.append(objs3_Ids)
            
#             objs4_Ids = [list(set(objs1_Ids)&set(objs3_Ids))] #group1
#             objs5_Ids = list(set(objs1_Ids)^set(objs3_Ids)) #others groups, no intersection elements
            objs5_Ids = list(set(objs1_Ids)-set(objs3_Ids))
            objs1_Ids = objs5_Ids


        if len(objs2_Ids)<2:
            log.info("No disjoint net found on %s"%self.Name)
            return
        
        objs2_Ids.sort(key=lambda x:len(x),reverse=True)
        i = 1
#         newNetObj = self.obj # self.Name
        for ids in objs2_Ids[1:]:
            newNetObj = self.edbApp.Edb.Cell.Net.Create(self.edbApp.layout,"%s_%s"%(self.Name,i))
            log.info("Disjoint net on %s, rename to %s, object count %s"%(self.Name,newNetObj.GetName(),len(ids)))
#             __rst = [self.edbApp.findObjById(id).SetNet(newNetObj) for id in ids]
            for id in ids:
                obj = self.edbApp.findObjById(id)
                obj.SetNet(newNetObj)
#             newNet = self.edbApp.Edb.Cell.Net.Create(self.edbApp.layout,"%s_%s"%(self.Name,i))
#             self.edbApp.NetClass['Non Power/Ground'].AddNet(newNetObj)
            i += 1
        self.edbApp.Nets.refresh()
    
    def disjoint2(self):
        objs1 = self.getNetConnected()
        objs1_Ids = [o.GetId() for o in objs1]
        
        objs2 = []
        objs2_Ids = []

        #get net group
        while len(objs1):
            obj1 = objs1.pop()
            temp = []
            objs3 = obj1.getPhysicallyConnected()

            for obj3 in objs3:
                if not self.edbApp.hasObj(obj3,temp):
                    temp.append(obj3)
                objs1 = self.edbApp.removeObj(obj3,objs1)

            objs2.append(temp)

        if len(objs2)<2:
            log.info("No disjoint net found on %s"%self.Name)
            return
        
        objs2.sort(key=lambda x:len(x),reverse=True)
        i = 1
        newNetObj = self.obj # self.Name
        for objs in objs2:
            log.info("Disjoint net on %s, rename to %s, object count %s"%(self.Name,newNetObj.GetName(),len(objs)))
            for obj in objs:
#                 obj.Net = newNet
                obj.SetNet(newNetObj)
#             newNet = self.edbApp.Edb.Cell.Net.Create(self.edbApp.layout,"%s_%s"%(self.Name,i))
            newNetObj = self.edbApp.Edb.Cell.Net.Create(self.edbApp.layout,"%s_%s"%(self.Name,i))
#             self.edbApp.NetClass['Non Power/Ground'].AddNet(newNetObj)
            i += 1
        self.edbApp.Nets.refresh()
 

class EdbNets(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(EdbNets,self).__init__(edbApp,type="Nets",definitionClass=EdbNet)

    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            if hasattr(self.edbApp.layout,self.type):
                objs = getattr(self.edbApp.layout,self.type)
                self._definitionDict  = ComplexDict(dict([(p.GetName(),self.definitionClass(p,self.edbApp)) for p in objs]))
            else:
                self._definitionDict = {}
        return self._definitionDict
    
    def disjointNets(self):
        '''
        Note: if  PEC Size not "0,0", will work with issue
        '''
        for net in list(self.All):
            if net.Name in  ["----","<NO-NET>","OUTLINES"]:
                continue
            log.info("Check disjoint on %s"%net)
            net.disjoint()
    
    
    def mergeShortNets(self,netList=None):
        '''
        Note: if  PEC Size not "0,0", will work with issue
        Connect the short-circuited nets even if they are not physically contacted.
        '''

        netObjectsList = []
        if not netList:
            netList = self.All
        else:
            netNames = self.getRegularNetNames(netList)
            netList = [self[name] for name in netNames]
                        
        for net in netList:
            if net.Name in  ["----","<NO-NET>","OUTLINES"]:
                continue 
            log.info("Get Net Connected objects: %s"%net.Name)
            objs = net.getNetConnected()
            if not objs:
                continue
            
            objs_Id = [x.ID for x in objs]
            netObjectsList.append([net,objs_Id])
        
        netObjectsList.sort(key=lambda x:len(x[1]),reverse=True)  #sort by objs count
        processNameList = []
        while len(netObjectsList):
            net,objs1_Id = netObjectsList.pop(0)
            netName = net.Name
            if netName in processNameList:
                #skip net already process
                continue
            processNameList.append(netName)

            log.info("Check Physically Connected on Net: %s"%netName)
            objsSet = set()
            for obj_id in objs1_Id:
                if obj_id in objsSet:
                    continue
                objs1 = self.edbApp.findObjById(obj_id)
                objs2_Id = [x.ID for x in objs1.getPhysicallyConnected()]
                objsSet.update(objs2_Id)

            shortObjs = list(objsSet - set(objs1_Id))
            if not shortObjs:
                log.info("No shorted net found on %s"%netName)
                continue

            for obj_id in shortObjs:
                obj = self.edbApp.findObjById(obj_id)
                objNetName = obj.GetNet().GetName()
                if objNetName == netName:
                    continue
                if objNetName not in processNameList:
                    processNameList.append(objNetName)
                log.info("Rename objects %s on net %s to %s"%(obj.Name,objNetName,netName))
                obj.SetNet(net.obj)

            newObjectsList = []
            for obj in netObjectsList:
                if obj[0].Name not in processNameList:
                    newObjectsList.append(obj)
            netObjectsList = newObjectsList
            
        self.refresh()
    
    
    def mergePhysicallyConnectedNets(self,netList=None):
        '''
        Note: if  PEC Size not "0,0", will work with issue
        '''

        netObjectsList = []
        if not netList:
            netList = self.All
        else:
            netNames = self.getRegularNetNames(netList)
            netList = [self[name] for name in netNames]
                        
        for net in netList:
            if net.Name in  ["----","<NO-NET>","OUTLINES"]:
                continue 
            log.info("Get Net Connected objects: %s"%net.Name)
            objs = net.getNetConnected()
            if not objs:
                continue
            
            objs_Id = [x.ID for x in objs]
            netObjectsList.append([net,objs_Id])
        
        netObjectsList.sort(key=lambda x:len(x[1]),reverse=True)  #sort by objs count
        
        processNameList = []
        while len(netObjectsList):
            net,objs1_Id = netObjectsList.pop(0)
            if net.Name in processNameList:
                #skip net already process
                continue
            processNameList.append(net.Name)
            objs1 = self.edbApp.findObjById(objs1_Id[0])
            log.info("Check Physically Connected on Net: %s"%net.Name)
            objs2 = objs1.getPhysicallyConnected()
            objs2_Id = [x.ID for x in objs2]
            objs3_Id = list(set(objs2_Id)-set(objs1_Id))
            if not objs3_Id:
                log.info("No shorted net found on %s"%net.Name)
                continue
            
            #short object found
            for obj3_Id in objs3_Id:
                obj3 = self.edbApp.findObjById(obj3_Id)
                netName3 = obj3.NetName
                if netName3 not in processNameList: #and netName3 != "----"
                    processNameList.append(netName3)
                log.info("Rename objects on net %s to %s: %s"%(netName3,net.Name,obj3.Name))
                obj3.SetNet(net.obj)

            newObjectsList = []
            for obj in netObjectsList:
                if obj[0].Name not in processNameList:
                    newObjectsList.append(obj)
                                
            netObjectsList = newObjectsList
            
        self.refresh()
    
    def getRegularNetNames(self,regNets):
        '''
        
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
            regNet = regNet.replace("$","\$").strip()
            nets += filter(lambda x: re.match(regNet+"$",x,re.IGNORECASE),self.NameList)
        return list(set(nets))