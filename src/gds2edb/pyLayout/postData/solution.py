#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2023-04-24

'''
Solution represents the smallest unit of results in a 3D layout, which can be understood as a collection of SNPs.
Solution代表3D Layout中结果的最小单元，可以理解为一个SNP的结集。


Examples:
    Add HFSS setupName
    >>>
    
'''
import os
import re
import time
from ..common.complexDict import ComplexDict
from ..common.common import log,findFilesByPattern


class DCSolution(object):
    
    def __init__(self,name = None,variation = None,layout=None):
        
        self.name = name
        self.layout = layout

    @property
    def Name(self):
        return self.name
    
    def exportHtmlReport(self,path = None):
        
        if not path:
            path = self.layout.projectDir + "\%s_%s_%s_DCReport.htm"%(self.layout.ProjectName,self.layout.DesignName,self.name)

        #在self.ResultsPath多级子目录下查找是否存在 ".*%s.dcb"%self.name的文件，
        dcbFiles = findFilesByPattern(os.path.join(self.layout.ResultsPath,self.layout.DesignName), ".*%s.dcb"%self.layout.ProjectName)
        #如果找到多个则以日期最新的为主
        if not dcbFiles:
            log.error("not found solution for %s, please analyze the setup first."%self.name)
            return
        elif len(dcbFiles) > 1:
            dcbFiles.sort(key=lambda x:os.path.getmtime(x))
            dcbFile = dcbFiles[-1]
        else:
            dcbFile = dcbFiles[0]
        log.info("export html report: %s"%path)
        self.layout.oDesign.DCReportGeneration(
            [
                "NAME:Report",
                "ReportFile:="		, path,
                "Color:="		, 0,
                "State:="		, True,
                "Filter:="		, "",
                "FailCheck:="		, True,
                "FailRadio:="		, True,
                "Limit:="		, True,
                "Threshold:="		, 1000000,
                "DCFile:="		, dcbFile,
                "SimName:="		, self.name
            ])
        
        #检测path文件的大小，间隔时间5秒钟，如果小于1kB则一直等待，超时时间10分钟
        timeout = 600
        interval = 5
        elapsed = 0
        while os.path.exists(path) and os.path.getsize(path) < 1024 and elapsed < timeout:
            log.info("waiting for html report generation: %ss"%str(elapsed))
            time.sleep(interval)
            elapsed += interval

        return path
#HFSS 3D Layout Design的Solution类
class SYZSolution(object):
    
    def __init__(self,name = None,variation = None,layout=None):
        
        self.name = name
        self.layout = layout

    @property
    def Name(self):
        return self.name
    
    
    def exportSNP(self,path = None):
        return self.exportNetworkData(path)
        
    def exportNetworkData(self,path = None):
        solutionName = self.name
        ext = ".s%sp"%len(self.layout.Ports)
        
        if not path:
#             path = self.layout.projectDir + "\%s"%solutionName
            path = os.path.join(self.layout.projectDir,"_".join([self.layout.projectName,self.layout.designName])+ext)
        
        elif ext not in path:
            path += ext
        else:
            pass

        try:
            log.info("export snp: %s"%path)
            oModule = self.layout.oDesign.GetModule("SolveSetups")
            variation_array=oModule.ListVariations(solutionName)
            
            # #delete diff Pairs，避免导出mixed-sparameters
            oModuleExt = self.layout.oDesign.GetModule("Excitations")
            oModuleExt.SetDiffPairs(
                [
                    "NAME:DiffPairs"
                ])
            
            if not variation_array:
                variation_array = [""]
            self.layout.oDesign.ExportNetworkData(variation_array[0], [solutionName], 3, path, ["ALL"], True, 50, "S", -1, 0, 15)
        except:
            log.error("Export snp fail, Solution data may be not available.")
#         variation_array=self.oModule.ListVariations(solutionName)
#         self.oDesign.ExportNetworkData(variation_array[0], [solutionName], 3, path, ["ALL"], True, 50, "S", -1, 0, 15)

        return path
        
    def exportProfile(self, path=None):
        setupName, sweepName = self.name.split(":")
        if not path:
            path = os.path.join(self.layout.projectDir,"_".join([self.layout.projectName,self.layout.designName,setupName, sweepName])+".prof")
            
        oModule = self.layout.oDesign.GetModule("SolveSetups")
        variation_array=oModule.ListVariations(self.name)
        if not variation_array:
            variation_array = [""]
        log.info("export profile: %s"%path)
        self.layout.oDesign.ExportProfile(setupName, variation_array[0], path)
        return path
        
    def exportConvergence(self, path=None):
        setupName, sweepName = self.name.split(":")
        if not path:
            path = os.path.join(self.layout.projectDir,"_".join([self.layout.projectName,self.layout.designName,setupName, sweepName])+".conv")
            
        oModule = self.layout.oDesign.GetModule("SolveSetups")
        variation_array=oModule.ListVariations(self.name)
        if not variation_array:
            variation_array = [""]
        log.info("export convergence: %s"%path)
        self.layout.oDesign.ExportConvergence(setupName, variation_array[0], path)  

#hfss Solution类
class HfssSolution(object):
    
    def __init__(self,name = None,variation = None,layout=None):
        
        self.name = name
        self.layout = layout

    @property
    def Name(self):
        return self.name
    
    
    def exportSNP(self,path = None):
        return self.exportNetworkData(path)
        
    def exportNetworkData(self,path = None):
        solutionName = self.name
        oModuleBoundary = self.layout.oDesign.GetModule("BoundarySetup")
        ext = ".s%sp"%str(int(oModuleBoundary.GetNumExcitations()/2))
        
        if not path:
#             path = self.layout.projectDir + "\%s"%solutionName
            path = os.path.join(self.layout.projectDir,"_".join([self.layout.projectName,self.layout.designName])+ext)
        
        elif ext not in path:
            path += ext
        else:
            pass

        try:
            log.info("export snp: %s"%path)
            oModule = self.layout.oDesign.GetModule("Solutions")
            variation_array=oModule.ListVariations(solutionName)
            # #delete diff Pairs，避免导出mixed-sparameters
            oModule1 = self.layout.oDesign.GetModule("BoundarySetup")
            oModule1.EditDiffPairs(
                [
                    "NAME:EditDiffPairs"
                ])

            if not variation_array:
                variation_array = [""]
            oModule.ExportNetworkData(variation_array[0], [solutionName], 3, path, ["All"], True, 50, "S", -1, 0, 15)
        except:
            log.error("Export snp fail, Solution data may be not available.")
        return path

    def exportProfile(self, path=None):
        setupName, sweepName = self.name.split(":")
        if not path:
            path = os.path.join(self.layout.projectDir,"_".join([self.layout.projectName,self.layout.designName,setupName, sweepName])+".prof")
            
        oModule = self.layout.oDesign.GetModule("Solutions")
        variation_array=oModule.ListVariations(self.name)
        if not variation_array:
            variation_array = [""]
        log.info("export profile: %s"%path)
        
        self.layout.oDesign.ExportProfile(setupName, variation_array[0], path)
        return path
        
    def exportConvergence(self, path=None):
        setupName, sweepName = self.name.split(":")
        if not path:
            path = os.path.join(self.layout.projectDir,"_".join([self.layout.projectName,self.layout.designName,setupName, sweepName])+".conv")
            
        oModule = self.layout.oDesign.GetModule("Solutions")
        variation_array=oModule.ListVariations(self.name)
        if not variation_array:
            variation_array = [""]
        log.info("export convergence: %s"%path)
        self.layout.oDesign.ExportConvergence(setupName, variation_array[0], path)  
        return path
        
class Solutions(object):
    
    def __init__(self,layout=None):
        self.solutionDict = None #ComplexDict component buffer
        self.layout = layout
            
    def __getitem__(self, key):
        """
        key: str, regex, list, slice
        """
        
        if isinstance(key, int):
            return self.SolutionDict[key]
        
        if isinstance(key, slice):
            return self.SolutionDict[key]
        
        if isinstance(key, str):
            if key in self.SolutionDict:
                return self.SolutionDict[key]
            else:
                #find by 正则表达式
                lst = [name for name in self.SolutionDict.Keys if re.match(r"^%s$"%key,name,re.I)]
                if not lst:
                    raise Exception("not found Solution: %s"%key)
                else:
                    #如果找到多个器件（正则表达式），返回列表
                    return self[lst]

        if isinstance(key, (list,tuple)):
            return [self[i] for i in list(key)]
    
    def __getattr__(self,key):
        if key in ['__get__','__set__']:
            #just for debug run
            return None
        
        try:
            return super(self.__class__,self).__getattribute__(key)
        except:
            log.debug("Lines __getattribute__ from _info: %s"%str(key))
            return self[key]
    
    def __contains__(self,key):
        return key in self.SolutionDict
    
    def __len__(self):
        return len(self.SolutionDict)
    
    def _hfss3DLayoutSolutionDict(self):
        solutionDict = {}
        maps = {}
        setups = self.layout.Setups
        for setup in setups:
            name = setup.name
            setupType = setup["SolveSetupType"]
            if setupType == "SIwaveDCIR":
                solutionDict.update({name:DCSolution(name,layout=self.layout)})
            elif setupType == "HFSS" or setupType == "SIwave":
                for sweep in setup.Sweeps:
                    name = "%s:%s"%(setup.name,sweep.name)
                    solutionDict.update({name:SYZSolution(name,layout=self.layout)})
                    maps.update({"%s_%s"%(setup.name,sweep.name):"%s:%s"%(setup.name,sweep.name)})
            else:
                log.warning("setup type: %s is not supported."%setupType)
            self.solutionDict  = ComplexDict(solutionDict,maps=maps)
    
    def _hfssSolutionDict(self):
        solutionDict = {}
        maps = {}
        setups = self.layout.Setups
        for setup in setups:
            for sweep in setup.Sweeps:
                name = "%s:%s"%(setup.name,sweep.name)
                solutionDict.update({name:HfssSolution(name,layout=self.layout)})
                maps.update({"%s_%s"%(setup.name,sweep.name):"%s:%s"%(setup.name,sweep.name)})
            self.solutionDict  = ComplexDict(solutionDict,maps=maps)
    
    @property
    def SolutionDict(self):
        if self.solutionDict is None:
        # 根据条件选择目标模块
            if self.layout.DesignType == 'HFSS':
                self._hfssSolutionDict()
            elif self.layout.DesignType == 'HFSS 3D Layout Design':
                self._hfss3DLayoutSolutionDict()
            else:
                raise ValueError("Unsupported DesignType: %s" % getattr(self.layout, "DesignType", None))

        return self.solutionDict 
    
    @property
    def All(self):
        return self.SolutionDict
    
    def refresh(self):
        self.solutionDict = None