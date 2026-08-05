#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 20230410

'''
    ArrayStruct used to manage string array struct in HFSS/3DL/SIwave or other AEDT tools, like setup information as below
    
    ```python
    datas = [
        "NAME:HFSS_Setup",
        [
            "NAME:Properties",
            "Enable:="        , "true"
        ],
        "CustomSetup:="        , False,
        "AutoSetup:="        , False,
        "SliderType:="        , "Balanced",
        "SolveSetupType:="    , "HFSS",
        "PercentRefinementPerPass:=", 30,
        "MinNumberOfPasses:="    , 1,
        "MinNumberOfConvergedPasses:=", 1,
        "UseDefaultLambda:="    , True,
        "UseMaxRefinement:="    , False,
        "MaxRefinement:="    , 1000000,
        ...
    ```
    
    Examples:
        >>> arys = ArrayStruct(datas)
    
        Get data "SolveSetupType"
        >>> arys.get("SolveSetupType")
        >>> arys["SolveSetupType"]
        
        Get data "Enable"
        >>> arys.get("Properties/Enable")
        >>> arys["Properties/Enable"]
    
        Set data "SolveSetupType"
        >>> arys.set("SolveSetupType","HFSS")
        >>> arys[SolveSetupType"] = "HFSS"
        
        Set data "Enable"
        >>> arys.set("Properties/Enable","true")
        >>> arys["Properties/Enable"] = "true"
        
        Get sub Array. if self[] value is list, it will return a sub ArrayStruct of the new list value.
        >>> arys["Properties"]
        But get() will return the list, will not generate new ArrayStruct
        >>>arys.get("Properties")
        
        Set a new list value to "Properties"
        >>> arys["Properties"] =   [
            "NAME:Properties",
            "Enable:="        , "true"
        ]
    
'''

import re
from copy import deepcopy
from .complexDict import ComplexDict
from .common import log

# --- Optimized Helper Functions ---

def _find_key_in_level(datas, key, ignorCase=True):
    """
    Simulates the exact logic of the original getArrayData search loop.
    Returns (index, type) where:
    - type 'value': Found "Key:=", value is at index + 1
    - type 'block': Found a list/tuple/ArrayStruct containing "NAME:Key", block is at index
    Returns (-1, None) if not found.
    """
    if not datas:
        return -1, None
        
    key_name = key.strip()
    key_lower = key_name.lower()
    
    name_key_str = "NAME:%s" % key_name
    name_key_lower = name_key_str.lower()
    
    value_key_str = "%s:=" % key_name
    value_key_lower = value_key_str.lower()

    for i, val in enumerate(datas):
        # Case 1: Val is a container (List, Tuple, or ArrayStruct)
        # Original code checks if this container CONTAINS "NAME:Key"
        if isinstance(val, (list, tuple, ArrayStruct)):
            # We need to scan inside val to see if it starts with or contains NAME:Key
            # Original code: for val2 in val: if val2 == "NAME:Key": return val
            found_name = False
            for sub_item in val:
                if isinstance(sub_item, str):
                    if ignorCase:
                        if sub_item.lower() == name_key_lower:
                            found_name = True
                            break
                    else:
                        if sub_item == name_key_str:
                            found_name = True
                            break
            if found_name:
                return i, 'block'
                
        # Case 2: Val is a string
        # Original code checks if val == "Key:="
        elif isinstance(val, str):
            if ignorCase:
                if val.lower() == value_key_lower:
                    return i, 'value'
            else:
                if val == value_key_str:
                    return i, 'value'
                        
    return -1, None

def getArrayData(datas, keys, ignorCase=True):
    '''
    Optimized iterative version matching original recursive logic.
    '''
    if not keys:
        return None

    current_data = datas
    
    for k in keys:
        if not isinstance(current_data, (list, tuple, ArrayStruct)):
            # If current data is not a container, we can't go deeper
            # Original code would fail here in the next recursion step's loop
            return None
            
        idx, typ = _find_key_in_level(current_data, k, ignorCase)
        
        if idx == -1:
            raise Exception("key %s not in array"%str(keys))
            
        if typ == 'value':
            # Value is at idx + 1
            if idx + 1 < len(current_data):
                current_data = current_data[idx+1]
            else:
                return None
        elif typ == 'block':
            # The block itself is at idx
            current_data = current_data[idx]
        else:
            return None
            
    return current_data
                    
def setArrayData(datas, keys, value, ignorCase=True):
    '''
    Optimized iterative version.
    '''
    if not keys:
        return None

    if len(keys) > 1:
        parent_data = getArrayData(datas, keys[:-1], ignorCase)
        if parent_data is None:
            raise Exception("Parent path not found for %s" % str(keys))
        
        key = keys[-1]
        idx, typ = _find_key_in_level(parent_data, key, ignorCase)
        
        if idx == -1:
            raise Exception("key error.%s"%str(keys))
            
        if typ == 'value':
            if idx + 1 < len(parent_data):
                old_val = parent_data[idx+1]
                if hasattr(old_val, '__class__') and not isinstance(old_val, bool):
                     try:
                         parent_data[idx+1] = old_val.__class__(value)
                     except Exception:
                         parent_data[idx+1] = value
                else:
                    parent_data[idx+1] = value
            else:
                raise Exception("Value missing for key %s" % key)
        elif typ == 'block':
            parent_data[idx] = value
        else:
            raise Exception("Unknown key type")
        return

    else: # len(keys) == 1
        key = keys[0]
        idx, typ = _find_key_in_level(datas, key, ignorCase)
        
        if idx == -1:
            raise Exception("key error.%s"%str(keys))
            
        if typ == 'value':
            if idx + 1 < len(datas):
                old_val = datas[idx+1]
                if hasattr(old_val, '__class__') and not isinstance(old_val, bool):
                     try:
                         datas[idx+1] = old_val.__class__(value)
                     except Exception:
                         datas[idx+1] = value
                else:
                    datas[idx+1] = value
            else:
                raise Exception("Value missing for key %s" % key)
        elif typ == 'block':
            datas[idx] = value
        else:
            raise Exception("Unknown key type")

def delArrayKey(datas, keys, ignorCase=True):
    '''
    Optimized iterative version.
    '''
    if not keys:
        return None

    if len(keys) > 1:
        parent_data = getArrayData(datas, keys[:-1], ignorCase)
        if parent_data is None:
            raise Exception("Parent path not found for %s" % str(keys))
        return delArrayKey(parent_data, [keys[-1]], ignorCase)
    
    else: # len(keys) == 1
        key = keys[0]
        idx, typ = _find_key_in_level(datas, key, ignorCase)
        
        if idx == -1:
            raise Exception("key not in array:%s"%str(keys))
            
        if typ == 'value':
            datas.pop(idx) 
            if idx < len(datas):
                datas.pop(idx)
        elif typ == 'block':
            datas.pop(idx)
        else:
            raise Exception("Unknown key type")


class ArrayStruct(object):
    '''
    classdocs
    '''

    def __init__(self, datas=None, maps=None):
        '''
        Constructor
        '''
        self._datas = [] if datas is None else datas #tuple2list(datas) will change list id
        self.maps = maps
        self._keys = None

    def __del__(self):
        del self._datas
        del self._keys
        del self.maps

    def _get_maps(self):
        if self.maps and isinstance(self.maps, (dict, ComplexDict)):
            return ComplexDict(self.maps)
        return None
    #20260613 增加__iter__() 方法，suport for for loop, return only key value
    def __iter__(self):
        return iter(self.Keys)
        
    def __getitem__(self, key):
        
        # if isinstance(key, int):
        #     if len(self.Keys):
        #         #use for loop iteration
        #         return self.Keys[key]
        #     else:
        #         #use as list
        #         return self.Array[key]
        if isinstance(key, (int,slice)):
            return self.Array[key] #return as list, not ArrayStruct, use as: a[0] = xxx
            # return self.Keys[key] #20260613 suport for for loop, return only key value

        #map key have high priority then Array key
        maps = self._get_maps()
        if maps:
            if key in maps:
                log.debug("found key in array, mapKey: %s->%s:"%(key,maps[key]))
                mapKey = maps[key]
                if isinstance(mapKey,ComplexDict): #if map key is dict, execulte lambda function
                    if isinstance(mapKey["Key"], str): #if only one key
                        data = self.get(mapKey["Key"])
                        return mapKey["Get"](data)
                    elif isinstance(mapKey["Key"], (list,tuple,ArrayStruct)): #if more then one key
                        datas = [self.get(value) for value in mapKey["Key"]] 
                        return mapKey["Get"](*datas)
                    else:
                        pass
                else:
                    return self.get(mapKey)
        
        #Array key
        val = self.get(key)
        if isinstance(val, (list,tuple)):
            return ArrayStruct(val)
#             return self.__class__(val)
        else:
            return val
        #return self.get(key)
    
    def __setitem__(self,key,value):
        
        #map key have high priority then Array key
        maps = self._get_maps()
        if maps:
            if key in maps:
                log.debug("found key in array, mapKey: %s->%s:"%(key,maps[key]))
                mapKey = maps[key]
                if isinstance(mapKey,ComplexDict): #if map key is dict, execulte lambda function
                    if isinstance(mapKey["Key"], str): #if only one key
                        self.set(mapKey["Key"],mapKey["Set"](value))

                    elif isinstance(mapKey["Key"], (list,tuple,ArrayStruct)): #if more then one key, lambda should return same size value
                        mapped_values = mapKey["Set"](value)
                        if len(mapped_values) != len(mapKey["Key"]):
                            raise Exception("Set map return size mismatch for key: %s" % str(key))
                        for i in range(len(mapKey["Key"])):
                            self.set(mapKey["Key"][i],mapped_values[i])
                    else:
                        pass
                else:
                    self.set(mapKey,value)
                
                return None
        else:
            pass

        #Array key have lower priority
        self.set(key,value)
        
    def __delitem__(self,key):

        #map key have high priority then Array key
        maps = self._get_maps()
        if maps:
            if key in maps:
                log.debug("found key in array, mapKey: %s:"% key)
                mapKey = maps[key]
                if isinstance(mapKey,ComplexDict):
                    log.debug("Could not remove function maps keys: %s"%key)
#                     if isinstance(mapKey["Key"], str):
#                         self.set(mapKey["Key"],mapKey["Set"](value))
#                     elif isinstance(mapKey["Key"], (list,tuple)):
#                         for i in range(len(mapKey["Key"])):
#                             self.set(mapKey["Key"][i],mapKey["Set"](value)[i])
#                     else:
#                         pass
                else:
                    self.delKey(mapKey)
                
                return None
        else:
            pass

        #Array key have lower priority
        self.delKey(key)
        
    def __contains__(self,key):
        
        if self.maps and key in self.maps:
            return True
        
        if key in self.Keys:
            return True
        
        try:
            self[key]
            return True
        except Exception:
            log.debug("Contains miss with key: %s"%key)
            return False
        
#         try:
#             self[key]
#         except:
#             return False
#         
#         return True
            
    def __getattr__(self,key):
        try:
            return  object.__getattribute__(self,key)
        except AttributeError:
            log.debug("__getattribute__ from _options")
            return self[key] #self.get(key)

        raise Exception("Key not found: %s"%key)

         
    def __setattr__(self, key, value):
        if key in ["_datas","_keys","maps"]:
            object.__setattr__(self,key,value)
        else:
            self[key] = value
            
    def __dir__(self):
        return dir(self.__class__) + list(self.__dict__.keys()) + self.Keys
        
    def __len__(self):
        return len(self.Array)
        
    def __str__(self, *args, **kwargs):
        return str(self.Array)
        
    def __repr__(self, *args, **kwargs):
        return "ArrayStruct object:" + str(self.Array)

    @property
    def Keys(self):
        '''
        Returns: 
        list: all subkeys 
        '''
        return self.keys()
    
    def keys(self):
        if not self._keys:
            self._keys = []
            for item in self._datas:
                if isinstance(item, str) and item.endswith(":="):
                    self._keys.append(item[:-2] )
                if isinstance(item, (list,tuple,ArrayStruct)):
                    for subItem in item:
                        if isinstance(subItem, str) and subItem.startswith("NAME:"):
                            self._keys.append(subItem[5:])
        return self._keys
    
    
    @property
    def Array(self):
        return self._datas 
    
    @property
    def Datas(self):
        return self._datas 
    
    
    @Datas.setter
    def Datas(self, value):
        self._datas = value
        self._keys = None

    
    def get(self,path):
        '''
        return list data
        '''
        datas = self._datas
        if not path:
            return datas
        
        if isinstance(path, str):
            keyList = re.split(r"[\\/]", path)
            return self.get(keyList)
        
        if isinstance(path,(list,tuple,ArrayStruct)):
            keys = [k for k in path if isinstance(k, str) and k.strip()] #filter empty key
            return getArrayData(datas, keys)
        
        raise Exception("key not found: %s"%str(path))
        
    def set(self,path,value):
        datas = self._datas
        if not path:
            raise Exception("set key must give.")
        
        if isinstance(path, str):
            keyList = re.split(r"[\\/]", path)
            return self.set(keyList,value)
        
        if isinstance(path,(list,tuple,ArrayStruct)):
            keys = [k for k in path if isinstance(k, str) and k.strip()] #filter empty key
            rst = setArrayData(datas, keys, value)
            self._keys = None
            return rst
        
        raise Exception("key not found: %s"%str(path))
    
    def append(self,value):
        self._datas.append(value)
        self._keys = None
        
    def insert(self,value,after=None):
        if after is None:
            self._datas.append(value)
        else:
            idx, typ = _find_key_in_level(self._datas, after)
            if idx == -1:
                raise Exception("key not in array:%s"%str(after))
            if typ == 'value':
                self._datas.insert(idx + 2, value)  # Insert after the value
            elif typ == 'block':
                self._datas.insert(idx + 1, value)  # Insert after the block
            else:
                raise Exception("Unknown key type")
        self._keys = None

    def replaceKey(self,oldKey,newKey):
        datas = self._datas
        if not oldKey or not newKey:
            raise Exception("replace key must give.")
        
        if isinstance(oldKey, str) and isinstance(newKey, str):
            oldKeyList = re.split(r"[\\/]", oldKey)
            newKeyList = re.split(r"[\\/]", newKey)
            if len(oldKeyList) != len(newKeyList):
                raise Exception("old key and new key must have same length.")
            for i in range(len(oldKeyList)):
                idx, typ = _find_key_in_level(datas, oldKeyList[i])
                if idx == -1:
                    raise Exception("key not in array:%s"%str(oldKey))
                if typ == 'value':
                    datas[idx] = "%s:=" % newKeyList[i]
                elif typ == 'block':
                    datas[idx] = "NAME:%s" % newKeyList[i]
                else:
                    raise Exception("Unknown key type")
        else:
            raise Exception("old key and new key must be string.")
        self._keys = None


    def delKey(self,path):
        
        datas = self._datas
        if not path:
            raise Exception("set key must give.")
        
        if isinstance(path, str):
            keyList = re.split(r"[\\/]", path)
            return self.delKey(keyList)
        
        if isinstance(path,(list,tuple,ArrayStruct)):
            keys = [k for k in path if isinstance(k, str) and k.strip()] #filter empty key
            rst = delArrayKey(datas, keys)
            self._keys = None
            return rst
            
        raise Exception("key not found: %s"%str(path))
        
        
    def update(self,datas):
        '''
        data should be like dict: dict, ComplexDict, ArrayStruct
        '''
        for item in datas:
            try:
                self[item] = datas[item]
            except Exception:
                log.debug("item not found when update ArrayStruct: %s"%str(item))
        self._keys = None

    
    def updateByKey(self,key,value):
        '''
        update all matched key to value 
        '''
        count = [0]  #python 2.7 not support nonlocal keyword
        def _update(key,value,datas):
            
            for i, k in enumerate(datas):
                if isinstance(k, (list,tuple,ArrayStruct)):
                    _update(key,value,k)
                elif isinstance(k, str) and k.lower() == "%s:="%key.lower():
                    index = i + 1
                    if index >= len(datas):
                        continue
                    old_val = datas[index]
                    if hasattr(old_val, '__class__') and not isinstance(old_val, bool):
                        try:
                            datas[index] = old_val.__class__(value)
                        except Exception:
                            datas[index] = value
                    else:
                        datas[index] = value
                    count[0] = count[0] + 1
                else:
                    pass
        _update(key, value, self.Datas) 
        self._keys = None
        return count[0]
    
    def setMaps(self,maps):
        self.maps = maps
    
    def copy(self):
        return self.__class__(deepcopy(self.Array),maps = self.maps)