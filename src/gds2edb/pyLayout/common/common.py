#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230410


'''_
common.py模块主要用于存放一些常用的函数接口，比如加载json,csv,txt文件，查找文件等操作

log is a global variable for log module, every module can import this variable to output log information.

'''
from __future__ import print_function

import re
import os
import sys
import csv,json
from copy import deepcopy
from shutil import copy,copy2
from functools import wraps
import time
import datetime
import contextlib  # 引入上下文管理包


try:
    from collections import Iterable #for python2
except: 
    from collections.abc import Iterable #for python3


#intial log
from .log import Log as logger
log = logger(logLevel = "INFO")  #CRITICAL > ERROR > WARNING > INFO > DEBUG,

isIronpython = "IronPython" in sys.version
isPython = not isIronpython
is_linux = "posix" in os.name

def reSubR(pattern, repl, string, count=0, flags=0):
    return re.sub(pattern, repl, string[::-1],count,flags)[::-1]

def reSubRight(pattern, repl, string, count=0, flags=0):
    return re.sub(pattern, repl, string[::-1],count,flags)[::-1]
    
def readData(path):
    '''读取文本文件

    Args:
        path (str): 文本文件路径

    Returns:
        list: 返回文件所有行
    '''

    with open(path, 'rb') as file:
        # 读取文件内容，得到字节串
        content = file.read()
        file.close()
        # 将字节串解码为 Unicode 字符串
    try:
        return content.decode("utf-8")
    except:
        return content.decode("ascii")


def readlines(path):
    '''读取文本文件

    Args:
        path (str): 文本文件路径

    Returns:
        list: 返回文件所有行
    '''

    try:
        datas = readData(path)
        return datas.splitlines()
    except:
        log.exception("File read error: %s"%path)

        

def writeData(data,path):
    '''写入文本文件

    Args:
        data (list,str): 文本信息
        path (str): 文件路径，如果存在则被覆盖
    '''
    if isinstance(data, list):
        data = "\n".join(data)
    with open(path,'w+') as f:
        f.write(data)
        f.close()


def readCfgFile(path):
    '''读取简单的配置文件

    Args:
        path (str): 配置文件路径

    Returns:
        dict: 配置文件内容
    '''
    if not os.path.exists(path):
        raise FileNotFoundError("配置文件%s不存在"%path)
    
    config_dict = {}
    for line1 in readlines(path):
        line = line1.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue

        if line.startswith("[") and not config_dict:
            #return ini file
            log.info("read as ini format: %s"%path)
            return readIniFile(path)
        
#         key_value = line.split("=",maxsplit=1)
        key_value = re.split("\s*=\s*",line,maxsplit=1)
        if len(key_value) != 2:
            continue
        
        if key_value[1].lower() == "true":
            key_value[1] = True
        elif key_value[1].lower() == "false":
            key_value[1] = False
        elif key_value[1].lower() in ["na","null","none"]:
            key_value[1] = None
        else:
            pass
        
        config_dict[key_value[0]] = key_value[1]
    
    return config_dict

def readIniFile(path):
    """
    read ini format file
    """
    if not os.path.exists(path):
        raise FileNotFoundError("配置文件%s不存在"%path)

    if isIronpython:
        import ConfigParser
        config = ConfigParser.ConfigParser()
        try:
            # 注意：Python 2.7 的 read 方法没有 encoding 参数
            # 如果文件不是 ASCII 编码，需要先解码
            with open(path, 'r') as f:
                content = f.read().decode('utf-8')  # 根据实际编码调整
                config.readfp(content.split('\n'))
        except ConfigParser.Error as e:
            raise ValueError("配置文件格式错误: %s" % e)

    else: #python 3.x
        import configparser
        config = configparser.ConfigParser(
            interpolation=None,  # 禁用字符串插值
            allow_no_value=True, # 允许没有值的键
            delimiters=('='),    # 严格使用等号作为分隔符
            inline_comment_prefixes=('#', ';')  # 支持的注释符号
        )

        try:
            config.read(path, encoding='utf-8')
        except configparser.Error as e:
            raise ValueError("配置文件格式错误: %s" % e)

    # 转换为字典结构
    config_dict = {}
    for section in config.sections():
        config_dict[section] = {}
        for option in config.options(section):
            try:
                # 自动类型转换（可选）
                value = config.get(section, option)
                if value.lower() in ('true', 'false'):
                    value = config.getboolean(section, option)
                elif value.isdigit():
                    value = config.getint(section, option)
                config_dict[section][option] = value
            except ValueError:
                config_dict[section][option] = value  # 保留原始字符串
 
    return config_dict


def _parse_value(value):
    """统一处理单元格值的类型转换"""
    if value is None:
        return ""
    elif isinstance(value, (str)):  # Python 2.7 需要处理 unicode
        lower_val = value.lower()
        if lower_val == "none":
            return ""
        elif lower_val == "true":
            return True
        elif lower_val == "false":
            return False
        else:
            return value.strip()  # 去除字符串两端空格
    else:
        return str(value)


def loadCSV(csvPath, fmt = 'list'):
    '''读取csv文件

    Args:
        csvPath (str): csv路径
        fmt (str, optional): 返回格式 list or dict. Defaults to 'list'.

    Returns:
        list: fmt = list
        dict: fmt = dict
    '''

    if not os.path.exists(csvPath):
        log.debug("csv not exit: %s"%csvPath)
        return []
    
    datas = []
    
    if isPython:
        # 使用 utf-8-sig 编码自动处理 BOM (Byte Order Mark)
        # 这可以解决 Windows Excel 保存的 UTF-8 with BOM 文件导致的列名乱码问题
        with open(csvPath, encoding='utf-8-sig') as f:
            if 'list' in fmt:
                reader  = csv.reader(f)
                datas = list(reader)
            elif 'dict' in fmt:         
                reader  = csv.DictReader(f)
                # 遍历每一行数据
                for row in reader:
                    # 对每一行的每个值进行strip()处理
                    stripped_row = {key: _parse_value(value) if isinstance(value, str) else value 
                                    for key, value in row.items()}
                    datas.append(stripped_row)
            else:
                log.debug("fmt must be list or dict")
            f.close()
    else:
        with open(csvPath) as f:
            if 'list' in fmt:
                reader  = csv.reader(f)
                datas = list(reader)
            elif 'dict' in fmt:         
                reader  = csv.DictReader(f)
                # 遍历每一行数据
                for row in reader:
                    # 对每一行的每个值进行strip()处理
                    stripped_row = {key: _parse_value(value) if isinstance(value, str) else value 
                                    for key, value in row.items()}
                    datas.append(stripped_row)
            else:
                log.debug("fmt must be list or dict")
            f.close()
    return datas


def writeCSV(csvPath,datas, header = [],fmt = 'list'):
    '''写入CSV文件

    Args:
        csvPath (str): 写入的csv文件路径，覆盖写入
        datas (list，dict): 写入的数据集
        header (list, optional): 写入title行. Defaults to [].
        fmt (str, optional): datas的数据格式 list or dict. Defaults to 'list'.
    
    Note:
        使用 utf-8-sig 编码写入，确保与 Microsoft Excel 等工具的兼容性。
        Excel 会自动识别 BOM 标记并正确显示中文内容。
    '''
    if isPython:
        # 使用 utf-8-sig 编码，添加 BOM 标记以兼容 Excel
        with open(csvPath, 'w+', encoding='utf-8-sig', newline='') as f:
            if fmt == 'list':
                if header:
                    f.write(",".join(header) + "\n")
                lines = (",".join((str(d) for d in data)) for data in list(datas))
                f.write("\n".join(lines))
            else:
                dialect = csv.excel
                dialect.lineterminator = "\n"
                f_csv = csv.DictWriter(f, header, dialect=dialect)
                f_csv.writeheader()
                f_csv.writerows(datas)
            f.close()
    else:
        with open(csvPath, 'w+') as f:
            if fmt == 'list':
                if header:
                    f.write(",".join(header) + "\n")
                lines = (",".join((str(d) for d in data)) for data in list(datas))
                f.write("\n".join(lines))
            else:
                dialect = csv.excel
                dialect.lineterminator = "\n"
                f_csv = csv.DictWriter(f, header, dialect=dialect)
                f_csv.writeheader()
                f_csv.writerows(datas)
            f.close()

def loadJson(jsonPath):
    '''读取json文件

    Args:
        jsonPath (str): json路径

    Returns:
        dict: 返回json代表的dict
    '''
    with open(jsonPath,'r') as load_f:
        config = json.load(load_f)
        load_f.close()
    return config

def writeJson(path,config):
    '''写入json文件

    Args:
        path (str): json路径
        config (dict): 文件内容
    '''
    dirPath = os.path.dirname(path)
    if not os.path.exists(dirPath):
        os.makedirs(dirPath, exist_ok=True)
    
    with open(path,"w+") as f:
        json.dump(config,f,indent=4, separators=(',', ': '))
        f.close()

def backupFile(path, backupDir=None, backupType="timestamp"):
    """
    备份文本文件的通用函数
    :param path: 待备份的文本文件路径（绝对/相对路径）
    :param backupDir: 备份文件存放目录（None则与原文件同目录）
    :param backupType: 备份命名方式 - "timestamp"（时间戳，推荐）/ "number"（序号）
    :return: 备份文件的完整路径（失败返回None）
    """
    # 1. 校验原文件是否存在且是文件（非目录）
    if not os.path.isfile(path):
        print("错误：文件 {path} 不存在或不是有效文件！")
        return None

    # 2. 处理备份目录（默认与原文件同目录）
    if backupDir is None:
        backupDir = os.path.dirname(path)
    # 确保备份目录存在（不存在则创建）
    
    if not os.path.exists(backupDir):
        os.makedirs(backupDir)

    # 3. 拆分原文件的路径、文件名、扩展名
    file_dir, file_fullname = os.path.split(path)
    file_name, file_ext = os.path.splitext(file_fullname)
    # 确保扩展名统一（无扩展名则补空）
    if not file_ext:
        file_ext = ""  

    # 4. 生成备份文件名（避免覆盖）
    backup_filename = ""
    if backupType == "timestamp":
        # 时间戳格式：YYYYMMDD_HHMMSS（精确到秒，无重复）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = "{file_name}_backup_{timestamp}{file_ext}".format(file_name=file_name,timestamp=timestamp,file_ext=file_ext)
    elif backupType == "number":
        # 序号格式：filename_backup_1.txt、filename_backup_2.txt...
        count = 1
        while True:
            temp_name = "{file_name}_backup_{count}{file_ext}".format(file_name=file_name,count=count,file_ext=file_ext)
            temp_path = os.path.join(backupDir, temp_name)
            if not os.path.exists(temp_path):
                backup_filename = temp_name
                break
            count += 1
    else:
        print("错误：不支持的备份类型 %s，仅支持 timestamp/number"%backupType)
        return None

    # 5. 拼接备份文件完整路径
    backup_path = os.path.join(backupDir, backup_filename)

    try:
        # 6. 执行备份（复制文件，保留原文件属性）
        # 方式1：shutil.copy2 保留文件元数据（修改时间、权限等），推荐
        copy2(path, backup_path)
        # 方式2：纯文本读取写入（适合仅备份内容，跨平台）
        # with open(path, "r", encoding="utf-8") as f_src, open(backup_path, "w", encoding="utf-8") as f_dst:
        #     f_dst.write(f_src.read())
        
        print("备份成功！备份文件路径：%s"%backup_path)
        return backup_path

    except PermissionError:
        print("错误：无权限访问文件 {path} 或写入备份目录 %s！"%backup_path)
        return None
    except Exception as e:
        print("备份失败！异常信息：{str(e)}")
        return None



def tuple2list(tuple_obj):
    if isinstance(tuple_obj, (tuple,list)):
        return [tuple2list(item) for item in tuple_obj]
    else:
        return tuple_obj


def findDictValue(key, dict1, default=None, valid=None, ignorCase=True, maps=None):
    '''
    Optimized version: Adds fast path for direct key lookup and fixes variable scope bugs.
    
    Args:
        key (str): Key to find.
        dict1 (dict): Dictionary to search.
        default (any): Default value if key not found.
        valid (any): If the found value is "falsy" (e.g., None, False, ""), return this instead.
        ignorCase (bool): If True, perform case-insensitive search.
        maps (dict): Alias mapping {alias: real_key}.

    Returns:
        Any: The found value, or default/valid fallback.
    '''
    if not isinstance(dict1, dict):
        return default if valid is None else valid

    # 1. Try Fast Path: Direct Lookup (Case Sensitive)
    # Even if ignorCase is True, if the key matches exactly, it's the fastest way.
    if key in dict1:
        val = dict1[key]
        if not val and valid is not None:
            return valid
        return val

    # 2. Slow Path: Case Insensitive Lookup
    if ignorCase:
        key_lower = key.lower()
        for k, v in dict1.items():
            if k.lower() == key_lower:
                if not v and valid is not None:
                    return valid
                return v

    # 3. Check Maps (Alias)
    if maps:
        # Optimization: If maps is a dict, direct lookup is faster than iteration
        # But we need case-insensitive match for the alias key itself usually? 
        # Assuming maps keys are aliases.
        
        # Try direct lookup in maps first (case sensitive)
        if key in maps:
            real_key = maps[key]
            # Recursively find the value using the real key, but disable maps to prevent infinite loops
            # Note: We pass ignorCase=True to find the real_key's value in dict1
            return findDictValue(real_key, dict1, default=default, valid=valid, ignorCase=ignorCase, maps=None)
        
        # If direct lookup failed and ignorCase is on, iterate maps
        if ignorCase:
            key_lower = key.lower()
            for alias, real_key in maps.items():
                if isinstance(alias, str) and alias.lower() == key_lower:
                    return findDictValue(real_key, dict1, default=default, valid=valid, ignorCase=ignorCase, maps=None)

    # 4. Return Default
    return default if valid is None else valid


def findDictKey(key, dict1, ignorCase=True,default="//key_not_found//"):
    '''
    Optimized version: Adds fast path for direct key lookup.
    
    Args:
        key (str): Key to find.
        dict1 (dict): Dictionary to search.
        ignorCase (bool): If True, perform case-insensitive search.

    Returns:
        str: The actual key found in dict1, or "//key_not_found//"
    '''
    if not isinstance(dict1, dict):
        return default

    # 1. Fast Path: Direct Lookup
    if key in dict1:
        return key

    # 2. Slow Path: Case Insensitive Lookup
    if ignorCase:
        key_lower = key.lower()
        for k in dict1:
            if isinstance(k, str) and k.lower() == key_lower:
                return k
                
    return default



def splitList(list_collection, n):
    """
    将集合均分，每份n个元素
    :param list_collection:
    :param n:
    :return:返回的结果为评分后的每份可迭代对象
    """
    for i in range(0, len(list_collection), n):
        yield list_collection[i: i + n]

def textSplit(strDatas, flag="{}", comment="$"):
    fragments = []  # 用列表替代字符串拼接
    stack = []      # 栈用于跟踪括号嵌套
    i = 0
    n = len(strDatas)
    
    while i < n:
        char = strDatas[i]
        
        # 处理注释行（仅在栈为空时生效）
        if char == comment and not stack:
            i += 1
            while i < n and strDatas[i] != '\n':
                i += 1
            continue
        
        # 遇到开括号时入栈
        if char == flag[0]:
            stack.append(char)
            fragments.append(char)
        # 遇到闭括号时出栈
        elif char == flag[-1] and stack:
            stack.pop()
            fragments.append(char)
            # 当栈为空时生成完整块
            if not stack:
                yield ''.join(fragments)
                fragments = []
        # 普通字符处理
        else:
            fragments.append(char)
        
        i += 1
    
    # # 处理末尾未闭合的片段
    # if fragments and not stack:
    #     yield ''.join(fragments)

def textSplitLines(lineDatas, flag="{}", comment="$"):
    fragments = []  # 用列表替代字符串拼接
    stack = []      # 栈用于跟踪括号嵌套
    i = 0
    n = len(lineDatas)
    
    while i < n:
        line = lineDatas[i]
        line = line.strip()
        # line = re.sub(r"%s.*"%comment, "", line)

        if not line:
            #删除空行
            i += 1
            continue
        
        # 删除注释行
        if line.startswith(comment):
            i += 1
            continue

        # 遇到开括号时入栈
        if line.startswith(flag[0]):
            stack.append(line)
            fragments.append(line)
        # 遇到闭括号时出栈
        elif line.startswith(flag[-1]) and stack:
            stack.pop()
            fragments.append(line)
            # 当栈为空时生成完整块
            if not stack:
                yield fragments
                fragments = []
        # 普通字符处理
        else:
            if stack:
                fragments.append(line)
            else:
            #Drop
                pass
            # fragments.append(line)
        
        i += 1
    
    # # 处理末尾未闭合的片段
    # if fragments and not stack:
    #     yield ''.join(fragments)

def update2Dict(dict1,dict2,ignorCase = True):
    '''
    dict2 update to dict1, considered Multi-level dict keys
    '''
    
    #if dict2 not dict, use dict2 value override dict1
    if not isinstance(dict2, (dict)):
        dict1 = dict2
        return dict1
    
    for key2 in dict2:
        key1 = findDictKey(key2,dict1,ignorCase,default="//key_not_found//")
            
        if key1 != "//key_not_found//":
            dict1[key1] = update2Dict(dict1[key1], dict2[key2])
        else:
            dict1[key2] = deepcopy(dict2[key2])
            
    return dict1
    
def backupFile(path, backupDir=None, backupType="timestamp"):
    """
    备份文本文件的通用函数
    :param path: 待备份的文本文件路径（绝对/相对路径）
    :param backupDir: 备份文件存放目录（None则与原文件同目录）
    :param backupType: 备份命名方式 - "timestamp"（时间戳，推荐）/ "number"（序号）
    :return: 备份文件的完整路径（失败返回None）
    """
    # 1. 校验原文件是否存在且是文件（非目录）
    if not os.path.isfile(path):
        print("错误：文件 {path} 不存在或不是有效文件！")
        return None

    # 2. 处理备份目录（默认与原文件同目录）
    if backupDir is None:
        backupDir = os.path.dirname(path)
    # 确保备份目录存在（不存在则创建）
    
    if not os.path.exists(backupDir):
        os.makedirs(backupDir)

    # 3. 拆分原文件的路径、文件名、扩展名
    file_dir, file_fullname = os.path.split(path)
    file_name, file_ext = os.path.splitext(file_fullname)
    # 确保扩展名统一（无扩展名则补空）
    if not file_ext:
        file_ext = ""  

    # 4. 生成备份文件名（避免覆盖）
    backup_filename = ""
    if backupType == "timestamp":
        # 时间戳格式：YYYYMMDD_HHMMSS（精确到秒，无重复）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = "{file_name}_backup_{timestamp}{file_ext}".format(file_name=file_name,timestamp=timestamp,file_ext=file_ext)
    elif backupType == "number":
        # 序号格式：filename_backup_1.txt、filename_backup_2.txt...
        count = 1
        while True:
            temp_name = "{file_name}_backup_{count}{file_ext}".format(file_name=file_name,count=count,file_ext=file_ext)
            temp_path = os.path.join(backupDir, temp_name)
            if not os.path.exists(temp_path):
                backup_filename = temp_name
                break
            count += 1
    else:
        print("错误：不支持的备份类型 %s，仅支持 timestamp/number"%backupType)
        return None

    # 5. 拼接备份文件完整路径
    backup_path = os.path.join(backupDir, backup_filename)

    try:
        # 6. 执行备份（复制文件，保留原文件属性）
        # 方式1：shutil.copy2 保留文件元数据（修改时间、权限等），推荐
        shutil.copy2(path, backup_path)
        # 方式2：纯文本读取写入（适合仅备份内容，跨平台）
        # with open(path, "r", encoding="utf-8") as f_src, open(backup_path, "w", encoding="utf-8") as f_dst:
        #     f_dst.write(f_src.read())
        
        print("备份成功！备份文件路径：%s"%backup_path)
        return backup_path

    except PermissionError:
        print("错误：无权限访问文件 {path} 或写入备份目录 %s！"%backup_path)
        return None
    except Exception as e:
        print("备份失败！异常信息：{str(e)}")
        return None


def getParent(path):
    return os.path.abspath(os.path.join(path, os.pardir))

def getFileList(path,reg = ".*"):
    '''列出给定目录下符合条件的文件路径

    Args:
        path (str): 文件夹路径
        reg (str, optional): 过滤条件. Defaults to ".*".

    Returns:
        list: 返回符合条件的文件路径
    '''
    files = os.listdir(path)
    regFiles = list(filter(lambda x: re.match(reg+"$",x,re.IGNORECASE),files))
    if regFiles:
        return [os.path.abspath(os.path.join(path,x))  for x in regFiles]
    else:
        []
        

def getAbsPath(path,root = None):
    if os.path.isabs(path):  
        return path
    else:  
        if not root:
            root = os.getcwd()
        return  os.path.abspath(os.path.join(root,path)) 

def getRelPath(path,root=None):
    
    if os.path.isabs(path):
        if not root:
            root = os.getcwd()
        return os.path.relpath(root, path)
    else:
        return path

def findFiles(root,reg = ".*"):
    '''在目录下查找文件，便利子目录

    Args:
        root (str): 根文件路径
        reg (str, optional): 过滤条件. Defaults to ".*".

    Returns:
        list: 返回符合条件的所有文件路径
    '''
    regFiles = []
    for root, dirs, files in os.walk(root):
        regFiles += [os.path.join(root,f) for f in filter(lambda x: re.match(reg, x,re.IGNORECASE),files)]

    return regFiles

def cmpFileNewer (file1_path, file2_path, check_create_time=False):
    """
    对比两个文件的日期，file1日期晚于file2则返回True
    :param file1_path: 文件1的路径（字符串）
    :param file2_path: 文件2的路径（字符串）
    :param check_create_time: 是否检查创建时间（False=检查修改时间，True=检查创建时间）
    :return: True/False，文件不存在/无权限时抛出异常
    """
    # 检查文件是否存在
    if not os.path.exists(file1_path):
        raise FileNotFoundError("file1_path not exist:%s"%file1_path)
    if not os.path.exists(file2_path):
        raise FileNotFoundError("file2_path not exist: %s"%file2_path)
    
    # 获取文件时间戳（修改时间/创建时间）
    if check_create_time:
        # 创建时间（Windows：ctime是创建时间；Linux/macOS：ctime是元数据修改时间）
        file1_time = os.path.getctime(file1_path)
        file2_time = os.path.getctime(file2_path)
    else:
        # 修改时间（跨平台一致）
        file1_time = os.path.getmtime(file1_path)
        file2_time = os.path.getmtime(file2_path)
    
    # 对比时间戳：时间戳越大，日期越晚
    return file1_time > file2_time

def isSamePath(path1,path2):
    """
    判定两个文件路径是否相同（os.path 实现）
    :param path1: 第一个文件路径（字符串）
    :param path2: 第二个文件路径（字符串）
    :return: 路径是否相同（布尔值）
    """
    # 步骤1：转换为绝对路径（消除相对路径歧义）
    abs_path1 = os.path.abspath(path1)
    abs_path2 = os.path.abspath(path2)
    
    # 步骤2：规范化路径（处理分隔符、末尾斜杠、上级目录../等问题）
    norm_path1 = os.path.normpath(abs_path1)
    norm_path2 = os.path.normpath(abs_path2)
    
    # 步骤3：比较规范化后的绝对路径
    return norm_path1 == norm_path2


def taskForEach(MaxParallel = 4):
    '''
    使用 subprocess 实现并行任务执行，确保进程间完全独立。
    关闭实时日志输出以避免管道死锁。
    '''
    import subprocess
    # import sys
    # import os
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def _kill_process_tree(process):
        """Helper to kill process and its children cross-platform
        
        跨平台进程树终止函数，确保所有子进程都被正确杀死。
        
        Linux 改进策略：
        1. 优先使用 psutil（如果可用）进行精确的进程树遍历
        2. 回退到 pgrep/pkill 命令查找并杀死所有子进程
        3. 最后使用 os.killpg 作为兜底方案
        """
        try:
            if not is_linux:
                # Windows: 使用 taskkill 递归终止进程树
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
            else:
                # Linux/Unix: 多层策略确保彻底终止
                import signal
                
                # 策略 1: 尝试使用 psutil（最可靠）
                try:
                    import psutil
                    parent = psutil.Process(process.pid)
                    children = parent.children(recursive=True)
                    
                    # 先终止子进程
                    for child in children:
                        try:
                            child.terminate()  # SIGTERM
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    # 等待子进程退出
                    _, alive = psutil.wait_procs(children, timeout=3)
                    
                    # 强制杀死仍然存活的进程
                    for p in alive:
                        try:
                            p.kill()  # SIGKILL
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    # 最后终止父进程
                    parent.terminate()
                    parent.wait(timeout=3)
                    
                    log.debug("Successfully killed process tree using psutil")
                    return
                    
                except ImportError:
                    log.debug("psutil not available, falling back to command-line methods")
                except Exception as e:
                    log.warning("psutil method failed: {}, trying alternative methods".format(e))
                
                # 策略 2: 使用 pgrep 查找所有子进程并杀死
                try:
                    # 查找所有子进程的 PID
                    result = subprocess.run(
                        ["pgrep", "-P", str(process.pid)],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        child_pids = result.stdout.strip().split('\n')
                        log.debug("Found {} child processes: {}".format(len(child_pids), child_pids))
                        
                        # 先发送 SIGTERM 给所有子进程
                        for pid in child_pids:
                            if pid.strip():
                                try:
                                    os.kill(int(pid.strip()), signal.SIGTERM)
                                except (ProcessLookupError, PermissionError, ValueError):
                                    pass
                        
                        # 短暂等待
                        time.sleep(1)
                        
                        # 强制杀死仍然存活的子进程
                        for pid in child_pids:
                            if pid.strip():
                                try:
                                    os.kill(int(pid.strip()), signal.SIGKILL)
                                except (ProcessLookupError, PermissionError, ValueError):
                                    pass
                    
                    # 杀死进程组
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass
                    
                    log.debug("Successfully killed process tree using pgrep/pkill")
                    return
                    
                except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                    log.debug("pgrep method failed: {}, using fallback".format(e))
                
                # 策略 3: 直接使用 pkill 按进程名杀死（兜底方案）
                try:
                    # 获取进程的命令行以提取进程名
                    try:
                        with open('/proc/{}/cmdline'.format(process.pid), 'r') as f:
                            cmdline = f.read()
                            proc_name = cmdline.split('\x00')[0].split('/')[-1] if cmdline else None
                    except:
                        proc_name = None
                    
                    if proc_name:
                        subprocess.run(
                            ["pkill", "-9", "-f", proc_name],
                            capture_output=True,
                            timeout=3
                        )
                        log.debug("Used pkill to terminate process: {}".format(proc_name))
                    
                    # 最后的兜底：尝试杀死进程组
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass
                        
                except Exception as e:
                    log.warning("All Linux kill methods failed: {}".format(e))
                    
        except Exception as e:
            log.warning("Failed to kill process {}: {}".format(process.pid, e))
    
    
    def execute_commands_parallel(commands, max_workers=MaxParallel):
        """
        commands: list of list/str
        """
        active_processes = []
        lock = threading.Lock()
        
        def run_cmd(cmd, idx):
            proc = None
            try:
                # log.info(f"Starting subprocess {idx}: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
                
                # 【关键修改】将 stdout 和 stderr 重定向到 DEVNULL，彻底避免管道阻塞
                # 如果需要保留日志，可以重定向到具体的文件，例如 stdout=open(f"log_{idx}.txt", "w")
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,  # 丢弃标准输出
                    stderr=subprocess.DEVNULL,  # 丢弃标准错误
                    text=True,
                    encoding='utf-8',
                    errors='replace'  # 遇到无法解码的字符时用 ? 替换，避免崩溃
                )
                
                with lock:
                    active_processes.append(proc)
                
                # 等待进程完成，不涉及任何 I/O 读取，因此不会死锁
                proc.wait()
                
                if proc.returncode != 0:
                    # log.error(f"Subprocess {idx} failed with code {proc.returncode}")
                    return False
                else:
                    log.info("Subprocess {idx} completed successfully.".format(idx))
                    return True
                
            except Exception as e:
                # log.error(f"Error running subprocess {idx}: {e}")
                return False
            finally:
                with lock:
                    if proc and proc in active_processes:
                        active_processes.remove(proc)

        # 使用线程池来管理并发 subprocess
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_cmd, cmd, i): i for i, cmd in enumerate(commands)}
            
            try:
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        log.error("Task {idx} generated an exception: {e}".format(idx=idx, e=e))
            except KeyboardInterrupt:
                log.warning("KeyboardInterrupt received. Terminating all subprocesses...")
                with lock:
                    for proc in active_processes:
                        try:
                            if proc.poll() is None: # 如果还在运行
                                time.sleep(5)
                                _kill_process_tree(proc)
                        except:
                            pass
                raise

    def forEach_wrapper(input_list, task_func_or_cmd_generator):
        """
        input_list: 数据列表
        task_func_or_cmd_generator: 生成命令的函数或命令列表
        """
        commands = []
        
        if input_list and isinstance(input_list[0], (list, tuple)) and isinstance(input_list[0][0], str):
            commands = input_list
        else:
            for item in input_list:
                try:
                    cmd = task_func_or_cmd_generator(item)
                    if isinstance(cmd, str):
                        import shlex
                        cmd = shlex.split(cmd)
                    commands.append(cmd)
                except Exception as e:
                    log.error("Failed to generate command for item: {e}".format(e=str(e)))

        if not commands:
            log.warning("No commands to execute.")
            return

        execute_commands_parallel(commands, max_workers=MaxParallel)

    return forEach_wrapper



def regAnyMatch(regs,val,flags = re.IGNORECASE):
    '''
    regs: str or list
    val: str or list
    '''
    if not regs:
        return False
    
    if isinstance(regs, str) and isinstance(val, str):
        return re.match(regs+"$",val,flags)
    
    if not isinstance(regs,str) and isinstance(val, str):
        return any([regAnyMatch(r+"$",val) for r in regs])

    if not isinstance(val, (str,list,tuple)):
        return False

    return any([regAnyMatch(regs,v) for v in val])

def copyAedt(source,target):
    
    #source = (source,source+".aedt")(".aedt" in source)
    if ".aedt" not in source:
        log.debug("source must .aedt file: %s"%source)
        return
    if not os.path.exists(source):
        log.debug("source file not found: %s"%source)
        return
    
    
    aedtTarget = (target+".aedt",target)[".aedt" in target]
    aedtTargetDir = os.path.dirname(aedtTarget)
    if not os.path.exists(aedtTargetDir):
        log.debug("make dir: %s"%aedtTargetDir)
        os.mkdir(aedtTargetDir)
    
    copy(source,aedtTarget)
    
    edbSource = source[:-5]+".aedb" +"/edb.def"
    edbTargetdir = aedtTarget[:-5]+".aedb"
    
    #if not 3DL
    if not os.path.exists(edbSource):
        return
    
    if not os.path.exists(edbTargetdir):
        log.debug("make dir: %s"%edbTargetdir)
        os.mkdir(edbTargetdir)
    copy(edbSource,edbTargetdir)
    

def ProcessTime(func):
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        log.info("start function: {0}".format(func.__name__))
        if isIronpython:
            tfun = time.clock
        else:
            tfun = time.time
            
        start = tfun()
        try:
            return func(*args, **kwargs)
        finally:
            end = tfun()
            log.info("{0}: Process time {1}s".format(func.__name__,end-start))
    return wrapped_function

def DisableAutoSave(func):
    @wraps(func)
    def wrapped_function(self,*args, **kwargs):
        log.info("Disable AutoSave from function: {0}".format(func.__name__))
        temp = self.layout.enableAutosave(flag=False)
        try:
            return func(self,*args, **kwargs)
        finally:
            log.info("Recover AutoSave from function: {0}".format(func.__name__))
            self.layout.enableAutosave(flag=temp)
    return wrapped_function

def disableLogStream(logger):
    try:
        logger1 = logger.logger.logger
    except:
        logger1 = logger.logger
        
    temp = []
    for handler in logger.handlers[:]:  # 遍历副本，避免修改原列表报错
        if handler.name == "stream_handler":
            temp.append(handler)
            logger1.removeHandler(handler)  # 移除方式（彻底删除）
            
    return temp

def enableLogStream(logger,handlers):
    
    try:
        logger1 = logger.logger.logger
    except:
        logger1 = logger.logger
        
    for handler in handlers:  # 遍历副本，避免修改原列表报错
        logger1.addHandler(handler)

def getAedtInstallPath(version=None):

    if version:
        ver = version.replace(".", "")[-3:]
        verEnv = "ANSYSEM_ROOT%s" % ver
        
        if verEnv in os.environ:
            return os.environ[verEnv] 
    
    if "ANSYSEM_ROOT" in os.environ: 
        return os.environ["ANSYSEM_ROOT"]


    ANSYSEM_ROOTs = list(
        filter(lambda x: "ANSYSEM_ROOT" in x, os.environ))
    if ANSYSEM_ROOTs:
        log.debug("Try to initialize Desktop in latest version")
        ANSYSEM_ROOTs.sort(key=lambda x: x[-3:])
        return os.environ[ANSYSEM_ROOTs[-1]]

    #判定某个工具是否已经存在于系统环境变量中，比where ansysedt查询ansysedt的路径，如果不存在返回None，兼容Windows和Linux
    def isToolInPath(toolName):
        isWindows = os.name == "nt"
        if isWindows:
            return os.system("where %s" % toolName) == 0
        else:
            return os.system("which %s" % toolName) == 0
    

def runSubProcess(command):
    import subprocess  # Ensure this import is at the top of the file
    import threading
    import queue
    import shlex

    # 添加 -u 参数禁用 Python 输出缓冲，确保日志实时到达管道
    # cmd = ["python", "-u", scriptPath, "-j", path]
    if isinstance(command, str):
        command = shlex.split(command)

    if not isinstance(command, (list,tuple)):  # 确保命令是一个列表
        log.exception("Invalid command: %s" % str(command))

    def _kill_process_tree(process):
        """Helper to kill process and its children cross-platform
        
        跨平台进程树终止函数，确保所有子进程都被正确杀死。
        
        Linux 改进策略：
        1. 优先使用 psutil（如果可用）进行精确的进程树遍历
        2. 回退到 pgrep/pkill 命令查找并杀死所有子进程
        3. 最后使用 os.killpg 作为兜底方案
        """
        try:
            if sys.platform == "win32":
                # Windows: 使用 taskkill 递归终止进程树
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
            else:
                # Linux/Unix: 多层策略确保彻底终止
                import signal
                
                # 策略 1: 尝试使用 psutil（最可靠）
                try:
                    import psutil
                    parent = psutil.Process(process.pid)
                    children = parent.children(recursive=True)
                    
                    # 先终止子进程
                    for child in children:
                        try:
                            child.terminate()  # SIGTERM
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    # 等待子进程退出
                    _, alive = psutil.wait_procs(children, timeout=3)
                    
                    # 强制杀死仍然存活的进程
                    for p in alive:
                        try:
                            p.kill()  # SIGKILL
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    # 最后终止父进程
                    parent.terminate()
                    parent.wait(timeout=3)
                    
                    log.debug("Successfully killed process tree using psutil")
                    return
                    
                except ImportError:
                    log.debug("psutil not available, falling back to command-line methods")
                except Exception as e:
                    log.warning("psutil method failed: {}, trying alternative methods".format(e))
                
                # 策略 2: 使用 pgrep 查找所有子进程并杀死
                try:
                    # 查找所有子进程的 PID
                    result = subprocess.run(
                        ["pgrep", "-P", str(process.pid)],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        child_pids = result.stdout.strip().split('\n')
                        log.debug("Found {} child processes: {}".format(len(child_pids), child_pids))
                        
                        # 先发送 SIGTERM 给所有子进程
                        for pid in child_pids:
                            if pid.strip():
                                try:
                                    os.kill(int(pid.strip()), signal.SIGTERM)
                                except (ProcessLookupError, PermissionError, ValueError):
                                    pass
                        
                        # 短暂等待
                        time.sleep(1)
                        
                        # 强制杀死仍然存活的子进程
                        for pid in child_pids:
                            if pid.strip():
                                try:
                                    os.kill(int(pid.strip()), signal.SIGKILL)
                                except (ProcessLookupError, PermissionError, ValueError):
                                    pass
                    
                    # 杀死进程组
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass
                    
                    log.debug("Successfully killed process tree using pgrep/pkill")
                    return
                    
                except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                    log.debug("pgrep method failed: {}, using fallback".format(e))
                
                # 策略 3: 直接使用 pkill 按进程名杀死（兜底方案）
                try:
                    # 获取进程的命令行以提取进程名
                    try:
                        with open('/proc/{}/cmdline'.format(process.pid), 'r') as f:
                            cmdline = f.read()
                            proc_name = cmdline.split('\x00')[0].split('/')[-1] if cmdline else None
                    except:
                        proc_name = None
                    
                    if proc_name:
                        subprocess.run(
                            ["pkill", "-9", "-f", proc_name],
                            capture_output=True,
                            timeout=3
                        )
                        log.debug("Used pkill to terminate process: {}".format(proc_name))
                    
                    # 最后的兜底：尝试杀死进程组
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass
                        
                except Exception as e:
                    log.warning("All Linux kill methods failed: {}".format(e))
                    
        except Exception as e:
            log.warning("Failed to kill process {}: {}".format(process.pid, e))

    def _enqueue_output(out, queue):
        """后台线程函数：持续读取输出并放入队列"""
        for line in iter(out.readline, ''):
            queue.put(line)
        out.close()


    log.info("Starting subprocess: %s" % " ".join(command))
    
    process = None
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'  # 遇到无法解码的字符时用 ? 替换，避免崩溃
        )
        
        # 异步读取日志
        q = queue.Queue()
        t = threading.Thread(target=_enqueue_output, args=(process.stdout, q))
        t.daemon = True
        t.start()
        
        while True:
            try:
                line = q.get(timeout=0.1)
                log.info(line.strip())
            except queue.Empty:
                pass
            
            if process.poll() is not None:
                # 读取剩余日志
                while not q.empty():
                    try: log.info(q.get_nowait().strip())
                    except: break
                break

        if process.returncode != 0:
            log.error("Subprocess failed with code: {}".format(process.returncode))
            
    except KeyboardInterrupt:
        log.warning("Ctrl+C detected. Terminating subprocess...")
        if process: _kill_process_tree(process)
        raise
    except Exception as e:
        log.error("Failed to run subprocess: {}".format(str(e)))
        if process: 
            time.sleep(5)
            _kill_process_tree(process)
        raise
    finally:
        if process and process.poll() is None:
            time.sleep(5)
            _kill_process_tree(process)

def runCommand(command,timeout_seconds=None):
    import subprocess
    try:
        # 执行命令，并等待其完成
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout_seconds)
        # 如果成功在超时时间内完成，可以获取输出
        return result.stdout
    except subprocess.TimeoutExpired:
        # 当命令执行时间超过 timeout 参数设定的值时触发
        print("Command timeout: %s seconds"%str(timeout_seconds))
        return "Command timeout"
        # 子进程会被自动终止
    except Exception as e:
        raise Exception("Command Error.")
        return "Command Error"

def parseArgs(parser):
    known_args, unknown_args = parser.parse_known_args()
    # 转换Namespace为字典，方便查看
    known_dict = vars(known_args)
    
    unknown_dict = {}
    if unknown_args:
        # 可选：将未定义参数解析为键值对（如 --foo bar 形式）
        i = 0
        while i < len(unknown_args):
            if unknown_args[i].startswith('-'):
                key = unknown_args[i].lstrip('-')
                # 判断下一个元素是否是值（不是以--开头）
                if i + 1 < len(unknown_args) and not unknown_args[i+1].startswith('-'):
                    value = unknown_args[i+1]
                    if value.lower() in ['true', 'false']:  # 假设布尔值可以转换为True或False
                        value = value.lower() == 'true'
                    elif value.lower() in ['none', 'null']:  # 假设None或Null可以转换为None
                        value = None
                    else:
                        pass
                    unknown_dict[key] = value
                    i += 2
                else:
                    unknown_dict[key] = ""  # 无值的参数设为
                    i += 1
            else:
                # 无--前缀的未定义参数，作为匿名参数
                unknown_dict['arg_%s'%i] = unknown_args[i]
                i += 1

    return known_args, unknown_dict


global_clr = None
def initClr():
    """
    Initialize CLR. 
    Note: In multiprocessing spawn mode, this might fail in child processes if called globally.
    It is recommended to call this only in the main process or handle exceptions in child processes.
    """
    global global_clr
    if global_clr:
        return global_clr

    # 设置环境变量以抑制 CLR 重复初始化警告（跨平台支持）
    # 这应该在首次尝试初始化 CLR 时设置，避免子进程中的重复初始化警告
    if 'ANSOFT_SUPPRESS_CLR_WARNING' not in os.environ:
        os.environ['ANSOFT_SUPPRESS_CLR_WARNING'] = '1'

    if isIronpython:
        import clr as _clr
        global_clr = _clr
        return _clr
    
    elif is_linux:
        try:
            from ansys.aedt.core.generic.clr_module import _clr
        except Exception as e:
            # Linux 平台也可能遇到 CLR 初始化问题
            if os.environ.get('ANSOFT_SUPPRESS_CLR_WARNING') == '1':
                log.debug("CLR initialization failed in child process on Linux (suppressed). Error: %s" % str(e))
                return None
            else:
                log.warning("CLR initialization failed on Linux: %s" % str(e))
                return None
        
        global_clr = _clr
        return _clr
    
    else:
        # Windows
        try:
            import clr as _clr
            global_clr = _clr
            return _clr
        except RuntimeError as e:
            # 如果在子进程中遇到初始化错误，记录警告并返回 None 或重新抛出
            # 这通常发生在 spawn 模式下子进程重复导入时
            if "Failed to initialize Python.Runtime.dll" in str(e):
                if os.environ.get('ANSOFT_SUPPRESS_CLR_WARNING') == '1':
                    log.debug("CLR initialization failed in child process on Windows (suppressed).")
                else:
                    log.warning("CLR initialization failed in child process (likely duplicate init). Ignoring if not needed.")
                # 返回 None 或根据调用者逻辑处理
                return None 
            raise


def findFileCaseInsensitive(directory, filename):
    """
    在目录中不区分大小写地查找文件
    
    适用于 Linux 等区分大小写的文件系统，提供跨平台兼容的文件查找功能。
    
    参数：
        directory: 要搜索的目录路径
        filename: 要查找的文件名（如 "stackup.csv"）
    
    返回：
        str: 如果找到匹配的文件，返回完整路径；否则返回 None
    
    示例：
        >>> # 在 Linux 下，即使实际文件是 StackUp.CSV，也能找到
        >>> path = find_file_case_insensitive("/path/to/dir", "stackup.csv")
        >>> print(path)  # /path/to/dir/StackUp.CSV
    """
    if not os.path.isdir(directory):
        return None
    
    filename_lower = filename.lower()
    try:
        for entry in os.listdir(directory):
            if entry.lower() == filename_lower:
                full_path = os.path.join(directory, entry)
                if os.path.isfile(full_path):
                    return full_path
    except PermissionError:
        log.warning("Permission denied when accessing directory: %s" % directory)
    
    return None


def findFilesByPattern(directory, pattern, caseInsensitive=True):
    """
    在目录中及其子目录中根据模式查找文件（支持通配符）
    
    参数：
        directory: 要搜索的目录路径
        pattern: 文件名模式（支持 * 和 ? 通配符，如 "*.csv"）
        caseInsensitive: 是否不区分大小写（默认 True）
    
    返回：
        list: 匹配的文件完整路径列表
    
    示例：
        >>> # 查找所有 CSV 文件（不区分大小写）
        >>> files = findFilesByPattern("/path/to/dir", "*.csv")
        >>> # 返回: ['/path/to/dir/StackUp.CSV', '/path/to/dir/model.csv']
    """
    import re
    import os
    
    # 将通配符模式转换为正则表达式
    # * -> .* (匹配任意字符0次或多次)
    # ? -> . (匹配任意字符1次)
    # regex_pattern = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
    regex_pattern = '^' + pattern + '$'  # 添加开始和结束锚点
    
    # 编译正则表达式
    flags = re.IGNORECASE if caseInsensitive else 0
    compiled_regex = re.compile(regex_pattern, flags)
    
    matched_files = []
    
    try:
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if compiled_regex.match(filename):
                    full_path = os.path.join(root, filename)
                    matched_files.append(full_path)
    except PermissionError:
        log.warning("Permission denied when accessing directory: %s" % directory)
    except Exception as e:
        log.warning("Error occurred while searching directory %s: %s" % (directory, str(e)))
    
    return matched_files
