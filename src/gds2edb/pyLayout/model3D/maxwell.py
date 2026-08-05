#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2024-07-26

from .Aedt3DToolBase import Aedt3DToolBase

class Maxwell(Aedt3DToolBase):

    def __init__(self,toolType=None, version=None, installDir=None,nonGraphical=False,newDesktop=False,usePyAedt=False,oDesktop = None):
        super(self.__class__,self).__init__(toolType="Maxwell 3D",version=version, installDir=installDir,
                                            nonGraphical=nonGraphical,newDesktop=newDesktop,usePyAedt=usePyAedt,oDesktop=oDesktop)
    
#for test
if __name__ == '__main__':
#     layout = Layout("2022.2")
    layout = Maxwell("2023.2")
    layout.initDesign()