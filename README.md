# GDSImportWizard
功能简介：程序通过Technology文件转出准确的叠层和材料参数，生成XML控制文档，把GDS文件导入3D Layout或者SIwave中进行仿真，适用于2.5D/3D封装的Interposer仿真。     
Readme: The program extract accurate stackup and material parameters from technology file, and generates XML control file, import GDS into 3D layout/SIwave to simulation, intend to 2.5d/3d package interposer simulation.

Function List:
-Extract nets from GDS and import to EDB
-Extract accurate material property from IRCX
-Extract accurate layer thickness and stack up from IRCX
-Generate control xml for AEDT Import Module
-Support dielectric merge when importing 
-Support overlapping and laminated stack up
-Automatic create Via Group and SnapViaGroups
-Generate components on top and bottom layer
-Generate TSV coating and Insulating layer
-Synchronous import to AEDT when EDB prepared


