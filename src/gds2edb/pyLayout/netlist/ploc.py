#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-07

import os
from ..common.common import log,readData,writeData
class PLOC(object):
    def __init__(self,path = None):
        self.path = path
        self.itemList = []
        if path:
            self.read(path)

    @property
    def Nets(self):
        return list(set([item["Net"] for item in self.itemList]))

    @property
    def Groups(self):
        return list(set([item["Group"] for item in self.itemList]))

    def read(self,path=None):
        path = path or self.path
        if not os.path.isfile(path):
                # print("file not exist")
                log.exception("file not exist")

        # header = ["Pin","X","Y","Layer","Net","Group"]
        PLOCList = []
        txts = readData(path)
        for line in txts.splitlines():
            if line.startswith("#"):
                continue
            splits = line.split()
            if len(splits) == 5:
                pin,x,y,Layer,Net = splits
                PLOCList.append({"DSP":line,"Pin":pin,"X":x,"Y":y,"Layer":Layer,"Net":Net,"Group":""})
            elif len(splits) == 6:
                pin,x,y,Layer,Net,Group = splits
                PLOCList.append({"DSP":line,"Pin":pin,"X":x,"Y":y,"Layer":Layer,"Net":Net,"Group":Group})
            else:
                log.error("PLOC error: %s"%line)

        self.itemList = PLOCList

    def write(self,path=None):
        path = path or self.path
        lines = []
        for item in self.itemList:
            # header = ["pin","x","y","Layer","Net","Group"]
            lines.append("{Pin} {X} {Y} {Layer} {Net} {Group}".format(**item))
        plocStr = "# VERSION 1.0" + "\n"
        plocStr += "# This PLOC file was generated or modified by an automated script, authored by yongsheng.guo@ansys.com." + "\n"
        plocStr += "\n".join(lines)
        writeData(plocStr,path)

    def add(self,item):
        '''_summary_

        Args:
            item (dict): _description_
        '''
        log.info("PLOC add item:"+str(item))
        temp = {"DSP":"","Pin":"","X":"","Y":"","Layer":"","Net":"","Group":""}
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
        return items
    def findbyXY(self,x,y):
        items = []
        for item in self.itemList:
            if item["X"] == x and item["Y"] == y:
                items.append(item)
        return items
    