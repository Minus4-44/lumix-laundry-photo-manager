from pathlib import Path
import shutil
import sys
import pytest
from PIL import Image
from pianji.library import Library
from pianji.discovery import scan_source
from pianji.bridge import Bridge


@pytest.fixture
def fixture(tmp_path):
    source=tmp_path/'SD';source.mkdir();Image.new('RGB',(30,30),'red').save(source/'a.jpg')
    (source/'a.rw2').write_bytes(b'owned RAW fixture');(source/'a.xmp').write_text('xmp')
    lib=Library(tmp_path/'library');lib.import_groups(scan_source(source),'event')
    yield source,lib
    lib.close()


def test_delete_person_and_activity_remove_empty_local_folders_and_restore(fixture):
    source,lib=fixture;photo=lib.catalog.photos()[0];act=photo['activity_id'];person=lib.catalog.add_person(act,'Alice')
    lib.set_person([photo['id']],person['id']);folder=lib.root/'event'/'Alice';assert folder.is_dir()
    assert not lib.delete_people([person['id']])['errors'];assert not folder.exists()
    assert not lib.delete_activity(act)['errors'];assert not (lib.root/'event').exists()
    assert not lib.restore_photos([photo['id']])['errors'];assert (lib.root/'event'/'待分类').is_dir()
    assert all(p.is_file() for p in source.iterdir())


def test_permanent_deletion_removes_trash_asset_and_photo_directories(fixture):
    _,lib=fixture;p=lib.catalog.photos()[0];lib.set_finished([p['id']],True);lib.set_finished([p['id']],False)
    lib.trash_photos([p['id']]);trash=lib.catalog.meta/'回收站'/p['id'];assert trash.is_dir()
    assert not lib.purge_trash([p['id']])['errors'];assert not trash.exists()
    assert lib.catalog.meta.is_dir() and lib.root.is_dir()


def test_cleanup_keeps_unknown_files_and_never_touches_outside(fixture,tmp_path):
    from pianji.cleanup import prune_empty
    _,lib=fixture;foreign=lib.root/'event'/'foreign.txt';foreign.write_text('foreign')
    outside=tmp_path/'outside';outside.mkdir();(outside/'empty').mkdir()
    lib.delete_activity(lib.catalog.activities()[0]['id']);assert foreign.read_text()=='foreign'
    result=prune_empty(lib.root,[outside/'empty',lib.root/'event',lib.catalog.meta,lib.root])
    assert outside.is_dir() and (outside/'empty').is_dir() and lib.root.is_dir() and lib.catalog.meta.is_dir()
    assert foreign.exists() and not result['removed']


def test_historical_cleanup_uses_journal_paths_only(fixture):
    from pianji.cleanup import cleanup_library
    _,lib=fixture;p=lib.catalog.photos()[0];old=next(a for a in p['assets'] if a['kind']=='jpeg');old_parent=Path(old['path']).parent
    lib.set_edited([p['id']],True);old_parent.mkdir(parents=True,exist_ok=True)
    unrelated=lib.root/'unmanaged-empty';unrelated.mkdir()
    result=cleanup_library(lib);assert not result['errors'] and not old_parent.exists()
    assert unrelated.is_dir() and all(Path(a['path']).is_file() for a in lib.catalog.photo(p['id'])['assets'])


def test_cleanup_does_not_follow_directory_junction(fixture,tmp_path):
    import os
    from pianji.cleanup import prune_empty
    _,lib=fixture;target=tmp_path/'outside';target.mkdir();(target/'empty').mkdir();link=lib.root/'link'
    if os.name=='nt':
        import subprocess
        subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],check=True,capture_output=True)
    else:link.symlink_to(target,target_is_directory=True)
    try:
        prune_empty(lib.root,[link/'empty',link]);assert (target/'empty').is_dir() and link.exists()
    finally:link.rmdir() if os.name=='nt' else link.unlink()


@pytest.fixture
def bridge_fixture(tmp_path):
    source=tmp_path/'SD';source.mkdir();Image.new('RGB',(30,30),'red').save(source/'a.jpg')
    bridge=Bridge(tmp_path/'config',dialog=lambda kind:str(tmp_path/'library'));assert bridge.choose_library()['ok']
    bridge._lib.import_groups(scan_source(source),'event')
    yield source,bridge
    bridge._close()


def test_delete_library_requires_confirmed_known_target_and_moves_actual_directory(bridge_fixture,tmp_path,monkeypatch):
    from pianji import library_deletion
    source,bridge=bridge_fixture;root=bridge._lib.root;foreign=root/'also-in-library.txt';foreign.write_text('included in whole-library deletion')
    original=(source/'a.jpg').read_bytes();calls=[];binroot=tmp_path/'test-bin'
    def recycle(path):calls.append(path);path.rename(binroot)
    monkeypatch.setattr(library_deletion,'recycle_directory',recycle)
    assert not bridge.inspect_library_delete(str(source))['ok']
    plan=bridge.inspect_library_delete(str(root))['data'];assert plan['photo_count']==1 and plan['bytes']>0
    assert not bridge.delete_library(plan['token'],'wrong')['ok'] and not calls
    assert bridge.delete_library(plan['token'],root.name)['ok']
    assert not root.exists() and (binroot/'also-in-library.txt').read_text().startswith('included')
    assert not bridge.get_settings()['data']['library_available'] and not bridge.list_libraries()['data']
    assert (source/'a.jpg').read_bytes()==original


def test_delete_library_failure_reopens_current_and_preserves_recent(bridge_fixture,monkeypatch):
    from pianji import library_deletion
    _,bridge=bridge_fixture;root=bridge._lib.root;plan=bridge.inspect_library_delete(str(root))['data']
    monkeypatch.setattr(library_deletion,'recycle_directory',lambda p:(_ for _ in ()).throw(PermissionError('busy')))
    assert not bridge.delete_library(plan['token'],root.name)['ok']
    assert bridge._lib and bridge._lib.catalog.photos() and bridge.list_libraries()['data'][0]['current']


def test_delete_library_rejects_replaced_target_and_changed_photos(bridge_fixture,tmp_path,monkeypatch):
    from pianji import library_deletion
    _,bridge=bridge_fixture;root=bridge._lib.root;plan=bridge.inspect_library_delete(str(root))['data'];calls=[]
    monkeypatch.setattr(library_deletion,'recycle_directory',lambda p:calls.append(p))
    (root/'new-file.txt').write_text('added after confirmation preview')
    assert not bridge.delete_library(plan['token'],root.name)['ok'] and not calls
    plan=bridge.inspect_library_delete(str(root))['data'];bridge._lib.close();bridge._lib=None
    root.rename(tmp_path/'preserved-old-library');root.mkdir();(root/'.片集').mkdir();(root/'.片集'/'catalog.sqlite3').write_text('replacement')
    assert not bridge.delete_library(plan['token'],root.name)['ok'] and not calls


def test_delete_noncurrent_library_preserves_current_library(bridge_fixture,tmp_path,monkeypatch):
    from pianji import library_deletion
    _,bridge=bridge_fixture;old=bridge._lib.root;current=tmp_path/'second';bridge._switch_library(current)
    plan=bridge.inspect_library_delete(str(old))['data']
    monkeypatch.setattr(library_deletion,'recycle_directory',lambda p:p.rename(tmp_path/'fake-bin'))
    assert bridge.delete_library(plan['token'],old.name)['ok']
    assert bridge._lib.root==current and bridge.get_settings()['data']['library_available']
    assert [p['path'] for p in bridge.list_libraries()['data']]==[str(current)]


def test_other_window_lock_blocks_delete_preview(bridge_fixture,tmp_path):
    _,bridge=bridge_fixture;old=bridge._lib.root;bridge._switch_library(tmp_path/'second');other=Library(old)
    try:assert not bridge.inspect_library_delete(str(old))['ok']
    finally:other.close()


def test_missing_trash_file_still_prunes_its_empty_asset_directory(fixture):
    _,lib=fixture;p=lib.catalog.photos()[0];lib.trash_photos([p['id']])
    photo=lib.catalog.photo(p['id'],include_trashed=True);Path(photo['assets'][0]['path']).unlink()
    assert not lib.purge_trash([p['id']])['errors']
    assert not (lib.catalog.meta/'回收站'/p['id']).exists()


@pytest.mark.skipif(sys.platform!='win32',reason='Windows 回收站 COM 回调仅适用于 Windows')
def test_recycle_callback_vetoes_permanent_delete_with_com_abort():
    from pianji.library_deletion import _sink_type
    from win32com.server.exception import COMException
    from win32com.shell import shellcon
    sink=_sink_type()()
    with pytest.raises(COMException) as error:sink.PreDeleteItem(0,None)
    assert error.value.scode==-2147467260
    assert sink.PreDeleteItem(shellcon.TSF_DELETE_RECYCLE_IF_POSSIBLE,None)==0


@pytest.mark.parametrize('operation',['person','activity'])
def test_missing_originals_delete_still_removes_known_empty_parents(fixture,operation):
    _,lib=fixture;p=lib.catalog.photos()[0];person=lib.catalog.add_person(p['activity_id'],'Alice');lib.set_person([p['id']],person['id'])
    old=lib.root/'event'/'Alice'
    for a in lib.catalog.photo(p['id'])['assets']:Path(a['path']).unlink()
    result=lib.delete_people([person['id']]) if operation=='person' else lib.delete_activity(p['activity_id'])
    assert not result['errors'] and not old.exists()
    assert lib.catalog.rows('SELECT id FROM photos WHERE id=?',(p['id'],)),'missing original association is retained'


def test_cleanup_exception_never_rolls_back_committed_photo_metadata(fixture,monkeypatch):
    from pianji import cleanup
    _,lib=fixture;p=lib.catalog.photos()[0]
    def broken(*a,**k):raise RuntimeError('unexpected cleanup failure')
    monkeypatch.setattr(cleanup,'prune_empty',broken)
    result=lib.set_edited([p['id']],True)
    assert not result['errors'];after=lib.catalog.photo(p['id']);assert after['edited']
    assert all(Path(a['path']).is_file() for a in after['assets'])
