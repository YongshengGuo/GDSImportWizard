#coding:utf-8
#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230410

import sys
import math
from ..common.unit import Unit
from ..common.common import log

class Point(object):
    def __init__(self,pt = None,arc = False,layout = None):
        '''
        pt: list,tuple,"x,y",Point, 3DL Point
        '''
        
        self.layout = layout
        self.x = 0
        self.y = 0
        self.arc = arc
        
        if isinstance(pt, (list,tuple)):
            self.x = pt[0]
            self.y = pt[1]
        elif "Wrapper" in str(type(pt)) or "Dispatch" in str(type(pt)):
            self.x = pt.GetX()
            self.y = pt.GetY()
        elif isinstance(pt, self.__class__):
            self.x = pt.x
            self.y = pt.y
        elif isinstance(pt,str):
            xy = pt.split(',')
            if len(xy)!=2:
                log.exception("Point input error %s"%pt)
            self.x = xy[0]
            self.y = xy[1]
        else:
            log.debug("Point init error")
            
        if layout:
            self.layout = layout
        else:
            try:
                self.layout = sys.modules["__main__"].layout
            except:
                self.layout = None #for edbApp
            
    def __getitem__(self, key):
        """
        key: int 0,1
        key: str X,Y
        """
        if isinstance(key, int):
            return [self.x,self.y][key]
        
        if isinstance(key, str):
            if key.lower() == 'x':
                return self.x
            elif key.lower() == 'y':
                return self.y
            elif key.lower() == 'xy':
                return [self.x,self.y]
            if key.lower() == 'xvalue':
                return Unit(self.x).V
            elif key.lower() == 'yvalue':
                return Unit(self.y).V
            elif key.lower() == 'xyvalue':
                return [Unit(self.x).V,Unit(self.y).V]
            
            else:
                log.exception("Point key error: %s"%key)
        
        log.exception("Point key error: %s"%str(key))
        
    def __getattr__(self,key):
        if key in ["x","y","arc","layout"]: #not key.lower()
            return object.__getattribute__(self,key)
        else:
            log.debug("__getattr__ from __getitem__: %s"%key)
            return self[key]
        
    def __str__(self):
        return "%s,%s"%(self.x,self.y)
        
    def __repr__(self):
        return "Point Object: [%s,%s]"%(self.x,self.y)
        
    def __len__(self):
        return 2
    
    def __abs__(self):
        return (self.xvalue**2+self.yvalue**2)**0.5
        
    @property
    def H3DLPoint(self):
        if not self.layout or not self.layout.oEditor:
            return
        pt3DL = self.layout.oEditor.Point().Set(self.x,self.y)
        if self.arc:
            pt3DL.SetArc(True)
        return pt3DL
    
    @property
    def XY(self):
        return self.x,self.y
        
    def __add__(self,u):
        if isinstance(u, self.__class__):
            x1 = Unit(self.x)
            x2 = Unit(u.x)
            y1 = Unit(self.y)
            y2 = Unit(u.y)
            
            return self.__class__([(x1+x2)[x1.unit],(y1+y2)[x1.unit]])
        else:
            return self + self.__class__(u)

    def __sub__(self,u):
        if isinstance(u, self.__class__):
            x1 = Unit(self.x)
            x2 = Unit(u.x)
            y1 = Unit(self.y)
            y2 = Unit(u.y)
            return self.__class__([(x1-x2)[x1.unit],(y1-y2)[x1.unit]])
        else:
            return self - self.__class__(u)

    def isArc(self):
        if self.arc:
            return True
        
        if self.yvalue>1e300:
            self.arc = True
            return True
        
        return False
    
    def distanceFromPoint(self,pt):
        pt2 = self.__class__(pt)
        dx = Unit(self.x).V - Unit(pt2.x).V
        dy = Unit(self.y).V - Unit(pt2.y).V
        return (dx**2 + dy**2)**0.5
    
    
class Polygen(object):
    
    def __init__(self,pts = None,closed = True,layout = None):
        '''
        pts: [[x1,y1],[x2,y2]]
        '''
        
        self.points = []
        self.closed = closed
        if pts:
            for pt in pts:
                if isinstance(pt, Point):
                    self.points.append(pt)
                else:
                    #pt is list or tuple
                    self.points.append(Point(pt))
        if layout:
            self.layout = layout
        else:
            try:
                self.layout = sys.modules["__main__"].layout
            except Exception:
                self.layout = None
    
    @property
    def H3DLPolygen(self):
        if not self.layout or not self.layout.oEditor:
            return
        
        ply = self.layout.oEditor.Polygon()
        for pt in self.points:
            ply.AddPoint(pt.H3DLPoint)
            
        if self.closed:
            ply.SetClosed(True)
        return ply
    
    def getPerimeter(self):
        n = len(self.points)
        perimeter = 0
        for i in range(n):
            x1 = Unit(self.points[i].x).V
            y1 = Unit(self.points[i].y).V
            x2 = Unit(self.points[(i+1) % n].x).V
            y2 = Unit(self.points[(i+1) % n].y).V
            side_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            perimeter += side_length
            
        return perimeter

    def getArea(self):
        n = len(self.points)
        area = 0
        for i in range(n):
            x1 = Unit(self.points[i].x).V
            y1 = Unit(self.points[i].y).V
            x2 = Unit(self.points[(i+1) % n].x).V
            y2 = Unit(self.points[(i+1) % n].y).V
            area += (x1 * y2 - x2 * y1) / 2
        return area
    
    def getCenter(self):
        x = sum([Unit(pt.x).V for pt in self.points])/len(self.points)
        y = sum([Unit(pt.y).V for pt in self.points])/len(self.points)
        return x,y

    @classmethod
    def circle(cls,center,r):
        ptCenter = Point(center)
        pts = [ptCenter-(r,0),Point([r,0],arc=True),ptCenter+(r,0),Point([r,0],arc=True)]
        return cls(pts)
        
    