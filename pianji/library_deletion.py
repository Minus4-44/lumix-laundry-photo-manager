"""Explicit whole-library recycling with a server-side preview and target check."""
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import sys
from contextlib import contextmanager,closing
from .cleanup import checked_path
from .domain import uid
from .fileops import identity
from .locking import LibraryLock
from .library import Library


def _sink_type():
    import winerror
    from win32com.shell import shellcon
    from win32com.server.exception import COMException
    from send2trash.win.IFileOperationProgressSink import FileOperationProgressSink
    class RecycleOnlySink(FileOperationProgressSink):
        def PreDeleteItem(self,flags,item):
            if not flags & shellcon.TSF_DELETE_RECYCLE_IF_POSSIBLE:
                raise COMException(desc='系统不能回收此目录，已取消；不会永久删除',scode=winerror.E_ABORT)
            return 0
    return RecycleOnlySink


def recycle_directory(path):
    if os.name!='nt':
        if sys.platform!='darwin':raise ValueError('删除照片库到系统回收站仅支持 Windows 与 macOS')
        from send2trash import send2trash
        # macOS: NSFileManager moves the bundle to ~/.Trash, still user-recoverable.
        send2trash(str(path))
        return
    import pythoncom
    from win32com.shell import shell,shellcon
    pythoncom.CoInitialize()
    try:
        operation=pythoncom.CoCreateInstance(shell.CLSID_FileOperation,None,pythoncom.CLSCTX_ALL,shell.IID_IFileOperation)
        operation.SetOperationFlags(shellcon.FOF_NOCONFIRMATION|shellcon.FOF_NOERRORUI|shellcon.FOF_SILENT|shellcon.FOFX_EARLYFAILURE|0x20000000|0x00080000)
        item=shell.SHCreateItemFromParsingName(str(path),None,shell.IID_IShellItem)
        sink=pythoncom.WrapObject(_sink_type()(),shell.IID_IFileOperationProgressSink)
        operation.DeleteItem(item,sink);result=operation.PerformOperations()
        if result or operation.GetAnyOperationsAborted():raise OSError('系统回收已取消或失败，未改为永久删除')
    finally:pythoncom.CoUninitialize()


def _root(bridge,path):
    raw=Path(os.path.abspath(path));root=raw.resolve()
    known=bridge._settings.get('recent_libraries',[])+([bridge._settings['library']] if bridge._settings.get('library') else [])
    if not any(Path(p).resolve()==root for p in known):raise ValueError('只能删除已打开过的照片库')
    if root==root.parent or root==Path.home().resolve():raise ValueError('不能删除磁盘根目录或用户目录')
    if bridge._config.resolve().is_relative_to(root) or Path(__file__).resolve().is_relative_to(root):raise ValueError('照片库范围包含应用或设置目录，不能整库删除')
    checked_path(root.parent,raw)
    if any(root.is_relative_to(p) or p.is_relative_to(root) for p in bridge._grants.values()):raise ValueError('照片库与读取来源重叠，不能删除')
    if any(Path(p).resolve()!=root and Path(p).resolve().is_relative_to(root) for p in known):raise ValueError('此目录包含其他照片库，不能整库删除')
    if not (root/'.片集'/'catalog.sqlite3').is_file():raise ValueError('照片库不存在或元数据缺失')
    checked_path(root,root/'.片集'/'catalog.sqlite3')
    return root


@contextmanager
def _lease(bridge,root):
    current=bridge._lib if bridge._lib and bridge._lib.root==root else None
    if current:
        with current.lock,current.journal.access:
            current._ready();yield current
    else:
        lock=LibraryLock(root)
        try:yield None
        finally:lock.close()


def _snapshot(root):
    files=[];total=0;fingerprint=[]
    def unreadable(error):raise error
    for parent,dirs,names in os.walk(root,followlinks=False,onerror=unreadable):
        for name in dirs:checked_path(root,Path(parent)/name)
        for name in names:
            path=checked_path(root,Path(parent)/name);stat=path.stat();relative=path.relative_to(root)
            files.append(relative.as_posix());total+=stat.st_size
            if '.片集' not in relative.parts:fingerprint.append((relative.as_posix(),stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns))
    token_hash=hashlib.sha256(json.dumps(sorted(fingerprint)).encode()).hexdigest()
    return {'file_count':len(files),'bytes':total,'fingerprint':token_hash}


def inspect(bridge,path):
    bridge._check_switch();root=_root(bridge,path)
    with _lease(bridge,root):
        snapshot=_snapshot(root)
        with closing(sqlite3.connect((root/'.片集/catalog.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
            count=db.execute('SELECT count(*) FROM photos').fetchone()[0]
            if db.execute("SELECT count(*) FROM operations WHERE phase!='committed'").fetchone()[0]:raise ValueError('有文件操作待恢复，请先打开照片库处理')
        plan={**snapshot,'path':str(root),'name':root.name,'photo_count':count,'identity':identity(root),'database_identity':identity(root/'.片集/catalog.sqlite3')}
    token=uid();bridge._library_deletions[token]=plan
    return {k:v for k,v in {**plan,'token':token}.items() if k not in ('identity','database_identity','fingerprint')}


def execute(bridge,token,name):
    bridge._check_switch();plan=bridge._library_deletions.get(token)
    if not plan or name!=plan['name']:raise ValueError('请输入照片库名称确认删除')
    root=_root(bridge,plan['path']);was_current=bool(bridge._lib and bridge._lib.root==root)
    with _lease(bridge,root) as current:
        if identity(root)!=plan['identity'] or identity(root/'.片集/catalog.sqlite3')!=plan['database_identity']:raise ValueError('照片库目录已被替换，请重新选择')
        if _snapshot(root)['fingerprint']!=plan['fingerprint']:raise ValueError('照片库内容已变化，请返回重新确认')
        if current:current.close();bridge._lib=None
    try:
        recycle_directory(root)
        if root.exists():raise OSError('系统回收未完成，照片库目录仍在原位置')
    except Exception:
        if was_current and root.is_dir():bridge._lib=Library(root)
        raise
    bridge._settings['recent_libraries']=[p for p in bridge._settings.get('recent_libraries',[]) if Path(p).resolve()!=root]
    if bridge._settings.get('library') and Path(bridge._settings['library']).resolve()==root:bridge._settings.pop('library')
    bridge._library_deletions.pop(token,None);bridge._persist()
    return {'deleted_path':str(root),'recycled':True}
