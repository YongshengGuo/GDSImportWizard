#coding:utf-8
#--- coding=utf-8
#--- @author: yongsheng.guo@ansys.com
#--- @Time: ver 1.0 20211121 
#--- @Time: ver 6.0 20230721

import sys
import re
sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim")
from pyLayout import ComplexDict,log,Unit
from pyLayout import textSplit
from techBase import TechBase
from options import options

import time
from decimal import Decimal
from collections import OrderedDict


def parseValues(value):
    value2 = re.sub(r"\s*=\s*","=",value)
    kvs = re.findall(r"\{*(\S*)=(\S*)\}*",value2)
    tempDict = {}
    for k,v in kvs:
        tempDict[k]=re.sub(r"\}","",v)

    for block in textSplit(value2[1:-1], flag="{}", comment="$"):
        if block:
#             print(block)
            kvs = re.findall(r"(\S*)\s*\{(.*)\}",block)
            for k,v in kvs:
                tempDict[k]={}
                for k2,v2 in re.findall(r"(\S*)\s*\{(.*?)\}",v):
                    tempDict[k][k2] = v2.split()
            

    return tempDict


def getLayerCond(layer):
    '''
    layer is itf data
    '''
    #calc cond
    if "RPSQ" in layer:
        layer["Cond"] = 1e6/(float(layer["RPSQ"] )*float(layer['THICKNESS'])) 
    elif "RHO" in layer:
        layer["Cond"] = 1e6/float(layer['RHO']) #append 20240802
    elif "RPSQ_VS_WIDTH_AND_SPACING" in layer:
        layer["Cond"] = 1e6/(float(layer["RPSQ_VS_WIDTH_AND_SPACING"]["VALUES"][0] )*float(layer['THICKNESS'])) 
    elif "RHO_VS_WIDTH_AND_SPACING"  in layer:
        layer["Cond"] = 1e6/(float(layer["RHO_VS_WIDTH_AND_SPACING"]["VALUES"][0]))
        
    elif "RPV" in layer:
        layer["Cond"] = 1e6*float(layer['THICKNESS'])/(float(layer["RPV"] )*float(layer['AREA'])) if "AREA" in layer else 0

    else:
        print("Resistance not defined on layer :%s"%layer["LayerName"])
        layer["Cond"] = 0

    return layer["Cond"]


def itfReader(path):
    path = path
    with open(path) as f:
        lines = f.readlines()
        f.close()
    
    itfDict = OrderedDict()
    itfDict["Layers"] = OrderedDict()

    iter_lines = iter(lines)
    while True:
        try:
            line = next(iter_lines).strip()
            if line.startswith("$"):continue
                
        except:
            break
        
        if "DIELECTRIC" in line or "CONDUCTOR" in line or "VIA" in line or "TSV" in line:
            
            flag = 0
            if "{" in line:
                flag += line.count("{")

            if "}" in line:
                flag -= line.count("}")
            
            typ,name,value = re.split(r"[\s{]+",line,2)
            temp = value
                
            while flag:
                try:
                    line = next(iter_lines).strip()
                    if line.startswith("$"):continue
                except:
                    Exception("Error in itf file, exit")

                
                if "{" in line:
                    flag += line.count("{")
    
                if "}" in line:
                    flag -= line.count("}")
                
                temp += " " + line
            
            itfDict["Layers"][name] = parseValues(temp)
            itfDict["Layers"][name]["Type"] = typ
            itfDict["Layers"][name]["LayerName"] = name
            continue
            
        if "=" in line:
#             print(line)
            k,v = line.split("=")
            itfDict[k] = v
            continue
        
    return itfDict
            
                


class ItfTech(TechBase):
    '''
    classdocs
    '''


    def __init__(self, path = None, layermapFile = None):
        '''
        Constructor
        '''
        super(ItfTech, self).__init__()
        self.path = path
        self.parsed = False
        self.units = {}
        if path: 
            self.parse(path)
        

    def parse(self,path = None):

        if self.parsed:
            return
        #重新初始化数据
        super(ItfTech, self).__init__()
        self.parsed = True

        path = path or self.path
        itfDatas = itfReader(path)
        Tref = itfDatas["GLOBAL_TEMPERATURE"] if "GLOBAL_TEMPERATURE" in itfDatas else 25
        h = Decimal("0")
        for name in list(itfDatas["Layers"].keys())[::-1]:
            layer = {
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


            layer2 = itfDatas["Layers"][name]
            layer["LayerName"] = name
            layer["Height"] = h
            #---via
            if "VIA" in layer2["Type"]:
                layer["Type"] = "Vias"
                layer["LowerLayer"] = layer2["FROM"]
                layer["UpperLayer"] = layer2["TO"] 
                layer["TC1"] = layer2["CRT1"] if "CRT1" in layer2 else None
                layer["TC2"] = layer2["CRT2"] if "CRT2" in layer2 else None
                layer["Tref"] = Tref
                layer["Height"] = ""
                self.Tech["Vias"].append(layer)
            #---tsv
            elif "TSV" in layer2["Type"]:
                
                #add via layer
                layer["Type"] = "Vias"
                layer["LowerLayer"] = layer2["FROM"]
                layer["UpperLayer"] = layer2["TO"] 
                layer["TC1"] = layer2["CRT1"] if "CRT1" in layer2 else None
                layer["TC2"] = layer2["CRT2"] if "CRT2" in layer2 else None
                layer["Tref"] = Tref
                
                self.Tech["Vias"].append(layer)
                
                #add substract layer
                layer_SI = {
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


                layer_SI["LayerName"] = "SUBSTRATE"
                layer_SI["Type"] = "Dielectrics"
                layer_SI["DK"] = 11.9
                layer_SI["Cond"] = 10
                layer_SI["Height"] = ""
                layer_SI["Thickness"] = layer2["THICKNESS"]
                self.Tech["Dielectrics"].append(layer_SI)
                h += Decimal(layer2["THICKNESS"])
                
                #add Insulatings layer
                layer_insulating = {
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
                layer_insulating["LayerName"] = name
                layer_insulating["Type"] = "Insulatings"
                layer_insulating["Height"] = ""
                if "INSULATION_THICKNESS" in layer2:
                    layer_insulating["Thickness"] = layer2["INSULATION_THICKNESS"]
                else:
                    log.warning("Insulation thickness not found, use default value 0.1um")
                    layer_insulating["Thickness"] = 0.1

                if "INSULATION_ER" in layer2:
                    layer_insulating["DK"] = layer2["INSULATION_ER"]
                else:
                    log.warning("Insulation DK not found, use default value 4.0")
                    layer_insulating["DK"] = 4.0

                self.Tech["Insulatings"].append(layer_insulating)
                
            #---conductor
            elif "CONDUCTOR" in layer2["Type"]:
                layer["Type"] = "Conductors"
                layer["Thickness"] = layer2["THICKNESS"]
                layer["TC1"] = layer2["CRT1"] if "CRT1" in layer2 else None
                layer["TC2"] = layer2["CRT2"] if "CRT2" in layer2 else None
                layer["Tref"] = Tref
                layer["Cond"] = getLayerCond(layer2)
                self.Tech["Conductors"].append(layer)
                
            #---dielectric
            elif "DIELECTRIC" in layer2["Type"]:
                layer["Type"] = "Dielectrics"
                layer["Thickness"] = layer2["THICKNESS"]
                layer["DK"] = layer2["ER"]
                self.Tech["Dielectrics"].append(layer)
                h += Decimal(layer2["THICKNESS"])
                        
            else:
                print("parse layer error: %s"%(str(layer2)))
                
        #---calc via cond
        for layer in self.Tech["Vias"]:
            itfData = itfDatas["Layers"][layer["LayerName"]]
            fromL = itfData["FROM"]
            to = itfData["TO"]

            fromLayer = self.findLayer(fromL)
            if not fromLayer:
                log.warning("Can't find %s via from layer %s"%(layer["LayerName"],fromL))
                continue
            toLayer = self.findLayer(to)
            if not toLayer:
                log.warning("Can't find %s via to layer %s"%(layer["LayerName"],to))
                continue
            topH = Decimal(fromLayer["Height"])
            bottomH = Decimal(toLayer["Height"])
            
            topT = Decimal(fromLayer["Thickness"])
            bottomT = Decimal(toLayer["Thickness"])

            Thickness = topH - bottomH - bottomT
            
            if topH>bottomH:
                Thickness = topH - bottomH -  bottomT
                layer["Height"] = bottomH
            else:
                Thickness = bottomH - topH - topT
                layer["Height"] = topH
            layer["Thickness"] = Thickness
            itfData["THICKNESS"] = Thickness
            layer["Cond"] = getLayerCond(itfData)
        
        
        for name in list(itfDatas["Layers"].keys())[::-1]:
            itfData = itfDatas["Layers"][name]
            if "MEASURED_FROM" in layer:
                if "TOP_OF_CHIP" in layer["MEASURED_FROM"]:
                    pass
                else:
                    layer = self.findLayer(name)
                    if not layer:
                        continue
                    fromLayer = self.findLayer(itfData["MEASURED_FROM"])
                    if fromLayer:
                        layer["Height"]  = fromLayer["Height"] + Decimal(fromLayer["Thickness"]) 
                

if __name__ == '__main__':
    path= r"C:\work\Project\AE\Script\gds2edb\itf2\StarRC_65RFSOI_1P5M_3Ic_2TTMc2_ALPA2_TYP_20220428.itf"
    itf = ItfTech(path)
    itf.parse()
    itf.toCSV(r"C:\work\Project\AE\Script\gds2edb\itf2\StarRC_65RFSOI_1P5M_3Ic_2TTMc2_ALPA2_TYP_20220428.csv")
    pass
