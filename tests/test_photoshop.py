from pathlib import Path
import plistlib
import sys
import pytest
from PIL import Image
from pianji.library import Library
from pianji.discovery import scan_source
from pianji.photoshop import open_in_photoshop, validate_executable

@pytest.mark.skipif(sys.platform!='win32',reason='Photoshop.exe 校验仅适用于 Windows')
def test_spaces_and_chinese_are_single_argument_and_open_does_not_mark_edited(tmp_path):
    src=tmp_path/'SD'; src.mkdir(); Image.new('RGB',(20,20)).save(src/'模特 一.jpg')
    lib=Library(tmp_path/'库'); lib.import_groups(scan_source(src),'活动')
    exe=tmp_path/'Adobe Photoshop'/'Photoshop.exe'; exe.parent.mkdir(); exe.write_bytes(b'fake launcher')
    calls=[]
    p=lib.catalog.photos()[0]
    open_in_photoshop(lib,p['id'],'jpeg',str(exe),launcher=lambda args,**kwargs:calls.append((args,kwargs)))
    assert calls==[([str(exe),p['assets'][0]['path']],{'shell':False})]
    assert not lib.catalog.photo(p['id'])['edited']
    with pytest.raises(ValueError,match='RAW'): open_in_photoshop(lib,p['id'],'raw',str(exe),launcher=lambda *a,**kw:None)

@pytest.mark.skipif(sys.platform!='darwin',reason='macOS 应用包路径仅适用于 macOS')
def test_macos_app_bundle_resolves_bundle_executable(tmp_path):
    app=tmp_path/'Adobe Photoshop 2026.app'; macos=app/'Contents'/'MacOS'; macos.mkdir(parents=True)
    (app/'Contents'/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'Adobe Photoshop 2026'}))
    exe=macos/'Adobe Photoshop 2026'; exe.write_bytes(b'fake launcher'); exe.chmod(0o755)
    assert validate_executable(str(app))==exe.resolve()
    assert validate_executable(str(exe))==exe.resolve()
    with pytest.raises(ValueError,match='Photoshop'): validate_executable(str(tmp_path))
