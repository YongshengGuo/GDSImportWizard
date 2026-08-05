#coding:utf-8
#--- coding=utf-8
#--- @author: yongsheng.guo@ansys.com
#--- @Time: ver 1.0 20211121 
#--- @Time: ver 6.0 20260227

'''
{
"Header": {},
"Unit": "um",
"Conductors": [],
"Dielectrics": [],
"Vias": [],
"Insulatings": [],
"Options":{}
}


layer:{
    'LayerName': None,
    'Type': None,
    'LayerMap': None,
    'TextLayerMap': None,
    'Thickness': None,
    'Height': None,
    'LowerLayer': None,
    'UpperLayer': None,
    'DK': None,
    'DF': None,
    'Cond': None,
    'TC1': None,
    'TC2': None,
    'Tref': None
}

Conductor:{
LayerName:None
Thickness:None
Height: None
Material:None
layerMap:None
DummyLayerMap:None
TextLayerMap: None
}

Dielectric:{
LayerName:None
Thickness:None
Height: None
Material:None
}


Via:{
LayerName:None
Lower:None
Upper: None
Material:None
}

for Material:{
Conductivity:{value:xxx,TemperatureDependence:{Tref,TC1,TC2}}
DielectricConstant:xxx
}

'''


import os,sys
try:
    from gds2edb.layermap import LayerMap
except Exception:
    from layermap import LayerMap
from options import options


sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim\pyLayout")
import re
from copy import deepcopy
from math import sqrt,log,exp
from pyLayout import writeJson, loadJson
from pyLayout import loadCSV,writeCSV,findDictValue
from pyLayout import log,ComplexDict
from decimal import Decimal


class TechBase(object):
    '''
    classdocs
    '''
    #precision = 6
    
    #input, tech: dict or json
    def __init__(self, tech = None):
        '''
        Constructor
        '''

        self._tech = ComplexDict({
            "Header": {},
            "Unit": "um",
            "Conductors": [],
            "Dielectrics": [],
            "Vias": [],
            "Insulatings": [],
            "Options":{}
        })

        if tech:
            if isinstance(tech, (dict,ComplexDict)):
                self._tech.updates(tech)
            elif isinstance(tech, (str)):
                self._tech.updates(loadJson(tech))
            elif isinstance(tech, (TechBase)):
                self._tech.updates(tech._tech)
            else:
                log.exception("Tech input error.")

    @property
    def Tech(self):
        return self._tech
               
    @property
    def Header(self):
        return self.Tech["Header"]

    @property
    def Conductors(self):
        return self.Tech["Conductors"]
    
    @property
    def Dielectrics(self):
        return self.Tech["Dielectrics"]        

    @property
    def Vias(self):
        return self.Tech["Vias"]

    @property
    def Insulatings(self):
        return self.Tech["Insulatings"]  
    @property
    def Options(self):
        return self.Tech["Options"]

    def addLayer(self,layer):
        """typ:Conductors,Dielectrics, Vias, Insulatings"""

        layerTemp={
            'LayerName': None,
            'Type': None,
            'LayerMap': None,
            'TextLayerMap': None,
            'Thickness': None,
            'Height': None,
            'LowerLayer': None,
            'UpperLayer': None,
            'DK': None,
            'DF': None,
            'Cond': None,
            'TC1': None,
            'TC2': None,
            'Tref': None
        }
        layerTemp.update(layer)

        if not layerTemp["Type"]: 
            log.exception("addLayer: Layer type is not defined:%s"%str(layer))

        fLayer = self.findLayer(layerTemp["LayerName"],layerTemp["Type"])
        if fLayer:
            fLayer.updates(layerTemp)
        else:
            self.Tech[layerTemp["Type"]].append(layerTemp)

    
        
    def findLayer(self,name,typ = "Conductors"):
        """typ:Conductors,Dielectrics, Vias, Insulatings, All"""
        
        if typ.lower() == "all":
            for each in ["Conductors","Dielectrics", "Vias"]:
                rst = self.findLayer(name, each)
                if rst:
                    return rst
            return None
        
        layers = self.Tech[typ]
        if isinstance(name, str):
            for layer in layers:
                if layer["LayerName"].lower() == name.lower():
                    return layer
            
        #get by index
        #判断name是否为数字，如果是数组则按照Index返回layer
        idx = None
        if isinstance(name, int):
            idx = name
        elif isinstance(name, str):
            name_str = name.strip()
            if re.match(r"^[+-]?\d+$", name_str):
                idx = int(name_str)

        if idx is not None and -len(layers) <= idx <= len(layers):
            if idx>0:
                idx = idx-1 #layer index start from 1
            return layers[idx]
        
        return None
    
    
    def copy(self):
#         _techDict = deepcopy(self._tech.Dict)
#         return TechBase(_techDict)
        return deepcopy(self)
    
    def setLayerMap(self,layerMap):
        layerMap = LayerMap(layerMap) #layerMap file or dict
        #先清理掉self.Conductors + self.Vias原有的LayerMap和TextLayerMap设置为[]
        #通过self.Conductors + self.Vias的LayerName在layerMap中查找对应的LayerMapping设置到self.Conductors + self.Vias中
        #如果layerMap中没有对应的LayerMapping，则self.Conductors + self.Vias的LayerMapping设置为None
        #如果layerMap有多个LayerMapping，Purpose为drawing设置给LayerMap，Purpose为Text设置给TextLayerMap

        for layer in self.Conductors + self.Vias:
            layer["LayerMap"] = []
            layer["TextLayerMap"] = []

            layer_name = layer.get("LayerName")
            candidates = [layer_name] if layer_name else []

            # # Normalize common internal names to layermap aliases.
            # if layer_name:
            #     m = re.match(r"^metal(\d+)$", layer_name, re.IGNORECASE)
            #     if m:
            #         candidates.append("M" + m.group(1))
            #     v = re.match(r"^via(\d+)$", layer_name, re.IGNORECASE)
            #     if v:
            #         candidates.append("V" + v.group(1))

            mappings = []
            for key in candidates:
                if key in layerMap:
                    value = layerMap[key]
                    if isinstance(value, list):
                        mappings.extend(value)
                    elif isinstance(value, dict):
                        mappings.append(value)

            if not mappings:
                layer["LayerMap"] = None
                layer["TextLayerMap"] = None
                continue

            for mapping in mappings:
                purpose = str(mapping.get("LayerPurpose", "")).strip().lower()
                map_value = mapping.get("LayerMap")
                if not map_value:
                    continue

                if purpose == "drawing":
                    if map_value not in layer["LayerMap"]:
                        layer["LayerMap"].append(map_value)
                elif purpose in ["text", "pin", "label"]:
                    if map_value not in layer["TextLayerMap"]:
                        layer["TextLayerMap"].append(map_value)

            layer["LayerMap"] = " ".join(layer["LayerMap"]) if layer["LayerMap"] else None
            layer["TextLayerMap"] = " ".join(layer["TextLayerMap"]) if layer["TextLayerMap"] else None

    def toFloat(self):
        for layer in self.Conductors:
            layer["Height"] = float(layer["Height"])
            layer["Thickness"] = float(layer["Thickness"])
            
        for layer in self.Dielectrics:
            layer["Height"] = float(layer["Height"])
            layer["Thickness"] = float(layer["Thickness"])
            layer["DK"] = float(layer["DK"])

            
    def toDecimal(self):
        for layer in self.Conductors:
            layer["Height"] = Decimal(layer["Height"])
            layer["Thickness"] = Decimal(layer["Thickness"])
            # layer["DK"] = Decimal(layer["DK"])
            
        for layer in self.Dielectrics:
            layer["Height"] = Decimal(layer["Height"])
            layer["Thickness"] = Decimal(layer["Thickness"])
            layer["DK"] = Decimal(layer["DK"])
    
    def sort(self, rvs = False):
        #SortLayer
        self.Conductors.sort(key=lambda x:float(x['Height']),reverse = rvs)
        self.Dielectrics.sort(key=lambda x:float(x['Height']),reverse = rvs)
     
    def setIgnoreLayers(self,layerReg = None):
        IgnoreLayersReg = layerReg
        if isinstance(IgnoreLayersReg, str):
            IgnoreLayersReg = [IgnoreLayersReg]
            
        #log.info(",".join(IgnoreLayersReg), -1)
            
        for layer in self.Conductors:
            if any(map(lambda reg:re.match(reg+"$",layer["LayerName"]),IgnoreLayersReg)):
                log.info("Ignore layer: %s"%layer["LayerName"])
                layer["LayerMap"] = None
                layer["TextLayerMap"] = None
                
        for layer in self.Vias:
            if any(map(lambda reg:re.match(reg+"$",layer["LayerName"]),IgnoreLayersReg)):
                log.info("Ignore layer: %s"%layer["LayerName"])
                layer["LayerMap"] = None
                layer["TextLayerMap"] = None   

    def removeInvalidMetalLayers(self):
        # Remove conductor layers without valid drawing mapping.
        invalid_names = []
        valid_conductors = []
        for layer in self.Conductors:
            layer_map = layer.get("LayerMap")
            if layer_map in [None, "","0","0;0","0:0", []]:
                invalid_names.append(layer.get("LayerName"))
                log.info("remove invalid metal layer: %s" % layer.get("LayerName"))
                continue
            valid_conductors.append(layer)

        if invalid_names:
            self.Tech["Conductors"] = valid_conductors

            # Clear vias that connect to removed metals.
            for via in self.Vias:
                if via.get("LowerLayer") in invalid_names:
                    via["LowerLayer"] = None
                if via.get("UpperLayer") in invalid_names:
                    via["UpperLayer"] = None

        return self
            
        
    def removeDuplicateDielectricLayers(self):
        
        layers = self.Dielectrics
        while True:
            flag = 0
            for i in range(len(layers)-1):
                if layers[i]["Height"] == layers[i+1]["Height"]:
                    dLayer = layers[i] if layers[i]["Thickness"]<= layers[i+1]["Thickness"] else layers[i+1]
                    flag =1
                    break
            if flag:
                log.info("merge Duplicate Layer %s"%dLayer["LayerName"])
                layers.remove(dLayer)
            else:
                break

    def setBase(self,base = None):
        hights = [l["Height"] for l in self.Dielectrics]
        if base == None:
            base = min(hights)
            
        for layer in self.Conductors:
            layer["Height"] -= base

        for layer in self.Dielectrics:
            layer["Height"] -= base


    def useSheetLayer(self,sheetLayerThreshold = 0):
        sheetLayerThreshold = sheetLayerThreshold or options["SheetLayerThreshold"]
        #convert 0.001um to sheet(0um) (xxxx)
        sheetLayerThreshold = Decimal(sheetLayerThreshold)
        for layer in self.Conductors:
            if layer["Thickness"] < sheetLayerThreshold:
                log.info("use sheet layer on: %s"%layer["LayerName"])
                layer["Thickness"] = 0

    def useDefaultDF(self,df = None):
        df = df or float(options["UseDefaultDF"])
        if not df:
            return

        for layer in self.Dielectrics:
            if layer["Cond"]:
                continue

            log.info("use default df on: %s"%layer["LayerName"])
            layer["DF"] = df
        
                
    def fixeLayerGap(self,gap = 0):
        fixedGap = gap or options["FixedSmallLayerGap"]
        fixedGap = Decimal(fixedGap)
        self.sort()
        dieList = self.Dielectrics
        metalList = self.Conductors
        #fixed dielectric gap
        for i in range(len(dieList)-1):
            d1_h = dieList[i]['Height'] + dieList[i]['Thickness']
            d2_l = dieList[i+1]['Height']
            gap = d2_l -d1_h
            if abs(gap)>0 :
                #dieList[i+1]['Height'] = d1_h
                dieList[i]['Thickness'] += gap
                log.info("Fix small layer gap: %s %s %s"%(dieList[i]["LayerName"],dieList[i+1]["LayerName"],gap))
        
        for metal in metalList:
            for die in dieList:
                gap = metal['Height']-die['Height']
                if abs(gap)<fixedGap and abs(gap)>0:
                    metal['Height'] -= gap
                    log.info("Fix small layer gap: %s %s"%(metal["LayerName"],gap))
#                     continue
                gap = metal['Height']-die['Height']-die['Thickness']
                if abs(gap)<fixedGap and abs(gap)>0:
                    metal['Height'] -= gap
                    log.info("Fix small layer gap: %s %s"%(metal["LayerName"],gap))
#                     continue
                gap = metal['Height'] + metal['Thickness']-die['Height']
                if abs(gap)<fixedGap and abs(gap)>0:
                    metal['Height'] -= gap
                    log.info("Fix small layer gap: %s %s"%(metal["LayerName"],gap))
#                     continue
                gap = metal['Height'] + metal['Thickness']-die['Height']-die['Thickness']
                if abs(gap)<fixedGap and abs(gap)>0:
                    metal['Height'] -= gap
                    log.info("Fix small layer gap: %s %s"%(metal["LayerName"],gap))
        
    def averageDK(self,layers):
        mdk = 1 
        if len(layers) == 1:
            mdk = layers[-1]["DK"]
        elif len(layers) > 1:
        #Weighted Average, Weighted Capacitance, Kraszewski equation, Landau equation, Lichtenecker equation    
            options["MergeDielectricMethod"] = int(options["MergeDielectricMethod"])        
            if options["MergeDielectricMethod"] == 0:
                mdk = sum([float(d["DK"])*float(d["Thickness"]) for d in layers])/sum([float(d["Thickness"]) for d in layers]) 
            elif options["MergeDielectricMethod"] == 1:
                mdk = sum([float(d["Thickness"]) for d in layers])/ sum([float(d["Thickness"])/float(d["DK"]) for d in layers])
            elif options["MergeDielectricMethod"] == 2:
                mdk = (sum([float(d["Thickness"])*sqrt(float(d["DK"])) for d in layers])/sum(float(d["Thickness"]) for d in layers))**2                    
            elif options["MergeDielectricMethod"] == 3:
                mdk = (sum([float(d["Thickness"])*(float(d["DK"]))**(1.0/3) for d in layers])/sum(float(d["Thickness"]) for d in layers))**3
            elif options["MergeDielectricMethod"] == 4:
                mdk = exp(sum([float(d["Thickness"])*log(float(d["DK"])) for d in layers])/sum(float(d["Thickness"]) for d in layers))                                      
        else:
            mdk = 1 
            
        return mdk
    
    def mergeThinLayer(self,tech=None):
        #must sort and float the layers first
        if not tech:
            tech = self.copy()
        else:
            tech = tech.copy()
        
        flag = 0
        layers = tech.Dielectrics
        for i in range(len(layers)-1):
            j = i-1 if i>0 else i+1
            k = i+1 if i<len(layers) else i-1
            threshold = options["DkDeviationThreshold"]
            #modify 202-04-21    
            if "%" in str(threshold):
                threshold =  Decimal(threshold.replace("%",""))*Decimal("0.01")
            else:
                threshold =  Decimal(threshold)
                
            #DK merge
            if abs(layers[i]["DK"]-layers[k]["DK"])< \
                min(layers[i]["DK"],layers[k]["DK"])*threshold:
                if layers[i]["Thickness"]> layers[k]["Thickness"]:
                    dLayer = layers[k] 
                    mLayer = layers[i]
                else:
                    dLayer = layers[i] 
                    mLayer = layers[k]
                flag =1
                break
            
            #Thickness merge
            ThinDielectricThreshold = Decimal(options["ThinDielectricThreshold"])
            if layers[i]["Thickness"]<ThinDielectricThreshold:
                dLayer = layers[i]
                mLayer = layers[j] if layers[j]["DK"]<= layers[k]["DK"] else layers[k]
                flag =1
                break
        if flag:
            if options["UseShortMergeLayerName"]:
                name_count1 = dLayer["LayerName"].split('-') 
                name1 = name_count1[0]
                count1 = int(name_count1[-1]) if len(name_count1)>1 else 1
                name_count2 = mLayer["LayerName"].split('-') 
                name2 = name_count2[0]
                count2 = int(name_count2[-1]) if len(name_count2)>1 else 1
                mLayer["LayerName"] = ("{0}-{1}-{2}".format(name2,name1,count1+count2))
            else:
                mLayer["LayerName"] = mLayer["LayerName"] + "_" + dLayer["LayerName"]

            mLayer["Thickness"] += dLayer["Thickness"]
            mLayer["DK"] = Decimal(self.averageDK([mLayer,dLayer])).quantize(Decimal("0.00"))
            mLayer["Height"] = min([mLayer["Height"],dLayer["Height"]])
            log.info("merge layer %s %s %s, averageDK %s"%(dLayer["LayerName"],dLayer["Thickness"],dLayer["DK"],mLayer["DK"]))
            layers.remove(dLayer)
            return self.mergeThinLayer(tech)
        else:
            return tech
        
    
    def mergeByLayer(self,tech=None):
        '''
        简化和分割介质层，以金属层为基准，假设介质和金属材料已经排序，所有数字已经转换为Decimal类型，
        所有介质层的高度和厚度已经计算好，所有金属层的高度和厚度已经计算好
        1. 以金属层为基准，计算金属层的上表面和下表面高度，按照高度获取介质层，计算介质层的上表面和下表面高度，
        按照上下高度切割介质层，计算切割后的介质层的averageDK，参数，作为新的介质层，添加到新的介质层列表中，
        LayerName按照原有的金属{LayerName}_fill进行命名
        2. 以临近的两个金属层为基础，计算两个金属层的上表面和下表面高度，按照高度获取介质层，
        按照上下高度切割介质层，计算切割后的介质层的averageDK，参数，作为新的介质层，添加到新的介质层列表中，
        LayerName按照原有的{起始介质LayerName}_{结束介质LayerName}_{介质层数量}进行命名
        3. 最上方金属层的上方和最下方金属层的下方介质，按照规则进行整体合并处理。
        4. 当介质层存在电导率时（硅材料），不进行切割和合并，直接添加到新的介质层列表中
        
        可以比照mergeThinLayer进行实现
        '''
        if not tech:
            tech = self.copy()
        else:
            tech = tech.copy()
            
        metals = tech.Conductors
        dies = tech.Dielectrics

        if not dies:
            return tech

        new_dielectrics = []

        def _bounds(layer):
            low = Decimal(layer["Height"])
            up = low + Decimal(layer["Thickness"])
            return low, up

        def _collect_pieces(low, up):
            pieces = []
            for dlayer in dies:
                dlow, dup = _bounds(dlayer)
                if dup <= low or dlow >= up:
                    continue

                piece = deepcopy(dlayer)

                # low side cut: move Height to cut position and trim Thickness.
                if dlow < low:
                    piece["Height"] = low
                    piece["Thickness"] = dup - low

                # up side cut: keep Height unchanged and trim Thickness only.
                if dup > up:
                    piece["Thickness"] = up - piece["Height"]

                if piece["Thickness"] > 0:
                    pieces.append(piece)
            pieces.sort(key=lambda x: x["Height"])
            return pieces

        def _make_layer(name, low, up, pieces):
            if up <= low:
                return None

            layer = {
                "LayerName": name,
                "Type": "Dielectrics",
                "LayerMap": None,
                "TextLayerMap": None,
                "Thickness": up - low,
                "Height": low,
                "LowerLayer": None,
                "UpperLayer": None,
                "DK": Decimal("1.0"),
                "DF": None,
                "Cond": None,
                "TC1": None,
                "TC2": None,
                "Tref": None,
            }

            if pieces:
                total_t = sum([Decimal(p["Thickness"]) for p in pieces])
                if total_t > 0:
                    dk_avg = self.averageDK(pieces)
                    layer["DK"] = dk_avg if isinstance(dk_avg, Decimal) else Decimal(str(dk_avg))

            return layer

        intervals = []

        for metal in metals:
            mlow, mup = _bounds(metal)
            if mup > mlow:
                intervals.append((mlow, mup, "%s_fill" % metal["LayerName"], "metal"))

        if len(metals) >= 2:
            for i in range(len(metals) - 1):
                _, m1_up = _bounds(metals[i])
                m2_low, _ = _bounds(metals[i + 1])
                if m2_low > m1_up:
                    intervals.append((m1_up, m2_low, None, "between"))

        if metals:
            m_low, _ = _bounds(metals[0])
            _, m_up = _bounds(metals[-1])
            d_low = min([_bounds(d)[0] for d in dies])
            d_up = max([_bounds(d)[1] for d in dies])

            if m_low > d_low:
                intervals.append((d_low, m_low, None, "edge"))
            if d_up > m_up:
                intervals.append((m_up, d_up, None, "edge"))
        else:
            d_low = min([_bounds(d)[0] for d in dies])
            d_up = max([_bounds(d)[1] for d in dies])
            intervals.append((d_low, d_up, None, "edge"))

        intervals.sort(key=lambda x: x[0])

        def _cond_gt_zero(layer):
            cond = layer.get("Cond")
            if cond in [None, "", 0, "0", "0.0"]:
                return False
            try:
                return Decimal(str(cond)) > 0
            except Exception:
                return bool(cond)

        for low, up, name, typ in intervals:
            pieces = _collect_pieces(low, up)
            if not pieces:
                continue
            #检测pieces里面的layer是否有Cond，如果有，则不进行切割和合并，直接添加到新的介质层列表中
            if any(_cond_gt_zero(p) for p in pieces):
                new_dielectrics.extend(pieces)
                continue
            
            if not name:
                start_name = pieces[0]["LayerName"]
                end_name = pieces[-1]["LayerName"]
                count = len(pieces)
                name = "%s_%s_%s" % (start_name, end_name, count)

            new_layer = _make_layer(name, low, up, pieces)
            if new_layer:
                new_dielectrics.append(new_layer)

        new_dielectrics.sort(key=lambda x: x["Height"])
        tech.Tech["Dielectrics"] = new_dielectrics
        return tech
        
    
    def simplifyTech(self,method = 0):
        """
        #must sort the layers first
        0:NoSimplify: No Merge on Dielectric, exact layers in IRCX
        1:MergeThinLayer: Merge layer thinner than a specific value
        2:BlockMerge:  use average DK on all layers except substrate
        """
            
        tech2 = self.copy()
        #清理layermap无效的金属层
        tech2.removeInvalidMetalLayers()
        
        # tech2.removeDuplicateLayers()
        # tech2.setIgnoreLayers()
        tech2.toDecimal()
        tech2.sort()
        method = int(method)
        if method == 0: 
            return tech2
                
        if method == 1:
            return self.mergeThinLayer(tech2)

        if method == 2:
            tech2.Options["DkDeviationThreshold"] = 0.2
            tech2.Options["ThinDielectricThreshold"] = 1
            return self.mergeThinLayer(tech2)
        if method == 3:
            return self.mergeByLayer(tech2)
    
    def removeInvalidLayers(self):
        # Remove conductor layers without valid drawing mapping.
        invalid_names = []
        valid_conductors = []
        for layer in self.Conductors:
            layer_map = layer.get("LayerMap")
            if layer_map in [None, "","0","0;0","0:0", []]:
                invalid_names.append(layer.get("LayerName"))
                log.info("remove invalid metal layer: %s" % layer.get("LayerName"))
                continue
            valid_conductors.append(layer)

        if invalid_names:
            self.Tech["Conductors"] = valid_conductors

            # Clear vias that connect to removed metals.
            for via in self.Vias:
                if via.get("LowerLayer") in invalid_names:
                    via["LowerLayer"] = None
                if via.get("UpperLayer") in invalid_names:
                    via["UpperLayer"] = None

        # remove vias without without valid LayerMap.
        valid_vias = []
        for via in self.Vias:
            layer_map = via.get("LayerMap")
            if layer_map in [None, "","0","0;0","0:0", []]:
                log.info("remove invalid via layer: %s" % via.get("LayerName"))
                continue
            valid_vias.append(via)
        self.Tech["Vias"] = valid_vias
        
        return self
    
    def writeJson(self,path):
        tech = self.copy()
        tech.toFloat()
        writeJson(path, tech.Tech)
        
    def toCSV(self,path):
        csv = []
        NO = 1
        self.sort(rvs = True)
        
        #---Dielectrics
        for layer in self.Tech["Dielectrics"]:
            row = {
                'LayerName': None,
                'Type': None,
                'LayerMap': None,
                'TextLayerMap': None,
                'Thickness': None,
                'Height': None,
                'LowerLayer': None,
                'UpperLayer': None,
                'DK': None,
                'DF': None,
                'Cond': None,
                'TC1': None,
                'TC2': None,
                'Tref': None
            }
            row.update(layer)
            csv.append(row)
            row["NO"] = NO
            NO += 1
            row["Type"] = "Dielectric"
            
        #---Conductors
        for layer in self.Tech["Conductors"]:
            row = {
                'LayerName': None,
                'Type': None,
                'LayerMap': None,
                'TextLayerMap': None,
                'Thickness': None,
                'Height': None,
                'LowerLayer': None,
                'UpperLayer': None,
                'DK': None,
                'DF': None,
                'Cond': None,
                'TC1': None,
                'TC2': None,
                'Tref': None
            }
            row.update(layer)
            csv.append(row)
            row["NO"] = NO
            NO += 1
            row["LayerName"] = layer["LayerName"]
            row["Type"] = "Conductor"
            
        #---Vias
        for layer in self.Tech["Vias"]:
            row = {
                'LayerName': None,
                'Type': None,
                'LayerMap': None,
                'TextLayerMap': None,
                'Thickness': None,
                'Height': None,
                'LowerLayer': None,
                'UpperLayer': None,
                'DK': None,
                'DF': None,
                'Cond': None,
                'TC1': None,
                'TC2': None,
                'Tref': None
            }
            row.update(layer)
            csv.append(row)
            row["NO"] = NO
            NO += 1
            row["Type"] = "Via"
            
    
        header = ["NO","LayerName","Type","LayerMap","TextLayerMap","Thickness","Height","LowerLayer","UpperLayer","DK","DF","Cond","TC1","TC2","Tref"]
        writeCSV(path,csv,header,fmt = "dict")
        return csv

    def toXml(self,path=None):

        xmlPath = ""
        if path:
            xmlPath = path
        elif options["ControlXmlPath"]:
            xmlPath = options["ControlXmlPath"]
        elif options["TechFile"]:
            xmlPath = os.path.splitext(options["TechFile"])[0] + ".xml"
        else:
            log.info("Please specify the path of control xml file.")


        stk = StackupXml
        
        xml = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' + '\n'
        xml +='<c:Control xmlns:c="http://www.ansys.com/control" schemaVersion="1.0">' + '\n'
        xml += g2e.Tech2Xml.Stackup.StackupXml  + '\n'
    #     xml += '<ImportOptions Flatten="true" GDSIIConvertPolygonToCircles="false" ImportDummyNet="%s" />'%("true" if g2e.Tech2Xml._options["ImportDummyNet"] else "false") + '\n'
        #20240104
        xml += '<ImportOptions Flatten="true" GDSIIConvertPolygonToCircles="true" GDSIIScalingFactor="%s" ImportDummyNet="%s"/>'%(
            g2e.Tech2Xml._options["GDSIIScalingFactor"],"true" if g2e.Tech2Xml._options["ImportDummyNet"] else "false") + '\n'
        
        xml += '<GDS_NET_DEFINITIONS NET_NAME_CASE_SENSITIVE="true" USE_TOP_LEVEL_TEXT_ONLY="false">' + '\n'
        
        xml += '<VDD_NETS>' + '\n'
        xml += ' <!--Add power Nets here-->' + '\n'
    #     xml += "\n".join(g2e.Tech2Xml.VDDNetList) + '\n'
        xml += '</VDD_NETS>' + '\n'
        xml += '<GND_NETS>' + '\n'
        xml += ' <!--Add gnd Nets here-->' + '\n'
    #     xml += "\n".join(g2e.Tech2Xml.GNDNetList) + '\n'
        xml += '</GND_NETS>' + '\n'        
        xml += '<SIGNAL_NETS>' + '\n'
        xml += ' <!--Add signal Nets here-->' + '\n'
    #     xml += "\n".join(g2e.Tech2Xml.signalNetList) + '\n'
        xml += '</SIGNAL_NETS>' + '\n'
        xml += '</GDS_NET_DEFINITIONS>' + '\n'
        xml += '</c:Control>' + '\n'  

        path = g2e.Tech2Xml.Options["ControlXmlPath"]
        with open(xmlPath, 'w+', encoding='utf-8') as f:
    #             f.write(Stackup(self.Tech).StackupXml)
            f.write(xml)
            f.close()
        
        print("finished write xml file: %s"%xmlPath)