
#--- coding=utf-8
#--- @author: yongsheng.guo@synopsys.com
#--- @Time: ver 6.0 20260225 

import sys,os
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)
sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim")
from pyLayout import log,runSubProcess
from pyLayout import getInstallPath


from options import options
import shutil
# from Common import * 
from CSVTech import CsvTech
from IRCXTech import IrcxTech
from itfTech import ItfTech
from miptTech import MiptTech
from ictTech import IctTech
from controlXml import ControlXml

from options import options  # type: ignore, global variable to store options

print("Note:This program only supports 3D Lalyout 2025R2, earlier versions are recommended to use V5. x version")


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


class GDS2Edb(object):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        #use options to store all options
        self.options = options
        self.tech = None

    def readOptions(self,path=None):

        if path == None:
            path = os.path.join(appDir,"gds2edb.cfg")
        options.readCfgOption(path)

    def getTech(self):
        techFile = options.techFile
        if not techFile or not os.path.exists(techFile):
            log.exception("TechFile must defined.")
            return
        
        tech = None
        if techFile[-5:].lower() == ".ircx":
            tech = IrcxTech()
            tech.parse(techFile)
        elif techFile[-4:].lower() == ".csv":
            tech = CsvTech()
            tech.parse(techFile)
        elif techFile[-4:].lower() == ".itf":
            tech = ItfTech()
            tech.parse(techFile)
        elif techFile[-5:].lower() == ".mipt":
            tech = MiptTech()
            tech.parse(techFile)
        elif techFile[-4:].lower() == ".ict":
            tech = IctTech()
            tech.parse(techFile)
        else:
            pass
        self.tech = tech
        return tech

    def setLayermap(self,layermapFile=None):
        if not self.tech:
            log.exception("TechFile must defined.")
            return
        if not layermapFile and "layerMap" in options:
            layermapFile = options["layerMap"]
        
        if not layermapFile or not os.path.exists(layermapFile):
            log.info("layermapFile must defined.")
            return
        self.tech.setLayerMap(layermapFile)

    def tech2csv(self,csvPath=None):
        tech = self.tech or self.getTech()
        self.setLayermap()
        if not tech:
            log.exception("TechFile must defined.")
            return
        csvOut = None
        if csvPath:
            csvOut = csvPath
        elif "CsvOut" in options and options["CsvOut"]:
            csvOut = options["CsvOut"]
        else:
            csvOut = options["techFile"][:-4] + ".csv"
        tech.toCSV(csvOut)
        print("finished write csv file: %s"%csvOut)

    def tech2xml(self):
        tech = self.tech or self.getTech()
        self.setLayermap()
        tech2 = tech.copy()
        tech2.removeDuplicateDielectricLayers()
        if "IgnoreLayersReg" in options and options["IgnoreLayersReg"]:
            tech2.setIgnoreLayers(options["IgnoreLayersReg"])

        if "SimplifyDieletricMethod" in options and options["SimplifyDieletricMethod"]:
            SimplifyDieletricMethod = options["SimplifyDieletricMethod"]
            tech3 =  tech2.simplifyTech(SimplifyDieletricMethod)
        else:
            tech3 = tech2
        if "SheetLayerThreshold" in options and options["SheetLayerThreshold"]:
            tech3.useSheetLayer(options["SheetLayerThreshold"])
        if "UseDefaultDF" in options and options["UseDefaultDF"]:
            tech3.useDefaultDF(options["UseDefaultDF"])
        tech3.setBase()
        tech3.fixeLayerGap()
        tech3.sort(True)

        cxml = ControlXml(tech3)
        return cxml.writeControlXml()


    def generateEBD(self):
        aedtInstallDir = options["AedtInstallDir"]
        #如果没有设置AedtInstallDir，则通过ANSYSEM_ROOTxxx环境变量检测最新版本的aedt路径，赋值给AedtInstallDir
        if not aedtInstallDir:
            for key in sorted(os.environ.keys(), reverse=True):
                if key.startswith("ANSYSEM_ROOT"):
                    aedtInstallDir = os.path.join(os.environ[key], "aedtdir")
                    options["AedtInstallDir"] = aedtInstallDir
                    break
                
        if not aedtInstallDir:
            log.info("AedtInstallDir must set before run")
            exit()
        
        ControlXmlPath = options["ControlXmlPath"]
        edbPath = options["edbPath"]
        GdsFile = options["GdsFile"]

        # check if the GDS file and ControlXmlPath exists
        if not GdsFile or not os.path.exists(GdsFile):
            log.info("bad GDS path")
            exit()
            
        if not edbPath:
            edbPath = os.path.splitext(GdsFile)[0] + ".aedb"
            options["edbPath"] = edbPath
            
        if not ControlXmlPath or not os.path.exists(ControlXmlPath):
            ControlXmlPath = self.tech2xml()
            options["ControlXmlPath"] = ControlXmlPath
            
        if not ControlXmlPath or not os.path.exists(ControlXmlPath):
            log.info("bad ControlXmlPath")
            exit()
  
        #windows
        if aedtInstallDir not in os.environ['PATH']:
            os.environ['PATH'] = aedtInstallDir + os.pathsep + os.environ['PATH']  
            
        command = ["anstranslator.exe",GdsFile,edbPath, "-c="+ControlXmlPath]
        log.info("command: %s"%(" ".join(command)))
        log.info("start translate gds to EDB")
        runSubProcess(command)
        log.info("finished EDB: %s"%edbPath)
        open_in_aedt = options["OpenInAedt"] if "OpenInAedt" in options else True
        if _to_bool(open_in_aedt):
            log.info("open EDB in aedt: %s"%edbPath)
            self.runAedtPost(edbPath)
        

    def runAedtPost(self, edb_path):
        from pyLayout import log,Layout  # type: ignore
        grpc = os.environ["AEDT_Specific_Grpc_Port"] if "AEDT_Specific_Grpc_Port" in os.environ else None
        layout = Layout(installDir=options["AedtInstallDir"],usePyAedt=options["UsePyaedt"] if "UsePyaedt" in options else False,grpc=grpc)
        layout.importEdb(str(edb_path))
        layout.release()
        
def parserArgs(parser):
    #1. update options from cfg file
    if "cfgFile" in options and options["cfgFile"] and options["cfgFile"] != "NA":
        #判定cfg文件是否存在，如果存在则读取，如果不存在则抛出异常
        if os.path.exists(options["cfgFile"]):
            print("cfgFile: %s"%options["cfgFile"])
        else:
            print("cfgFile: %s not exist"%options["cfgFile"])
            exit()
        options.readCfgOption(options["cfgFile"])
    else:
        options.readOptions()

    #2. update options from environ
    options.updateEnvOption()
    #3. update options from args
    options.updateFromArgs(parser)
    if "AedtVersion" in options and options["AedtVersion"] != "NA":
        options["AedtInstallDir"] = getInstallPath(options["AedtVersion"])
    else:
        options["AedtInstallDir"] = getInstallPath()


def gds2edbBatch():
    g2e = GDS2Edb()
    # #1. update options from cfg file
    # if "cfgFile" in options and options["cfgFile"] and options["cfgFile"] != "NA":
    #     #判定cfg文件是否存在，如果存在则读取，如果不存在则抛出异常
    #     if os.path.exists(options["cfgFile"]):
    #         print("cfgFile: %s"%options["cfgFile"])
    #     else:
    #         print("cfgFile: %s not exist"%options["cfgFile"])
    #         exit()
        
    #     g2e.readOptions(options["cfgFile"])
    # else:
    #     g2e.readOptions()

    #2. update options from environ
    options.updateEnvOption()
    #3. update options from args
    options.updateFromArgs(parser)
    if "AedtVersion" in options and options["AedtVersion"] != "NA":
        options["AedtInstallDir"] = getInstallPath(options["AedtVersion"])
    else:
        options["AedtInstallDir"] = getInstallPath()
        
    flag = False
    if "tech2csv" in options and options["tech2csv"] == True:
        g2e.tech2csv()
        flag = True
    if "tech2xml" in options and options["tech2xml"] == True:
        g2e.tech2xml()
        flag = True
    
    if not flag:
        g2e.generateEBD()
        options.writeCfgOption(options["gdsFile"][:-4] + ".cfg")


import argparse
def main():
    # Create argument parser
    example = (
        "Example usage: \n"
        "python GDS2EDB.py optionList \n"

        )

    parser = argparse.ArgumentParser(description='options test.',formatter_class=argparse.RawTextHelpFormatter,epilog=example)

    # gdsFile = None,techFile=None, edbPath = None)

    parser.add_argument('techFile', type=str,nargs='?',
                        help='Set technology file path, suport type: .csv .ircx .itf')

    parser.add_argument('gdsFile', type=str,nargs='?',
                        help='Set GDSII file path')

    parser.add_argument('edbPath', type=str,nargs='?',
                        help='Set ansys EDB output path')

    parser.add_argument('-l', '--layerMap', default = "NA", 
                        help='Set the path of the layer map file, default: NA')

    parser.add_argument('-t2x', '--tech2xml', default = "NA", action='store_true',
                        help='Convert the technology file to an XML file, which can be used as a Control XML file for importing 3D Layout.')

    parser.add_argument('-t2c', '--tech2csv', default = "NA", action='store_true',
                        help='Convert the technology file to an csv file, CSV can be further edited as an input file for gds2edb and can also be used for sharing.')

    parser.add_argument('-cfg', '--cfgFile', default = "NA",
                        help='Set the path of the config file, default to using the gds2edb.cfg file in the project file.')

    parser.add_argument('-v', '--AedtVersion', default = "NA",
                        help='Set AedtVersion number (e.g. 2024.2),default: lastest version')
    
    known_args, unknown_args = options.updateFromArgs(parser)
    if known_args["techFile"]:
        parserArgs(parser)
        gds2edbBatch()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()