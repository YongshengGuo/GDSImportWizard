#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2024-07-26

import re

from ..common.common import log
from .Aedt3DToolBase import Aedt3DToolBase


class Q3D(Aedt3DToolBase):

    def __init__(self,toolType=None, version=None, installDir=None,nonGraphical=False,newDesktop=False,usePyAedt=False,oDesktop = None):
        super(self.__class__,self).__init__(toolType="Q3D Extractor",version=version, installDir=installDir,
                                            nonGraphical=nonGraphical,newDesktop=newDesktop,usePyAedt=usePyAedt,oDesktop=oDesktop)
    
    def assignNets(self,netInfo):
        '''
        netInfo: {objName:net}
        '''
#         netInfo = ComplexDict(netInfo)
        netDict = {}
        for obj in self.Objects.NameList:
            if obj in netInfo:
                net = netInfo[obj]
                if net in netDict:
                    netDict[net].append(obj)
                else:
                    netDict[net] = [obj]
            else:
                log.debug("skip group object:%s"%obj)
        i = 1
        n = len(netDict)
        oModule = self.oDesign.GetModule("BoundarySetup")
        for net in netDict:
            #group name: Valid characters are letters, numbers, underscores
            group = re.sub(r"\W","_",net) #match [^a-zA-Z0-9]
            log.info(("Assign net: %s"%net).ljust(50,"-") + "%s/%s"%(i,n))
            print(group)
            print(netDict[net])
            oModule.AssignSignalNet(
                [
                    "NAME:%s"%group,
                    "Objects:=",netDict[net]
                ])

            i = i+1
    
#for test
if __name__ == '__main__':
#     layout = Layout("2022.2")
    layout = Q3D()
    layout.initDesign()