set AedtInstallDir="C:\Program Files\AnsysEM\v231\Win64"
set gdsFile=%~dp0T28_new.gds
set techFile=%~dp0tsmc.ircx
set ipy64=%AedtInstallDir%\common\commonfiles\IronPython\ipy64.exe

set UseTemperatureDependMaterial=True
ipy64 ./GDSImportWizardV5.84/GDSImportWizard.py
pause