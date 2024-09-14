@echo off
setlocal

:: Check if the ./urdf folder exists
if not exist urdf (
    echo Error, the urdf folder doesn't exist. Please place this script into the same folder as the urdf folder.
    pause
    exit /b 1
)

:: Set robot_mesh to the parent directory name (xxx_description)
for %%F in (.) do set robot_mesh=%%~nxF

:: Set robot_name by removing _description from robot_mesh
set robot_name=%robot_mesh:_description=%

:: Check if the ./urdf/%robot_name%.xacro file exists
if not exist urdf\%robot_name%.xacro (
    echo Error, the urdf\%robot_name%.xacro file doesn't exist.
    pause
    exit /b 1
)

:: Check if xacro.py exists, if not download it
if not exist xacro.py (
    curl https://raw.githubusercontent.com/doctorsrn/xacro2urdf/master/xacro.py -o xacro.py
)

:: Create directories and copy files
mkdir urdf\%robot_mesh%\meshes
xcopy /E /I meshes urdf\%robot_mesh%\meshes

:: Run xacro.py to generate the URDF file
python xacro.py -o %robot_name%.urdf urdf\%robot_name%.xacro

:: Move files into the new directory
mkdir %robot_name%_to_unity
move %robot_name%.urdf %robot_name%_to_unity
move urdf\%robot_mesh% %robot_name%_to_unity

:: Print success message
echo Success. Your files are ready in the folder '%robot_name%_to_unity'.

:: Pause at the end to allow the user to see the output
pause
