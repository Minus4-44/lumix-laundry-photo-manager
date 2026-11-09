from pathlib import Path
from datetime import datetime
import os
import plistlib
import subprocess
import sys


def _bundle_executable(bundle):
    """Resolve the process binary inside a macOS .app bundle."""
    try:
        name=plistlib.loads((bundle/'Contents'/'Info.plist').read_bytes()).get('CFBundleExecutable')
    except (OSError,ValueError): name=None
    if name:
        candidate=bundle/'Contents'/'MacOS'/name
        if candidate.is_file(): return candidate
    macos=bundle/'Contents'/'MacOS'
    entries=sorted(p for p in macos.iterdir() if p.is_file()) if macos.is_dir() else []
    return entries[0] if entries else None


def detect_executable(root=Path('/Applications')):
    """Best-effort lookup of an installed Photoshop on macOS."""
    root=Path(root)
    if sys.platform!='darwin' or not root.is_dir(): return None
    for bundle in sorted(root.glob('Adobe Photoshop*.app')):
        binary=_bundle_executable(bundle)
        if binary: return binary.resolve()
    return None


def validate_executable(path):
    exe=Path(path).expanduser()
    if not exe.is_absolute(): raise ValueError('请填写程序的完整路径')
    if sys.platform=='darwin':
        if exe.is_dir() and exe.suffix.lower()=='.app':
            binary=_bundle_executable(exe)
            if not binary: raise ValueError('此应用程序包中找不到可执行文件')
            return binary.resolve()
        if exe.is_file() and os.access(exe,os.X_OK): return exe.resolve()
        raise ValueError('请选择有效的 Photoshop 应用程序（.app）')
    if not exe.is_file() or exe.suffix.lower()!='.exe': raise ValueError('请选择有效的Photoshop.exe程序路径')
    return exe.resolve()

def open_in_photoshop(lib,photo_id,format,executable,launcher=subprocess.Popen):
    exe=validate_executable(executable)
    if format not in ('jpeg','raw'): raise ValueError('请选择JPEG或RAW')
    with lib.lock:
        p=lib.catalog.photo(photo_id)
        asset=next((a for a in p['assets'] if a['kind']==format),None)
        if not asset: raise ValueError('此照片未导入'+('RAW' if format=='raw' else 'JPEG'))
        file=Path(asset['path'])
        if not file.is_file(): raise ValueError('照片文件缺失，请重新定位文件')
        launcher([str(exe),str(file)],shell=False)
        with lib.catalog.connect() as db: db.execute('UPDATE photos SET opened_at=? WHERE id=?',(datetime.now().isoformat(),photo_id))
    return {'requested':True,'format':format}
