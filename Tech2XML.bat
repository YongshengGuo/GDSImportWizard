set AedtInstallDir="C:\Program Files\ANSYS Inc\v252\AnsysEM"
set ipy64=%AedtInstallDir%\common\commonfiles\IronPython\ipy64.exe

::SpecificTemperatureForResist Used to generate conductivity at a specific temperature, and can be commented out when not in use
set SpecificTemperatureForResist=25

%ipy64% C:\work\Study\Script\repository\HFSS\GDSII\GDS2XML\GDSTranslator\GDSTranslator\GDSImportWizard.py Tech2XML -Techfile test.ircx -ControlXmlPath test_25deg.xml
pause