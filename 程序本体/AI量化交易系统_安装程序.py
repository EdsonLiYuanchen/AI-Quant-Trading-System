# -*- coding: utf-8 -*-
"""
AI 量化交易系统 · 安装程序（引导式解压安装）
=============================================
本安装程序随发布包一起分发：它是一个单文件 PyInstaller 可执行程序，
内部已嵌入完整的便携版（AI量化交易系统_便携版.zip，约 114 MB）。

双击运行后引导式完成：
  1. 校验嵌入的便携包完整性
  2. 选择安装目录（默认 当前目录；含空格/中文路径会给出警告）
  3. 解压便携包（增量、跳过已存在文件、完成后清理 .part 残留）
  4. 自动运行 启动.bat，完成安装

用法:
    AI量化交易系统_安装程序.exe            # 交互模式
    AI量化交易系统_安装程序.exe /auto      # 静默模式：安装到 exe 所在目录并自动启动
    AI量化交易系统_安装程序.exe /auto /dir=D:/AIQuant   # 静默并指定目录
    AI量化交易系统_安装程序.exe /extract   # 只解压，不自动启动程序
"""
import os
import stat
import sys
import time
import zipfile

# 控制台可能是 GBK，强制 stdout 用 UTF-8，避免中文/符号打印崩溃
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

APP = 'AI量化交易系统_便携版'
ZIP_NAME = 'AI量化交易系统_便携版.zip'
LAUNCHER = os.path.join(APP, '启动.bat')
KEY_FILES = [
    os.path.join(APP, '启动.bat'),
    os.path.join(APP, '使用说明.txt'),
    os.path.join(APP, 'app', 'AI_Trading_System.exe'),
]
# 关键依赖抽样检查（_internal 下的核心库），防止解压中途损坏
INTERNAL_SAMPLE = [
    os.path.join(APP, 'app', '_internal', 'pandas'),
    os.path.join(APP, 'app', '_internal', 'sklearn'),
    os.path.join(APP, 'app', '_internal', 'akshare'),
]


def _zip_name():
    """定位内嵌的便携包：PyInstaller 打包模式下在 _MEIPASS/portable 里，
    开发模式下在脚本目录。"""
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        p = os.path.join(meipass, 'portable', ZIP_NAME)
        if os.path.isfile(p):
            return p
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ZIP_NAME)
    if os.path.isfile(p):
        return p
    raise SystemExit('[错误] 找不到内嵌便携包 %s，安装包可能损坏' % ZIP_NAME)


def _progress_cb(tz):
    member = tz.member
    frac = tz.n / float(max(tz.total, 1))
    bar = int(frac * 40)
    sys.stdout.write('\r[%s%s] %3.0f%%  %s' % ('#' * bar, '.' * (40 - bar), frac * 100, os.path.basename(member)))
    sys.stdout.flush()


def verify_zip(zpath):
    """校验内嵌 zip 完整性。"""
    with zipfile.ZipFile(zpath) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit('[错误] 内嵌便携包损坏（坏文件: %s），请重新下载' % bad)
        names = zf.namelist()
    need = [os.path.join(APP, k).replace('\\', '/') for k in
            ('启动.bat', '使用说明.txt', os.path.join('app', 'AI_Trading_System.exe'))]
    missing = [n for n in need if n not in names]
    if missing:
        raise SystemExit('[错误] 内嵌便携包缺少关键文件: %s' % ', '.join(missing))
    print('  便携包校验通过（%d 个文件）' % len(names))


def is_bad_path(p):
    """安装路径含空格/中文时给出警告。"""
    return any(c.isspace() for c in p) or any(ord(c) > 127 for c in p)


def extract(zpath, out_dir):
    """增量解压：跳过已存在且大小一致的文件；写 .part 再改名，避免残留半成品。"""
    total = 0
    skipped = 0
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            target = os.path.join(out_dir, *info.filename.split('/'))
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if os.path.isfile(target) and os.path.getsize(target) == info.file_size:
                skipped += 1
                continue
            part = target + '.part'
            with zf.open(info) as src, open(part, 'wb') as dst:
                while True:
                    buf = src.read(1024 * 256)
                    if not buf:
                        break
                    dst.write(buf)
            # 保留 zip 里的可执行位（bat 等）
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                os.chmod(part, stat.S_IMODE(mode) | stat.S_IWRITE)
            os.replace(part, target)
            total += 1
        # 清理历史残留的 .part
        for root, _dirs, files in os.walk(out_dir):
            for f in files:
                if f.endswith('.part'):
                    os.remove(os.path.join(root, f))
    return total, skipped


def check_installer(install_dir):
    problems = []
    for k in KEY_FILES:
        p = os.path.join(install_dir, *k.split(os.sep))
        if not os.path.isfile(p):
            problems.append('缺少: %s' % k.replace('\\', '/'))
    for k in INTERNAL_SAMPLE:
        p = os.path.join(install_dir, *k.split(os.sep))
        if not os.path.isdir(p):
            problems.append('缺少目录: %s' % k.replace('\\', '/'))
    return problems


def launch(install_dir):
    bat = os.path.join(install_dir, APP, '启动.bat')
    if not os.path.isfile(bat):
        print('[错误] 找不到启动脚本 %s' % bat)
        return False
    # 复制并运行，避免双击 bat 时窗口路径问题；用 explorer 风格启动
    import subprocess
    subprocess.Popen([bat], cwd=os.path.join(install_dir, APP), shell=True)
    return True


def parse_args(argv):
    opts = {'auto': False, 'extract_only': False, 'dir': None}
    for a in argv:
        if a == '/auto':
            opts['auto'] = True
        elif a == '/extract':
            opts['extract_only'] = True
        elif a.startswith('/dir='):
            opts['dir'] = a[5:].strip().strip('"')
    return opts


def default_dir(opts):
    if opts['dir']:
        return os.path.abspath(opts['dir'])
    if opts['auto']:
        # 静默模式：装到 exe 所在目录（打包模式即 _MEIPASS，其下 portable 存有便携包）
        base = getattr(sys, '_MEIPASS', None)
        if not base:
            base = os.path.dirname(os.path.abspath(sys.argv[0]))
        return base
    return os.getcwd()
def main():
    opts = parse_args(sys.argv[1:])
    zpath = _zip_name()

    print('=' * 58)
    print('  AI 量化交易系统 v2.0.0 · 安装程序')
    print('=' * 58)

    if not opts['auto']:
        print('\n[1/3] 正在校验安装包...')
    else:
        print('正在校验安装包...')
    verify_zip(zpath)

    out_dir = default_dir(opts)
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, APP)

    if not opts['auto'] and not opts['extract_only']:
        print('当前交互模式已切换为自动安装（extract_only 标志: %s）' % opts['extract_only'])
        print('\n[2/3] 安装目录: %s' % out_dir)
        if is_bad_path(out_dir):
            print('  [!] 路径包含空格或中文字符，部分旧版运行库可能异常，建议安装到如 C:/AIQuant')
        try:
            choice = input('回车直接安装 / 输入新路径 / 输入 q 取消: ').strip()
            if choice.lower() == 'q':
                print('已取消安装')
                return 0
            if choice:
                out_dir = os.path.abspath(choice.strip('"'))
                os.makedirs(out_dir, exist_ok=True)
                target = os.path.join(out_dir, APP)
                if is_bad_path(out_dir):
                    print('  [!] 新路径同样包含空格或中文字符，请知悉')
            print('\n[3/3] 开始解压...')
        except (EOFError, KeyboardInterrupt):
            print('\n已取消安装')
            return 0
    else:
        print('安装到: %s' % out_dir)
        print('开始解压...')

    t0 = time.time()
    new, skipped = extract(zpath, out_dir)
    dt = time.time() - t0
    print('\n解压完成: 新写 %d 个文件，跳过 %d 个已存在文件（%.1f 秒）' % (new, skipped, dt))

    problems = check_installer(out_dir)
    if problems:
        print('\n[警告] 安装目录不完整:')
        for p in problems:
            print('  - ' + p)

    if opts['extract_only']:
        print('\n解压完成，未自动启动（/extract 模式）。')
        print('手动启动: 双击 %s' % os.path.join(out_dir, APP, '启动.bat'))
        return 0

    print('\n正在启动 AI 量化交易系统...')
    if launch(out_dir):
        print('=' * 58)
        print('  [OK] 安装完成！程序已启动。')
        print('  安装位置: %s' % out_dir)
        print('  启动程序: 双击 %s' % os.path.join(out_dir, APP, '启动.bat'))
        print('  卸载方法: 直接删除 %s 文件夹' % os.path.join(out_dir, APP))
        print('=' * 58)
    else:
        print('[提示] 启动失败，请手动双击 %s' % os.path.join(out_dir, APP, '启动.bat'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
