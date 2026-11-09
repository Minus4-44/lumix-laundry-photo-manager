"""Short native window fades. All Form/Timer access stays on the Windows UI thread."""
import ctypes
import logging
import sys
import threading
import time


class WindowFade:
    def __init__(self,paint,finish,*,enabled=True):
        self.paint=paint;self.finish=finish;self.enabled=enabled
        self.value=1.;self.phase='waiting';self.started=0.;self.duration=0.

    def prepare(self):
        self.value=0. if self.enabled else 1.;self.paint(self.value)

    def reveal(self,now):
        if self.phase in ('closing','closed'):return
        if not self.enabled:self.value=1.;self.phase='open';self.paint(1.);return
        self._start(1.,now,.22,'opening')

    def _start(self,target,now,duration,phase):
        self.origin=self.value;self.target=target;self.started=now
        self.duration=duration;self.phase=phase

    def request_close(self,now):
        if self.phase=='closed':return True
        if not self.enabled or self.value<=.001:self.phase='closed';return True
        if self.phase=='closing':return False
        self._start(0.,now,.16,'closing');return False

    def tick(self,now):
        if self.phase not in ('opening','closing'):return
        fraction=max(0.,min(1.,(now-self.started)/self.duration))
        self.value=self.origin+(self.target-self.origin)*(1-(1-fraction)**3)
        self.paint(self.value)
        if fraction>=1:
            closing=self.phase=='closing';self.phase='closed' if closing else 'open'
            if closing:self.finish()


def animations_enabled():
    try:
        allowed=ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042,0,ctypes.byref(allowed),0):
            return bool(allowed.value)
    except (AttributeError,OSError):pass
    return True


def bind_window_motion(window,cleanup):
    """Bind before native Show; preserve normal shutdown/lock release exactly once."""
    if sys.platform!='win32':
        # macOS/Linux: native fade uses WinForms only; keep the plain lifecycle.
        state={'closed':False}
        def cleanup_once():
            if state['closed']:return
            state['closed']=True
            cleanup()
        window.events.closed+=lambda *_:cleanup_once()
        return cleanup_once

    state={'fade':None,'timer':None,'failed':False};lock=threading.Lock();cleaned=False
    def cleanup_once():
        nonlocal cleaned
        with lock:
            if cleaned:return
            cleaned=True
        cleanup()

    def prepare():
        try:
            from System.Windows.Forms import Timer
            native=window.native;timer=Timer();timer.Interval=15
            fade=WindowFade(lambda value:setattr(native,'Opacity',value),window.destroy,enabled=animations_enabled())
            state.update(fade=fade,timer=timer)
            prepared_at=time.perf_counter()
            def tick(*_):
                try:
                    now=time.perf_counter()
                    # A failed/delayed document load must never strand an invisible window.
                    if fade.phase=='waiting':
                        if now-prepared_at<2:return
                        fade.reveal(now)
                    fade.tick(now)
                    if fade.phase not in ('opening','closing'):timer.Stop()
                except Exception:
                    logging.exception('Window fade failed; restoring normal lifecycle')
                    timer.Stop();state['failed']=True;fade.enabled=False
                    if fade.phase=='closing':window.destroy()
                    elif not native.IsDisposed:native.Opacity=1
            timer.Tick+=tick
            def dispose_timer(*_):timer.Stop();timer.Dispose()
            native.FormClosed+=dispose_timer
            fade.prepare()
            if fade.enabled:timer.Start()
        except Exception:
            logging.exception('Native motion unavailable; using normal window lifecycle')
            state['fade']=None
            if window.native is not None:window.native.Opacity=1

    def reveal():
        fade=state['fade']
        if not fade or fade.phase in ('closing','closed'):return
        try:
            from System import Action
            def show():
                if window.native.IsDisposed:return
                fade.reveal(time.perf_counter())
                if fade.phase=='opening':state['timer'].Start()
            window.native.Invoke(Action(show))
        except Exception:
            logging.exception('Window reveal failed')

    def closing():
        fade=state['fade']
        if fade:
            fade.enabled=not state['failed'] and animations_enabled()
            if not fade.request_close(time.perf_counter()):
                state['timer'].Start();return False
        cleanup_once()

    def closed():
        cleanup_once()

    window.events.before_show+=prepare;window.events.loaded+=reveal
    window.events.closing+=closing;window.events.closed+=closed
    return cleanup_once
