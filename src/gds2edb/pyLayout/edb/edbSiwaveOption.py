#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20250403


import os,sys,re
# from ..common.common import readCfgFile,log
from ..common.common import *
from ..common.config import Config
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class EdbSIwaveOptions(object):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        self._config = None
        self.edbApp = edbApp
        self.loadOptions()

    def __getitem__(self, key):
        """
        key: str
        """
        return self.get(key)


    def __setitem__(self,key,value):
        self.set(key,value)

    def __getattr__(self,key):

        if key in ["edbApp","_config","maps","cell"]:
            return object.__getattribute__(self,key)
        else:
            log.debug("__getattr__ from _dict: %s"%key)
            return self[key]
        

    def __setattr__(self, key, value):
        if key in ["edbApp","_config","maps","cell"]:
            object.__setattr__(self,key,value)
        else:
            log.debug("get property '%s' from dict."%key)
            self[key] = value

    def __repr__(self):
        return "%s Object: %s"%(self.__class__.__name__,"SIwaveOptions")
    
    def __contains__(self,key):
        return key in self.Config
    
    def __dir__(self):
        return list(dir(self.__class__)) + list(self.__dict__.keys()) + list(self.Props)

    @property
    def Config(self):
        if not self._config:
            self.loadOptions()
            
        return self._config

    @property
    def Props(self):
        propKeys = list(self.Config.Keys)
        if self.Config.maps:
            propKeys += list(self.Config.maps.keys())
        
        return propKeys
    

    def get(self,key):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if not self._config:
            self.loadOptions()
  
        
        if not isinstance(key, str): #key must string
            log.exception("Property error: %s"%(str(key)))

        if key in self._config and self._config[key] != None: # Map value or already have value
            siwave_id = self.edbApp.Edb.ProductId.SIWave
            cell = self.edbApp.cell
            val= cell.GetProductProperty(siwave_id, int(self._config[key]))
            if val[0]:
                return val[1]
            else:
                log.error("Get Property error: %s"%(key))
#             cell.SetProductProperty(siwave_id, 515, '1')
            return None
        return None
        
        
    
    def set(self,key,value):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if not self._config:
            self.loadOptions()
  
        
        if not isinstance(key, str): #key must string
            log.exception("Property error: %s"%(str(key)))

        if key in self._config and self._config[key] != None: # Map value or already have value
            siwave_id = self.edbApp.Edb.ProductId.SIWave
            cell = self.edbApp.cell
            rst = cell.SetProductProperty(siwave_id,int(self._config[key]), str(value))
            if not rst:
                log.error("Get Property error: %s"%(key))
            else:
                log.info("Sucessful set %s value %s"%(key,value))
        else:
            log.error("Unknown Property key: %s"%(key))



    def loadOptions(self):
        cfgPath = os.path.join(appDir,"SIwaveProductProperties.cfg")
        cfgDict = readCfgFile(cfgPath)
        maps = {}
        for key,value in cfgDict.items():
            key2 = key.replace("_","") ##remove -  
            if key2 != key:
                key3 = key.title().replace("_","")
                maps[key3] = key
        self._config = Config(cfgDict)
        self._config.setMaps(maps)


