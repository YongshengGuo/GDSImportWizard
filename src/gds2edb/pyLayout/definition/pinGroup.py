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


import re
from itertools import groupby

from ..common.common import log
from ..common.unit import Unit
from ..common.complexDict import ComplexDict
from ..common.arrayStruct import ArrayStruct
from .definition import Definitions,Definition
from ..primitive.pin import Pin

class PinGroup(Definition):
    '''_summary_
    '''
    def __init__(self, name = None,pinNames = None,layout = None):
        super(self.__class__,self).__init__(name,type="PinGroup",layout=layout)
        self._info.update("PinNames",pinNames)
    

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
        maps.update({"PinCount":{
            "Key":"self",
            "Get":lambda s:len(s.PinNames)
            }})

        maps.update({"CompName":{
            "Key":"self",
            "Get":lambda s: Pin(s.PinNames[0],s.layout).CompName  #s.layout.Pins[s.PinNames[0]].CompName
            }})

        self._info.setMaps(maps)
        self._info.update("self", self)
        self.parsed = True
    
    def hasPin(self,pinName):
        for pin in self.PinNames:
            if pin.lower() == pinName.lower():
                return True
        return False
        

class PinGroups(Definitions):

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="PinGroup",definitionCalss=PinGroup)

#     def _getDefinitionDict(self):
#         return  ComplexDict(dict([(name,Net(name,self.layout)) for name in self.layout.oEditor.GetNetClassNets('<All>')]))

    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            self._definitionDict = ComplexDict()
            
            groups = self.layout.oEditor.FindObjects('Type', "PinGroup")
            self._definitionDict  = ComplexDict(dict([(name,self.definitionCalss(name,[],self.layout)) for name in groups]))
            
#             groupDict = self.getExistGroupInfoFromEdb()
#             self._definitionDict  = ComplexDict(dict([(name,self.definitionCalss(name,groupDict[name],self.layout)) for name in groupDict]))
        return self._definitionDict

    def getExistGroupInfoFromEdb(self):
        from ..edb.edbApp import EdbApp
        log.info("Get pingroups from EDB.....")
        edbApp = EdbApp(edbpath= self.layout.edbPath,installDir=self.layout.installDir)
        groupDict = {}
        for group in edbApp.PinGroups.All:
            groupDict[group.Name] = group.PinNames
        edbApp.close()
        return groupDict
    
    def findPinGroupByPin(self,pinName):
        for group in self.All:
            if group.hasPin(pinName):
                return group
        return None

    def _gridPins(self,pins,rows,cols):

        # 定义网格的列数和行数
#         cols = 20
#         rows = 20

        # 计算x和y的最小最大值
        x_values = [pin.X for pin in pins]
        y_values = [pin.Y for pin in pins]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)

        # 生成网格边界
        x_bins = [x_min + i * (x_max - x_min) / cols for i in range(cols + 1)]
        y_bins = [y_min + i * (y_max - y_min) / rows for i in range(rows + 1)]

        # 定义一个函数，计算某个值属于哪个网格
        def get_bin_index(value, bins):
            for i in range(len(bins) - 1):
                if bins[i] <= value < bins[i + 1]:
                    return i
            return len(bins) - 2  # 处理最大值的情况（右边界）

        # 分配每个坐标到网格
        grid_assignment = {}
        for pin in pins:
            col = get_bin_index(pin.X , x_bins)
            row = get_bin_index(pin.Y, y_bins)

            key = "%s_%s" % (col, row)  # 创建键
            if key in grid_assignment:
                grid_assignment[key].append(pin)
            else:
                grid_assignment[key] = [pin]
        return grid_assignment


    def createByPins(self,pinList=None,compName=None,groupName = None):
        
        if not pinList:
            log.info("pinList is empty,skip")
            return ""

        if compName and compName not in pinList[0]:
            # short Pin Name
            pinList = ["%s-%s"%(compName,p) for p in pinList]
        else:
            # full Pin Name
            pass

        if not groupName:
            pin0 = Pin(pinList[0],self.layout)
            groupName = "PinGroup_%s_%s"%(pin0.Net,pinList[0])
        
        if groupName in self.layout.PinGroups:
            log.info("PinGroup %s already exist,skip."%groupName)
            return

        self.layout.oEditor.CreatePinGroups(
                [
                    "NAME:PinGroupDatas",
                    [
                        "NAME:%s"%groupName, 
                    ] + pinList
                ])
            
        self.push(groupName,self.definitionCalss(groupName,pinList,self.layout))


    def createByGrid(self,pinList,compName,nets=None,groupName = None,rows = 1,cols = 1):
        
        if not compName:
            log.exception("CompName must definition before create pingroup.")
        
        if isinstance(nets, str):
            nets = self.layout.Nets.getRegularNets(nets)

        pinsForGrid = []
        Pins = self.layout.Components[compName].Pins
        if nets:
            for net in nets:
                pins = [p for p in Pins if p.Net.lower() == net.lower()]
                if pins:
                    pinsForGrid.extend(pins)
        else:
            if not pinList:
                log.info("pinList and nets are empty, skip createByGrid")
                return
            if compName and compName not in pinList[0]:
                pinList = ["%s-%s"%(compName,p) for p in pinList]
            pinNameSet = set(pinList)
            pinsForGrid = [p for p in Pins if p.Name in pinNameSet]

        if not pinsForGrid:
            log.info("No pins found to create grid pin groups, skip")
            return

        grid_assignment = self._gridPins(pinsForGrid,int(rows),int(cols))

        for k,v in grid_assignment.items():
            sorted_data = sorted(v, key=lambda x: x.Net)
            grouped_data = groupby(sorted_data, key=lambda x: x.Net) 
            for netName, netPins in grouped_data:
                if not groupName:
                    groupName = "PinGroup_%s_%s"%(netName,compName)
                pinNames = [p.Name for p in netPins]
                log.info("Create PinGroup, component:%s Net:%s Grid:%s pinCount:%s"%(compName,netName,k,len(pinNames)))
                self.createByPins(pinNames,groupName = groupName+"_"+k)

    def createByDict(self,gDict):
        '''_summary_

        Args:
            gDict (_type_): {"Name":"","Refdes":"","Pins":[],"Nets":"","Rows":1,"Cols":1}]
            pins:should be short pins
        '''

        if not ("Refdes" in gDict and gDict["Refdes"]):
            log.error("Refdes name is required")
            return
        if isinstance(gDict["Nets"], str):
            gDict["Nets"] = self.layout.Nets.getRegularNets(gDict["Nets"])
            
        pinList = []
        if "Pins" in gDict and gDict["Pins"]:
            pinList = ["%s-%s"%(gDict["Refdes"],p) for p in gDict["Pins"]]  #default shortpin name 
        elif "Nets" in gDict and gDict["Nets"]:
            for net in gDict["Nets"]:
                pinList += [pin.Name for pin in self.layout.Components[gDict["Refdes"]].Pins if pin.Net.lower() == net.lower()]
        else:
            log.exception("Pins or Nets is required")

        if not pinList: 
            log.info("No pins found to create pinGroup, skip.")
            return

        if "Rows" in gDict and gDict["Rows"]:
            Rows = int(gDict["Rows"])
        else:
            Rows = 1
        if "Cols" in gDict and gDict["Cols"]:
            Cols = int(gDict["Cols"])
        else:
            Cols = 1
        
        if "Nets" not in gDict or not gDict["Nets"]: 
            gDict["Nets"] = [Pin(pinList[0],self.layout).Net]  #self.layout.Pins[pinList[0]].Net

        if Rows<1 or Cols<1:
            #group per pin
            for name in pinList:
                gName = "PinGroup_%s_%s"%(gDict["Nets"][0],name)
                self.createByPins([name],gDict["Refdes"],gDict["Name"])
        elif Rows>1 or Cols>1:
            self.createByGrid(pinList,gDict["Refdes"],nets=gDict["Nets"],groupName = gDict["Name"],rows = gDict["Rows"],cols = gDict["Cols"])
        else:
            if "Name" not in gDict or gDict["Name"]=="":
                gDict["Name"] = "PinGroup_%s_%s"%(gDict["Nets"][0],pinList[0])
            self.createByPins(pinList,gDict["Refdes"],gDict["Name"])

    def createByDictList(self,gDictList):
        '''gDict (_type_): {"Name":"","Refdes":"","Pins":[],"Nets":"","Rows":1,"Cols":1}]
        '''
        def _createByPins(self,pinList=None,compName=None,groupName = None):
            
            if not pinList:
                log.info("pinList is empty,skip")
                return ""
            
            if isinstance(pinList, str):
                pinList = re.split("[\s,;]+",pinList)

            if compName and compName not in pinList[0]:
                # short Pin Name
                pinList = ["%s-%s"%(compName,p) for p in pinList]
            else:
                # full Pin Name
                pass

            if not groupName:
                pin0 = Pin(pinList[0],self.layout)
                groupName = "PinGroup_%s_%s"%(pin0.Net,pinList[0])
            
            if groupName in self.layout.PinGroups:
                log.info("PinGroup %s already exist,skip."%groupName)
                return

            return groupName,pinList

        def _createByGrid(self,pinList,compName,nets=None,groupName = None,rows = 1,cols = 1):
            
            pinList2 = []
            Pins = self.layout.Components[compName].Pins
            for pin in Pins:
                if pin.Name in pinList:
                    pinList2.append(pin)
            
            grid_assignment = self._gridPins(pinList2,int(rows),int(cols))
            groupDef = []
            for k,v in grid_assignment.items():
                sorted_data = sorted(v, key=lambda x: x.Net)
                grouped_data = groupby(sorted_data, key=lambda x: x.Net) 
                for netName, netPins in grouped_data:
                    if not groupName:
                        groupName = "PinGroup_%s_%s"%(netName,compName)
                    pinNames = [p.Name for p in netPins]
                    log.info("Create PinGroup, component:%s Net:%s Grid:%s pinCount:%s"%(compName,netName,k,len(pinNames)))
                    groupDef.append(_createByPins(self,pinNames,groupName = groupName+"_"+k))
                    # self.createByPins(pinNames,groupName = groupName+"_"+k)
            return groupDef

        groupsDef = []
        for gDict in gDictList:
            if not ("Refdes" in gDict and gDict["Refdes"]):
                log.error("Refdes name is required")
                return
            if isinstance(gDict["Nets"], str):
                gDict["Nets"] = self.layout.Nets.getRegularNets(gDict["Nets"])
            
            #20251105
            if "Pins" in gDict and isinstance(gDict["Pins"], str):
                gDict["Pins"] = re.split("[\s,;]+",gDict["Pins"])
                
            pinList = []
            if "Pins" in gDict and gDict["Pins"]:
                pinList = ["%s-%s"%(gDict["Refdes"],p) for p in gDict["Pins"]]
            elif "Nets" in gDict and gDict["Nets"]:
                for net in gDict["Nets"]:
                    pinList += [pin.Name for pin in self.layout.Components[gDict["Refdes"]].Pins if pin.Net.lower() == net.lower()]
            else:
                log.exception("Pins or Nets is required")
            
            if not pinList: 
                log.info("No pins found to create pinGroup, skip.")
                return

            if "Rows" in gDict and gDict["Rows"]:
                Rows = int(gDict["Rows"])
            else:
                Rows = 1
            if "Cols" in gDict and gDict["Cols"]:
                Cols = int(gDict["Cols"])
            else:
                Cols = 1
            
            if "Nets" not in gDict or not gDict["Nets"]: 
                gDict["Nets"] = [Pin(pinList[0],self.layout).Net]  #self.layout.Pins[pinList[0]].Net

            if Rows<1 or Cols<1:
                #group per pin
                for name in pinList:
                    gName = "PinGroup_%s_%s"%(gDict["Nets"][0],name)
                    groupsDef.append(_createByPins(self,[name],gDict["Refdes"],groupName = gName))
            elif Rows>1 or Cols>1:
                groupsDef += _createByGrid(self,pinList,gDict["Refdes"],nets=gDict["Nets"],groupName = gDict["Name"],rows = gDict["Rows"],cols = gDict["Cols"])
                # self.createByGrid(pinList,gDict["Refdes"],nets=gDict["Nets"],groupName = gDict["Name"],rows = gDict["Rows"],cols = gDict["Cols"])
            else:
                #Rows=1 and Cols=1
                if "Name" not in gDict or gDict["Name"]=="":
                    gDict["Name"] = "PinGroup_%s_%s"%(gDict["Nets"][0],pinList[0])
                groupsDef.append(_createByPins(self,pinList,gDict["Refdes"],groupName = gDict["Name"]))
                # self.createByPins(pinList,gDict["Refdes"],gDict["Name"])

        if not groupsDef:
            log.info("No PinGroup created.")
            return
        
        groupDefition = ["NAME:PinGroupDatas"]
        for groupName,pinList in groupsDef:
            log.info("Create Pin Group: %s"%groupName)
            groupDefition.append(["NAME:%s"%groupName]+pinList)
        self.layout.oEditor.CreatePinGroups(groupDefition)
        log.info("Total %s PinGroup created."%len(groupDefition))

        for groupName,pinList in groupsDef:
            self.push(groupName,self.definitionCalss(groupName,pinList,self.layout))


    def deletePinGroup(self,groupName):
        self.layout.oEditor.Delete([groupName])
        self.pop(groupName)

    def deleteAllPinGroups(self):
        names = self.NameList
        if len(names)>0:
            log.info("Remove All PinGroups %s"%(",".join(names)))
            self.layout.oEditor.Delete(names)
            self._definitionDict  = ComplexDict()
        else:
            return