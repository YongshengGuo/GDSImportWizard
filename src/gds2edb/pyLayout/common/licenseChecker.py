#coding:utf-8
#--- coding=utf-8
#--- @author: yongsheng.guo@ansys.com
#--- @Time: ver 6.0 20230721

import sys,os,re
from .common import log,loadJson,writeJson,readCfgFile,is_linux
from .complexDict import ComplexDict
import math,time

class LicenseChecker(object):
    
    def __init__(self,server):
        '''
        '''
        self.server = server
        self.unusedCount = 0


    def checkFeature(self,feature,count = 1):
        '''
        count: 检测的个数
#         count = 1 检测一个有效
#         count = 2 检测两个有效
#         count = "<3" 检测有效数量少于3个 
        '''
        if count<1:
            return True

        rst = self.getFeatureCount(feature)
        if not rst:
            return False
        
        unused = int(rst[0]) - int(rst[1])
        self.unusedCount = unused
        if int(rst[0]) - int(rst[1])>=int(count):
            return True
        else:
            return False

    def checkDesktop(self,count = 1):
        return self.checkFeature("electronics_desktop",count)

    def check3DLayoutGUI(self,count = 1):
        return self.checkFeature("electronics_desktop",count) and self.checkFeature("electronics3d_gui",count)
        
    def checkHFSSGUI(self,count = 1):
        return self.checkFeature("electronics_desktop",count) and self.checkFeature("electronics3d_gui",count)

    def checkQ3DGUI(self,count = 1):
        return self.checkFeature("electronics_desktop",count) and self.checkFeature("electronics3d_gui",count)

    def checkSIwaveGUI(self,count = 1):
        return self.checkFeature("electronics_desktop",count) and self.checkFeature("electronics3d_gui",count)
    
    def checkMaxwellGUI(self,count = 1):
        return self.checkFeature("electronics_desktop",count) and self.checkFeature("electronics3d_gui",count)

    def checkCircuitGUI(self,count = 1):
        return self.checkFeature("electronics_desktop",count) and self.checkFeature("electronicsckt_gui",count)

    def checkHFSSSolver(self,count = 1):
        return self.checkFeature("elec_solve_hfss",count) and self.checkFeature("elec_solve_level1",count) and self.checkFeature("elec_solve_level2",count)

    def checkMaxwellSolver(self,count = 1):
        return self.checkFeature("elec_solve_maxwell",count) and self.checkFeature("elec_solve_level1",count) and self.checkFeature("elec_solve_level2",count)

    def checkQ3DSolver(self,count = 1):
        return self.checkFeature("elec_solve_q3d",count) and self.checkFeature("elec_solve_level1",count) and self.checkFeature("elec_solve_level2",count)

    def checkSIwaveSolver(self,count = 1):
        return self.checkFeature("elec_solve_siwave",count) and self.checkFeature("elec_solve_level1",count) and self.checkFeature("elec_solve_level2",count)

    def checkPSISolver(self,count = 1):
        return self.checkFeature("elec_solve_siwave",count) and self.checkFeature("elec_solve_level1",count) and self.checkFeature("elec_solve_level2",count)

    def checkHPC(self,count = 1):
        return self.checkFeature("anshpc",count)

    def checkHPCPack(self,count = 1):
        return self.checkFeature("anshpc_pack",count)
    
    def checkHPCPackByCores(self,cores = 4):
        pack = 0
        if cores>8*4*4*4+4:
            pack = math.ceil(math.log((cores-4)/2) / math.log(4))
        elif cores>8*4*4+4:
            pack = 4
        elif cores>8*4+4:
            pack = 3
        elif cores>8+4:
            pack = 2
        elif cores>4:
            pack = 1
        else:
            pass
        return self.checkFeature("anshpc_pack",pack)

    def waitForlicense(self,featureList,timeout = 100*60):
        '''
        []: {"feature":elec_solve_hfss,count:1},{"module":"3DLayoutGUI",count:1}
        '''
        
        flag = False
        start_time = time.time()
        n = 0
        while not flag:
            flag = True
            
            elapsed_time = time.time() - start_time
            if elapsed_time>timeout:
                log.error("Time out for license check,time cost seconds: %.1f "%elapsed_time)
                return False
            
            for feature in featureList:
                
                if  "count" not in feature:
                    feature["count"] = 1
                
                if "module" in feature and feature["module"].strip():
                    try:
                        func = getattr(self, "check"+ feature["module"].strip())
                    except:
                        log.info("No module defition: %s"%feature["module"])
                        
                    rst = func(feature["count"])
                    flag = flag and rst
                    if not rst:
                        n += 1 
                        elapsed_time = time.time() - start_time
                        log.info("Wart for license module %s ...,  round %s, waiting time: %.1f seconds"%(feature["module"],n,elapsed_time))
                        time.sleep(5) #wait for 5 sceond 
                        continue

                if "feature" in feature and feature["feature"].strip():
                    rst = self.checkFeature(feature["feature"].strip(),feature["count"])
                    flag = flag and rst
                    if not rst:
                        n += 1 
                        elapsed_time = time.time() - start_time
                        log.info("Wart for license feature %s ...,  round %s, waiting time: %.1f seconds"%(feature["feature"],n,elapsed_time))
                        time.sleep(5) #wait for 5 sceond 
                        continue
                    
        elapsed_time = time.time() - start_time
        log.info("Check license success, time cost: %.1f seconds"%elapsed_time)
        return True


    def getFeatureCount(self,feature):
        '''
        Check license
        '''
        aedtInstallDir = None
        if "ANSYSEM_ROOT" in os.environ and os.environ["ANSYSEM_ROOT"].strip():
            aedtInstallDir = os.environ["ANSYSEM_ROOT"]
        else:
            ANSYSEM_ROOTs = list(
                filter(lambda x: "ANSYSEM_ROOT" in x, os.environ))
            if ANSYSEM_ROOTs:

                ANSYSEM_ROOTs.sort(key=lambda x: x[-3:])
                aedtInstallDir = os.environ[ANSYSEM_ROOTs[-1]]

        if not aedtInstallDir:
            log.exception("AEDT InstallDir not found, please set environ ANSYSEM_ROOT=Ansys EM install path...")
        
        
        licClientPath = os.path.join(aedtInstallDir,"licensingclient", "linx64" if is_linux else "winx64") #linx64
        if os.path.exists(licClientPath):
            #before 25R2
            log.info(licClientPath)
            os.environ["PATH"] = licClientPath  + os.pathsep + os.environ["PATH"]
        else:
            #begin 26R1
            licClientPath = os.path.join(os.path.dirname(aedtInstallDir),"licensingclient","linx64" if is_linux else "winx64")
            log.info(licClientPath)
            os.environ["PATH"] = licClientPath + os.pathsep + os.environ["PATH"]

        log.info("Check license %s on server %s"%(feature,self.server))
        if not self.server:
            log.exception("Server not set, please set server first.")

        cmd = "lmutil lmstat -c %s -f %s"%(self.server,feature)
        rst = None
        with os.popen(cmd,"r") as output:
            rst = output.read()
            # for line in output:
            #     log.info(line)
            output.close()
#         print(rst)
        
        rst2 = re.findall("Total\D*(\d+)\D*issued;\D*Total\D*(\d+)\D*",rst,re.DOTALL)
        if rst2:
            if len(rst2[0]) != 2:
                log.info(rst)
                log.info("get license error.")
                
            total,used = rst2[0]
            log.info("Total:%s,used:%s"%(total,used))
            return total,used
        else:
            log.info('License Server not reachable,  "%s" can not check '%feature)
            return None

