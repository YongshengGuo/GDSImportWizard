#coding:utf-8
#--- coding=utf-8
#--- @author: yongsheng.guo@ansys.com
#--- @Time: ver 1.0 20211121 
#--- @Time: ver 6.0 20260227

# layer:{
#     'LayerName': None,
#     'Type': None,
#     'LayerMap': None,
#     'TextLayerMap': None,
#     'Thickness': None,
#     'Height': None,
#     'LowerLayer': None,
#     'UpperLayer': None,
#     'DK': None,
#     'DF': None,
#     'Cond': None,
#     'TC1': None,
#     'TC2': None,
#     'Tref': None
# }


import sys,os
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)
sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim")

import re
from pyLayout import log,regAnyMatch
from options import options


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

class Material(object):

    def __init__(self,name = "", materialDsp = {}):
        '''
        Constructor
        '''
        self.name = name
        self._materialDsp = materialDsp
        self._property = {}
        self._propertyTemp = {}
        self._isDepend = False
        self._parsed = False

        if materialDsp:
            self.parse()

    @property
    def MaterialXml(self):
        return self.getDependMaterialXml()
    
    @property
    def Def(self):
        if not self._property:
            self.parse()
        return self._property    
    
    
    def getDependMaterialXml(self):
        if not self._property:
            self.parse()

        if not self._property:
            return ""

        prop = []
        for k,v in self._property.items():
            if isinstance(v, dict):
                if "ThermalExpression" in v:
                    prop.append(('<{0}>' + "\n"
                    '<Double>{1}</Double>' + "\n"
                    '<ThermalExpression Expression="{ThermalExpression}"/>'.format(ThermalExpression=v["ThermalExpression"]) + "\n"
                    '</{0}>').format(k,v["Value"]))
                else:
                    prop.append(('<{0}>' + "\n"
                    '<Double>{1}</Double>' + "\n"
                    '</{0}>').format(k,v["Value"]))
            else:
                prop.append(('<{0}>' + "\n"
                '<Double>{1}</Double>' + "\n"
                '</{0}>').format(k,v))
        
        return(
            '<Material Name="{0}">' + "\n"
            '{1}' + "\n"
            '</Material>'
            ).format(self.name,"\n".join(prop))

    def parse(self):

        if self._parsed:
            return

        dsp = self._materialDsp
        if "DK" in dsp and dsp["DK"]:
            #20220609 convert Decimal to float
            self._property["Permittivity"] = float(dsp["DK"])

        if "DF" in dsp and dsp["DF"]:
            self._property["DielectricLossTangent"] = dsp["DF"]

        if "Cond" in dsp and dsp["Cond"]:
            self._property["Conductivity"] = dsp["Cond"]

        if "TC1" in dsp and dsp["TC1"] and abs(float(dsp["TC1"]))>1e-9:
            TC1 = float(dsp["TC1"])
            if "Tref" in dsp and dsp["Tref"]:
                Tref = float(dsp["Tref"])
            else:
                Tref = 25
            if "TC2" in dsp and dsp["TC2"]:
                TC2 = float(dsp["TC2"])
            else:
                TC2 = 0

            if "ChangeReferenceTemperature" in options and options["ChangeReferenceTemperature"]:
                Equation = "{cond}/(1+({TC1}*($AmbientTemperature -{Tref}))+({TC2}*($AmbientTemperature -{Tref})**2))".format(
                        cond = dsp["Cond"],TC1 = TC1, TC2 = TC2, Tref = Tref)
                refTempCond = Equation.replace("$AmbientTemperature",str(options["ChangeReferenceTemperature"]))
                cond = str(eval(refTempCond))
                Tref = options["ChangeReferenceTemperature"]
            else:
                cond = dsp["Cond"]

            self._property["Conductivity"] = {}
            self._property["Conductivity"]["Value"] = cond
            self._property["Conductivity"]["ThermalExpression"] = "1/(1+({TC1}*(Temp-{Tref}))+({TC2}*(Temp-{Tref})**2))".format(
                        TC1 = TC1, TC2 = TC2, Tref = Tref)
            self._property["Conductivity"]["Equation"] = "{cond}/(1+({TC1}*($AmbientTemperature-{Tref}))+({TC2}*($AmbientTemperature-{Tref})**2))".format(
                        cond = dsp["Cond"],TC1 = TC1, TC2 = TC2, Tref = Tref)
            self._isDepend = True
        self._parsed = True

class Layer(object):
    
    #precision = 6
    
    #inherited from tech
    Options = {}
    
    def __init__(self, layerDict, typ = "Conductor"):
        '''
        """typ:Conductor,Dielectric, Via, Insulating"""
        '''
        self._layerDict = layerDict
        self._type = typ
        self._layerDef = None
        self._xmlT = ""
        self._textXml = ""
        self.tsvDef = None
        
        if self._layerDict:
            self.parse()
        
#     @property
#     def precision(self):
#         return options["Precision" ] if "Precision" in options else 6  
        
        
    @property    
    def LayerDef(self):
        if not self._layerDef:
            self.parse()
        return self._layerDef
    
    @property
    def LayerXml(self):
        if not self._layerDef:
            self.parse()

        xml = self._xmlT.format(**self.LayerDef)
        return xml
    
    @property
    def TextXml(self):
        if not self._layerDef:
            self.parse()

        return self._textXml
    
    @property
    def Material(self):
        if self._type in ["Conductor","Via"]:
            name = self._layerDict["LayerName"]+"_cond"
        elif self._type in ["Insulating"]:
            name = self._layerDict["LayerName"]+"_Insulating"
        else:
            name = self._layerDict["LayerName"]
            
        return Material(name,self._layerDict)

    @property
    def Name(self):
        return self._layerDict["LayerName"]
        
    
    def getLayerXml(self):
        return self._xmlT.format(**self.LayerDef)
        
        
    def parse(self):
        layerDef = {}
        self._layerDef = layerDef
        layerDict = self._layerDict
        if self._type == "Conductor":
            layermap = re.split(r"[;:,-]+", layerDict["LayerMap"])
            layerDef["Name"] = layermap[0]
            layerDef["GDSDataType"] = layermap[1] if len(layermap)>1 else 0
            layerDef["Material"] = layerDict["LayerName"]+"_cond"
            layerDef["TargetLayer"] = layerDict["LayerName"]
            layerDef["Type"] = "conductor"
            layerDef["Thickness"] = layerDict["Thickness"]
            layerDef["Elevation"] = layerDict["Height"]
            #'<Layer Name="170" Material="ubump_cond" GDSDataType="0" TargetLayer="ubump" Type="conductor" Thickness="0.0" Elevation="145.841" />'
            self._xmlT = '<Layer Name="{Name}" Material="{Material}" GDSDataType="{GDSDataType}" TargetLayer="{TargetLayer}" Type="{Type}" Thickness="{Thickness}" Elevation="{Elevation}" '
#             if options["ConvertPolygonToCircle"] and options["VersionKey"]>"212":

            if options["ConvertPolygonToCircleOnLayers"] and regAnyMatch(re.split(r"[;,\s]+", options["ConvertPolygonToCircleOnLayers"]),self.Name):
                self._xmlT += ' ConvertPolygonToCircle="true" ConvertPolygonToCircleRatio="%s" '%options["ConvertPolygonToCircleRatio"]
            
            if options["UnionPrimitivesOnLayer"] and regAnyMatch(re.split(r"[;,\s]+", options["UnionPrimitivesOnLayer"]),self.Name):
                self._xmlT += ' UnionPrimitives="true"'

            if options["ReconstructArcsOnLayers"] and regAnyMatch(re.split(r"[;,\s]+", options["ReconstructArcsOnLayers"]),self.Name):
                self._xmlT += ' ReconstructArcs="true" ArcTolerance="{ArcTolerance}"'.format(ArcTolerance=options["ArcTolerance"])

            if options["SolveInsideOnLayers"] and regAnyMatch(re.split(r"[;,\s]+", options["SolveInsideOnLayers"]),self.Name):
                self._xmlT += ' SolveInside="true"'

            self._xmlT += '/>'
            
        elif self._type == "Via":
            #layermap = layerDict["LayerMap"]["Layer"].split(":")
            layermap = re.split(r"[;:,-]+", layerDict["LayerMap"])
            layerDef["Name"] = layermap[0]
            layerDef["GDSDataType"] = layermap[1] if len(layermap)>1 else 0
            #layerDef["Name"],layerDef["GDSDataType"] = layerDict["LayerMap"]["Layer"].split(":")
            layerDef["Material"] = layerDict["LayerName"]+"_cond"
            layerDef["TargetLayer"] = layerDict["LayerName"]
            layerDef["Type"] = "via"
            layerDef["StartLayer"] = layerDict["UpperLayer"]
            layerDef["StopLayer"] = layerDict["LowerLayer"]
            
            self._xmlT = '<Layer Name="{Name}" Material="{Material}" GDSDataType="{GDSDataType}" TargetLayer="{TargetLayer}"  StartLayer="{StartLayer}" StopLayer="{StopLayer}" '
            
            if options["ConvertPolygonToCircleOnLayers"] and regAnyMatch(re.split(r"[;,\s]+", options["ConvertPolygonToCircleOnLayers"]),self.Name):
                self._xmlT += ' ConvertPolygonToCircle="true" ConvertPolygonToCircleRatio="%s" '%options["ConvertPolygonToCircleRatio"]
            
            if options["UnionPrimitivesOnLayer"] and regAnyMatch(re.split(r"[;,\s]+", options["UnionPrimitivesOnLayer"]),self.Name):
                self._xmlT += ' UnionPrimitives="true"'

            if options["ReconstructArcsOnLayers"] and regAnyMatch(re.split(r"[;,\s]+", options["ReconstructArcsOnLayers"]),self.Name):
                self._xmlT += ' ReconstructArcs="true" ArcTolerance="{ArcTolerance}"'.format(ArcTolerance=options["ArcTolerance"])

            if options["SolveInsideOnLayers"] and regAnyMatch(re.split(r"[;,\s]+", options["SolveInsideOnLayers"]),self.Name):
                self._xmlT += ' SolveInside="true"'

            self._xmlT += '>' + "\n"
            
            if options["CreatViaGroups"] and not regAnyMatch(re.split(r"[;,\s]+", options["NotUseViaGroupsOnLayers"]),layerDict["LayerName"]):
                xmlCreatViaGroupsOption = ['{0}="{1}"'.format(*y) for y in  [x.split(":") for x in options["CreatViaGroupsOption"].split(",")] ]
                self._xmlT += '<CreateViaGroups %s />'%" ".join(xmlCreatViaGroupsOption) + "\n"
                self._xmlT += '<SnapViaGroups Method="areaFactor" Tolerance="3" RemoveUnconnected="true" />' + "\n"
                
            if self.tsvDef:
                self._xmlT += '<TSVProperties Thickness="{0}" Material="{1}" />\n'.format(self.tsvDef._layerDict["Thickness"],self.tsvDef.Material.name)

            self._xmlT += '</Layer>'
            
        elif self._type == "Dielectric":
            layerDef["Name"] = layerDict["LayerName"]
            layerDef["Material"] = layerDict["LayerName"]
            layerDef["Thickness"] = layerDict["Thickness"]
            self._xmlT = '<Layer Name="{Name}" Material="{Material}"  Thickness="{Thickness}"/>'
        
        elif self._type == "Insulating":
            pass

        else:
            log.error("Not support layer type: %s"%self._type)
            
            
        #---TextLayerMap
        if self._layerDict["TextLayerMap"]:
            TextLayerMap = re.split(r"[;:,-]+", self._layerDict["TextLayerMap"])
            layerDef["TextName"] = TextLayerMap[0]
            layerDef["TextGDSDataType"] = TextLayerMap[1] if len(TextLayerMap)>1 else 0
            _textXml = '<Layer Name="{TextName}" Material="{Material}" GDSDataType="{TextGDSDataType}" TargetLayer="{TargetLayer}" Type="{Type}" Thickness="{Thickness}" Elevation="{Elevation}" />'
            self._textXml = _textXml.format(**self.LayerDef)
        

class ControlXml(object):
    '''
    classdocs.
    '''
    def __init__(self, tech = None):
        '''
        Constructor
        '''
        self._tech = tech
        self._parsed = False
        

    @property
    def Tech(self):
        return self._tech

    @property
    def Materials(self):
        if not self._MaterialList:
            self.parseTech()
        return dict([(m.name,m.Def) for m in self._MaterialList])

    def preOptionsLayer(self):
        #归一化Options layers,以self._conductorList
        if "UnionPrimitivesOnLayer" in options and options["UnionPrimitivesOnLayer"]:
            layers = re.split(r"[;,\s]+", options["UnionPrimitivesOnLayer"])
            UnionPrimitivesOnLayer = []
            for layer in layers:
                condLayer = self._tech.findLayer(layer)
                if not condLayer:
                    log.warning("UnionPrimitivesOnLayer layer %s not found in tech file"%layer)
                    continue
                else:
                    UnionPrimitivesOnLayer.append(condLayer["LayerName"])
            options["UnionPrimitivesOnLayer"] = ",".join(UnionPrimitivesOnLayer)
        if "ComponentOnLayers" in options and options["ComponentOnLayers"]:
            layers = re.split(r"[;,\s]+", options["ComponentOnLayers"])
            ComponentOnLayers = []
            for layer in layers:
                condLayer = self._tech.findLayer(layer)
                if not condLayer:
                    log.warning("ComponentOnLayers layer %s not found in tech file"%layer)
                    continue
                else:
                    ComponentOnLayers.append(condLayer["LayerName"])
            options["ComponentOnLayers"] = ",".join(ComponentOnLayers)


    def parse(self):
        if self._parsed: 
            return
        tech = self._tech
        tech.removeInvalidLayers()
        tech.sort()
        self.preOptionsLayer()
        
        self._conductorList = []
        self._dielectricList = []
        self._ViaList = []
        self._MaterialList = []
        
        for layer in tech.Conductors:
            if layer["LayerMap"] in ["0:0","0",None,"0;0"]:# == "0:0" or not layer["LayerMap"]["Layer"]:
                continue
            
            #layerMaps = re.split(r"[;:,-]+", layer["LayerMap"]["Layer"])
            #Modify 20220326, support multi layermap to one 3DL layer
            layerMaps = layer["LayerMap"].split() #multi layermap split by space
            for layerMap in layerMaps:
                layer1 = layer.copy()
                layer1["LayerMap"] = layer["LayerMap"]
                layer1["LayerMap"]= layerMap
                sLayer = Layer(layer1,typ = "Conductor")
                self._conductorList.append(sLayer)
            self._MaterialList.append(sLayer.Material)
            

        for layer in tech.Vias:
            if layer["LayerMap"] in ["0:0","0",None,"0;0"]:# == "0:0" or not layer["LayerMap"]["Layer"]:
                continue
            
            #Modify 20220326, support multi layermap to one 3DL layer
            layerMaps = layer["LayerMap"].split() #multi layermap split by space
            for layerMap in layerMaps:
                layer1 = layer.copy()
                layer1["LayerMap"] = layer["LayerMap"]
                layer1["LayerMap"] = layerMap
                sLayer = Layer(layer1,typ = "Via")
                self._ViaList.append(sLayer)
            self._MaterialList.append(sLayer.Material)

        for layer in tech.Dielectrics:  
            sLayer = Layer(layer,typ = "Dielectric")
            self._dielectricList.append(sLayer)
            self._MaterialList.append(sLayer.Material)
            
        for layer in tech.Insulatings:
            sLayer = Layer(layer,typ = "Insulating")
            self._MaterialList.append(sLayer.Material)
            
            for via in self._ViaList:
                if via.Name.lower() == layer["LayerName"].lower():
                    via.tsvDef = sLayer

        self._parsed = True
        
    def getStackupXml(self):
        materialXml = "\n".join([m.MaterialXml for m in self._MaterialList])
        dielectricXml = "\n".join([l.LayerXml for l in self._dielectricList])
        conductorXml = "\n".join([l.LayerXml for l in self._conductorList])
        textXml = "\n".join([l.TextXml for l in self._conductorList if l.TextXml])
        viaXml = "\n".join([l.LayerXml for l in self._ViaList])

        xml = (
            '<Stackup schemaVersion="1.0">' + '\n'
            '<Materials>' + '\n'
            '{0}' + '\n'
            '</Materials>' + '\n'
            '<ELayers LengthUnit="um" MetalLayerSnappingTolerance="%s">' %(options["MetalLayerSnappingTolerance"].strip()+options["DefaultUnit"]) + '\n'
           '<Dielectrics>' + '\n'
           '{1}' + '\n'
           '</Dielectrics>' + '\n'
           '<Layers>' + '\n'
           '{2}'  + '\n'
           '</Layers>'  + '\n'
            ).format(materialXml,dielectricXml,conductorXml + "\n" + textXml)
        
        #if not have via, via xml should not present
        if viaXml.strip():
            xml += (
               '<Vias>'  + '\n'
               '{0}' + '\n'
               '</Vias>' + '\n' 
                ).format(viaXml)
        
        xml += (
           '</ELayers>' + '\n'
           '</Stackup>'
            )

        return xml
    
    def writeControlXml(self,path=None):
        self.parse()

        xmlPath = ""
        if path:
            xmlPath = path
        elif "ControlXmlPath" in options and options["ControlXmlPath"]:
            xmlPath = options["ControlXmlPath"]
        elif options["TechFile"]:
            xmlPath = os.path.splitext(options["TechFile"])[0] + ".xml"
        else:
            log.info("Please specify the path of control xml file.")

        stackupXml = self.getStackupXml()

        
        xml = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' + '\n'
        xml +='<c:Control xmlns:c="http://www.ansys.com/control" schemaVersion="1.0">' + '\n'
        xml += stackupXml  + '\n'
    #     xml += '<ImportOptions Flatten="true" GDSIIConvertPolygonToCircles="false" ImportDummyNet="%s" />'%("true" if options["ImportDummyNet"] else "false") + '\n'
        #20240104
        xml += '<ImportOptions DeleteEmptyNonLaminateSignalLayers="%s" Flatten="true" GDSIIConvertPolygonToCircles="true" GDSIIScalingFactor="%s" ImportDummyNet="%s"/>'%(
            "true" if options["DeleteEmptyNonLaminateSignalLayers"] else "false", options["GDSIIScalingFactor"],"true" if options["ImportDummyNet"] else "false") + '\n'
        
        #---CutoutPolygon
        if "CutoutPolygon" in options and options["CutoutPolygon"]:
            points = options["CutoutPolygon"].split(";")
            if len(points) < 3:
                log.error("CutoutPolygon should be at least 3 points and more")
            else:
                xml += '<CutoutSubdesign>' + '\n'
                xml += '<Polygon>' + '\n'

                for point in points:
                    xy = re.split(r"[,\s]+",point)
                    if len(xy) != 2:
                        log.exception("CutoutPolygon should be x,y;x,y;x,y...")
                    xml += '<Point x="%s%s" y="%s%s"/>'%(xy[0],options["DefaultUnit"],xy[1],options["DefaultUnit"] ) + '\n'
                xml += '</Polygon>' + '\n'
                xml += '</CutoutSubdesign>' + '\n'
                
        xml += '<GDS_NET_DEFINITIONS NET_NAME_CASE_SENSITIVE="true" USE_TOP_LEVEL_TEXT_ONLY="false">' + '\n'
        xml += '<USE_TEXT_FROM_HIERARCHY_LEVEL>0 1 2 3 4-MAX</USE_TEXT_FROM_HIERARCHY_LEVEL>' + '\n'
        xml += '<VDD_NETS><!--Add power Nets here--></VDD_NETS>' + '\n'
        xml += '<GND_NETS><!--Add gnd Nets here--></GND_NETS>' + '\n'    
        xml += '<SIGNAL_NETS>*</SIGNAL_NETS>' + '\n'
        xml += '</GDS_NET_DEFINITIONS>' + '\n'
                
        #--- ComponentOnLayers
        # must after <GDS_NET_DEFINITIONS> tag, otherwise will cause error
        generate_component = options["GenerateComponent"] if "GenerateComponent" in options else False
        if _to_bool(generate_component):
            if "ComponentOnLayers" in options and options["ComponentOnLayers"]:
                xml += '<GDS_COMPONENTS LengthUnit="%s">'%options["DefaultUnit"] + '\n'
                for layer in self._conductorList:
                    LayerName = layer._layerDict["LayerName"]
                    if regAnyMatch(re.split(r"[;,]+",options["ComponentOnLayers"]),LayerName):
                        xml += '<GDS_AUTO_COMPONENT Layer="%s" Tolerance="%s"/>'%(LayerName,options["ComponentPinsDistanceTolerance"]+options["DefaultUnit"]) + '\n'
                xml += '</GDS_COMPONENTS>' + '\n'

        xml += '</c:Control>' + '\n'  

        with open(xmlPath, 'w+', encoding='utf-8') as f:
            f.write(xml)
            f.close()
        
        print("finished write xml file: %s"%xmlPath)
        return xmlPath


    def getDependMaterialXml(self):
        materialXml = "\n".join([m.DependMaterialXml for m in self._MaterialList])
        xml = (
            '<Stackup schemaVersion="1.0">' + '\n'
            '<Materials>' + '\n'
            '{0}' + '\n'
            '</Materials>' + '\n'
           '</Stackup>'
            ).format(materialXml)
     
        return xml
    
    def writeDependXml(self,path):
        with open(path,"w+") as f:
            print("write depend xml:%s"%path)
            f.write(self.getDependMaterialXml())
            f.close()
            return path
        
    def write(self,path):
        with open(path,"w+") as f:
            print("write stakup:%s"%path)
            f.write(self.StackupXml)
            f.close()

if __name__ == '__main__':
    ircxTech = r"D:\Study\Script\repository\HFSS\GDSII\GDS2XML\TECH2XML_test\TSMC_INTERPOSER.json"
    stk = Stackup(ircxTech)
    stk.parseTech()
#     print(stk.getDependMaterialXml())
    stk.write(r"D:\Study\Script\repository\HFSS\GDSII\GDS2XML\TECH2XML_test\TSMC_INTERPOSER_stk.xml")
    stk.writeDependXml(r"D:\Study\Script\repository\HFSS\GDSII\GDS2XML\TECH2XML_test\TSMC_INTERPOSER_mat.xml")
    pass        

