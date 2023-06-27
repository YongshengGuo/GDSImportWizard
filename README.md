# GDSImportWizard
Latest version:  https://github.com/YongshengGuo/GDSImportWizard/releases/latest

Author: yongsheng.guo@ansys.com

功能简介：
该工具可快速将GDS格式文件导入到Ansys HFSS 3D Layout中进行仿真建模和分析，支持非加密的IRCX文件、itf文件，也支持自定义的工艺文件格式（未直接支持的文件可通过CSV导入定义）。支持应用包括2.5D/3D Package、RF Chip、TSV、Silicon-SI等。

Readme:
This toolkit enables fast import of GDS format files into Ansys HFSS 3D Layout for simulation modeling and analysis. It supports non-encrypted IRCX files, itf files, and custom process file formats (unsupported files can be imported through CSV definitions). Applications supported include advanced 2.5D/3D packaging, RF chips, TSV, Silicon-SI, and more.

***
### A smart tool to translate GDSII to HFSS 3DLayout quickly:
* Extract nets from GDS and import to EDB
* Extract accurate material property from IRCX
* Extract accurate layer thickness and stackup from IRCX
* Automatic generate control xml for AEDT GDSII Importing
* Support four type dielectric merge when importing  (Update in V4.0)
* Automatic create Via Group and SnapViaGroups
* Automatic generate components on top and bottom layer for easier port setup
* Synchronous import to AEDT when EDB prepared
* Automatic detect and fix of small gaps between layers to avoid mesh Issue (New in V4.0)
* Support sheet layers to simplify thinner metal layer mesh e.g. 0.001um（ New in V4.0 ）
* support to generate temperature dependent material （ New in V5.0）
* Add CSV input template to provide more flexible input for other Technology File（ New in V5.0）
* Support New TSV Layer feature in 3D Layout 2022R1 (New in V5.0)
* Support ConvertPolygonToCircle Feature to reduce mesh(New in V5.0)
* More flexible setting options and enhanced command line(No-GUI) support(windows and Linux) 
***
