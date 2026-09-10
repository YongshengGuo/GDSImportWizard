
#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2024-11-13
# install_pyaedt_gui.py
# PyAEDT Panel Installer — Standardized GUI (Windows-only, Python 3.10+)
# ⚠️ DO NOT MODIFY — GENERATED from ansys.aedt.core_pannel_plan_std.md v1.2

#检测oDesktop是否存在于运行环境，如果存在获取aedt的路径，使用aedt自带的python重新运行这个脚本,然后退出，需要兼容python2.7
import os
import sys


def _bootstrap_from_aedt():
    Module = sys.modules['__main__']
    if not hasattr(Module, "oDesktop"):
        return False

    import subprocess
    oDesktop = getattr(Module, "oDesktop")
    relaunched_flag = "PYAEDT_GUI_RELAUNCHED"

    if os.environ.get(relaunched_flag) == "1":
        return True

    script_path = os.path.abspath(__file__) if "__file__" in globals() else os.path.abspath(sys.argv[0])
    python_candidates = []

    try:
        exe_dir = os.path.normpath(oDesktop.GetExeDir())
        # Typical AEDT path: ...\v261\AnsysEM\Win64
        ansysem_dir = os.path.dirname(exe_dir)
        version_dir = os.path.dirname(ansysem_dir)

        python_candidates.append(os.path.join(
            ansysem_dir, "commonfiles", "CPython", "3_10", "winx64", "Release", "python", "python.exe"
        ))
        # Fallback when exe_dir depth is different.
        python_candidates.append(os.path.join(
            version_dir, "AnsysEM", "commonfiles", "CPython", "3_10", "winx64", "Release", "python", "python.exe"
        ))
    except Exception:
        python_candidates = []

    os.environ["AEDT_Specific_Grpc_Port"] = str(oDesktop.GetGrpcServerPort())
    for py_exe in python_candidates:
        if os.path.exists(py_exe):
            env = os.environ.copy()
            env[relaunched_flag] = "1"
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            subprocess.Popen(
                [py_exe, script_path], env=env, startupinfo=startupinfo
            )
            return True

    raise RuntimeError("Detected AEDT environment, but AEDT bundled python.exe was not found.")


"""Repository-root launcher that forwards to src/gds2edb/gdsImportWizard.py."""
# os.environ["AEDT_Specific_Grpc_Port"] = "50053"
def main():
    from pathlib import Path
    import runpy
    project_root = Path(__file__).resolve().parent
    entry = project_root / "src" / "gds2edb" / "gdsImportWizard.py"
    if not entry.exists():
        raise FileNotFoundError("Entry file not found: {entry}".format(entry=entry))

    runpy.run_path(str(entry), run_name="__main__")
    return 0


if __name__ == "__main__" and not _bootstrap_from_aedt():
    raise SystemExit(main())
