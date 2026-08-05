#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20231107

from .common.common import log,loadJson,writeJson
from .common.complexDict import ComplexDict
import sys,os,re


class Option(ComplexDict):
    
    
    def __init__(self,dictData=None):
        super(self.__class__,self).__init__(dictData=dictData,path=None,maps=None)
        FormatDict = {
            "list":[],
            "dict":[],
            "float":[],
            "int":[],
            "bool":[],
            "func":[]
            }
        self.update("FormatDict", FormatDict)
        self.format()
        
    
    def readConfig(self,path):
        if os.path.exists(path):
            config = loadJson(path)
            self.updateOptions(config)
            self.format()
        else:
            log.exception("Not found config file %s"%path)

    def writeConfig(self,path):
        self.writeJson(path)

#     def getFileConfig(self,path):
#         if os.path.exists(path):
#             config = loadJson(path)
#             self.updateOptions(config)
#         else:
#             log.info("Not found config file, create new config: tech2xmlOption.json")
#             writeJson(path,self._dict)
    
    def add(self,key,value):
        return self.update(self,key,value)

    
    def updateEnvOption(self):
        for key in os.environ:
            if key in self:
                self[key] = os.environ[key]
        self.format()
        
    def updateArgsOption(self):
        #for arguments
        args = sys.argv[1:]
    #         print(args)
        l = len(args)
        for i in range(l):
            if args[i].startswith("-"):
                if i > l-2:
                    continue
                
                if not args[i+1].startswith("-"):
                    self.add(args[i][1:],args[i+1])
                    i += 1
                else:
                    self.add(args[i][1:],None)
        self.format()

    def format(self):
        options = self._dict
        #---int
        for k in self.FormatDict["int"]:
            if isinstance(options[k], str):
                options[k] = int(options[k])
                
        #---float
        for k in self.FormatDict["float"]:
            if isinstance(options[k], str):
                options[k] = float(options[k])
        #---bool
        for k in self.FormatDict["bool"]:
            if isinstance(options[k], str):
                if options[k].lower() in ["true","1"]:
                    options[k] = True
                elif options[k].lower() in ["false","0"]:
                    options[k] = False
    
        #---list
        for k in self.FormatDict["list"]:
            if isinstance(options[k], str):
                options[k] = re.split("[\s,]*",re.sub(r"[\[\]\'\"]","",options[k]))
    
        #---dict
        for k in self.FormatDict["dict"]:
            if isinstance(options[k], str):
                options[k] = dict([x.split(':', 1) for x in re.split("[\s,]*",re.sub(r"[\[\]\'\"]","",options[k]))])
                
        #---func
        for k in self.FormatDict["func"]:
            if isinstance(options[k], str):
                options[k] = eval(options[k])


options = Option({
    
    "H3DL_CutExpansion": "10mm",
    "H3DL_backdrillStub": "8mil",
    #--- Net classify
    "H3DL_PowerNetReg": ".*VDD.*,.*VCC.*",
    "H3DL_GNDNetReg": ".*GND.*,.*VSS.*",
    "H3DL_SignetNetReg": "None",
    "H3DL_IgnoreNetReg": ".*NC.*",
    #--- RLC
    "H3DL_ResistorReg": "R\\d+",
    "H3DL_InductorReg": "L\\d+",
    "H3DL_CapacitorReg": "C\\d+",
    #--- Solder
    "H3DL_solderBallHeightRatio":0.7, #2/3 ?
    "H3DL_solderBallWidthRatio":0.7,  # 0.8?
    #---license
    "AEDT_WaitForLicense": False,
    "AEDT_LicenseServer": "", #1055@shnyguo, ANSYSLMD_LICENSE_FILE and ANSYSLI_SERVERS
    "AEDT_KeepGUILicense": False, # True: keep false: not keep
    #---solver
    "AEDT_HPC_MachineName":'localhost',
    "AEDT_HPC_NumCores":None,
    #---default
    "H3DL_Default":None
})

