#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20251011


import re,os
from ..common.common import *


class SiwFile(object):

    def __init__(self,path=None):
        self.path = path
        self.bDatas = None

        if path:
            self.load(path)
    
    def replace(self,regx,replaceTxt,loc=0):
        if isinstance(replaceTxt,str):
            replaceTxt = replaceTxt.encode()
        if isinstance(regx, str):
            regx = regx.encode()
        pattern = re.compile(regx)
        replaced_data = pattern.sub(replaceTxt,self.bDatas)
        self.bDatas = replaced_data
        return replaced_data

    def load(self,path):
        if path is not None and os.path.exists(path):
            self.path = path
        else:
            log.error("SiwFile: path is not exists!")
            return

        with open(path,'rb') as file:
            # 2. 读取所有字节数据
            binary_data = file.read()
            file.close()

        self.bDatas = binary_data

    def save(self,path=None):
        if path is None:
            path = self.path
        with open(path,'wb') as f:
            f.write(self.bDatas)