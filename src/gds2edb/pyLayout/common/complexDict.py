#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230410
'''
提供一种简单快捷的方式获取JSON 或者 dict的键值

Provide a simple way to access JSON cotent or dict variables

Examples:
    >>> ops = ComplexDict({
    "Header":
            {
                "Comment": "a demo"
            },
    "TempList": [1,2,3],
    "X":1,
    "Y",1
        })
    
    Access value using path mode for dict value
    >>> ops["/Header/Comment"]
    a demo
    >>> ops["Header/Comment"]  #first / is optional
    a demo
    
    Access using key list mode
    >>> ops[("Header","Comment")]
    
    assign values using path mode
    >>> ops["/Header/Comment"] = "demo2"
    
    assign values using key list mode
    >>> ops[("Header","Comment"] = "demo2"
    
    Test value in ComplexDict object
    >>> "/Header/Comment" in ops
    True
    
    maps: used to map alias key
    
    maps 用于使用别名映射ComplexDict现有的key，使用seMaps为ComplexDict设置maps映射
    如下，用X1映射ops中的X, Y1映射OPS中的Y
    >>> maps = {"X1":"X"，"Y1":Y}
    >>> ops.setMaps(maps)
    >>> ops.X1
    返回 OPS.X的值
    >>> ops.Y1
    返回 OPS.Y的值
    
    可以进行映射运算，改变数值，需要借助lambda表达式
    >>>> maps = {"X1":{key:X,"Get"：lambda x: x-1}}
    >>> ops.setMaps(maps)
    >>> ops.X1
    返回 ops.X -1 
    
    >>>> maps = {"X1":{key:X,"Set"：lambda x: x-1}}
    >>> ops.setMaps(maps)
    >>> ops.X1 = 2
    赋值 ops.X = 2-1
    
    多个运算值的支持，支持映射多个key并对起value进行运算，进行返回。 支持对数值运算后对多个key进行赋值操作。
    >>>> maps = {"X1":{key:(X,Y)},"Get"：lambda (x,y): x+y,"Set": lambda (x,y):(x+y,x-y)}
    >>> ops.setMaps(maps)
    >>> ops.X1
    返回 ops.X + ops.Y
    >>> ops.X1 = (2,5)
    赋值 ops.X = 2 + 5, ops.Y = 2 - 5

不要尝试图使用Get/Set函数Map已经存在的属性
    
Return:
    if return value is dict, will be return ComplexDict object, else return the value

'''

'''
提供一种简单快捷的方式获取JSON 或者 dict的键值
Provide a simple way to access JSON cotent or dict variables
'''
import sys
import os
import re
from copy import deepcopy
from .common import loadJson, writeJson, findDictValue, findDictKey, update2Dict, regAnyMatch
from .common import log

# ----------------------------------------------------------------------
# Optimized Helper Functions (Non-recursive, No Regex)
# ----------------------------------------------------------------------

_SENTINEL = object()

def _normalize_key_path(key):
    if not isinstance(key, str):
        return key
    return key.replace('\\', '/')

def _split_path_parts(key):
    if not isinstance(key, str):
        return []
    return [part for part in _normalize_key_path(key).split('/') if part]

def _is_path_container(value):
    return isinstance(value, (dict, list, tuple)) or (
        hasattr(value, '__getitem__') and not isinstance(value, (str, bytes))
    )

def _find_matching_dict_key(current_data, key_part, ignorCase=True, default=_SENTINEL):
    if not isinstance(current_data, dict):
        return default

    if key_part in current_data:
        return key_part

    if ignorCase:
        existing_key = findDictKey(key_part, current_data, ignorCase=True, default=_SENTINEL)
        if existing_key != _SENTINEL:
            return existing_key

    normalized_key = _normalize_key_path(key_part)
    for existing_key in current_data:
        if not isinstance(existing_key, str):
            continue

        if ignorCase:
            if _normalize_key_path(existing_key).lower() == normalized_key.lower():
                return existing_key
        elif _normalize_key_path(existing_key) == normalized_key:
            return existing_key

    return default

def _resolve_existing_path_token(current_data, raw_parts, start_index, ignorCase=True, require_container=False):
    if start_index >= len(raw_parts):
        return _SENTINEL, 0

    if isinstance(current_data, dict):
        for end_index in range(len(raw_parts), start_index, -1):
            candidate = '/'.join(raw_parts[start_index:end_index])
            actual_key = _find_matching_dict_key(current_data, candidate, ignorCase=ignorCase, default=_SENTINEL)
            if actual_key == _SENTINEL:
                continue

            if require_container:
                next_value = _resolve_next_level(current_data, actual_key, ignorCase, default=_SENTINEL)
                if next_value is _SENTINEL or not _is_path_container(next_value):
                    continue

            return actual_key, end_index - start_index

        return _SENTINEL, 0

    return raw_parts[start_index], 1

def _walk_path_to_parent(raw_parts, dict1, ignorCase=True, enableUpdate=False):
    current = dict1
    index = 0

    while len(raw_parts) - index > 1:
        next_key, consumed = _resolve_existing_path_token(
            current,
            raw_parts,
            index,
            ignorCase=ignorCase,
            require_container=True,
        )

        if next_key == _SENTINEL:
            if enableUpdate and isinstance(current, dict):
                next_key = raw_parts[index]
                current[next_key] = {}
                current = current[next_key]
                index += 1
                continue
            break

        current = _resolve_next_level(current, next_key, ignorCase, default=_SENTINEL)
        if current is _SENTINEL:
            raise Exception("key error: path not found at '%s'" % raw_parts[index])
        index += consumed

    return current, index

def _resolve_next_level(current_data, key_part, ignorCase=True, default=_SENTINEL):
    """Helper to get next level data without recursion."""
    if isinstance(current_data, (list, tuple)):
        try:
            return current_data[int(key_part)]
        except (ValueError, IndexError, TypeError):
            return default
            
    if isinstance(current_data, dict):
        # Fast path: direct key
        if key_part in current_data:
            return current_data[key_part]
        # Slow path: case insensitive
        if ignorCase:
            val = findDictValue(key_part, current_data, default=default, ignorCase=True)
            return val
        return default
        
    if hasattr(current_data, '__getitem__'): # e.g. ComplexDict
         try:
             return current_data[key_part]
         except (KeyError, TypeError):
             if ignorCase and isinstance(current_data, dict): 
                  val = findDictValue(key_part, current_data, default=default, ignorCase=True)
                  return val
             return default
    return default

def getDictData(key, dict1, default=None, ignorCase=True):
    '''Optimized get: Iterative, no regex.'''
    if dict1 is None:
        return default

    if isinstance(dict1, (list, tuple)):
        try:
            return dict1[int(key)]
        except (ValueError, IndexError, TypeError):
            return default

    key_parts = []
    if isinstance(key, str):

        #key may have "\\", "/"
        if isinstance(dict1, dict):
            existing_key = _find_matching_dict_key(dict1, key, ignorCase=ignorCase, default=_SENTINEL)
            if existing_key != _SENTINEL:
                return dict1[existing_key]

        key_parts = _split_path_parts(key)
        if not key_parts:
            return default
        # Single key optimization
        if len(key_parts) == 1:
             val = _resolve_next_level(dict1, key_parts[0], ignorCase, default=_SENTINEL)
             return default if val is _SENTINEL else val

    elif isinstance(key, (list, tuple)):
        key_parts = [k for k in key if k and isinstance(k, str) and k.strip()]
        if not key_parts:
            return default
    else:
        return default

    current = dict1
    index = 0
    while index < len(key_parts):
        part, consumed = _resolve_existing_path_token(current, key_parts, index, ignorCase=ignorCase)
        if part == _SENTINEL:
            part = key_parts[index]
            consumed = 1

        next_val = _resolve_next_level(current, part, ignorCase, default=_SENTINEL)
        if next_val is _SENTINEL:
            return default
        current = next_val
        index += consumed
        
    return current

def setDictData(key, value, dict1, ignorCase=True, enableUpdate=False):
    '''Optimized set: Iterative, handles creation if enableUpdate.'''
    if dict1 is None:
        raise Exception("Cannot set value to None dict")

    # Unwrap ComplexDict
    actual_value = value._dict if isinstance(value, ComplexDict) else value

    key_parts = []
    if isinstance(key, str):
        #key may have "\\", "/"
        #考虑兼容 "AirPosZExt/Ext":"1.5mm", key中间有"/"或者"\\"，应当识别成key，不应做分割处理
        if isinstance(dict1, dict):
            existing_key = _find_matching_dict_key(dict1, key, ignorCase=ignorCase, default=_SENTINEL)
            if existing_key != _SENTINEL:
                dict1[existing_key] = actual_value
                return None

        key_parts = _split_path_parts(key)
    elif isinstance(key, (list, tuple)):
        key_parts = [k for k in key if k and isinstance(k, str) and k.strip()]
    else:
        raise Exception("key error: %s" % str(key))

    if not key_parts:
        raise Exception("Empty key")

    parent, leaf_start = _walk_path_to_parent(key_parts, dict1, ignorCase=ignorCase, enableUpdate=enableUpdate)
    remaining_parts = key_parts[leaf_start:]

    if not remaining_parts:
        raise Exception("Empty key")

    if isinstance(parent, dict):
        leaf_candidate = '/'.join(remaining_parts)
        existing_key = _find_matching_dict_key(parent, leaf_candidate, ignorCase=ignorCase, default=_SENTINEL)
        if existing_key != _SENTINEL:
            last_key = existing_key
        elif len(remaining_parts) == 1:
            last_key = remaining_parts[0]
        else:
            raise Exception("key error: path not found at '%s'" % remaining_parts[0])
    else:
        if len(remaining_parts) != 1:
            raise Exception("key error: path not found at '%s'" % remaining_parts[0])
        last_key = remaining_parts[0]

    if isinstance(parent, list):
        try:
            parent[int(last_key)] = actual_value
        except (ValueError, IndexError):
            raise Exception("key error: invalid index '%s'" % last_key)
    elif isinstance(parent, tuple):
        raise Exception("key error: cannot set value to tuple parent")
    elif isinstance(parent, dict):
        if ignorCase:
            existing_key = findDictKey(last_key, parent, ignorCase=True,default=_SENTINEL)
            if existing_key != _SENTINEL:
                parent[existing_key] = actual_value
                return
        
        # If key doesn't exist and enableUpdate is False, original code behavior varies.
        # Here we strictly follow: if path exists, set it. If leaf doesn't exist:
        if last_key not in parent:
             if not enableUpdate:
                 # Original code raised exception if no separator found, but here we parsed it.
                 # To be safe, if strict mode, we might raise. But usually set implies create/update.
                 pass 
             
        parent[last_key] = actual_value
    else:
        raise Exception("key error: cannot set value to non-dict/non-list parent")

def delDictKey(key, dict1, ignorCase=True):
    '''Optimized del: Iterative.'''
    if dict1 is None:
        raise Exception("Cannot delete from None dict")

    key_parts = []
    if isinstance(key, str):
        if isinstance(dict1, dict):
            existing_key = _find_matching_dict_key(dict1, key, ignorCase=ignorCase, default=_SENTINEL)
            if existing_key != _SENTINEL:
                del dict1[existing_key]
                return

        key_parts = _split_path_parts(key)
    elif isinstance(key, (list, tuple)):
        key_parts = [k for k in key if k and isinstance(k, str) and k.strip()]
    else:
        raise Exception("key error: %s" % str(key))

    if not key_parts:
        raise Exception("Empty key")

    parent, leaf_start = _walk_path_to_parent(key_parts, dict1, ignorCase=ignorCase, enableUpdate=False)
    remaining_parts = key_parts[leaf_start:]

    if not remaining_parts:
        raise Exception("Empty key")

    if isinstance(parent, dict):
        leaf_candidate = '/'.join(remaining_parts)
        existing_key = _find_matching_dict_key(parent, leaf_candidate, ignorCase=ignorCase, default=_SENTINEL)
        if existing_key != _SENTINEL:
            last_key = existing_key
        elif len(remaining_parts) == 1:
            last_key = remaining_parts[0]
        else:
            raise Exception("key error: path not found at '%s'" % remaining_parts[0])
    else:
        if len(remaining_parts) != 1:
            raise Exception("key error: path not found at '%s'" % remaining_parts[0])
        last_key = remaining_parts[0]

    if isinstance(parent, list):
        try:
            del parent[int(last_key)]
        except (ValueError, IndexError):
            raise Exception("key error: invalid index '%s'" % last_key)
    elif isinstance(parent, tuple):
        raise Exception("key error: cannot delete key from tuple parent")
    elif isinstance(parent, dict):
        if ignorCase:
            existing_key = findDictKey(last_key, parent, ignorCase=True,default=_SENTINEL)
            if existing_key != _SENTINEL:
                del parent[existing_key]
                return
            else:
                raise Exception("key error: %s not found" % last_key)
        else:
            if last_key in parent:
                del parent[last_key]
            else:
                raise Exception("key error: %s not found" % last_key)
    else:
        raise Exception("key error: cannot delete from non-dict/non-list parent")

# ----------------------------------------------------------------------
# ComplexDict Class
# ----------------------------------------------------------------------

class ComplexDict(object):  
    '''
    High-performance dictionary wrapper with path access, case-insensitivity, and mapping.
    '''
    __slots__ = ['_dict', 'maps', 'ignorCase']
    enableUpdate = False

    def __init__(self, dictData=None, path=None, maps=None):
        self._dict = {}
        self.ignorCase = True
        self.maps = maps
        
        if path:
            if os.path.exists(path):
                self._dict = loadJson(path)
            else:
                raise Exception("dictData not found:%s" % path)
            
        if isinstance(dictData, ComplexDict):
            self._dict = dictData._dict
            if self.maps is None and dictData.maps is not None:
                self.maps = dictData.maps
        elif isinstance(dictData, dict):
            self._dict = dictData

    # --- Magic Methods ---

    #20260613 增加__iter__() 方法，suport for for loop, return only key value
    def __iter__(self):
        return iter(self._dict.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            keys = list(self._dict.keys())
            if 0 <= key < len(keys):
                val = self._dict[keys[key]]
                return ComplexDict(val) if isinstance(val, dict) else val
            raise IndexError("Index out of range")
        
        if isinstance(key, slice):
            keys = list(self._dict.keys())
            return [self[i] for i in range(len(keys))[key]]

        val = self.get(key, default=_SENTINEL)
        if val == _SENTINEL:
            raise KeyError("key error: %s" % str(key))
        
        if isinstance(val, dict):
            return ComplexDict(val)
        return val

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.delKey(key)

    def __contains__(self, key):
        if self.maps:
            rst = findDictKey(key, self.maps, default=_SENTINEL, ignorCase=self.ignorCase)
            if rst != _SENTINEL:
                return True

        if key in self._dict:
            return True
        # Optimized check without exception throwing
        val = getDictData(key, self._dict, default=_SENTINEL, ignorCase=self.ignorCase)
        return val is not _SENTINEL

    def __getattr__(self, key):
        # Prevent recursion for slots
        if key in ('_dict', 'maps', 'ignorCase', 'enableUpdate'):
            raise AttributeError(key)
        
        if not isinstance(key, str):
            raise AttributeError("property or key must be string: %s" % str(key))
            
        try:
            return self.__getitem__(key)
        except KeyError:
            raise AttributeError("property or key not found: %s" % key)

    def __setattr__(self, key, value):
        if key in self.__slots__: #('_dict', 'maps', 'ignorCase')
            object.__setattr__(self, key, value)
        else:
            self.__setitem__(key, value)

    def __len__(self):
        return len(self._dict)

    def __str__(self):
        return str(self._dict)

    def __repr__(self):
        if isinstance(self._dict, dict):
            return "ComplexDict (dict) object with length: %s" % str(self._dict)
        elif isinstance(self._dict, (list, tuple)):
            return "ComplexDict (list) object with length: %s" % str(self._dict)
        else:
            return object.__repr__(self)

    def __bool__(self):
        return bool(self._dict)

    def __dir__(self):
        # Combine class attrs, instance slots, and dict keys for autocomplete
        return list(dir(self.__class__)) + list(self.__slots__) + list(self.Props)

    def __deepcopy__(self, memo):
        new_inst = ComplexDict.__new__(ComplexDict)
        new_inst._dict = deepcopy(self._dict, memo)
        new_inst.maps = deepcopy(self.maps, memo)
        new_inst.ignorCase = self.ignorCase
        new_inst.enableUpdate = self.enableUpdate
        return new_inst

    # --- Properties & Basic Accessors (Restored) ---

    @property
    def Props(self):
        propKeys = list(self._dict.keys())
        if self.maps:
            propKeys += list(self.maps.keys())
        return propKeys

    @property
    def Values(self):
        return self._dict.values()

    def values(self):
        return self._dict.values()

    @property
    def Keys(self):
        return self._dict.keys()

    def keys(self):
        return self._dict.keys()

    @property
    def Items(self):
        return self._dict.items()

    def items(self):
        return self._dict.items()

    @property
    def Count(self):
        return len(self._dict)

    @property
    def Dict(self):
        return self._dict

    # --- Core Logic (Get/Set/Del with Maps) ---
    
    def get(self,key,default = None):
        '''
        datas: {key1:value1}
        maps: {key2:key1}
        
        get(key2) from datas
        
        firt try to get from maps, then dict
        
        return dict or value
        
        fa = lambda (x,y):x+y
        fa([1,2])
        
        fb = lambda (a,b),(x,y):(a+b,x+y)
        fb([1,2],[3,4])
        
        '''
        #map key have high priority then Array key
        if self.maps and isinstance(self.maps,(dict,ComplexDict)):
            maps = ComplexDict(self.maps)
            if key in maps:
                mapKey = maps[key]
                log.debug("found key in maps: %s->%s:"%(key,mapKey))
                if isinstance(mapKey,ComplexDict): #if map key is dict, execulte lambda function
                    if isinstance(mapKey["Key"], str): #if only one key
                        data = getDictData(mapKey["Key"],self._dict, default = _SENTINEL) 
                        if data != _SENTINEL:
                            return mapKey["Get"](data)
                        elif "Default" in mapKey:
                            return mapKey["Default"]
                        else:
                            raise KeyError("key error: %s"%str(mapKey))
                        
                    elif isinstance(mapKey["Key"], (list,tuple,ComplexDict)): #if more then one key, lambda should return same size value
                        datas = [getDictData(value,self._dict, default = _SENTINEL) for value in mapKey["Key"]] 
                        if all([d!= _SENTINEL for d in datas]):
                            return mapKey["Get"](*datas)
                        elif "Default" in mapKey:
                            return mapKey["Default"]
                        else:
                            raise KeyError("key error: %s"%str(mapKey))
                    else:
                        pass
                else:
                    #return map key values
                    val = getDictData(mapKey,self._dict, default = _SENTINEL)
                    if val != _SENTINEL:
                        return val
        
        val = getDictData(key, self._dict, default = _SENTINEL)
        
        if val == _SENTINEL:
            if default == None:
                raise KeyError("key error: %s"%str(key))
            else:
                return default
        else:
            return val
    
    def set(self,key,value):
        '''
        set key to dict
        maps key have high priority then dict
        '''
        
        #map key have high priority then Array key
        if self.maps and isinstance(self.maps,(dict,ComplexDict)):
            maps = ComplexDict(self.maps)
            if key in maps:
                log.debug("found key in array, mapKey: %s->%s:"%(key,maps[key]))
                mapKey = maps[key]
                if isinstance(mapKey,ComplexDict):
                    if isinstance(mapKey["Key"], str):
                        if "Set" not in mapKey:
                            log.exception("%s property is read only."%mapKey["Key"])
                            
                        if mapKey["Key"].lower() == "self":
                            return mapKey["Set"](self[mapKey["Key"]],value)
                        else:
                            returnValue = mapKey["Set"](value)
                            
                        if returnValue!=None: 
                            #set return value to dict
                            setDictData(mapKey["Key"],returnValue,self._dict,enableUpdate=self.enableUpdate)
                        else:
                            #if returnValue is none value, which mean returnValue not need,value is set by function.
                            pass
                        
                    elif isinstance(mapKey["Key"], (list,tuple,ComplexDict)):
                        if "Set" not in mapKey:
                            log.exception("%s property is read only."%mapKey["Key"])
                        returnValue = mapKey["Set"](value)
                        if returnValue != None and len(returnValue) != len(mapKey["Key"]):
                            raise Exception("Set map return size mismatch for key: %s" % str(key))
                        for i in range(len(mapKey["Key"])): #mapKey["Key"] should be same size with returnValue
                            if returnValue!=None: 
                                setDictData(mapKey["Key"][i],returnValue[i],self._dict,enableUpdate=self.enableUpdate)
                            else:
                                #if returnValue is none value, which mean returnValue not need,value is set by function.
                                pass
                    else:
                        pass
                else:
                    setDictData(mapKey,value,self._dict,enableUpdate=self.enableUpdate)
                
                return None

        setDictData(key,value,self._dict,enableUpdate=self.enableUpdate)
        

    def delKey(self, key):
        if self.maps and isinstance(self.maps, (dict, ComplexDict)):
            for k, v in self.maps.items():
                if isinstance(k, str) and k.lower() == key.lower():
                    if isinstance(v, dict):
                        log.debug("Could not remove function maps keys: %s" % key)
                        return None
                    else:
                        log.debug("del key from map key %s:" % k)
                        delDictKey(v, self._dict)
                        return None
        delDictKey(key, self._dict)

    # --- Restored Utility Methods ---

    def clear(self):
        self._dict.clear()
        # Do NOT delete self._dict, just clear it.

    def updates(self, dict2, copy=True):
        '''Deep update from another dict/ComplexDict'''
        if isinstance(dict2, ComplexDict):
            src = dict2._dict
        elif isinstance(dict2, dict):
            src = dict2
        else:
            return

        cp = deepcopy if copy else lambda x: x
        
        if not self._dict:
            self._dict = cp(src)
            return

        for key in src:
            try:
                val = self.get(key, default=_SENTINEL)
            except:
                log.warning("key:%s not found in layer" % key)
                val = _SENTINEL
                
            if val is _SENTINEL: # Not found
                if isinstance(src[key], (dict, ComplexDict)):
                    self.update(key, cp(src[key]._dict if isinstance(src[key], ComplexDict) else src[key]))
                else:
                    self.update(key, src[key])
            else:
                if isinstance(val, (dict, ComplexDict)):
                    val2 = ComplexDict(val) if isinstance(val, dict) else val
                    src_val = src[key]
                    if isinstance(src_val, ComplexDict):
                         val2.updates(src_val, copy=copy)
                    elif isinstance(src_val, dict):
                         val2.updates(src_val, copy=copy)
                    self[key] = val2.Dict
                else:
                    self[key] = src[key]

    def update(self, key, value):
        self._dict[key] = value
        
    def updateByKey(self, key, value):
        '''Update all matched keys (case-insensitive) recursively'''
        count = [0]
        def _update(k, v, datas):
            if isinstance(datas, ComplexDict):
                datas = datas.Dict
            if not isinstance(datas, dict):
                return
            for dk in datas:
                if isinstance(datas[dk], (dict, ComplexDict)):
                    _update(k, v, datas[dk])
                elif isinstance(dk, str) and dk.lower() == k.lower():
                    datas[dk] = v
                    count[0] += 1
        _update(key, value, self._dict)
        return count[0]

    def append(self, dict2):
        if isinstance(dict2, ComplexDict):
            self._dict.update(dict2._dict)
        elif isinstance(dict2, dict):
            self._dict.update(dict2)

    def setMaps(self, maps):
        self.maps = maps

    def getMappingKeys(self, key):
        '''Get real key from maps'''
        if not isinstance(key, str):
            return key
        
        if isinstance(self.maps, (dict, ComplexDict)):
            for k, v in self.maps.items():
                if isinstance(k, str) and k.lower() == key.lower():
                    log.debug("found key in maps, mapKey: %s:" % v)
                    return v["Key"] if isinstance(v, dict) else v
        return _SENTINEL

    def getReallyKey(self, key):
        '''Get real key from maps or dict (case-insensitive)'''
        if not isinstance(key, str):
            return key
        
        key2 = self.getMappingKeys(key)
        if key2 != _SENTINEL:
            return key2
        else:
            for k in self._dict:
                if isinstance(k, str) and k.lower() == key.lower():
                    return k
            return key

    def findNode(self, nodeName):
        '''Find a node by key name recursively'''
        for k, v in self._dict.items():
            if isinstance(k, str) and k.lower() == nodeName.lower():
                return v
            elif isinstance(v, (dict, ComplexDict)):
                rst = ComplexDict(v).findNode(nodeName)
                if rst:
                    return rst
        return None

    def copy(self):
        return self.__class__(deepcopy(self._dict))

    def writeJson(self, path):
        writeJson(path, self._dict)

    
    def normalizeKeys(self):
        #标准化key，如果可以里面有/或者\\, 则将其分割为多级key
        #比如 key = {"Header/Comment":value}  will be normalized to {"Header":{"Comment":value}}
        # Iterate over a snapshot to avoid "dictionary keys changed during iteration".
        for k, v in list(self._dict.items()):
            if isinstance(v, (dict, ComplexDict)):
                v = ComplexDict(v)
                v.normalizeKeys()
                self._dict[k] = v.Dict
            if isinstance(k, str) and ("/" in k or "\\" in k):
                parts = re.split(r'[\\/]', k)
                current = self._dict
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = v
                del self._dict[k]
        
    def loadConfig(self, config):
        if isinstance(config, str):
            if os.path.exists(config):
                self._dict = loadJson(config)
            else:
                raise Exception("Path not found:%s" % config)
        elif isinstance(config, dict):
            self._dict = config
        elif isinstance(config, ComplexDict):
            self._dict = config.Dict
        else:
            raise Exception("loadConfig: config must be path, dict or ComplexDict. %s" % str(config))
        
        # self.normalizeKeys()
    
    @classmethod
    def readJson(cls, path):
        if os.path.exists(path):
            config = loadJson(path)
            return cls(config)
        else:
            raise Exception("Not found config file %s" % path)