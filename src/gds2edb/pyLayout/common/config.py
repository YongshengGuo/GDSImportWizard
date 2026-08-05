
#coding:utf-8
#--- coding=utf-8
#--- @author: yongsheng.guo@ansys.com
#--- @Time: ver 6.0 20230721

import sys,os,re
from .common import log,loadJson,writeJson,readCfgFile
from .complexDict import ComplexDict


class Config(ComplexDict):
    
    
    def __init__(self,dictData=None):
        super(Config,self).__init__(dictData=dictData,path=None,maps=None)
        FormatDict = {
            "list":[],
            "dict":[],
            "str":[],
            "float":[],
            "int":[],
            "bool":[],
            "func":[]
            }
        self.update("FormatDict", FormatDict)
        self.format()
        
    
    def readJson(self,path):
        if os.path.exists(path):
            config = loadJson(path)
            self.updates(config)
            self.format()
        else:
            log.exception("Not found config file: %s"%path)
    
    def readCfgFile(self,path):
        """
        read ini format file
        """
        cfg_dict = readCfgFile(path)
        self.updates(cfg_dict)
        self.format()

        
    def updateEnvOption(self):
        for key in os.environ:
            if key in self:
                self[key] = os.environ[key]
        self.format()
        
    def updateArgsOption(self):
        #for arguments
        args = sys.argv[1:]
        l = len(args)
        i = 0
        while i < l:
            if args[i].startswith("-"):
                if i < l-1 and not args[i+1].startswith("-"):
                    self._dict[args[i][1:]] = args[i+1]
                    i += 2
                else:
                    self._dict[args[i][1:]] = None
                    i += 1
            else:
                i += 1
        self.format()

    def _split_items(self, value):
        text = re.sub(r"[\[\]'\"]", "", value).strip()
        if not text:
            return []
        return [item for item in re.split(r"[\s,]+", text) if item]

    def format(self):
        options = self._dict
        #---int
        for k in self.FormatDict["int"]:
            if k in options and isinstance(options[k], str):
                options[k] = int(options[k])
                
        #---float
        for k in self.FormatDict["float"]:
            if k in options and isinstance(options[k], str):
                options[k] = float(options[k])

        #---str
        for k in self.FormatDict["str"]:
            if k in options and not isinstance(options[k], str):
                options[k] = str(options[k])

        #---bool
        for k in self.FormatDict["bool"]:
            if k in options and isinstance(options[k], str):
                if options[k].lower() in ["true","1"]:
                    options[k] = True
                elif options[k].lower() in ["false","0"]:
                    options[k] = False
    
        #---list
        for k in self.FormatDict["list"]:
            if k in options and isinstance(options[k], str):
                options[k] = self._split_items(options[k])
    
        #---dict
        for k in self.FormatDict["dict"]:
            if k in options and isinstance(options[k], str):
                items = self._split_items(options[k])
                options[k] = dict(item.split(':', 1) for item in items if ':' in item)
                
        #---func
        for k in self.FormatDict["func"]:
            if k in options and isinstance(options[k], str):
                options[k] = eval(options[k])
            
                
#         return ComplexDict(options)

