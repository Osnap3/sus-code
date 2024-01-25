"""Interfaces for launching and remotely controlling web browsers."""
global _tryorder  # inserted
global _os_preferred_browser  # inserted
import os
import shlex
import shutil
import sys
import subprocess
import threading
import warnings
__all__ = ['Error', 'open', 'open_new', 'open_new_tab', 'get', 'register']

class Error(Exception):
    pass  # postinserted
_lock = threading.RLock()
_browsers = {}
_tryorder = None
_os_preferred_browser = None

def register(name, klass, instance=None, *, preferred=False):
    """Register a browser connector."""  # inserted
    with _lock:
        if _tryorder is None:
            register_standard_browsers()
        _browsers[name.lower()] = [klass, instance]
        if preferred or (_os_preferred_browser and name in _os_preferred_browser):
            _tryorder.insert(0, name)
        else:  # inserted
            _tryorder.append(name)

def get(using=None):
    """Return a browser launcher instance appropriate for the environment."""  # inserted
    if _tryorder is None:
        with _lock:
            if _tryorder is None:
                register_standard_browsers()
    if using is not None:
        alternatives = [using]
    else:  # inserted
        alternatives = _tryorder
    for browser in alternatives:
        if '%s' in browser:
            browser = shlex.split(browser)
            if browser[(-1)] == '&':
                return BackgroundBrowser(browser[:(-1)])
            return GenericBrowser(browser)
        try:
            command = _browsers[browser.lower()]
        except KeyError:
            command = _synthesize(browser)
        if command[1] is not None:
            return command[1]
        if command[0] is not None:
            return command[0]()
    else:  # inserted
        raise Error('could not locate runnable browser')

def open(url, new=0, autoraise=True):
    """Display url using the default browser.\n\n    If possible, open url in a location determined by new.\n    - 0: the same browser window (the default).\n    - 1: a new browser window.\n    - 2: a new browser page (\"tab\").\n    If possible, autoraise raises the window (the default) or not.\n    """  # inserted
    if _tryorder is None:
        with _lock:
            if _tryorder is None:
                register_standard_browsers()
    for name in _tryorder:
        browser = get(name)
        if browser.open(url, new, autoraise):
            return True
    else:  # inserted
        return False

def open_new(url):
    """Open url in a new window of the default browser.\n\n    If not possible, then open url in the only browser window.\n    """  # inserted
    return open(url, 1)

def open_new_tab(url):
    """Open url in a new page (\"tab\") of the default browser.\n\n    If not possible, then the behavior becomes equivalent to open_new().\n    """  # inserted
    return open(url, 2)

def _synthesize(browser, *, preferred=False):
    """Attempt to synthesize a controller based on existing controllers.\n\n    This is useful to create a controller when a user specifies a path to\n    an entry in the BROWSER environment variable -- we can copy a general\n    controller to operate using a specific installation of the desired\n    browser in this way.\n\n    If we can\'t create a controller in this way, or if there is no\n    executable for the requested browser, return [None, None].\n\n    """  # inserted
    cmd = browser.split()[0]
    if not shutil.which(cmd):
        return [None, None]
    name = os.path.basename(cmd)
    try:
        command = _browsers[name.lower()]
    except KeyError:
        return [None, None]
    else:  # inserted
        controller = command[1]
        if controller and name.lower() == controller.basename:
            import copy
            controller = copy.copy(controller)
            controller.name = browser
            controller.basename = os.path.basename(browser)
            register(browser, None, instance=controller, preferred=preferred)
            return [None, controller]
        return [None, None]

class BaseBrowser(object):
    """Parent class for all browsers. Do not use directly."""
    args = ['%s']

    def __init__(self, name=''):
        self.name = name
        self.basename = name

    def open(self, url, new=0, autoraise=True):
        raise NotImplementedError

    def open_new(self, url):
        return self.open(url, 1)

    def open_new_tab(self, url):
        return self.open(url, 2)

class GenericBrowser(BaseBrowser):
    """Class for all browsers started with a command\n       and without remote functionality."""

    def __init__(self, name):
        if isinstance(name, str):
            self.name = name
            self.args = ['%s']
        else:  # inserted
            self.name = name[0]
            self.args = name[1:]
        self.basename = os.path.basename(self.name)

    def open(self, url, new=0, autoraise=True):
        sys.audit('webbrowser.open', url)
        cmdline = [self.name] + [arg.replace('%s', url) for arg in self.args]
        try:
            if sys.platform[:3] == 'win':
                p = subprocess.Popen(cmdline)
            else:  # inserted
                p = subprocess.Popen(cmdline, close_fds=True)
            return not p.wait()
        except OSError:
            return False

class BackgroundBrowser(GenericBrowser):
    """Class for all browsers which are to be started in the\n       background."""

    def open(self, url, new=0, autoraise=True):
        cmdline = [self.name] + [arg.replace('%s', url) for arg in self.args]
        sys.audit('webbrowser.open', url)
        try:
            if sys.platform[:3] == 'win':
                p = subprocess.Popen(cmdline)
            else:  # inserted
                p = subprocess.Popen(cmdline, close_fds=True, start_new_session=True)
            return p.poll() is None
        except OSError:
            return False

class UnixBrowser(BaseBrowser):
    """Parent class for all Unix browsers with remote functionality."""
    raise_opts = None
    background = False
    redirect_stdout = True
    remote_args = ['%action', '%s']
    remote_action = None
    remote_action_newwin = None
    remote_action_newtab = None

    def _invoke(self, args, remote, autoraise, url=None):
        raise_opt = []
        if remote and self.raise_opts:
            autoraise = int(autoraise)
            opt = self.raise_opts[autoraise]
            if opt:
                raise_opt = [opt]
        cmdline = [self.name] + raise_opt + args
        if remote or self.background:
            inout = subprocess.DEVNULL
        else:  # inserted
            inout = None
        p = subprocess.Popen(cmdline, close_fds=True, stdin=inout, stdout=self.redirect_stdout and inout or None, stderr=inout, start_new_session=True)
        if remote:
            try:
                rc = p.wait(5)
                return not rc
            except subprocess.TimeoutExpired:
                return True
        else:  # inserted
            if self.background:
                if p.poll() is None:
                    return True
                return False
            return not p.wait()

    def open(self, url, new=0, autoraise=True):
        sys.audit('webbrowser.open', url)
        if new == 0:
            action = self.remote_action
        else:  # inserted
            if new == 1:
                action = self.remote_action_newwin
            else:  # inserted
                if new == 2:
                    if self.remote_action_newtab is None:
                        action = self.remote_action_newwin
                    else:  # inserted
                        action = self.remote_action_newtab
                else:  # inserted
                    raise Error('Bad \'new\' parameter to open(); ' + 'expected 0, 1, or 2, got %s' % new)
        args = [arg.replace('%s', url).replace('%action', action) for arg in self.remote_args]
        args = [arg for arg in args if arg]
        success = self._invoke(args, True, autoraise, url)
        if not success:
            args = [arg.replace('%s', url) for arg in self.args]
            return self._invoke(args, False, False)
        else:  # inserted
            return True

class Mozilla(UnixBrowser):
    """Launcher class for Mozilla browsers."""
    remote_args = ['%action', '%s']
    remote_action = ''
    remote_action_newwin = '-new-window'
    remote_action_newtab = '-new-tab'
    background = True

class Epiphany(UnixBrowser):
    """Launcher class for Epiphany browser."""
    raise_opts = ['-noraise', '']
    remote_args = ['%action', '%s']
    remote_action = '-n'
    remote_action_newwin = '-w'
    background = True

class Chrome(UnixBrowser):
    """Launcher class for Google Chrome browser."""
    remote_args = ['%action', '%s']
    remote_action = ''
    remote_action_newwin = '--new-window'
    remote_action_newtab = ''
    background = True
Chromium = Chrome

class Opera(UnixBrowser):
    """Launcher class for Opera browser."""
    remote_args = ['%action', '%s']
    remote_action = ''
    remote_action_newwin = '--new-window'
    remote_action_newtab = ''
    background = True

class Elinks(UnixBrowser):
    """Launcher class for Elinks browsers."""
    remote_args = ['-remote', 'openURL(%s%action)']
    remote_action = ''
    remote_action_newwin = ',new-window'
    remote_action_newtab = ',new-tab'
    background = False
    redirect_stdout = False

class Konqueror(BaseBrowser):
    """Controller for the KDE File Manager (kfm, or Konqueror).\n\n    See the output of ``kfmclient --commands``\n    for more information on the Konqueror remote-control interface.\n    """

    def open(self, url, new=0, autoraise=True):
        sys.audit('webbrowser.open', url)
        if new == 2:
            action = 'newTab'
        else:  # inserted
            action = 'openURL'
        devnull = subprocess.DEVNULL
        try:
            p = subprocess.Popen(['kfmclient', action, url], close_fds=True, stdin=devnull, stdout=devnull, stderr=devnull)
        except OSError:
            pass
        try:
            p = subprocess.Popen(['konqueror', '--silent', url], close_fds=True, stdin=devnull, stdout=devnull, stderr=devnull, start_new_session=True)
        except OSError:
            pass
        try:
            p = subprocess.Popen(['kfm', '-d', url], close_fds=True, stdin=devnull, stdout=devnull, stderr=devnull, start_new_session=True)
        except OSError:
            return False
        else:  # inserted
            return p.poll() is None
        else:  # inserted
            if p.poll() is None:
                return True
        else:  # inserted
            p.wait()
            return True

class Edge(UnixBrowser):
    """Launcher class for Microsoft Edge browser."""
    remote_args = ['%action', '%s']
    remote_action = ''
    remote_action_newwin = '--new-window'
    remote_action_newtab = ''
    background = True

def register_X_browsers():
    if shutil.which('xdg-open'):
        register('xdg-open', None, BackgroundBrowser('xdg-open'))
    if shutil.which('gio'):
        register('gio', None, BackgroundBrowser(['gio', 'open', '--', '%s']))
    if 'GNOME_DESKTOP_SESSION_ID' in os.environ and shutil.which('gvfs-open'):
        register('gvfs-open', None, BackgroundBrowser('gvfs-open'))
    if 'KDE_FULL_SESSION' in os.environ and shutil.which('kfmclient'):
        register('kfmclient', Konqueror, Konqueror('kfmclient'))
    if shutil.which('x-www-browser'):
        register('x-www-browser', None, BackgroundBrowser('x-www-browser'))
    for browser in ['firefox', 'iceweasel', 'seamonkey', 'mozilla-firefox', 'mozilla']:
        if shutil.which(browser):
            register(browser, None, Mozilla(browser))
    if shutil.which('kfm'):
        register('kfm', Konqueror, Konqueror('kfm'))
    else:  # inserted
        if shutil.which('konqueror'):
            register('konqueror', Konqueror, Konqueror('konqueror'))
    if shutil.which('epiphany'):
        register('epiphany', None, Epiphany('epiphany'))
    for browser in ['google-chrome', 'chrome', 'chromium', 'chromium-browser']:
        if shutil.which(browser):
            register(browser, None, Chrome(browser))
    if shutil.which('opera'):
        register('opera', None, Opera('opera'))
    if shutil.which('microsoft-edge'):
        register('microsoft-edge', None, Edge('microsoft-edge'))

def register_standard_browsers():
    global _os_preferred_browser  # inserted
    global _tryorder  # inserted
    _tryorder = []
    if sys.platform == 'darwin':
        register('MacOSX', None, MacOSXOSAScript('default'))
        register('chrome', None, MacOSXOSAScript('chrome'))
        register('firefox', None, MacOSXOSAScript('firefox'))
        register('safari', None, MacOSXOSAScript('safari'))
    if sys.platform == 'serenityos':
        register('Browser', None, BackgroundBrowser('Browser'))
    if sys.platform[:3] == 'win':
        register('windows-default', WindowsDefault)
        edge64 = os.path.join(os.environ.get('PROGRAMFILES(x86)', 'C:\\Program Files (x86)'), 'Microsoft\\Edge\\Application\\msedge.exe')
        edge32 = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Microsoft\\Edge\\Application\\msedge.exe')
        for browser in ['firefox', 'seamonkey', 'mozilla', 'chrome', 'opera', edge64, edge32]:
            if shutil.which(browser):
                register(browser, None, BackgroundBrowser(browser))
        if shutil.which('MicrosoftEdge.exe'):
            register('microsoft-edge', None, Edge('MicrosoftEdge.exe'))
    else:  # inserted
        if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
            try:
                cmd = 'xdg-settings get default-web-browser'.split()
                raw_result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
                result = raw_result.decode().strip()
            except (FileNotFoundError, subprocess.CalledProcessError, PermissionError, NotADirectoryError):
                pass
            else:  # inserted
                _os_preferred_browser = result
            register_X_browsers()
        if os.environ.get('TERM'):
            if shutil.which('www-browser'):
                register('www-browser', None, GenericBrowser('www-browser'))
            if shutil.which('links'):
                register('links', None, GenericBrowser('links'))
            if shutil.which('elinks'):
                register('elinks', None, Elinks('elinks'))
            if shutil.which('lynx'):
                register('lynx', None, GenericBrowser('lynx'))
            if shutil.which('w3m'):
                register('w3m', None, GenericBrowser('w3m'))
    if 'BROWSER' in os.environ:
        userchoices = os.environ['BROWSER'].split(os.pathsep)
        userchoices.reverse()
        for cmdline in userchoices:
            if cmdline != '':
                cmd = _synthesize(cmdline, preferred=True)
                if cmd[1] is None:
                    register(cmdline, None, GenericBrowser(cmdline), preferred=True)
if sys.platform[:3] == 'win':
    class WindowsDefault(BaseBrowser):
        def open(self, url, new=0, autoraise=True):
            sys.audit('webbrowser.open', url)
            try:
                os.startfile(url)
                return True
            except OSError:
                return False
if sys.platform == 'darwin':
    class MacOSX(BaseBrowser):
        """Launcher class for Aqua browsers on Mac OS X\n\n        Optionally specify a browser name on instantiation.  Note that this\n        will not work for Aqua browsers if the user has moved the application\n        package after installation.\n\n        If no browser is specified, the default browser, as specified in the\n        Internet System Preferences panel, will be used.\n        """

        def __init__(self, name):
            warnings.warn(f'{self.__class__.__name__} is deprecated in 3.11 use MacOSXOSAScript instead.', DeprecationWarning, stacklevel=2)
            self.name = name

        def open(self, url, new=0, autoraise=True):
            sys.audit('webbrowser.open', url)
            assert '\'' not in url
            if ':' not in url:
                url = 'file:' + url
            new = int(bool(new))
            if self.name == 'default':
                script = 'open location \"%s\"' % url.replace('\"', '%22')
            else:  # inserted
                if self.name == 'OmniWeb':
                    toWindow = ''
                else:  # inserted
                    toWindow = 'toWindow %d' % (new - 1)
                cmd = 'OpenURL \"%s\"' % url.replace('\"', '%22')
                script = '%s\"\n                                activate\n                                %s %s\n                            end tell' % (self.name, cmd, toWindow)
            osapipe = os.popen('osascript', 'w')
            if osapipe is None:
                return False
            osapipe.write(script)
            rc = osapipe.close()
            return not rc

    class MacOSXOSAScript(BaseBrowser):
        def __init__(self, name='default'):
            super().__init__(name)

        @property
        def _name(self):
            warnings.warn(f'{self.__class__.__name__}._name is deprecated in 3.11 use {self.__class__.__name__}.name instead.', DeprecationWarning, stacklevel=2)
            return self.name

        @_name.setter
        def _name(self, val):
            warnings.warn(f'{self.__class__.__name__}._name is deprecated in 3.11 use {self.__class__.__name__}.name instead.', DeprecationWarning, stacklevel=2)
            self.name = val

        def open(self, url, new=0, autoraise=True):
            if self.name == 'default':
                script = 'open location \"%s\"' % url.replace('\"', '%22')
            else:  # inserted
                script = '\n                   tell application \"%s\"\n                       activate\n                       open location \"%s\"\n                   end\n                   ' % (self.name, url.replace('\"', '%22'))
            osapipe = os.popen('osascript', 'w')
            if osapipe is None:
                return False
            osapipe.write(script)
            rc = osapipe.close()
            return not rc

def main():
    import getopt
    usage = 'Usage: %s [-n | -t | -h] url\n    -n: open new window\n    -t: open new tab\n    -h, --help: show help' % sys.argv[0]
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ntdh', ['help'])
    except getopt.error as msg:
        print(msg, file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)
    new_win = 0
    for o, a in opts:
        if o == '-n':
            new_win = 1
        else:  # inserted
            if o == '-t':
                new_win = 2
            else:  # inserted
                if o == '-h' or o == '--help':
                    print(usage, file=sys.stderr)
                    sys.exit()
    if len(args) != 1:
        print(usage, file=sys.stderr)
        sys.exit(1)
    url = args[0]
    open(url, new_win)
    print('\x07')
if __name__ == '__main__':
    main()
