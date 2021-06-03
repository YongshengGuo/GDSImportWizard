# GDSImportWizard
功能简介：程序通过Technology文件提取准确的叠层和材料参数，生成XML控制文档，然后把GDS文件导入3D Layout或者SIwave中进行仿真，适用于2.5D/3D封装的Interposer仿真或者其它未加密IRCX文件的应用。  

Readme: The program extract accurate stackup and material parameters from technology file, and generates XML control file, import GDS into 3D layout/SIwave to simulation, intend to 2.5d/3d package interposer simulation or other unencrypted IRCX Input.
***
### A smart tool to translate GDSII to HFSS 3DLayout quickly:
* Extract nets from GDS and import to EDB
* Extract accurate material property from IRCX
* Extract accurate layer thickness and stackup from IRCX
* Automatic generate control xml for AEDT GDSII Importing
* Support four type dielectric merge when importing  (Update in V4.0)
* Support overlapping and laminated stackup
* Automatic create Via Group and SnapViaGroups
* Automatic generate components on top and bottom layer for easier port setup
* Automatic generate TSV Insulation coating
* Synchronous import to AEDT when EDB prepared
* Automatic detect and fix of small gaps between layers to avoid mesh Issue (New in V4.0)
* Support sheet layers to simplify thinner metal layer mesh e.g. 0.001um（ New in V4.0 ）
***
You are welcome to contact ANSYS local technical support if you have any problems.
