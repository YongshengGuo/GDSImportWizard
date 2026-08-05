
from .desktop import initializeDesktop,releaseDesktop,getInstallPath
from .aedtTool import AedtTool
from .primitive.component import Components
from .primitive.pin import Pins
from .primitive.pin import Pin
from .definition.net import Nets
from .definition.layer import Layers
from .definition.material import Materials
from .definition.variable import Variables
from .definition.setup import Setups
from .definition.path import Path,Node
from .definition.padStack import PadStacks
from .definition.componentLib import ComponentDef
from .definition.pinGroup import PinGroups
from .definition.airbox import Airbox

from .primitive.port import Ports
from .primitive.line import Lines
from .primitive.via import Vias
from .primitive.primitive import Objects3DL

from .common.complexDict import ComplexDict
from .common.arrayStruct import ArrayStruct
from .common.common import *
from .common.unit import Unit
from .common.licenseChecker import LicenseChecker


from .options import options
from .postData.solution import Solutions
from .postData.touchStone import Touchstone

from .model3D.HFSS import Aedt3DToolBase
from .model3D.HFSS import HFSS
from .model3D.Q3D import Q3D
from .model3D.maxwell import Maxwell
from .model3D.icepak import Icepak

from .edb.edbApp import EdbApp,EdbSIwaveOptions,edbToSIwave,initEdb
from .edb.edbComponent import EdbComponent,EdbComponents
from .edb.edbPinGroup import EdbPinGroup,EdbPinGroups
from .edb.edbLayer import EdbLayer,EdbLayers
from .edb.edbSiwaveOption import EdbSIwaveOptions
from .edb.edbPrimitive import EdbPrimitive,EdbPrimitives
from .edb.edbVia import EdbVia,EdbVias
from .edb.edbNet import EdbNet,EdbNets
from .edb.siwFile import SiwFile

#for spice processing
from .netlist.spiceModel import SpiceModel,Element,Subckt,Node
from .netlist.cpp import CPP
from .netlist.ploc import PLOC
from .netlist.CPAModel import CPAModel

#---log is a globle variable
from .common.common import log,isIronpython
from .common.progressBar import ProgressBar
from .common.xlsReader import XlsReader
from .common.licenseChecker import LicenseChecker


from .pyLayout import Layout
from .workflow.extractBase import ExtractBase
from .workflow.simConfig import SimConfig
from .workflow.edbSetupBase import EdbSetupBase

version = "V0.12.6 20250726"
log.info("pyLayout Version: %s"%version)
# log.info("the lastest release on: https://github.com/YongshengGuo/pyLayout")
log.setLogLevel(logLevel="INFO")
# log.setLogLevel(logLevel="DEBUG")

# import os
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 

