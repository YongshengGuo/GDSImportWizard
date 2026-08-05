    #coding:utf-8
    #--- coding=utf-8
    #--- @author: yongsheng.guo@ansys.com
    #--- @Time: 20230410
    #--- @update 20230618

'''
通过仿真配置文件(json)驱动HFSS 3D Layout进行S参数的提取。

# workflow:

laod PCB -> load stackup -> configComponents -> ConfigNets -> Cutout -> Port -> solveSetup -> Solve -> datas -> Post

Eaxmples:

    configPath = os.path.join(r"config\galileo_pcie_snpExtract.json")
    sim = ExtractLayout(configPath)
    sim.run()


'''

import sys,os,re

from ..pyLayout import Layout
from ..definition.path import Path,Node
from ..common.common import log,writeJson,getParent,readData,writeData,regAnyMatch
from ..common.complexDict import ComplexDict
from .simConfig import SimConfig
# log.info("Start ExtractLayout analyse, this progrom powered by Ansys AE.")

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class ExtractBase(object):
    '''
    classdocs
    '''

    def __init__(self, simConfig, oDesktop = None):
        '''
        Constructor
        '''
        self._config = None
        self.layout = None
        self._config = SimConfig(simConfig)
        self.oDesktop = oDesktop
                
    @property
    def Config(self):
        return self._config

    def initLayout(self):
        #just for debug usage
        self.layout = Layout()
        self.layout.initDesign()

    def loadLayout(self):
        
        if "Import" not in self.Config:
            return
        log.info("load layout file")
        
        #initial layout
#         self.layout = Layout("2022.2")
        version = self.Config["AEDT/Version"]
        installPath = self.Config["AEDT/InstallPath"]
        nonGraphical = self.Config["AEDT/NonGraphical"]
        UsePyaedt  = self.Config["AEDT/UsePyaedt"]
        NewSession  = self.Config["AEDT/NewSession"]

        #if version and installPath are null, least version will be initialized
        self.layout = Layout(version=version, installDir=installPath,nonGraphical=nonGraphical,newDesktop=NewSession,usePyAedt=UsePyaedt,oDesktop=self.oDesktop)
        self.layout.options["AEDT_WaitForLicense"] = self.Config["AEDT/WaitForLicense"]
        self.layout.options["AEDT_LicenseServer"] = self.Config["AEDT/LicenseServer"]
        self.layout.options["AEDT_KeepGUILicense"] = self.Config["AEDT/KeepGUILicense"]
        
        logPath = self.Config["AEDT/LogPath"]
        if logPath:
            self.layout.setLogPath(logPath)
        
        if not version:
            self.Config["AEDT/Version"] = self.layout.Version
            
        if not installPath:
            self.Config["AEDT/InstallPath"] = self.layout.InstallPath
            
        
        Import = self.Config["Import"]

        if not Import["Enable"]:
            log.info("Import not enable.")
            return
  
        layoutPath = Import["LayoutPath"]
        edbOutPath = Import["EdbOutPath"]
        controlFile = Import["ControlFile"]
        layoutType = Import["LayoutType"]
        extractExePath = Import["extractExePath"]
        
        
#         self.layout.initDesign() #for debug
        
        if layoutPath.lower().endswith(".aedt") and Import["SaveAs"]:
            #for multi-process, avoid aedt lock
            Layout.copyAEDT(layoutPath,Import["SaveAs"])
            self.layout.openAedt(Import["SaveAs"],unlock=True) #try to open with lock file
        else:
            #for brd, odb ... import
            self.layout.loadLayout(layoutPath, edbOutPath, controlFile, layoutType,extractExePath)
            if Import["SaveAs"]:
                self.layout.saveAs(Import["SaveAs"]) #for other format

        configPath = self.layout.ProjectPath + ".json"        
        self._config.writeJson(configPath)
        self.layout.save()

    def preConfig(self):

        #PortbyPins, {"PosPins":[],"NegPins":[],"Refdes":null,"PosNet":null,"NegNet":null,"Name":null,"PortZ0":0.1}
        PortbyPins = []
        if "Ports" in self.Config and "PortbyPins" in self.Config["Ports"]:
            PortbyPins = self.Config["Ports"]["PortbyPins"]
            if not PortbyPins:
                PortbyPins = []
            
        for group in PortbyPins:
            if not group["Refdes"]:
                continue
            
            if not group["PosPins"]: #must have net
                #set pins by net
                if  group["Refdes"] and group["PosNet"]: 
                    group["PosPins"] = [pin.Name for pin in self.layout.Components[group["Refdes"]].Pins if pin.Net.lower() == group["PosNet"].lower()]
            else:
                #must have pins, set net by pin
                if isinstance(group["PosPins"], str):
                    group["PosPins"] = re.split(r"[,;\s]+",group["PosPins"])
                
                if isinstance(group["PosPins"], (list,tuple)): # not group["PosNet"] and isinstance(group["PosPins"], (list,tuple)): #20260605
                    pinNets = set()
                    for pin in group["PosPins"]:
                        if pin in self.layout.Pins:
                            pinNets.add(self.layout.Pins[pin].Net)
 
                        elif "%s-%s"%(group["Refdes"],pin) in self.layout.Pins:
                            pinNets.add(self.layout.Pins["%s-%s"%(group["Refdes"],pin)].Net)

                        else:
                            log.info("Pin '%s' not found, will ignor."%pin)
                    #20260605        
                    if len(pinNets) == 0:
                        log.exception("PinGroup PosPins definiton error, no valid nets found: %s"%str(group["PosPins"]))
                    elif len(pinNets) == 1:
                        group["PosNet"] = pinNets.pop()
                    elif len(pinNets) > 1:
                        log.exception("PinGroup PosPins must not definited on multi-nets: %s - %s"%(str(group["PosPins"]), str(pinNets)))
                    else:
                        pass
 
            if not group["NegPins"]:
                if group["Refdes"] and group["NegNet"]: 
                    group["NegPins"] = [pin.Name for pin in self.layout.Components[group["Refdes"]].Pins if pin.Net.lower() == group["NegNet"].lower()]
            else:
                #must have pins, set net by pin
                
                if isinstance(group["NegPins"], str):
                    group["NegPins"] = re.split(r"[,;\s]+",group["NegPins"])

                if isinstance(group["NegPins"], (list,tuple)): # not group["NegNet"] and isinstance(group["NegPins"], (list,tuple)):  #20260605
                    pinNets = set()
                    for pin in group["NegPins"]:
                        if pin in self.layout.Pins:
                            pinNets.add(self.layout.Pins[pin].Net)
  
                        elif "%s-%s"%(group["Refdes"],pin) in self.layout.Pins:
                            pinNets.add(self.layout.Pins["%s-%s"%(group["Refdes"],pin)].Net)

                        else:
                            log.info("Pin '%s' not found, will ignor."%pin)
                    #20260605
                    if len(pinNets) == 0:
                        log.exception("PinGroup NegPins definiton error, no valid nets found: %s"%str(group["NegPins"]))
                    elif len(pinNets) == 1:
                        group["NegNet"] = pinNets.pop()
                    elif len(pinNets) > 1:
                        log.exception("PinGroup NegPins must not definited on multi-nets: %s - %s"%(str(group["NegPins"]), str(pinNets)))
                    else:
                        pass
        
        #--- keepnet
        KeepNet  = self.Config["ClearLayout"]["KeepNet"]
        if not KeepNet:  
            KeepNet = []
        if isinstance(KeepNet, str):
            KeepNet = re.split(r"[,;\s]+",KeepNet)
        
        #---PortOnNets
        if self.Config["ClearLayout"]["KeepNetWithPort"]:
            #--- net on Ports    
            if "Ports" in self.Config and self.Config["Ports"]["Enable"]:
                ports = self.Config["Ports"]            
                if ports["PortOnNets"]:
                #create port on nets
                    nets  = self.layout.Nets.getRegularNets(ports["PortOnNets"]) + self.layout.Nets.getRegularNets(ports["RefNets"]) 
                    KeepNet += nets
    
                if ports["PortbyPins"]:
                    for group in ports["PortbyPins"]:
                        if group["PosNet"]:
                            KeepNet.append(group["PosNet"])
                        if group["NegNet"]:
                            KeepNet.append(group["NegNet"])
            #--- net on source                
            if "Source" in self.Config and self.Config["Source"]["Enable"]:
                Source = self.Config["Source"]
                if Source["SourceDefs"]:
                    for source in Source["SourceDefs"]:
                        if source["PosNet"]:
                            KeepNet.append(source["PosNet"])
                        if source["NegNet"]:
                            KeepNet.append(source["NegNet"])

        self.Config["ClearLayout"]["KeepNet"] = list(set(KeepNet))

        #---solderball
        if "SolderBall" in self.Config and self.Config["SolderBall"]["Enable"]:
            if not self.Config["SolderBall"]["SolderOnComponents"]:
                self.Config["SolderBall"]["SolderOnComponents"] = []
            
            if isinstance(self.Config["SolderBall"]["SolderOnComponents"], str): #convert to list
                self.Config["SolderBall"]["SolderOnComponents"] = re.split("[,;\s]+",self.Config["SolderBall"]["SolderOnComponents"].strip())

            if self.Config["SolderBall"]["AutoSolderball"]:
                if "Ports" in self.Config and "PortbyPins" in self.Config["Ports"]:
                    nets  = self.layout.Nets.getRegularNets(self.Config["Ports"]["PortOnNets"])
                    compNames = self.layout.Nets.getComponentsOnNets(nets, ignorRLC = not self.Config["Ports"]["PortOnRLC"])
                    self.Config["SolderBall"]["SolderOnComponents"] += compNames
                    
                    PortbyPins = self.Config["Ports"]["PortbyPins"]
                    for group in PortbyPins:
                        if "Refdes" in group and group["Refdes"]:
                            self.Config["SolderBall"]["SolderOnComponents"].append(group["Refdes"])
                            
                    self.Config["SolderBall"]["SolderOnComponents"] = list(set(self.Config["SolderBall"]["SolderOnComponents"]))
        
        
        #Component: Capacitor,Inductor,Resistor的Pin数量大于2时，PartType改成Other
        log.info("Check RLC Component PartType")
        for comp in self.layout.Components:
            if comp.PartType == "Capacitor" or comp.PartType == "Inductor" or comp.PartType == "Resistor":
                if len(comp.Pins) > 2:
                    log.info("Component: %s,%s,pinCount:%s will change to Other type"%(comp.Name,comp.PartType,len(comp.Pins)))
                    comp.changePartType("Other")
        
        configPath = self.layout.ProjectPath + ".json"
        self.Config.writeJson(configPath)

    def loadStackup(self):
        '''
        - {Name: SURFACE,Type: signal, Material: copper, FillMaterial: M4 ,Thickness: 3.556e-05, Roughness: 0.5um,2.9 ,DK: 4,DF: 0.02, Cond: 5.8e7, EtchFactor: 2.5}
        - {Name: SURFACE,Type: dielectric, Material: M4 ,Thickness: 3.556e-05,DK: 4,DF: 0.02}
        '''
        if "Stackup" not in self.Config:
            return
        
        log.info("load stackup file")
        
        Stackup = self.Config["Stackup"]
        if not Stackup["Enable"]:
            log.info("Stackup not enable.")
            return
        
        materials = None
        try:
            materials = self.Config["Stackup/Matrials"]
        except Exception:
            materials = None
        if (not materials) and "Materials" in self.Config["Stackup"]:
            materials = self.Config["Stackup/Materials"]
        if not materials:
            materials = ComplexDict()
        for name in materials.Keys:
            material = materials[name]
            material.update("Name",name)
            self.layout.Materials.add(material)
        
        if Stackup["Layers"]:
            self.layout.Layers.loadFromDict(Stackup["Layers"])
        else:
            log.info("Stackup layers is empty, skip.")
            
        self.layout.save()

    def configComponents(self):
        
        if "Component" not in self.Config:
            return
        log.info("configComponents Models")
        
        Component = self.Config["Component"]
        
        if not Component["Enable"]:
            log.info("Component not enable.")
            return
        
        models = Component["Models"]
        if not models:
            log.info("Component models is empty, skip.")
            return
        
        self.layout.Components.updateModels(models)
        self.layout.save()

        
    def configNets(self):
        if "Net" not in self.Config:
            return
        log.info("config NetClass")
        
        Net = self.Config["Net"]
        
        if not Net["Enable"]:
            log.info("Net not enable.")
            return
        
        pwrGnd = []
        if "PowerNets" in Net and Net["PowerNets"]:
            pwrGnd += Net["PowerNets"]
        if "GroundNets" in Net and Net["GroundNets"]:
            pwrGnd += Net["GroundNets"]      
        
        if pwrGnd:
            self.layout.Nets.addPwrGndNets(pwrGnd)
        
        if "SignalNets" in Net and Net["SignalNets"]:
            self.layout.Nets.removePwrGndNets(Net["SignalNets"])
        
        if "ShortNets" in Net and Net["ShortNets"]:
            for k,v in Net["ShortNets"].items():
                nets = self.layout.Nets.getRegularNets(v)
                if not nets:
                    continue
                for net in nets:
                    if net == k:
                        continue
                    log.info("short net %s to %s"%(net,k))
                    self.layout.Nets[net].rename(k)
                    
#         if "MergePhysicallyConnected" in Net and Net["MergePhysicallyConnected"]:
#             log.info("Merge Physically Connected nets ...")
#             self.layout.Nets.mergePhysicallyConnectedNets()
            
        self.layout.save()
    
    def cutoutDesign(self):
        '''
        Cutout:
          # NetInclude for net must be full included
          # PowerNet and GNDNet will be included and cut at boundary
          NetInclude: []
          NetClip: []
          KeepPowerNet: Yes
          Enable: True
          CutExpansion: 10mm

        '''

        if "Cutout" not in self.Config:
            return
        log.info("cutout Design")
        
        cutout = self.Config["Cutout"]  #return as ComplexDict()
        if not cutout["Enable"]:
            log.info("cutout not enable.")
            return
        
        # Net include
        NetInclude = cutout["NetInclude"]
        if not NetInclude and "Ports" in self.Config:
            NetInclude = self.Config["Ports/PortOnNets"]
            
        NetInclude = self.layout.Nets.getRegularNets(NetInclude)
            
        if not NetInclude:
            log.info("No Net include, cutout skip")
            return
        
        # Net cutout
        NetClip = cutout["NetClip"]
        
        if not NetClip:
            NetClip = []
        
        NetClip = self.layout.Nets.getRegularNets(NetClip)
        
        if cutout["KeepPowerNet"]:
            NetClip += [net for net in self.layout.Nets.PowerNetNames if net not in NetInclude]
            
        if cutout["KeepOtherNets"]:
            NetClip += [net for net in self.layout.Nets.NameList if net not in NetInclude and net not in NetClip]
            
        if cutout["SubProjectName"]:
            newAedtPath = os.path.join(self.layout.projectDir,cutout["SubProjectName"])
            self.layout.saveAs(newAedtPath, True)
            
        self.layout.clip(self.layout.designName, NetInclude, NetClip, cutout["CutExpansion"], InPlace = True)
        
        self.layout.save()
        
    def backdrill(self):
        if "Backdrill" not in self.Config:
            return
        log.info("Set backdrill")
        
        if not self.Config["Backdrill"]["Enable"]:
            log.info("Backdrill not enable.")
            return
        if not self.Config["Backdrill"]["Nets"]:
            log.info("No backdrill nets set, PortOnNets value will be used.")
            self.Config["Backdrill"]["Nets"] = self.Config["Ports/PortOnNets"]

        Nets = self.layout.Nets.getRegularNets(self.Config["Backdrill"]["Nets"])
        stub = self.Config["Backdrill"]["Stub"]
        for net in Nets:
            self.layout.nets[net].backdrill(stub=stub)
        self.layout.save()
        
    def clearLayout(self):
        if "ClearLayout" not in self.Config:
            return
        log.info("clearLayout")
        
        clearLayout = self.Config["ClearLayout"]  #return as ComplexDict()
        if not clearLayout["Enable"]:
            log.info("cutout not enable.")
            return
        
        # Net include
        KeepNet  = clearLayout["KeepNet"]
        if not KeepNet:  
            KeepNet = []
            
        RemoveNet = clearLayout["RemoveNet"]
        if RemoveNet:
            for net in RemoveNet:
                if net in KeepNet:
                    KeepNet.remove(net)
        removeNets = [net for net in self.layout.Nets.NameList if net not in KeepNet]
#         log.info("Remove nets: %s"%removeNets)
        if removeNets:
            self.layout.Nets.deleteNets(removeNets)
    
        if "RemoveComponentNetsLessThen" in clearLayout:
            ConnectedNetsLessThen =  int(clearLayout["RemoveComponentNetsLessThen"])
        else:
            ConnectedNetsLessThen = None            
        if "RemoveComponentPinsLessThen" in clearLayout:
            PinsLessThen= int(clearLayout["RemoveComponentPinsLessThen"])
        else:
            PinsLessThen = None

        self.layout.Components.deleteInvalidComponents(ConnectedNetsLessThen,PinsLessThen)
        
        self.layout.initDesign()
        self.layout.save()

    def geometryCheckAndAutofix(self):
        if "GeometryCheckAndAutofix" not in self.Config:
            return
        log.info("GeometryCheckAndAutofix ... ")
        
        GeometryCheckAndAutofix = self.Config["GeometryCheckAndAutofix"]  #return as ComplexDict()
        if not GeometryCheckAndAutofix["Enable"]:
            log.info("GeometryCheckAndAutofix not enable.")
            return
        
        options = GeometryCheckAndAutofix["Options"]
        checkList = []
        for k,v in options.Dict.items():
            if v:
                log.info("Add check: %s"%k)
                checkList.append(k)

        if len(checkList)<1:
            return

        message = self.layout.geometryCheckAndAutofix(checkList)
        log.info(message)
        if message:
            self.layout.save()
            self.layout.initDesign()
        else:
            log.info("Geometry Check without any error.")

    def createSolderall(self):

        if "SolderBall" not in self.Config:
            return
        #---solderBall befor port
        solderBall = self.Config["SolderBall"]

        if not solderBall["Enable"]:
            log.info("solderball not enable.")
            return
        log.info("Create solderball")

        solderSizes = solderBall["SolderBallSize"]
        pecSizes = solderBall["PECSize"]

        #set solderball ratio
        ratio = solderSizes["Ratio"]
        if ratio[0] !=None:
            self.layout.options["H3DL_solderBallHeightRatio"] = ratio[0]
        if ratio[1] !=None:
            self.layout.options["H3DL_solderBallWidthRatio"] = ratio[1]
        
        if "SolderOnComponents" not in solderBall or not solderBall["SolderOnComponents"]:
            log.info("No solderball components set, solderball will be not set.")
            return

        solderComps = solderBall["SolderOnComponents"]
        solderComps = list(set(solderComps))
        #---create solderball on components
        for name in solderComps:
            if name not in self.layout.Components:
                log.warning("Component not found, solderball skip.")
                continue            
            
            size = solderSizes["Default"][:] #copy to avoid modify self.Config
            for each in solderSizes.Keys:
                if regAnyMatch(each,name):
                    size = solderSizes[each]
                    
            pecSize = pecSizes["Default"] #copy to avoid modify self.Config
            for each in pecSizes.Keys:
                if regAnyMatch(each,name):
                    pecSize = pecSizes[name]
            
            if "Options" in solderBall and solderBall["Options"] != None:
                solderOptions = solderBall["Options"]
            else:
                solderOptions = None
            
            self.layout.Components[name].createSolderBall(size,pecSize=pecSize,solderOptions=solderOptions)

        self.layout.save()

    def setPorts(self):
        
        if "Ports" not in self.Config:
            return
        log.info("Create ports")
        
        ports = self.Config["Ports"]
#         solderComps = []
        
        if not ports["Enable"]:
            log.info("ports not enable.")
            return
        
        #---PortOnNets
        if ports["PortOnNets"]:
        #create port on nets
            nets  = ports["PortOnNets"]
            if "PortOnRLC" in ports and ports["PortOnRLC"]:
                ignorRLC = ports["PortOnRLC"]
            else:
                ignorRLC = True
            compNames = self.layout.Nets.getComponentsOnNets(nets, ignorRLC = ignorRLC)
            if "IgnoreComponent" in ports and ports["IgnoreComponent"]:
                ignorComps = ports["IgnoreComponent"]
                if isinstance(ignorComps, str):
                    ignorComps = re.split(r"[,;\s]+",ignorComps)
                compNames = [comp for comp in compNames if comp not in ignorComps]
                
            if "IgnorePart" in ports and ports["IgnorePart"]:
                ignorParts = ports["IgnorePart"]
                if isinstance(ignorParts, str):
                    ignorParts = re.split(r"[,;\s]+",ignorParts)
                
                partsComps = set()
                for part in ignorParts:
                    partsComps.update(self.layout.Components.getComponentsByPart(part))

                compNames = [comp for comp in compNames if comp not in partsComps]
            
            self.layout.Nets.createPortsOnNets(ports["PortOnNets"], comps = compNames)
            
        #---PortbyPins
        if ports["PortbyPins"]:
            for p in ports["PortbyPins"]:
                #{"PosPins":[],"NegPins":[],"Refdes":null,"PosNet":null,"NegNet":null,"Name":null,"PortZ0":0.1}{"PosPins":[],
                # "NegPins":[],"Refdes":null,"PosNet":null,"NegNet":null,"Name":null,"PortZ0":0.1}
                #PosPins and NegPins are preConfig
                if not p["PosPins"] or not p["NegPins"]:
                    continue

                #posPins=None,refPins=None,compName=None,posNet=None,negNet=None,name=None,portZ0=0.1)
                temp = {"PosPins":[],"NegPins":[],"Refdes":None,"PosNet":None,"NegNet":None,"Name":None,"PortZ0":0.1}
                temp.update(p)
                self.layout.Ports.addPinGroupPort(posPins=temp["PosPins"],refPins=temp["NegPins"],
                    compName=temp["Refdes"],posNet=temp["PosNet"],negNet=temp["NegNet"],
                    name=temp["Name"],portZ0=temp["PortZ0"]) 
    

        log.info("Total port count: %s"%self.layout.Ports.Count)
        #---PortbyPins
        portOrder = ports["OrderPorts"]
        if portOrder["Enable"]:
            self.layout.ports.reorder(compOrder=portOrder["CompOrder"],netOrder=portOrder["NetOrder"],portOrder = portOrder["PortOrder"])
        self.layout.save()
    
    def setPadstack(self):
        if "PadStack" not in self.Config:
            return
        log.info("Create PadStack")
        
        PadStack = self.Config["PadStack"]
#         solderComps = []

        if not PadStack["Enable"]:
            log.info("PadStack not enable.")
            return

        for name,ps in PadStack.Items:
            if not isinstance(ps,(dict,ComplexDict)):
                continue
            
            psDefs = None
            try:
                psDefs = self.layout.PadStacks[name]
            except:
                log.info("No PadStack Matched: %s"%name)
                
            if not psDefs:
                continue
            for psDef in psDefs:
                log.info("Set PadStack %s properties."%psDef.Name)
                for k,v in ps.items():
                    try:
                        psDef[k] = v
                        log.info("Set PadStack %s property: %s->%s"%(psDef.Name,str(k),str(v)))
                    except:
                        log.info("PadStack %s property set error: %s->%s"%(psDef.Name,str(k),str(v)))

    def createPinGroup(self):
        if "PinGroup" not in self.Config:
            return
        
        log.info("createPinGroup")
        
        PinGroup = self.Config["PinGroup"]
        if not PinGroup["Enable"]: 
            log.info("PinGroup is disabled,skip.")
            return
        
        if "RemoveExistPinGroups" in PinGroup and PinGroup["RemoveExistPinGroups"]:
            self.layout.PinGroups.deleteAllPinGroups()

        if not PinGroup["Groups"]:
            return
        groupDictList = []
        for group in PinGroup["Groups"]:
            #gDict (_type_): {"Name":"","Refdes":"","Pins":[],"Nets":"","Rows":1,"Cols":1}]
            temp = {"Name":"","Refdes":"","Pins":[],"Nets":"","Rows":1,"Cols":1}
            temp.update(group)
            groupDictList.append(temp)
            # self.layout.PinGroups.createByDict(temp)
        self.layout.PinGroups.createByDictList(groupDictList)
        self.layout.save()
        
    def createSource(self):
        if "Source" not in self.Config:
            return
        log.info("Create Source")
        Source = self.Config["Source"]
        if not Source["Enable"]:
            log.info("Source not enable.")
            return
        
        SourceDefs = Source["SourceDefs"]
        if "RemoveExistSources" in Source and Source["RemoveExistSources"]:
            self.layout.Sources.deleteAllSources()
            self.layout.PinGroups.deleteAllPinGroups()

        if not SourceDefs: 
            return
        for SourceDef in SourceDefs:
            temp = ComplexDict({"Pt0":None,"Pt1":None,"Layer":None,"Layer2":None,
                    "PosPins":None,"RefPins":None,"CompName":None,"PosNet":None,"NegNet":None,
                    "Type":None,"Name":None,"Magnitude":None,"Resistance":None})
            temp.updates(SourceDef)
            self.layout.Sources.addSourceByDict(temp)
        self.layout.save()
        
    def solveSetup(self):

        if "Setup" not in self.Config:
            return
        
        log.info("Add solver setup")
        
        Setup = self.Config["Setup"]
        
        if not Setup["Enable"]:
            log.info("Setup not enable.")
            return

        #清楚所有setups #20260718
        self.layout.Setups.deleteAll()
        
        setup1 = self.layout.Setups.add(Setup["Name"], Setup["SolutionType"])
#         datas = setup1.getData()
        for k,v in Setup["Options"].Dict.items():
            try:
                val = setup1[k]
            except:
                count = setup1.updateByKey(k,v) #update by key
                if not count:
                    log.warning("key %s not found in %s"%(k,Setup["Name"]))
            else:
                setup1[k] = val.__class__(v)

        #for sweep datas
        if "Sweep" not in Setup:
            return
        
        Sweep = Setup["Sweep"]
        if not Sweep["Enable"]:
            log.info("Sweep not enable.")
            return
        
        sweep1 = setup1.addSweep(Sweep["Name"],sweepFreqData=Sweep["Options"]["SweepData"]) #fix 3DL-siwave bug
#         datas = sweep1.getData()
        for k,v in Sweep["Options"].Dict.items():
            try:
                val = sweep1[k]
            except:
                log.warning("Sweep option %s not found."%k)
            else:
                sweep1[k] = val.__class__(v)
        self.layout.save()
    
    def setAirbox(self):
        if "Airbox" not in self.Config:
            return
        if not self.Config["Airbox"]["Enable"]: 
            log.info("Airbox is disabled,skip.")
            return

        log.info("Set airbox")
        options = self.Config["Airbox"]["Options"]
        for k,v in options.Dict.items():
            try:
                self.layout.Airbox[k] = v
            except:
                log.warning("Airbox option %s not found."%k)

    def analyze(self):

        if "Analysis" not in self.Config:
            return
        Analysis = self.Config["Analysis"]
        if not Analysis["Enable"]:
            log.info("Analysis not enable.")
            return
        log.info("Run the simution")

        setup = self.Config["Setup"] 
        sweepName = ""
        if setup["Enable"]:
            setupName = setup["Name"]
            if "Sweep" in setup and "Name" in setup["Sweep"]:
                sweepName = setup["Sweep/Name"]
        else:
            setups = self.layout.Setups
            if len(setups)<1:
                log.exception("layout don't have any analysis setup ...")
            
            setup2 = setups[0]
            setupName = setup2.name
            if setup2.Sweeps:
                sweepName = setup2.Sweeps[0].name

        if self.layout.NonGraphical or ("BatchMode" in Analysis and Analysis["BatchMode"]): # batchAnalyze only in NonGraphical mode
            log.info("Run the batch mode simution under NonGraphical mode.")
            tempPath = self.layout.ProjectPath
            cores = 4
            Analysis = self.Config["Analysis"]
            if "Cores" in Analysis and Analysis["Cores"]:
                cores = Analysis["Cores"]
            self.layout.batchAnalysis(cores=cores)
            self.layout.openAedt(tempPath)
            self.layout.initDesign()
        else:

            if "Cores" in Analysis and Analysis["Cores"]:
                self.layout.setCores(cores=Analysis["Cores"], hpcType=Analysis["HPCType"])
            
            log.info("Starting analysis for setup %s ..."%setupName)       
            self.layout.Setups[setupName].analyze()
        
        if "ExportSNP" in Analysis:
            #not work for SIwaveDC, CPA
            solution = self.layout.Solutions["%s:%s"%(setupName,sweepName)]
            if "ExportSNP" in Analysis and Analysis["ExportSNP"]:
                if not Analysis["SnpPath"] and self.Config["Header"]["Name"]:
                    Analysis["SnpPath"] = os.path.join(self.layout.ProjectDir,self.Config["Header"]["Name"])
                solution.exportSNP(Analysis["SnpPath"])
        self.layout.save()
    
    def workflow(self):
        '''
        workflow:
        
        laod PCB -> load stackup -> configComponents -> ConfigNets -> Cutout -> Port -> solveSetup -> Solve -> datas -> Post
        '''
        
        #---load layout file
        self.loadLayout()
        
        #---disable autoSave, must after oDesktop valid (loadLayout)
        autoSave = self.layout.enableAutosave(False) 
        #---preConfig
        self.preConfig()
        
        #---load stackup
        self.loadStackup()
        
        #ConfigNets
#         layout.configNets()
        #---cutout pcb to reduced simulaiton time
        self.cutoutDesign()
        
        #---clear layout befor analysis
        self.clearLayout()
        
        #--- Config Nets
        self.configNets()

        #---Component models
        self.configComponents()
    
        #---backdrill
        self.backdrill()
    
        #---pin group
        self.createPinGroup()

        #---Create solderball
        self.createSolderall()
        
        #---setPadstack
        self.setPadstack()
        
        #---create ports
        self.setPorts()
        
        #---create createSource
        self.createSource()

        #---create ports
        self.geometryCheckAndAutofix()
        
        #---solve frequency, sweep scope
        self.solveSetup()

        #---set airbox
        self.setAirbox()

        #---run the simution
        self.analyze()
        
        self.layout.enableAutosave(autoSave)

    def run(self):
        '''
        workflow:
        
        laod PCB -> load stackup -> configComponents -> ConfigNets -> Cutout -> Port -> solveSetup -> Solve -> datas -> Post
        '''
        try:
            self.workflow()
            
            #plot message
            log.info("--------------------------------------------------------")
            log.info("-------Below Message only use for Debug-----------------")
            messages = self.layout.getAedtMessage(0) #1 – warning and above
            log.info("Desktop Message:")
            log.info("".join(messages))
            messages = self.layout.getDesignMessage(0) #1 – warning and above
            log.info("Design Message:")
            log.info("".join(messages))
            log.info("---------End Message only use for Debug-----------------")
            log.info("--------------------------------------------------------")

            #---quit Aedt
            self.layout.close()
            self.layout.quitAedt(force=True)
        except Exception as e:
            log.info(str(e))
            self.layout.killProcess()
            
#for test
if __name__ == '__main__':
    
#     configPath = os.path.join(appDir,r"snpExtract_galileo_brd.json")
    configPath = r"C:\work\Project\AE\Script\snp_extraction\test_from_users\test_004ED0_PCB.json"
    layout = Layout()
    layout.initDesign() #use exist aedt 
    sim = ExtractBase()
    sim.layout = layout
    sim.solveSetup()

    print("finished.")
    pass        
