#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-07

cppTemp = '''*******************************************
* This CPP file was generated or modified by an automated script, authored by yongsheng.guo@ansys.com.
*******************************************
* CPP info for component = {component}  

* Begin Chip Package Protocol
* 
* Start Version Info
* CPP_Version 1.1
* Generator_Program SIwave_CPA 
* End Version Info
* 
* Start Design Property
* DesignType Package
* End Design Property
*
* Start Package Property
* PkgType flipchip dieup
* End Package Property
*
* Start Units
* Length um
* End Units
*
* Start Power Ground Ports
{portList}
* End Power Ground Ports
*
* End Chip Package Protocol
'''


import os
from ..common.common import log,readData,writeData
class CPP(object):
    def __init__(self,path = None):
        self.path = path
        self.itemList = []
        self.component = None
        if path:
            self.read(path)

    @property
    def Nets(self):
        return list(set([item["ChipNet"] for item in self.itemList]))

    @property
    def Groups(self):
        return list(set([item["Group"] for item in self.itemList]))

    def read(self,path=None):
        path = path or self.path
        if not os.path.isfile(path):
                # print("file not exist")
                log.exception("file not exist")

        

        # header = ["pin","x","y","Group","Net"]
        CPPList = []
        txts = readData(path)
        for line in txts.splitlines():
            if "CPP info for component" in line:
                #component name
                self.component = line.split("=")[-1].strip()
                continue

            splits = line[1:].strip().split(":")
            if len(splits) != 5:
                continue
            
            tempDict = {}
            tempDict["DSP"] = line
            tempDict["Pin"] = splits[0]
            tempDict["X"],tempDict["Y"] = splits[1].replace("(","").replace(")","").strip().split()
            tempDict["Group"],tempDict["Net"] = [x.strip() for x in splits[2].split("=")]
            CPPList.append(tempDict)
        self.itemList = CPPList


    def write(self,path=None):
        path = path or self.path
        lines = []
        for item in self.itemList:
            #["pin","x","y","Group","Net"]
            lines.append("* {Pin} : ({X} {Y}) : {Group}  = {Net} : {Group} : OTHER".format(**item))
        cppStr = cppTemp.format(component = self.component,portList = "\n".join(lines))
        writeData(cppStr,path)

    def add(self,item):
        '''_summary_

        Args:
            item (dict): _description_
        '''
        log.info("CPP add item:"+str(item))
        temp = {"Pin":"","X":"","Y":"","Net":"","Group":""}
        temp.update(item)
        self.itemList.append(temp)

    def hasPin(self,pin):
        return bool(self.findbyPin(pin))


    def findbyGroup(self,Group):
        items = []
        for item in self.itemList:
            if item["Group"].lower() == Group.lower():
                items.append(item)
        return items
    
    def findbyNet(self,Net):
        items = []
        for item in self.itemList:
            if item["Net"].lower() == Net.lower():
                items.append(item)
        return items
    
    def findbyPin(self,pin):
        items = []
        for item in self.itemList:
            if item["Pin"].lower() == pin.lower():
                items.append(item)
        
        if not items:
            for item in self.itemList:
                if item["Pin"].lower().endswith(pin.lower()):
                    items.append(item)

        return items
    def findbyXY(self,x,y):
        items = []
        for item in self.itemList:
            if item["X"] == x and item["X"] == y:
                items.append(item)
        return items
    
