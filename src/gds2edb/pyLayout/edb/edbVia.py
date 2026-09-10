
#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-15

'''
pingroup for edb function
'''
import os,sys,re
from ..common.common import *
from ..common.complexDict import ComplexDict
from ..primitive.geometry import Point,Polygon

from .edbDefinition import EdbDefinition,EdbDefinitions

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

# if isIronpython:
#     import clr as _clr # @UnresolvedImport
# elif is_linux:
#     try:
#         from ansys.aedt.core.generic.clr_module import _clr # @UnresolvedImport
#     except:
#         log.info("Make sure pyaedt have installed on linux: pip install pyaedt")
#         from ansys.aedt.core.internal.clr_module import _clr # @UnresolvedImport
# else:
#     #for windows
#     import clr as _clr # @UnresolvedImport
    
    
try:
    _clr = initClr()
    from System import String
except:
    log.debug("CLR initialization failed in child process (likely duplicate init). Ignoring if not needed.")


def getViaName(via,edbApp):
    if via.IsLayoutPin():
        return "%s-%s"%(via.GetComponent().GetName(),via.GetName())
    else:
        name = ""
        if isIronpython:
            val = _clr.StrongBox[str]()
            rst = via.GetProductProperty(edbApp.Edb.ProductId.Designer, 11, val)
            if rst:
                name = val.Value
        else:
            val = String("")
            #edbApp.Edb.ProductId.Designer  0 Deprecated. use Hfss3DLayout instead.  
            _, name = via.GetProductProperty(edbApp.Edb.ProductId.Designer, 11, val)
        
        name = str(name).strip("'")

#         edbApp.SetProductProperty(edbApp.Edb.ProductId.Designer, 11, name)
        return name


class EdbVia(EdbDefinition):
    def __init__(self,pin,edbApp=None):
        super(EdbVia,self).__init__(pin,type="EdbVia",edbApp=edbApp)

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return

        maps = {
            "Name":{"Key":"self","Get":lambda s:s.GetName()},
            "ID":{"Key":"self","Get":lambda s:s.GetId()},
            "ObjType":{"Key":"self","Get":lambda s:s.obj.GetObjType().ToString()},
            "Net":{"Key":"self","Get":lambda s:s.obj.GetNet(),"Set":lambda s,x:s.SetNet(x)},
            "NetName":{"Key":"self","Get":lambda s:s.obj.GetNet().GetName()},
            "Group":{"Key":"self","Get":lambda s:s.obj.GetGroup()},
            "GroupName":{"Key":"self","Get":lambda s:s.obj.GetGroup().GetName()},
            "Component":{"Key":"self","Get":lambda s:s.edbApp.Components[s.obj.GetComponent()]},
            "ComponentName":{"Key":"self","Get":lambda s:s.obj.GetComponent().GetName()},
            "PinGroups":{"Key":"self","Get":lambda s:s.obj.GetPinGroups()},
            "PinGroupName":{"Key":"self","Get":lambda s:s.obj.GetPinGroups().GetName()},
            "Layer":{"Key":"self","Get":lambda s:s.obj.GetLayer()},
            "LayerName":{"Key":"self","Get":lambda s:s.obj.GetLayer().GetName()},
            "Location":{"Key":"self","Get":lambda s:s.getLocation()},
            "IsPin":{"Key":"self","Get":lambda s:s.IsLayoutPin()},
            "IsVia":{"Key":"self","Get":lambda s:not s.IsLayoutPin()},
        }

        self.maps.update(maps)
        self._info.update("self", self)
        self._info.setMaps(self.maps)
        self.parsed = True

    def getLocation(self):
        rst = self.obj.GetPositionAndRotation()
        if rst[0]:
            return Point((lambda l:[l.X.ToDouble(),l.Y.ToDouble()])(rst[1]))
        else:
            return None
    
    def getHoleDiameter(self):
        rst = self.obj.GetHoleOverrideValue()
        if rst[0]:
            return rst[1].ToDouble()
        else:
            return None

    def GetName(self):
        return getViaName(self.obj,self.edbApp)

class EdbVias(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(EdbVias,self).__init__(edbApp,type="PadstackInstances",definitionClass=EdbVia)

    #via GetName only give short name
    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            if hasattr(self.edbApp.layout,self.type):
                objs = getattr(self.edbApp.layout,self.type)
                self._definitionDict = {}
                self._definitionDict  = ComplexDict(dict([(getViaName(p,self.edbApp),self.definitionClass(p,self.edbApp)) for p in objs]))
            else:
                self._definitionDict = {}
        return self._definitionDict