#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230611


'''
Examples:
        >>> line = Line('line1')
        返回line1的Line对象
        
        >>> line.changeLineWidth('0.2mm')
        修改line的线宽为0.2mm
    
        >>> line.selectNetConnected()
        选中跟line的net属性相连的网络
        
        >>> line.selectPhysicallyConnected()
        选中跟line的物理相连的网络
        
    Line["line1"].Net
        
'''

import re
from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log

from .geometry import Point
from .primitive import Primitive,Primitives

class Line(Primitive):
    '''_summary_
    '''

    def __init__(self, name, layout=None):
        '''Initialize Pin object
        Args:
            name (str): poly name in layout
            layout (PyLayout): PyLayout object, optional
        '''
        super(self.__class__,self).__init__(name,layout)

class Lines(Primitives):
    
    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="line",primitiveClass=Line)

    def add(self,points,layerName,width="0.1mm"):
        '''
        points:list,tuple, Point
        '''
        if not points or len(points)<2:
            log.exception("Points of line must have 2 points")
            
#         if not name:
#             name = self.getUniqueName()
            
        pts = [Point(p) for p in points]
        pUnit = self.layout.unit
        
        xyListTemp = []
        for i in range(len(pts)):
            xyListTemp.append("x:=")
            xyListTemp.append(0)
            xyListTemp.append("y:=")
            xyListTemp.append(0)
        
            
        name = self.layout.oEditor.CreateLine(
            [
                "NAME:Contents",
                "lineGeometry:=", 
                ["Name:=", "line_0", 
                "LayerName:=", self.layout.layers.getRealLayername(layerName),
                "lw:=", width,
                "endstyle:=", 0,
                "StartCap:=", 0,
                "n:=", len(xyListTemp),
                "U:=", pUnit] + xyListTemp
#                 "x:=", 17,"y:=", 28,
#                 "MR:=", "600mm"]
            ])
        
        self.push(name)
        for i in range(len(pts)):
            self[name]["Pt%s"%i] = pts[i]
            
        return self[name]
        
    