#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2025-05-07

import sys,os

import re
import zipfile
import time


from .cpp import CPP
from .ploc import PLOC
from .spiceModel import SpiceModel
from ..common.common  import log,readData,writeData,textSplitLines,getFileList
from ..common.unit import Unit


def readZipData(zipFile,subPath):
    with zipfile.ZipFile(zipFile, 'r') as zip_ref:
        with zip_ref.open(subPath) as file:
            content = file.read()
            return content
            # print(content.decode('utf-8'))

class CPAModel(object):
    
    def __init__(self,path=None):
        self.path = path
        self.TopSubcktModel = None
        self.TopSubcktPath = None
        self.PLOC = None
        self.CPPDict = None
        self.spiceModel = None

        self.setPath(path)


    def setPath(self, path):
        # 如果 path 为 zip 文件，则进行解压，获取解压后的文件夹

        if not path:
            return

        #判断path路径是否存在
        if not os.path.exists(path):
            log.exception("File not exist: %s"%path)
            return

        pathback = path
        if zipfile.is_zipfile(path):
            zipFile = zipfile.ZipFile(path, 'r')
            extractDir = os.path.splitext(path)[0]
            zipFile.extractall(extractDir)
            zipFile.close()
            path = extractDir
            
            # # 查找解压后的目标文件
            # for file in zipFile.namelist():
            #     if file.endswith("_wrapper_ASCII.sp"):
            #         self.path = os.path.join(extractDir, file)
            #         break
            #     elif file.endswith("_ASCII.ploc"):
            #         self.path = os.path.join(extractDir, file)
            #         break
            # return

        # 如果 path 不是以 Extraction 结尾，则查找 path 的多级子目录，直至找到 Extraction 目录
        if not path.endswith("Extraction"):
            currentPath = path
            maxDepth = 5  # 限制搜索深度，避免无限递归
            depth = 0
            
            while depth < maxDepth:
                # 检查当前目录是否包含 Extraction 子目录
                for root, dirs, files in os.walk(currentPath):
                    if "Extraction" in dirs:
                        extractionPath = os.path.join(root, "Extraction")
                        self.path = extractionPath
                        return
                
                # 向上查找父目录
                parentPath = os.path.dirname(currentPath)
                if parentPath == currentPath:  # 已到达根目录
                    break
                currentPath = parentPath
                depth += 1
            
            # 如果未找到 Extraction 目录，使用原路径
            # self.path = path
            log.exception("Extraction dir not found in CPA model: %s"%pathback)
        else:
            self.path = path

            self.readTopSubckt()
            self.readPLOC()
            self.readCPPs()


    def readTopSubckt(self,path=None):
        if not path:
            files = getFileList(self.path,".*_wrapper_ASCII.sp")
            if files:
                path = files[0]
            else:
                log.exception("Top Spice file not found for check.")

        if not os.path.isfile(path):
            print("file not exist")
            return

        smodel = SpiceModel(path)
        subckt0 = smodel.subckts[0]
        self.TopSubcktModel = subckt0
        self.TopSubcktPath = path
        self.spiceModel = smodel
        

    def readPLOC(self,path=None):
        if not path:
            files = getFileList(self.path,".*_ASCII.ploc")
            if files:
                path = files[0]
            else:
                log.exception("Top Spice file not found for check.")

        if not os.path.isfile(path):
            print("file not exist")
            return

        self.PLOC = PLOC(path)

    def readCPPs(self,path=None):
        if not path:
            files = getFileList(self.path,".+cpp")
            if not files:
                log.exception("Top Spice file not found for check.")

        CPPDict = {}
        for file in files:
            cpp = CPP(file)
            CPPDict[cpp.component] = cpp
        self.CPPDict = CPPDict

    def save(self):
        for cpp in self.CPPDict.values():
            cpp.write()
        self.PLOC.write()
        self.spiceModel.write()

        
