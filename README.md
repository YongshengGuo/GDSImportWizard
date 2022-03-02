# GDSImportWizard
Latest version:  https://github.com/YongshengGuo/GDSImportWizard/releases/latest

Author: yongsheng.guo@ansys.com

功能简介：
用于2.5D/3D 先进封装的导入和仿真，快速将Interposer的设计文件（GDSII）快速导入Ansys 3DLayout进行仿真分析，支持非加密的IRCX文件和自定义的工艺文件格式。

Readme:
Used for the import and Simulation of 2.5d/3d advanced packaging, quickly import the interposer file (GDSII) into ANSYS 3dlayout for simulation analysis, and support unencrypted ircx file and user-defined Technology File.

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
