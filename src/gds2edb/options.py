
#coding:utf-8
#--- coding=utf-8
#--- @author: yongsheng.guo@ansys.com
#--- @Time: ver 6.0 20230721

import sys,os,re
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)
sys.path.append(os.path.join(appDir,"site-packages"))
sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim")

from pyLayout import ComplexDict,log,loadJson,writeJson,readCfgFile,writeData



class Option(ComplexDict):
    
    def __init__(self,data=None):

        ComplexDict.__init__(self)
        
        if data:
            if isinstance(data, dict):
                self._dict = data
            elif isinstance(data, ComplexDict):
                self._dict = data.copy()._dict  
            elif isinstance(data, str):
                self.readCfgOption(data)
            else:
                log.exception("Invalid data input: %s"%str(data))
            
        
    def readCfgOption(self,path):
        """
        read ini format file, key=value
        """
        cfg_dict = readCfgFile(path)
        self.updates(cfg_dict)

    def writeCfgOption(self,path):
        """
        write ini format file, key=value
        """
        temp = []
        for k,v in self._dict.items():
            if isinstance(v,(list,tuple)):
                v = ",".join(v)
            elif isinstance(v,dict):
                v = ",".join(["%s:%s"%(k2,v2) for k2,v2 in v.items()])
            else:
                v = str(v)

            temp.append("%s=%s"%(k,v))
        writeData("\n".join(temp),path)


    def updateEnvOption(self):
        _options = self.keys()
        for key in os.environ:
            if key in _options:
                self.update(key,os.environ[key])

    def updateFromArgs(self,parser):
        known_args, unknown_args = parser.parse_known_args()
            
        # 4. 处理结果
#         print("=== 已定义的参数 ===")
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
                        unknown_dict[key] = unknown_args[i+1]
                        i += 2
                    else:
                        unknown_dict[key] = True  # 无值的参数设为True
                        i += 1
                else:
                    # 无--前缀的未定义参数，作为匿名参数
                    unknown_dict['arg_%s'%i] = unknown_args[i]
                    i += 1

        if known_dict:
            for k,v in known_dict.items():
                try:
                    if v == "NA" or v == None:
                        continue
                    
                    self.update(k,v)
                    # self[k] = v
                except:
                    log.exception("%s not in options."%k)
                
        if unknown_dict:
            for k,v in unknown_dict.items():
                try:
                    self.update(k,v) 
                    # self[k] = v
                except:
                    log.info("unknown options: %s=%s."%(k,v))

        return known_dict, unknown_dict
 
    def updateFromEnviron(self):
        for k in os.environ:
            try:
                self[k] = os.environ[k]
                log.info("update from environ: %s=%s."%(k,os.environ[k]))
            except:
                pass

#---global options
options = Option()


import argparse
def main():
    # Create argument parser
    example = (
        "Example usage: \n"
        "python options.py optionList \n"

        )

    parser = argparse.ArgumentParser(description='options test.',formatter_class=argparse.RawTextHelpFormatter,epilog=example)
    

    parser.add_argument('-g', '--gui', action='store_true', default = "NA",
                        help='Enable GUI mode, only for aedt, default: False')

    parser.add_argument('-v', '--AedtVersion', default = "NA",
                        help='Set AedtVersion number (e.g. 2024.2),default: lastest version')
    
    parser.add_argument('-pyaedt', '--UsePyaedt', action='store_true', default = "NA",
                        help='use pyaedt to initial aedt desktop')

    known_args, unknown_args = options.updateFromArgs(parser)
    if known_args:
        print(known_args)
    else:
        parser.print_help()

    if unknown_args:
        print(unknown_args)
    else:
        pass


if __name__ == '__main__':
    main()

    # options.writeCfgOption(r"C:\work\Project\AE\Script\gds2edb\options.cfg")
    # opt = Option(_options)
    # opt.readCfgFile(r"C:\work\Project\AE\Script\gds2edb\options.cfg")
    # options.writeCfgFile(r"C:\work\Project\AE\Script\gds2edb\options.cfg")
