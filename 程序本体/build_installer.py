# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 一键打包安装程序
输出: dist/AI量化交易系统_安装程序.exe
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

APP_NAME = "AI量化交易系统"
APP_EXEC = "AI_Trading_System.exe"
VERSION = "1.0"
INSTALL_SUBDIR = "AI量化交易系统"

EXCLUDE_PACKAGES = [
    "torch", "torchvision", "torchaudio",
    "cv2", "opencv",
    "transformers", "tokenizers",
    "librosa", "soundfile", "_soundfile_data",
    "numba", "llvmlite",
    "imageio_ffmpeg",
    "sentencepiece",
    "easytrader", "pywinauto", "easyutils",
    "pythonnet", "clr", "comtypes",
    "proxy_tools",
    "flask", "werkzeug",
]

HIDDEN_IMPORTS = [
    "tkinter", "tkinter.ttk", "tkinter.scrolledtext",
    "tkinter.messagebox", "tkinter.filedialog",
    "智能数据查询", "长线选股", "自选股",
    "同花顺账户导入", "增强版数据爬取", "爬取金融数据",
    "多模型AI量化交易", "分析数据", "持仓管理",
    "实时行情增强", "tonghuashun_realtime",
    "database_manager", "enhanced_database_manager",
    "stream_guard", "ai_strategy",
    "AI量化交易系统Web", "AI量化交易系统GUI",
    "headless_server", "quant_metrics",
    "全球证券接口预留",
    "mplfinance", "matplotlib",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_agg",
    "sklearn", "sklearn.ensemble", "sklearn.model_selection",
    "sklearn.metrics", "scipy", "openpyxl",
    "numpy", "pandas", "akshare",
    "requests", "bs4", "lxml",
    "sqlalchemy", "mysql", "pymysql",
    "webview", "bottle",
]


def run_pyinstaller_build(app_dir, dist_dir, build_dir):
    print("[1/4] 清理旧构建...")
    for d in [build_dir, dist_dir]:
        p = os.path.join(d, "AI_Trading_System")
        if os.path.exists(p):
            shutil.rmtree(p, ignore_errors=True)
        p = os.path.join(d, "AI_Trading_System.exe")
        if os.path.exists(p):
            try:
                os.remove(p)
            except PermissionError:
                pass
        for sub in os.listdir(d) if os.path.exists(d) else []:
            full = os.path.join(d, sub)
            if os.path.isdir(full) and sub.startswith("AI_"):
                try:
                    shutil.rmtree(full, ignore_errors=True)
                except Exception:
                    pass

    print("[2/4] 运行 PyInstaller 构建应用...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm", "--onedir",
        "--name=" + APP_EXEC,
        "--nowindowed",
        "--add-data=data_cache;data_cache",
        "--add-data=smart_cache;smart_cache",
        "--add-data=portfolio.pkl;.",
        "--add-data=portfolio.json;.",
        "--add-data=watchlist.json;.",
        "--add-data=fund_portfolio.json;.",
        "--add-data=fund_portfolio.pkl;.",
        "--add-data=fund_records.json;.",
        "--add-data=web;web",
    ]
    for m in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import=" + m])
    for exc in EXCLUDE_PACKAGES:
        cmd.extend(["--exclude-module=" + exc])
    cmd.append("--noupx")
    cmd.append("launcher.py")

    result = subprocess.run(
        cmd, cwd=app_dir,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        print("PyInstaller 构建失败!")
        print("STDERR (最后1500字符):")
        print(result.stderr[-1500:])
        raise RuntimeError("PyInstaller 构建失败 (code {})".format(result.returncode))
    print("  PyInstaller 构建完成。")


def clean_dist(dist_dir):
    """清理 _internal 中的重型依赖"""
    app_folder = os.path.join(dist_dir, "AI_Trading_System")
    internal_dir = os.path.join(app_folder, "_internal")
    if not os.path.exists(internal_dir):
        print("  [clean] _internal 不存在，跳过清理")
        return
    removed = 0
    for name in os.listdir(internal_dir):
        for exc in EXCLUDE_PACKAGES:
            if name.lower().startswith(exc.lower()):
                full = os.path.join(internal_dir, name)
                if os.path.isdir(full):
                    sz = sum(
                        f.stat().st_size
                        for f in Path(full).rglob("*") if f.is_file()
                    )
                    shutil.rmtree(full, ignore_errors=True)
                    print("  已移除: {} ({:.1f} MB)".format(name, sz / 1024 / 1024))
                    removed += 1
                break
    print("  清理完成，移除了 {} 个目录。".format(removed))


def ensure_webview_runtime(dist_dir):
    """确保 WebView2 运行时安装程序在 dist 中"""
    runtime_src = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "dist", "MicrosoftEdgeWebViewRuntimeSetup.exe"
    )
    runtime_dst = os.path.join(dist_dir, "MicrosoftEdgeWebViewRuntimeSetup.exe")
    if not os.path.exists(runtime_dst) and os.path.exists(runtime_src):
        shutil.copy2(runtime_src, runtime_dst)
        print("  WebView2 运行时安装程序已准备 ({:.1f} MB)".format(
            os.path.getsize(runtime_dst) / 1024 / 1024
        ))
    elif not os.path.exists(runtime_dst):
        print("  警告: WebView2 运行时安装程序未找到，将依赖系统自带")


def build_installer_exe(output_dir, dist_dir):
    src_dir = os.path.join(output_dir, "setup_source")
    os.makedirs(src_dir, exist_ok=True)

    # 复制安装程序源文件
    installer_src = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "installer_source"
    )
    for fname in ["install.py", "uninstall.ps1"]:
        src = os.path.join(installer_src, fname)
        dst = os.path.join(src_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print("  已复制: {}".format(fname))
    # 同时复制到 output_dir 根目录（PyInstaller --add-data 从 cwd 找文件）
    for fname in ["install.py", "uninstall.ps1"]:
        src = os.path.join(installer_src, fname)
        dst = os.path.join(output_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)


    # 复制 _internal 文件夹到输出目录（PyInstaller 需要它在这里）
    internal_src = os.path.join(dist_dir, "AI_Trading_System.exe", "_internal")
    internal_dst = os.path.join(output_dir, "_internal")
    if os.path.exists(internal_src):
        if os.path.exists(internal_dst):
            shutil.rmtree(internal_dst, ignore_errors=True)
        shutil.copytree(internal_src, internal_dst)
        from pathlib import Path as _P
        sz = sum(f.stat().st_size for f in _P(internal_src).rglob("*") if f.is_file())
        print("  已复制 _internal ({:.1f} MB)".format(sz / 1024 / 1024))
    else:
        print("  警告: _internal 不存在于 {}".format(internal_src))

    # 确保 WebView2 运行时在 output_dir 中
    webview_src = os.path.join(dist_dir, "MicrosoftEdgeWebViewRuntimeSetup.exe")
    webview_dst = os.path.join(output_dir, "MicrosoftEdgeWebViewRuntimeSetup.exe")
    if os.path.exists(webview_src) and not os.path.exists(webview_dst):
        shutil.copy2(webview_src, webview_dst)
        print("  已复制 WebView2 运行时安装程序")

    print("[3/4] 打包安装程序...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm", "--onefile",
        "--nowindowed", "--windowed",
        "--name=" + APP_NAME + "_安装程序",
        "--add-data=_internal;.",
        "--add-data=install.py;.",
        "--add-data=uninstall.ps1;.",
        "--add-data=MicrosoftEdgeWebViewRuntimeSetup.exe;.",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--exclude-module=win32com",
        os.path.join(src_dir, "install.py"),
    ]
    result = subprocess.run(
        cmd, cwd=output_dir,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        print("安装程序打包失败:")
        print(result.stdout[-1000:])
        print(result.stderr[-1000:])
        return False
    src_exe = os.path.join(output_dir, "dist", APP_NAME + "_安装程序.exe")
    dst_exe = os.path.join(dist_dir, APP_NAME + "_安装程序.exe")
    if os.path.exists(src_exe):
        shutil.move(src_exe, dst_exe)
        sz = os.path.getsize(dst_exe)
        print("  安装程序: {} ({:.1f} MB)".format(dst_exe, sz / 1024 / 1024))
    return True


def main():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(app_dir, "dist")
    build_dir = os.path.join(app_dir, "build_installer")
    output_dir = os.path.join(app_dir, "_installer_temp")
    os.makedirs(dist_dir, exist_ok=True)

    run_pyinstaller_build(app_dir, dist_dir, build_dir)

    print("[3/4] 清理不必要的依赖...")
    clean_dist(dist_dir)

    ensure_webview_runtime(dist_dir)

    os.makedirs(output_dir, exist_ok=True)
    if not build_installer_exe(output_dir, dist_dir):
        print("安装程序创建失败")
        sys.exit(1)

    shutil.rmtree(output_dir, ignore_errors=True)
    shutil.rmtree(build_dir, ignore_errors=True)

    installer = os.path.join(dist_dir, APP_NAME + "_安装程序.exe")
    app_folder = os.path.join(dist_dir, "AI_Trading_System")
    print("\n[完成] 输出目录: " + dist_dir)
    if os.path.exists(installer):
        print("  - 安装程序: {}".format(installer))
        print("    大小: {:.1f} MB".format(os.path.getsize(installer) / 1024 / 1024))
    if os.path.exists(app_folder):
        total = sum(
            f.stat().st_size for f in Path(app_folder).rglob("*") if f.is_file()
        )
        print("  - 应用目录: {}".format(app_folder))
        print("    大小: {:.1f} MB".format(total / 1024 / 1024))


if __name__ == "__main__":
    main()
