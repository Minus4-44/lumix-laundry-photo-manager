from pathlib import Path
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from .bridge import Bridge
from .window_motion import bind_window_motion

def resource_root(): return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
def config_root():
    if sys.platform=='darwin': return Path.home()/'Library'/'Application Support'/'Pianji'
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData'/'Local')))/'Pianji'
def gui_backend(): return 'edgechromium' if sys.platform=='win32' else None
def icon_path():
    name='lumix.icns' if sys.platform=='darwin' else 'lumix.ico'
    icon=resource_root()/'pianji'/'ui'/name
    return str(icon) if icon.exists() else None

def start():
    root=config_root(); root.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(root/'pianji.log',maxBytes=2_000_000,backupCount=3,encoding='utf-8')],format='%(asctime)s %(levelname)s %(message)s')
    import webview
    bridge=Bridge(root,model_root=resource_root()/'models')
    window=webview.create_window('洗衣机管理器',str(resource_root()/'pianji'/'ui'/'index.html'),js_api=bridge,width=1440,height=960,min_size=(1040,720),background_color='#151619',text_select=False,zoomable=False)
    bridge._window=window
    cleanup=bind_window_motion(window,bridge._close)
    try: webview.start(gui=gui_backend(),storage_path=str(root/'webview'),private_mode=True,debug=False,icon=icon_path())
    finally:
        cleanup()
        logging.info('Window closed')
