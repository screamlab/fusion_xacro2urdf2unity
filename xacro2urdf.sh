#!/bin/bash

# Check if the ./urdf folder exists
if [ ! -d ./urdf ]; then
    echo "Error, the urdf folder doesn't exist. Please place this script into the same folder as the urdf folder."
    exit 1
fi

# Get the parent directory name (xxx_description)
robot_mesh=$(basename "$PWD")

# Remove _description from robot_mesh to get robot_name (xxx)
robot_name=${robot_mesh%_description}

# Check if the ./urdf/$robot_name.xacro file exists
if [ ! -f ./urdf/"$robot_name".xacro ]; then
    echo "Error, the ./urdf/$robot_name.xacro file doesn't exist."
    exit 1
fi

# Check if xacro.py exists, if not download it
if [ ! -f ./xacro.py ]; then
    curl https://raw.githubusercontent.com/doctorsrn/xacro2urdf/master/xacro.py -o ./xacro.py
fi

# Create directories and copy meshes
mkdir -p ./urdf/"$robot_mesh"
cp -r ./meshes ./urdf/"$robot_mesh"

# Run xacro.py to generate the URDF file
python xacro.py -o ./"$robot_name".urdf ./urdf/"$robot_name".xacro

# Create the output directory and move the files
mkdir -p ./"$robot_name"_to_unity
mv ./"$robot_name".urdf ./"$robot_name"_to_unity
mv ./urdf/"$robot_mesh" ./"$robot_name"_to_unity

# Print success message
echo "Success. Your files are ready in the folder '${robot_name}_to_unity'."
