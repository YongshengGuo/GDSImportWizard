#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-10-25

import re
from ..common.complexDict import ComplexDict
from ..common.common import log,tuple2list
from .definition import Definitions,Definition
from ..common.arrayStruct import ArrayStruct
from ..common import hfss3DLParameters

class Airbox(Definition):
    '''_summary_
    '''

    def __init__(self,name = "Airbox",layout=None):
        '''Initialize Component object
        Args:
            compName (str): refdes of component in PCB, optional
            layout (PyLayout): PyLayout object, optional
        '''
        super(self.__class__,self).__init__(name,type="Airbox",layout=layout)

        
    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return

        maps = {}
        datas = hfss3DLParameters.hfssExtents
        _array = ArrayStruct(tuple2list(datas),maps)
        self._info.update("Name",self.name)
        self._info.update("Array", _array)
        self._info.update("self", self)
        self.parsed = True
        
        
    def update(self):
        self.layout.oDesign.EditHfssExtents(self.Array.Datas)
        # self.parse(force=True) #hfssExtents 不能直接获取参数