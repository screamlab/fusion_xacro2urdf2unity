import os
import re
import shutil
import urllib.request
import subprocess
import argparse
import sys


def patch_xacro_for_minidom_compat(xacro_path: str) -> None:
    """
    Patch doctorsrn/xacro2urdf xacro.py to be compatible with Python 3.12+.
    Safe for Python 3.8~3.11 (no-op if not needed).
    """
    try:
        with open(xacro_path, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"Warning: failed to read '{xacro_path}' for minidom compatibility patch: {e}", file=sys.stderr)
        return

    # 已 patch 過就不再動
    if "_write_data_compat" in src:
        return

    needle = "xml.dom.minidom._write_data(writer, attrs[a_name].value)"
    if needle not in src:
        return

    inject = (
        "import xml.dom.minidom\n\n"
        "def _write_data_compat(writer, data, attr=None):\n"
        "    try:\n"
        "        # Python 3.12+\n"
        "        return xml.dom.minidom._write_data(writer, data, attr)\n"
        "    except TypeError:\n"
        "        # Python <= 3.11\n"
        "        return xml.dom.minidom._write_data(writer, data)\n\n"
    )

    lines = src.splitlines(True)
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1

    if insert_at == 0 and lines:
        # Avoid inserting before shebang or encoding declaration if present
        first_line = lines[0]
        if first_line.startswith("#!") or "coding" in first_line:
            insert_at = 1
    patched = (
        "".join(lines[:insert_at])
        + "\n"
        + inject
        + "".join(lines[insert_at:])
    )
    patched = patched.replace(
        needle,
        "_write_data_compat(writer, attrs[a_name].value, None)"
    )

    try:
        with open(xacro_path, "w", encoding="utf-8") as f:
            f.write(patched)
    except OSError as e:
        raise OSError(f"Failed to write patched xacro file '{xacro_path}': {e}") from e


def main():
    parser = argparse.ArgumentParser(
        description="Convert xacro file to URDF and prepare files for Unity."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=os.getcwd(),
        help="Path to the folder containing the 'urdf' folder (default: current directory)."
    )
    args = parser.parse_args()

    # 切換到指定工作目錄
    os.chdir(args.path)

    # 檢查 urdf 資料夾
    if not os.path.exists("urdf"):
        sys.stderr.write(
            "Error: 'urdf' folder not found. "
            "Please place this script in the parent folder of 'urdf'.\n"
        )
        sys.exit(1)

    # 取得機器人資料夾名稱（xxx_description）
    robot_mesh = os.path.basename(os.getcwd())
    robot_name = robot_mesh.replace("_description", "")

    # 檢查 xacro
    xacro_file = os.path.join("urdf", f"{robot_name}.xacro")
    if not os.path.exists(xacro_file):
        sys.stderr.write(f"Error: '{xacro_file}' not found.\n")
        sys.exit(1)

    # 下載 xacro.py（若不存在）
    xacro_script = "xacro.py"
    if not os.path.exists(xacro_script):
        url = "https://raw.githubusercontent.com/doctorsrn/xacro2urdf/master/xacro.py"
        print("Downloading xacro.py ...")
        urllib.request.urlretrieve(url, xacro_script)

    # Patch xacro.py（Python 3.12 相容）
    patch_xacro_for_minidom_compat(xacro_script)

    # 建立 urdf/<robot_mesh>/meshes 並複製 meshes
    urdf_mesh_dir = os.path.join("urdf", robot_mesh, "meshes")
    os.makedirs(urdf_mesh_dir, exist_ok=True)
    if os.path.exists("meshes"):
        shutil.copytree("meshes", urdf_mesh_dir, dirs_exist_ok=True)

    # 產生暫存 xacro（移除 .gazebo include）
    temp_xacro_file = xacro_file + ".temp"
    with open(xacro_file, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r'<xacro:include\b[^>]*\.gazebo[^>]*>',
        '<!-- omitted .gazebo include -->',
        content
    )

    with open(temp_xacro_file, "w", encoding="utf-8") as f:
        f.write(content)

    # 執行 xacro → urdf
    urdf_output = f"{robot_name}.urdf"
    print("Generating URDF ...")
    subprocess.run(
        [sys.executable, xacro_script, "-o", urdf_output, temp_xacro_file],
        check=True
    )

    os.remove(temp_xacro_file)

    # 修正 mesh 路徑（file:// → package://）
    with open(urdf_output, "r", encoding="utf-8") as f:
        urdf_data = f.read()

    urdf_data = re.sub(
        r'file://.*?[/\\]meshes',
        f'package://{robot_mesh}/meshes',
        urdf_data
    )

    with open(urdf_output, "w", encoding="utf-8") as f:
        f.write(urdf_data)

    # 輸出到 Unity 用資料夾
    output_dir = f"{robot_name}_to_unity"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    urdf_dest = os.path.join(output_dir, os.path.basename(urdf_output))
    mesh_src = os.path.join("urdf", robot_mesh)
    mesh_dest = os.path.join(output_dir, robot_mesh)

    try:
        shutil.move(urdf_output, output_dir)
        shutil.move(mesh_src, output_dir)
    except OSError as exc:
        # Best-effort rollback to avoid leaving a partially moved state
        try:
            if os.path.exists(urdf_dest) and not os.path.exists(urdf_output):
                shutil.move(urdf_dest, urdf_output)
        except OSError:
            pass
        try:
            if os.path.exists(mesh_dest) and not os.path.exists(mesh_src):
                shutil.move(mesh_dest, mesh_src)
        except OSError:
            pass
        print(f"❌ Error while moving generated files: {exc}", file=sys.stderr)
        raise
    print(f"✅ Success. Files are ready in '{output_dir}'.")


if __name__ == "__main__":
    main()
