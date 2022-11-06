rem neccessary zip-tool: 7-zip -> download from the internet, add to PATH-variable

rem create new directory
md Strakmachine

rem create sub-folders
md .\Strakmachine\doc
md .\Strakmachine\XFLR5
md .\Strakmachine\bin
md .\Strakmachine\scripts
md .\Strakmachine\build
md .\Strakmachine\ressources

rem copy all script-files to strakmachine pure
rem use copy to create exe-files
copy .\scripts\planform_creator.py .\Strakmachine\scripts\
copy .\scripts\planform_creator_gui.py .\Strakmachine\scripts\
copy .\scripts\strak_machine.py .\Strakmachine\scripts\
copy .\scripts\strak_machine_gui.py .\Strakmachine\scripts\
copy .\scripts\xoptfoil_visualizer-jx.py .\Strakmachine\scripts\
copy .\scripts\best_airfoil.py .\Strakmachine\scripts\
copy .\scripts\change_airfoilname.py .\Strakmachine\scripts\
copy .\scripts\show_status.py .\Strakmachine\scripts\
copy .\scripts\FLZ_Vortex_export.py .\Strakmachine\scripts\
copy .\scripts\XFLR5_export.py .\Strakmachine\scripts\
copy .\scripts\DXF_export.py .\Strakmachine\scripts\

rem copy xoptfoil and xfoil-worker to bin-folder
copy .\bin\*.exe .\Strakmachine\bin\

rem copy Xoptfoil-JX instruction
echo V | xcopy .\doc\Xoptfoil-JX\*.* .\Strakmachine\doc\Xoptfoil-JX

rem copy troubleshooting guide
copy .\doc\Troubleshooting.docx .\Strakmachine\doc

rem copy installation instruction
copy .\doc\HowToInstall.docx .\Strakmachine

rem copy first steps
copy .\doc\FirstSteps.docx .\Strakmachine

rem copy all ressource-files
xcopy .\ressources\*.* .\Strakmachine\ressources\ /Y /E /H /C /I

rem copy airfoil-library
xcopy .\airfoil_library\*.* .\Strakmachine\airfoil_library\ /Y /E /H /C /I

rem delete all batch files
del .\Strakmachine\*.bat

rem copy batch files
xcopy .\batch_files\*.* .\Strakmachine\ /Y /E /H /C /I

rem create zip-archive
for /f "tokens=3,2,4 delims=/- " %%x in ("%date%") do set d=%%y%%x%%z
set data=%d%
Echo zipping...
"C:\Program Files\7-Zip\7z.exe" a -tzip "Strakmachine_R1.zip" ".\Strakmachine"
echo Done!
pause
