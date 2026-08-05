#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2026-03-08

import re
from pyLayout import loadCSV,writeCSV,findDictValue
from pyLayout import log
import time
from decimal import Decimal
from techBase import TechBase

class CsvTech(TechBase):
    '''
    classdocs
    '''
    
    def __init__(self, path = None):
        '''
        Constructor
        '''
        super(CsvTech, self).__init__()
        self.path = path
        self.parsed = False
        if path: 
            self.parse(path)
        
    
    def parse(self,path = None):
        
        if self.parsed:
            return
        super(CsvTech, self).__init__()
        self.parsed = True
        
        path = path or self.path
        csvDict = loadCSV(path, fmt="dict")
        conds = list(filter(lambda c:c["Type"].lower().startswith("c") or c["Type"].lower().startswith("v"),csvDict))[::-1]
        h = Decimal("0")
        for i in range(len(conds)):

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

            layer.update(conds[i])
            # h += Decimal(layer["Thickness"]) 
            
            if layer['Type'].lower().startswith("c"):
                if not layer["Thickness"].strip():
                    log.info("Thickness is empty for layer: %s, will be ignore."%layer["LayerName"])
                    continue
                self.Tech["Conductors"].append(layer)

            elif layer['Type'].lower().startswith("v"):
                if not layer["LowerLayer"].strip():
                    layer["LowerLayer"] = conds[i-1]["LayerName"]
                if not layer["UpperLayer"].strip():
                    layer["UpperLayer"] = conds[i+1]["LayerName"]
                
                #Add 20220608 for Icap layer support
                if "none" in layer["LowerLayer"].lower():
                    layer["LowerLayer"] = ""
                if "none" in layer["UpperLayer"].lower():
                    layer["UpperLayer"] = ""                    
                    
                self.Tech["Vias"].append(layer)
            else:
                print("%s not a Conductors or via layer"%layer["LayerName"])
            
        Dielectrics = list(filter(lambda c:c["Type"].lower().startswith("d"),csvDict))[::-1]
        #if no Dielectrics define, will define from cond
        #laminated for len(Dielectrics)==0
        if len(Dielectrics)==0:

            #h = 0
            #support negative value for height, 20220606
            h = min([Decimal(l["Height"]) for l in self.Tech["Conductors"]])
            for i in range(len(conds)):
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

                layer["LayerName"] = findDictValue("LayerName", conds[i]).strip()+"_fill"
                layer["Thickness"] = findDictValue("Thickness", conds[i])
                layer["Height"] = findDictValue("Height", conds[i],valid = h) 
                layer["DK"] = findDictValue("DK", conds[i],valid = 1)
                layer["DF"] = findDictValue("DF", conds[i],valid = 0)
                #layer["Cond"] = 0
                h += Decimal(layer["Thickness"])
                self.Tech["Dielectrics"].append(layer)
                
        else:
        #Dielectrics define in overlapping for len(Dielectrics)!=0
            #h = 0
            #support negative value for height, 20220606, but if min conductors height not negative value , H should be 0
            h = min([Decimal(l["Height"]) for l in self.Tech["Conductors"]]) 
            if h>0: h =0
            
            for i in range(len(Dielectrics)):
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
                layer.update(Dielectrics[i])
                layer["Height"] = findDictValue("Height", Dielectrics[i],valid = h) 
                layer["DK"] = findDictValue("DK", Dielectrics[i],valid = 1) 
                layer["DF"] = findDictValue("DF", Dielectrics[i],valid = 0)
                layer["Cond"] = findDictValue("Cond", Dielectrics[i],valid = 0) 
                h += Decimal(layer["Thickness"])
                self.Tech["Dielectrics"].append(layer)
        
        #Insulatings
        Insulatings = list(filter(lambda c:c["Type"].lower().startswith("i"),csvDict))
        for i in range(len(Insulatings)):
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
            layer.update(Insulatings[i])
            layer["DK"] = findDictValue("DK", Insulatings[i],valid = 4)
            layer["DF"] = findDictValue("DF", Insulatings[i],valid = 0)
            self.Tech["Insulatings"].append(layer)
            
        #Options in CSV
        Options = list(filter(lambda c:c["Type"].lower().startswith("o"),csvDict))[::-1]
        for i in range(len(Options)):
            self.Tech["Options"].update({findDictValue("LayerName", Options[i]):findDictValue("LayerMap", Options[i])})
        
        
if __name__ == '__main__':
    csvPath = r"C:\work\Project\AE\Script\gds2edb\CSVTech_Example.csv"
    CSV = CsvTech(csvPath)
    CSV.parse()
    CSV.writeJson(r"C:\work\Project\AE\Script\gds2edb\CSVTech_Example.csv.json")
    pass