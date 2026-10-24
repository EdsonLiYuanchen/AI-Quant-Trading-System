import os
import glob

# 使用绝对路径
data_dirs = {
    "1": r"C:\Users\Edson\code\.vscode\量化交易\金融数据",
    "2": r"C:\Users\Edson\code\.vscode\量化交易\分析数据"
}

def get_files_in_dir(directory):
    """获取目录中的所有文件"""
    if not os.path.exists(directory):
        return []
    return [f for f in glob.glob(os.path.join(directory, "*")) if os.path.isfile(f)]

def display_files(files):
    """显示文件列表"""
    if not files:
        print("  (该文件夹为空)")
        return
    
    for idx, f in enumerate(files, 1):
        file_size = os.path.getsize(f) / 1024  # KB
        print(f"  [{idx}] {os.path.basename(f)} ({file_size:.2f} KB)")

def delete_files(files_to_delete):
    """删除指定的文件"""
    if not files_to_delete:
        print("没有文件需要删除")
        return
    
    print("\n开始删除...")
    deleted = 0
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            print(f"  ✓ 已删除: {os.path.basename(file_path)}")
            deleted += 1
        except Exception as e:
            print(f"  ✗ 删除失败 {os.path.basename(file_path)}: {e}")
    
    print("\n" + "="*60)
    print(f"✓ 成功删除 {deleted}/{len(files_to_delete)} 个文件")
    print("="*60)

def main():
    print("="*60)
    print("清空数据文件夹")
    print("="*60)
    
    # 选择要操作的文件夹
    print("\n请选择要操作的文件夹:")
    print("  [1] 金融数据文件夹")
    print("  [2] 分析数据文件夹")
    print("  [3] 两者都操作")
    folder_choice = input("请输入选项 (1/2/3): ").strip()
    
    selected_dirs = []
    if folder_choice == "1":
        selected_dirs = [data_dirs["1"]]
    elif folder_choice == "2":
        selected_dirs = [data_dirs["2"]]
    elif folder_choice == "3":
        selected_dirs = [data_dirs["1"], data_dirs["2"]]
    else:
        print("[ERROR] 无效选项！")
        input("\n按回车键退出...")
        return
    
    # 检查文件夹并获取文件
    all_files = {}
    for directory in selected_dirs:
        if not os.path.exists(directory):
            print(f"[ERROR] 文件夹不存在: {directory}")
            continue
        files = get_files_in_dir(directory)
        all_files[directory] = files
    
    if not all_files:
        print("[ERROR] 所有选中的文件夹都不存在！")
        input("\n按回车键退出...")
        return
    
    # 显示所有文件
    total_files = 0
    print("\n" + "="*60)
    for directory, files in all_files.items():
        folder_name = "金融数据" if "金融数据" in directory else "分析数据"
        print(f"\n【{folder_name}】文件夹 ({len(files)} 个文件):")
        print(f"路径: {directory}")
        display_files(files)
        total_files += len(files)
    
    if total_files == 0:
        print("\n✓ 所有文件夹都是空的，无需清除")
        input("\n按回车键退出...")
        return
    
    # 选择删除模式
    print("\n" + "="*60)
    print("请选择删除模式:")
    print("  [1] 全部删除")
    print("  [2] 按序号选择删除")
    mode = input("请输入选项 (1/2): ").strip()
    
    if mode == "1":
        # 全部删除
        print("\n" + "="*60)
        confirm = input(f"确认删除所有 {total_files} 个文件吗？(输入 y 确认): ")
        
        if confirm.lower() == 'y':
            for directory, files in all_files.items():
                folder_name = "金融数据" if "金融数据" in directory else "分析数据"
                if files:
                    print(f"\n正在删除【{folder_name}】文件夹中的文件...")
                    delete_files(files)
        else:
            print("\n[ERROR] 取消删除操作")
    
    elif mode == "2":
        # 按序号选择删除
        # 创建全局文件索引
        file_index_map = {}
        current_idx = 1
        print("\n" + "="*60)
        print("文件列表（带全局序号）:")
        for directory, files in all_files.items():
            folder_name = "金融数据" if "金融数据" in directory else "分析数据"
            print(f"\n【{folder_name}】:")
            for f in files:
                file_size = os.path.getsize(f) / 1024  # KB
                print(f"  [{current_idx}] {os.path.basename(f)} ({file_size:.2f} KB)")
                file_index_map[current_idx] = f
                current_idx += 1
        
        print("\n" + "="*60)
        print("请输入要删除的文件序号（用逗号分隔，如: 1,3,5）")
        print("或输入范围（如: 1-5）")
        print("或混合使用（如: 1,3,5-8,10）")
        indices_input = input("序号: ").strip()
        
        # 解析输入的序号
        selected_indices = set()
        try:
            parts = indices_input.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    selected_indices.update(range(start, end + 1))
                else:
                    selected_indices.add(int(part))
            
            # 获取要删除的文件
            files_to_delete = [file_index_map[idx] for idx in sorted(selected_indices) if idx in file_index_map]
            
            if not files_to_delete:
                print("[ERROR] 没有选择有效的文件！")
            else:
                print(f"\n已选择 {len(files_to_delete)} 个文件:")
                for f in files_to_delete:
                    print(f"  - {os.path.basename(f)}")
                
                confirm = input("\n确认删除这些文件吗？(输入 y 确认): ")
                if confirm.lower() == 'y':
                    delete_files(files_to_delete)
                else:
                    print("\n[ERROR] 取消删除操作")
        
        except ValueError:
            print("[ERROR] 输入格式错误！")
    
    else:
        print("[ERROR] 无效选项！")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()
