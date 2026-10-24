import os

# 要删除的文件列表
files_to_delete = [
    "run_app.bat",
    "启动应用程序.bat", 
    "启动GUI.bat",
    "install_ollama.bat",
    "README_AI增强版.md",
    "requirements_ai.txt",
    "requirements_多模型.txt",
    "使用教程.txt",
    "快速启动指南.txt",
    "功能更新日志.md",
    "Bug修复日志.md",
    "项目文件说明.md",
    "AI模型使用说明.md",
    "快速开始.md",
    "打包为exe.py",
    "cleanup_files.py"  # 删除自身
]

current_dir = os.path.dirname(__file__)
print("开始清理文件...")

for filename in files_to_delete:
    filepath = os.path.join(current_dir, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"✓ 已删除: {filename}")
        except Exception as e:
            print(f"✗ 删除失败 {filename}: {e}")
    else:
        print(f"- 文件不存在: {filename}")

print("\n清理完成！保留的核心文件：")
core_files = [
    "AI量化交易系统GUI.py",
    "start.bat",
    "start_gui.py", 
    "爬取金融数据.py",
    "多模型AI量化交易.py",
    "分析数据.py",
    "清空金融数据.py",
    "requirements.txt",
    "README.md",
    "使用说明.md",
    "安装依赖.bat",
    "应用程序部署指南.md",
    "ai_strategy_model.pkl"
]

for file in core_files:
    if os.path.exists(os.path.join(current_dir, file)):
        print(f"✓ {file}")

print("\n现在可以直接双击 start.bat 启动应用程序！")