
#coding:utf-8
#--- coding=utf-8
#--- @author: yongsheng.guo@ansys.com
#--- @Time: ver 1.0 20211121 
#--- @Time: ver 6.0 20230721

import sys
sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim\pyLayout")
from pyLayout import ComplexDict,log,Unit

import re
from techBase import TechBase
from options import options


class IrcxTech(TechBase):
    '''
    classdocs
    '''
    
    def __init__(self, path = None, layermapFile = None):
        '''
        Constructor
        '''
        super(IrcxTech, self).__init__()
        self.path = path
        self.parsed = False
        self.units = {}
        if path: 
            self.parse(path)
        
    
    def parse(self,path = None):

        if self.parsed:
            return
        #重新初始化数据
        super(IrcxTech, self).__init__()
        self.parsed = True

        path = path or self.path
        with open(path, "r") as fo:
            IRCXTxt = fo.read()
            fo.close()
            
        #---UNITS
        regex=re.compile(r"UNITS\s*\{(.*?)\}",re.DOTALL)
        txt = regex.findall(IRCXTxt)
        Tref = 20
        if txt:
            lines = txt[0].splitlines()
            sLines = [re.split(r"\s*:\s*",line) for line in lines]
            fLines = filter(lambda l:len(l)==2, sLines)
            self.units  = dict(fLines)
            options["DefaultUnit"]= self.units["THICKNESS"]

            #--- Tref
            Tref = self.units["TEMPERATURE"].split("degree")[0]
            
            
        #--- layerTexts
        regex=re.compile(r"LAYER\s*\{(.*?)\}",re.DOTALL)
        layersTxt = regex.findall(IRCXTxt)
        if not layersTxt:
            log.info("bad IRCX file input, please check input files")
            self._techDict = None
            return
        #print(layersTxt)
        #split with *
        regex=re.compile(r"\*",re.DOTALL)
        layersTxtList = re.split(regex,layersTxt[0])
        #print("\n\n\n".join(layersTxtList))  
        
        for layers in layersTxtList:
            #---layers
            if layers.strip().startswith("CONDUCTOR"):
                #---CONDUCTOR
                sLines = [re.split(r"\s+",x) for x in layers.splitlines()]
                lenL = len(sLines[1])
                conductorList = []
                for x in sLines[1:]:
                    if len(x)==lenL:
                        conductorList.append(x)
                    else:
                        log.info("ignore line: "+" ".join(x))
                        
                header = conductorList[0]
                datas = conductorList[1:]
                conductors = [dict(zip(header,d)) for d in datas]
                for layer2 in conductors:
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
                    layer["LayerName"] = layer2["FIELD"]
                    layer["Type"] = "Conductor"
                    # layer["LayerMap"] = layer2["LAYER"]
                    layer["Thickness"] = layer2["THICKNESS"]
                    layer["Height"] = layer2["HEIGHT"]
                    layer["Cond"] = 1e6/(float(layer2["RESIST"] )*float(layer2['THICKNESS']))
                    layer["Tref"] = Tref
                    layer["TC1"] = layer2["TC1"]
                    layer["TC2"] = layer2["TC2"]
                    self.Tech["Conductors"].append(layer)

                
            elif layers.strip().startswith("VIA"):
                #--- VIA
                sLines = [re.split(r"\s+",x) for x in layers.splitlines()]
                lenL = len(sLines[1])
                visList = []
                for x in sLines[1:]:
                    if len(x)==lenL:
                        visList.append(x)
                    else:
                        log.info("ignor line: "+" ".join(x))
                header = visList[0]
                datas = visList[1:]
                Vias = [dict(zip(header,d)) for d in datas]
                for layer2 in Vias:
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
                    layer["LayerName"] = layer2["FIELD"]
                    layer["Type"] = "Conductor"
                    # layer["LayerMap"] = layer2["LAYER"]
                    # layer["Thickness"] = layer2["THICKNESS"]
                    # layer["Height"] = layer2["HEIGHT"]
                    layer["LowerLayer"] = layer2["LOWER"]
                    layer["UpperLayer"] = layer2["UPPER"]
                    layer["Tref"] = Tref
                    layer["TC1"] = layer2["TC1"]
                    layer["TC2"] = layer2["TC2"]

                    upper = self.findLayer(layer["LowerLayer"],typ="Conductors")
                    lower = self.findLayer(layer["UpperLayer"],typ="Conductors")
                    layer['Thickness'] = float(upper["Height"]) - float(lower["Height"]) - float(lower["Thickness"]) 
                    #avoid issue for ircx with Reverse upper/lower setting, 20230506
                    if layer['Thickness']<0:
                        print("warning: the via upper/lower layer maybe reversed.")
                        upper,lower = lower,upper
                        layer['Thickness'] = float(upper["Height"]) - float(lower["Height"]) - float(lower["Thickness"]) 
                    layer["Cond"] = 1e6/(float(layer2["RESIST"])*float(layer2["WIDTH"])*float(layer2["LENGTH"])/float(layer['Thickness']))

                    self.Tech["Vias"].append(layer)

            elif layers.strip().startswith("DIELECTRIC"):
                #--- DIELECTRIC
                sLines = [re.split(r"\s+",x) for x in layers.splitlines()]
                lenL = len(sLines[1])
                dielectricList = []
                for x in sLines[1:]:
                    if len(x)==lenL:
                        dielectricList.append(x)
                    else:
                        log.info("ignor line: "+" ".join(x))
                
                header = dielectricList[0]
                datas = dielectricList[1:]
                Dielectrics = [dict(zip(header,d)) for d in datas]
                
                for layer2 in Dielectrics:
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
                    layer["LayerName"] = layer2["FIELD"]
                    layer["Type"] = "Dielectric"
                    layer["Thickness"] = layer2["THICKNESS"]
                    layer["Height"] = layer2["HEIGHT"]
                    layer["DK"] = layer2["CONSTANT"]
                    self.Tech["Dielectrics"].append(layer)

            else:
                pass


        #TSV Insulating
        regex=re.compile(r"CONTACT_TABLE\[tsv\]\s*\{(.*?)\}",re.DOTALL)
        txt = regex.findall(IRCXTxt)
        if txt:
            lines = txt[0].splitlines()
            sLines = [re.split(r"\s+",line) for line in lines]
            fLines = filter(lambda l:len(l)==2, sLines)
            layerDict = dict(fLines)

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

            layer["LayerName"] = "tsv"
            layer["Type"] = "Insulating"
            layer["DK"] = layerDict["tsv_LINER_ER"]
            layer["Thickness"] = layerDict["tsv_LINER_THICKNESS"]
            self.Tech["Insulatings"].append(layer)

        #判断self.Tech的Conductors和Dielectrics是否同时存在名字为substrate的层
        #如果存在则将Conductors的cond值给到Dielectrics的substrate层
        subLayer = self.findLayer("substrate",typ="Conductors")       
        if subLayer:
            subCond = subLayer["Cond"]
            dieLayer = self.findLayer("substrate",typ="Dielectrics")
            if dieLayer:
                dieLayer["Cond"] = subCond
        
        #---LAYER_MAPPING
        regex=re.compile(r"\[LAYER_MAPPING\](.*)",re.DOTALL)
        layerMapTxt = regex.findall(IRCXTxt)[0]
        #print(layerMapTxt)     
        layerMapList  = [x.split() for x in layerMapTxt.splitlines() if not x.strip().startswith("#") ]
        layerMapList = filter(lambda x:len(x)>3, layerMapList)
        LayerMapping = dict([(d[0],d) for d in layerMapList])

        for k,v in LayerMapping.items():
            
            if "pin" in k:
                name = k[:-4] #remove _pin
                layer = self.findLayer(name,typ="Conductors")
                if not layer:
                    layer = self.findLayer(name,typ="Vias")
                if layer:
                    layer["TextLayerMap"]=v[1] if not layer["TextLayerMap"] else layer["TextLayerMap"]+";"+v[1]
            elif "ImportDummyLayer" in options and options["ImportDummyLayer"] and "DUM" in k:
                name = k.replace("DUM","metal")
                if not layer:
                    layer = self.findLayer(name,typ="Vias")
                if layer:
                    layer["LayerMap"]=v[1] if not layer["LayerMap"] else layer["LayerMap"]+";"+v[1]
            else:
                layer = self.findLayer(k)
                if not layer:
                    layer = self.findLayer(k,typ="Vias")
                if layer:
                    layer["LayerMap"]=v[1] if not layer["LayerMap"] else layer["LayerMap"]+";"+v[1]
            
if __name__ == '__main__':
    ircxPath = r"C:\work\Project\AE\Script\gds2edb\ircx_2025R2\TSMC_INTERPOSER.ircx"
    ircx = IrcxTech(ircxPath)
    ircx.parse()
    ircx.toCSV(r"C:\work\Project\AE\Script\gds2edb\ircx_2025R2\TSMC_INTERPOSER.csv")
    
    pass