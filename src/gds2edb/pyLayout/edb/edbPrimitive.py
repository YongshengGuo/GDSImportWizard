
#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-15

'''
pingroup for edb function
'''
import os,sys,re,math
from ..common.common import *
from ..common.complexDict import ComplexDict
from ..primitive.geometry import Point,Polygon
from .edbDefinition import EdbDefinition,EdbDefinitions

try:
    _clr = initClr()
    from System import String
except:
    log.debug("CLR initialization failed in child process (likely duplicate init). Ignoring if not needed.")  
# from System import String

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

'''
GetPrimitiveType()

Rectangle 0 Rectangle.  
Circle 1 Circle.  
Polygon 2 Polygon.  
Path 3 Path.  
Bondwire 4 Bondwire.  
PrimitivePlugin 5 Primitive types from plugins.  
Text 6 Text.  
Path3D 7 Path3D  
BoardBendDef 8 BoardBendDef.
InValidType 9 Invalid type.
'''


def getPrimitiveName(obj,edbApp):
    
    name = ""
    if isIronpython:
        val = _clr.StrongBox[str]()
        rst = obj.GetProductProperty(edbApp.Edb.ProductId.Designer, 1, val)
        if rst:
            name = val.Value
    else:
        val = String("")
        #edbApp.Edb.ProductId.Designer  0 Deprecated. use Hfss3DLayout instead.  
        _, name = obj.GetProductProperty(edbApp.Edb.ProductId.Designer, 1, val)
        
    name = str(name).strip("'")
    PrimitiveType = str(obj.GetPrimitiveType()).lower()
    if name == "":
        if PrimitiveType == "path":
            ptype = "line"
        elif PrimitiveType == "rectangle":
            ptype = "rect"
        elif PrimitiveType == "polygon":
            ptype = "poly"
        elif PrimitiveType == "bondwire":
            ptype = "bwr"
        else:
            ptype = PrimitiveType
            
        name = "{}__{}".format(ptype, obj.GetId())
#             self.edbApp.SetProductProperty(self._pedb._edb.ProductId.Designer, 1, name)
    return name


class EdbPrimitive(EdbDefinition):
    def __init__(self,obj,edbApp=None):
        super(self.__class__,self).__init__(obj,type="EdbPrimitive",edbApp=edbApp)

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return

        maps = {
            "Name":{"Key":"self","Get":lambda s:s.GetName()},
            "ID":{"Key":"self","Get":lambda s:s.obj.GetId()},
            "Net":{"Key":"self","Get":lambda s:s.obj.GetNet(),"Set":lambda s,x:s.SetNet(x)},
            "NetName":{"Key":"self","Get":lambda s:s.obj.GetNet().GetName()},
            "Group":{"Key":"self","Get":lambda s:s.obj.GetGroup()},
            "GroupName":{"Key":"self","Get":lambda s:s.obj.GetGroup().GetName()},
            "Component":{"Key":"self","Get":lambda s:s.obj.GetComponent()},
            "ComponentName":{"Key":"self","Get":lambda s:s.obj.GetComponent().GetName()},
            "ObjType":{"Key":"self","Get":lambda s:s.obj.GetObjType().ToString()},
            "PrimitiveType":{"Key":"self","Get":lambda s:s.obj.GetPrimitiveType()},
            "Layer":{"Key":"self","Get":lambda s:s.obj.GetLayer()},
            "LayerName":{"Key":"self","Get":lambda s:s.obj.GetLayer().GetName()},
            
            "Area":{"Key":"self","Get":lambda s:s.getArea()},
            "Points":{"Key":"self","Get":lambda s:s.getPoints()},
            "Voids":{"Key":"self","Get":lambda s:s.getVoids()},
        }
        
        self._info.update("_PolygonData",None)

        self.maps.update(maps)
        self._info.update("self", self)
        self._info.setMaps(self.maps)
        self.parsed = True
        
    @property
    def PolygonData(self):
        self.parse()
        if self._PolygonData is None:
            self._PolygonData = self.obj.GetPolygonData()
            # if str(self.PrimitiveType) == "Path":
            #     self._PolygonData = self.obj.GetCenterLine()
            # else:
            #     self._PolygonData = self.obj.GetPolygonData()
                
        return self._PolygonData

    def getArea(self):
        if self.PolygonData:
            return self._PolygonData.Area()
        else:
            return None
    
    def getPolygonPoints(self):
        if self.PolygonData:
            pts = self.PolygonData.Points
            points = [(pt.X.ToDouble(), pt.Y.ToDouble()) for pt in pts]
            return points
        else:
            return []
    
    def getPoints(self):
        if self.PolygonData:
            if str(self.PrimitiveType) == "Path":
                polyDatas = self.obj.GetCenterLine() #line: return center line
            else:
                polyDatas = self.PolygonData
                
            pts = polyDatas.Points
            points = [(pt.X.ToDouble(), pt.Y.ToDouble()) for pt in pts]
            return points
        else:
            return []

    def getVoids(self):
        
        if str(self.PrimitiveType) == "Polygon":
            voids = list(self.obj.Voids)
            voidsPrims = [EdbPrimitive(v, self.edbApp) for v in voids]
            #ComplexDict(dict([(getPrimitiveName(p,self.edbApp),self.definitionClass(p,self.edbApp)) for p in objs]))
            return voidsPrims
        else:
            return []
        
    def plot(self,ax = None,plotVoids=False,**kwargs):
        '''
        plot 2D points of the primitive.
        points是hfss格式, points = [(x1,y1),(x2,y2),(x3,1e300),(x4,y4)...] Arc的点x作为为半径，y坐标无效，Arc判断标准是Y坐标大于1e300
        在绘制(x3,1e300)时，应该以(x2,y2)为起点，(x4,y4)为终点，绘制一个拱高为x3的圆弧。
        self.PolygonData.IsClosed()为True时，表示首尾相连，绘制时需要将最后一个点和第一个点连接起来。
        '''
        created_fig = False
        if ax is None:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            created_fig = True

        try:
            ax.set_aspect('equal', adjustable='datalim')
        except Exception:
            pass

        def _is_arc_point(pt):
            try:
                return pt[1] > 1e300
            except Exception:
                return False

        def _next_regular_index(start_index, pts):
            for idx in range(start_index, len(pts)):
                if not _is_arc_point(pts[idx]):
                    return idx
            return None

        def _sample_arc_points(start_pt, end_pt, arch_height, segments=72):
            sx, sy = start_pt
            ex, ey = end_pt
            chord = math.hypot(ex - sx, ey - sy)
            if chord == 0 or arch_height == 0:
                return None

            sagitta = abs(arch_height)
            # From chord length c and sagitta h:
            #   R = c^2 / (8h) + h/2
            # where R is the circle radius that produces the arc.
            circle_radius = (chord * chord) / (8.0 * sagitta) + (sagitta / 2.0)
            center_offset = circle_radius - sagitta

            midx = (sx + ex) / 2.0
            midy = (sy + ey) / 2.0

            # Positive arch height means clockwise, negative arch height means counterclockwise.
            # The signed arch height controls which side of the chord the center lies on.
            center_side = 1.0 if arch_height > 0 else -1.0
            ux = (ey - sy) / chord * center_side
            uy = -(ex - sx) / chord * center_side
            cx = midx + ux * center_offset
            cy = midy + uy * center_offset

            start_angle = math.atan2(sy - cy, sx - cx)
            end_angle = math.atan2(ey - cy, ex - cx)
            delta = end_angle - start_angle

            if arch_height > 0 and delta > 0:
                delta -= 2.0 * math.pi
            elif arch_height < 0 and delta < 0:
                delta += 2.0 * math.pi

            arc_points = [start_pt]
            for idx in range(1, segments):
                angle = start_angle + delta * (float(idx) / segments)
                arc_points.append((cx + circle_radius * math.cos(angle), cy + circle_radius * math.sin(angle)))
            arc_points.append(end_pt)
            return arc_points

        points = self.getPolygonPoints() or []
        
        if not points:
            log.warning("No points available for plotting. The primitive may not have valid polygon data.")
            return ax

        is_closed = False
        try:

            poly_data = self.PolygonData
            if poly_data is not None and hasattr(poly_data, "IsClosed"):
                is_closed_attr = poly_data.IsClosed
                is_closed = bool(is_closed_attr() if callable(is_closed_attr) else is_closed_attr)
        except Exception:
            is_closed = False

        if is_closed and points:
            first_regular_point = None
            for pt in points:
                if not _is_arc_point(pt):
                    first_regular_point = pt
                    break

            # Append the first valid point to ensure the last segment links back.
            if first_regular_point is not None and points[-1] != first_regular_point:
                points = list(points)
                points.append(first_regular_point)

        path_vertices = []
        path_codes = []
        index = 0
        last_regular_point = None

        try:
            from matplotlib.path import Path
            from matplotlib.patches import PathPatch
        except Exception:
            Path = None
            PathPatch = None

        while index < len(points):
            current_point = points[index]

            if _is_arc_point(current_point):
                if last_regular_point is None:
                    index += 1
                    continue

                next_index = _next_regular_index(index + 1, points)
                if next_index is None:
                    break

                next_regular_point = points[next_index]
                arch_height = current_point[0]
                arc_points = _sample_arc_points(last_regular_point, next_regular_point, arch_height)
                if arc_points is None:
                    if not path_vertices:
                        path_vertices.append(last_regular_point)
                        path_codes.append(Path.MOVETO if Path is not None else 1)
                    elif path_vertices[-1] != last_regular_point:
                        path_vertices.append(last_regular_point)
                        path_codes.append(Path.LINETO if Path is not None else 2)
                    path_vertices.append(next_regular_point)
                    path_codes.append(Path.LINETO if Path is not None else 2)
                else:
                    if Path is None:
                        raise ImportError("matplotlib.path.Path is required for PathPatch rendering")

                    if not path_vertices:
                        path_vertices.append(arc_points[0])
                        path_codes.append(Path.MOVETO)
                    elif path_vertices[-1] != arc_points[0]:
                        path_vertices.append(arc_points[0])
                        path_codes.append(Path.LINETO)

                    for pt in arc_points[1:]:
                        path_vertices.append(pt)
                        path_codes.append(Path.LINETO)

                last_regular_point = next_regular_point
                index = next_index + 1
                continue

            if not path_vertices:
                if Path is not None:
                    path_codes.append(Path.MOVETO)
                path_vertices.append(current_point)
            elif path_vertices[-1] != current_point:
                if Path is not None:
                    path_codes.append(Path.LINETO)
                path_vertices.append(current_point)

            last_regular_point = current_point
            index += 1

        if Path is not None and len(path_vertices) >= 2:
            path_codes = path_codes[:len(path_vertices)]
            path = Path(path_vertices, path_codes)
            patch_kwargs = dict(kwargs)
            if "color" in patch_kwargs and "edgecolor" not in patch_kwargs and "ec" not in patch_kwargs:
                patch_kwargs["edgecolor"] = patch_kwargs.pop("color")
            else:
                patch_kwargs.pop("color", None)
            patch_kwargs.pop("marker", None)
            patch_kwargs.pop("markersize", None)
            patch_kwargs.pop("ms", None)
            patch_kwargs.pop("label", None)
            patch_kwargs.setdefault("fill", False)
            patch_kwargs.setdefault("facecolor", "none")
            ax.add_patch(PathPatch(path, **patch_kwargs))

        try:
            ax.relim()
            ax.autoscale_view()
        except Exception:
            pass

        if ax is not None and hasattr(ax, "figure"):
            ax.figure.canvas.draw_idle()
            if created_fig:
                try:
                    import matplotlib
                    backend = matplotlib.get_backend().lower()
                    if backend not in ("agg", "pdf", "ps", "svg", "template"):
                        ax.figure.show()
                except Exception:
                    pass
                
        #绘制voids
        if plotVoids:
            voids = self.getVoids()
            for v in voids:
                v.plot(ax=ax,**kwargs)  
                
        return ax

    def GetName(self):
        return getPrimitiveName(self.obj, self.edbApp)


class EdbPrimitives(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        
        layout.Primitives
        '''
        super(EdbPrimitives,self).__init__(edbApp,type="Primitives",definitionClass=EdbPrimitive)

#

    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            if hasattr(self.edbApp.layout,self.type):
                objs = getattr(self.edbApp.layout,self.type)
                self._definitionDict = {}
                self._definitionDict  = ComplexDict(dict([(getPrimitiveName(p,self.edbApp),self.definitionClass(p,self.edbApp)) for p in objs]))
            else:
                self._definitionDict = {}
        return self._definitionDict
    
    
    
