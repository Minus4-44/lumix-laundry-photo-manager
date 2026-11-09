from pathlib import Path
import os
from PyInstaller.utils.hooks import collect_data_files

project = Path(SPECPATH).parent
datas=[(str(project/'pianji'/'ui'),'pianji/ui'),(str(project/'models'),'models'),(str(project/'licenses'),'licenses'),(str(project/'THIRD-PARTY-NOTICES.md'),'.')]
datas += collect_data_files('webview')
datas += collect_data_files('rawpy')
a=Analysis([str(project/'run.py')],pathex=[str(project)],binaries=[],datas=datas,hiddenimports=['webview.platforms.cocoa','pianji.selftest'],hookspath=[],hooksconfig={},runtime_hooks=[],excludes=['tkinter','pytest','PyInstaller','pywin32','pythonnet','clr','win32com'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='LUMIX Photo Manager',icon=str(project/'pianji/ui/lumix.icns'),debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,disable_windowed_traceback=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name=os.environ.get('PIANJI_BUNDLE_NAME','LUMIX Photo Manager'))
app=BUNDLE(coll,name=os.environ.get('PIANJI_APP_NAME','LUMIX Photo Manager.app'),icon=str(project/'pianji/ui/lumix.icns'),bundle_identifier='io.github.edison0315.lumix-photo-manager',info_plist={
    'CFBundleName':'LUMIX Photo Manager',
    'CFBundleDisplayName':'LUMIX 洗衣机管理器',
    'CFBundleShortVersionString':'0.12.1',
    'CFBundleVersion':'0.12.1',
    'CFBundleDevelopmentRegion':'zh_CN',
    'NSHighResolutionCapable':True,
    'NSHumanReadableCopyright':'由 Edison-0315 制作；与 Panasonic / LUMIX 无官方隶属关系。',
    'LSMinimumSystemVersion':'11.0',
    'LSApplicationCategoryType':'public.app-category.photography',
    'NSRequiresAquaSystemAppearance':False,
})
