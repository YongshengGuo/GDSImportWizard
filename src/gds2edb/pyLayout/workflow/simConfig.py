#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20240830


'''
minidom not work for ironpython, etree is used for xml reading
'''

import sys,os
from ..common.common import log,writeJson
from ..common.complexDict import ComplexDict

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)


class SimConfig(ComplexDict):
    '''
    intial the default config.
    if simConfigPath given, it will be update to get new config
    '''
    
    def __init__(self, simConfig = None, defaultConfig = None):
        '''
        simConfig: Path, dict, complexDict
        defaultConfig: Path, dict, complexDict, priority for script directory
        
        '''
        super(self.__class__,self).__init__()
#         self._dict = None
# 
        #load default config
        if not defaultConfig:
            configPath = os.path.join(os.path.dirname(sys.argv[0]),"default.json")
            if not os.path.exists(configPath):
                log.info("Not found default.json in script dir, use default.json")
                configPath = os.path.join(appDir,"default.json")
            else:
                pass
#                 log.info("Load config file from %s"%configPath)
            defaultConfig = configPath
            self.loadConfig(defaultConfig)
        else:
            if os.path.exists(defaultConfig):
                self.loadConfig(defaultConfig)
            elif os.path.exists(os.path.join(os.path.dirname(sys.argv[0]),defaultConfig)):
                self.loadConfig(os.path.join(os.path.dirname(sys.argv[0]),defaultConfig))
            elif os.path.exists(os.path.join(appDir,defaultConfig)):
                self.loadConfig(os.path.join(appDir,defaultConfig))
            else:
                log.error("%s not found."%defaultConfig)
         
        if simConfig:
#             conf = ComplexDict.loadConfig(simConfig)
            self.updateConfig(simConfig)
#             self.setConfigFile(simConfig)


    def __repr__(self):
        return "Config Object: %s"%(self._dict["Header"]["Name"])
    

    @property
    def Config(self):
        return self._dict
    
    def setConfigFile(self,path):
        if not os.path.exists(path):
            log.warning("Configuration Path not found %s"%path)
            return
        conf = ComplexDict.loadConfig(path)
        self.updateConfig(conf)
#         self._dict = path

    def loadConfig(self,config):
        return super(SimConfig,self).loadConfig(config)

    
    def clean(self):
        for key in list(self.Keys):
            #remove keys 
            if not isinstance(self[key],(dict,ComplexDict)):
                log.info("del issue key: %s"%key)
                del self[key]
                continue
            
            if "Enable" in self[key] and not self[key]["Enable"]:
                log.info("clear dict key: %s"%key)
                del self[key]
            
    def updateConfig(self,config):
        '''
        Agrs:
            config(dict,jsonPath,ComplexDict):  update analyze config infomation to layout
        '''
        
        # if self._dict == None:
        #     self._dict = ComplexDict()
        
        options = self.loadConfig(config)
        self.updates(options)

    def updateConfigByKey(self, configDict):

        for k,v in configDict.items():
            try:
                val = self[k]
            except:
                count = self.updateByKey(k,v) #update by key
                if not count:
                    log.warning("key %s not found."%k)
                else:
                    log.info("update Config:%s value: %s, for %s times"%(k,v,count))
            else:
                self[k] = v #add k,v

    def writeJson(self,path,clean=True):
        if clean:
            self.clean()
        writeJson(path,self._dict)
    
