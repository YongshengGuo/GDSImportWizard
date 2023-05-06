setenv AedtInstallDir /data/tools/AnsysEM/v231/Linux64
setenv gdsFile /home/yguo/Project/GDSImport/T28_new.gds
setenv techFile /home/yguo/Project/GDSImport/tsmc.ircx
setenv ipy64 "$AedtInstallDir/common/mono/Linux64/bin/mono $AedtInstallDir/common/IronPython/ipy64.exe"
$ipy64  GDSImportWizard.py