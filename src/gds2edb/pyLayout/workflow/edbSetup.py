    #coding:utf-8
    #--- coding=utf-8
    #--- @author: yongsheng.guo@ansys.com
    #--- @Time: 20251021


'''
For EDB setup, addressing the problem of inaccurate execution on Linux systems.
'''

import sys,os,re
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
# sys.path.append(appDir)
pylayoutLibDir = os.path.dirname(os.path.dirname(appDir))
print("pylayout App dir:%s"%pylayoutLibDir)
sys.path.append(pylayoutLibDir)
from pyLayout import EdbSetupBase

def edbSetup(args):
    configPath = args.configPath
    edbPath = args.edbPath
    installDir = args.installDir
    
    edbBase = EdbSetupBase(configPath)
    
    if args:
        if args.edbPath != "NA":
            edbBase.Config["Import/EdbPath"] = args.edbPath
            
        if args.installDir != "NA":
            edbBase.Config["AEDT/InstallPath"] = args.installDir

    edbBase.run()


import argparse
def main():
    # Create argument parser
    example = (
        "Example usage: \n"
        "python edbSetupBase.py configPath edbPath \n"

        )

    parser = argparse.ArgumentParser(description='EDB setup script, use json as input.',formatter_class=argparse.RawTextHelpFormatter,epilog=example)
    
    # Add arguments

    parser.add_argument('configPath', type=str, nargs='?',
                        help='Set configPath path')
    
    parser.add_argument('edbPath', type=str, nargs='?', default = "NA",
                    help='Set edbPath path')
    
    parser.add_argument('installDir', type=str, nargs='?', default = "NA",
                        help='Set installDir path')

    # Parse arguments
    args = parser.parse_args()
    if args.configPath:
        edbSetup(args)
    else:
        parser.print_help()
        
#for test
if __name__ == '__main__':
    main()

# 
# def edbSetup(edbPath,configPath,installDir):
#     from pyLayout import EdbApp,SimConfig,log
#     
#     config = SimConfig(configPath)
#     Options = config["Setup"]["Options"]
# 
#     edbApp = EdbApp(installDir=installDir)
#     edbApp.open(edbPath)
#     siwOption = edbApp.SIwaveOptions
#     edbApp.removeAllSimSetup() #remove exist simsetup
# 
#     for k,v in Options.Dict.items():
#         try:
#             siwOption[k] = str(v)
#             print("Edb set %s value %s"%(k,v))
#         except:
#             log.warning("Option %s not found in EDB"%(k))
#     
#     edbApp.save()
#     edbApp.close()
#     print("EDB setup Sucessfull.")
# 
# 
# import argparse
# def main():
#     # Create argument parser
#     example = (
#         "Example usage: \n"
#         "python psisim.py simXls layoutPath \n"
# 
#         )
# 
#     parser = argparse.ArgumentParser(description='EDB setup',formatter_class=argparse.RawTextHelpFormatter,epilog=example)
#     
#     # Add arguments
#     parser.add_argument('edbPath', type=str,help='edbPath')
#     parser.add_argument('configPath', type=str,help='configPath')
#     parser.add_argument('installDir', type=str,help='installDir')
#     parser.add_argument('mainDir', type=str,help='mainDir')
# 
#     # Parse arguments
#     args = parser.parse_args()
#     if args.edbPath:
#         sys.path.insert(0, args.mainDir)
#         sys.path.insert(0, os.path.join(args.mainDir,"site-packages"))
#         edbSetup(args.edbPath,args.configPath,args.installDir)
#     else:
#         parser.print_help()
        
# #for test
# if __name__ == '__main__':
#     main()
#     sys.exit()
#     

