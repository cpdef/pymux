#!/usr/bin/env python3
import curses
import sys
import os

from signal import signal, SIGTSTP, SIGINT
from time import sleep, time
from backend import Session
from procinfo import ProcessInfo

proc_info = ProcessInfo()

class Terminal(object):
    keymap = {
            'SIGTSTP' : b'\x1a',

            curses.KEY_BACKSPACE : b'\x08', 
            curses.KEY_CANCEL : b'\x03',
            curses.KEY_CLEAR : b'\x0c',
            curses.KEY_DC : b'~4',
            curses.KEY_DOWN : b'~B',
            curses.KEY_END : b'~F',
            curses.KEY_F1 : b'~a',
            curses.KEY_F2 : b'~b',
            curses.KEY_F3 : b'~c',
            curses.KEY_F4 : b'~d',
            curses.KEY_F5 : b'~e',
            curses.KEY_F6 : b'~f',
            curses.KEY_F7 : b'~g',
            curses.KEY_F8 : b'~h',
            curses.KEY_F9 : b'~i',
            curses.KEY_F10 : b'~j',
            curses.KEY_F11 : b'~k',
            curses.KEY_F12 : b'~l',
            curses.KEY_HOME : b'~H',
            curses.KEY_IC : b'~3',
            curses.KEY_LEFT : b'~D',
            curses.KEY_NPAGE : b'~2',
            curses.KEY_PPAGE : b'~1',
            curses.KEY_RIGHT : b'~C',
            curses.KEY_UP : b'~A',
    }
 
    def __init__(self, window):
        window.nodelay(1) #don't block with window.getch()
        
        # set w, h
        self.height, self.width = window.getmaxyx()
        self.width -= 1; self.height -= 1; #max is max-1
        self.session = Session(width=self.width, height = self.height)
        self._window = window

        self.scrollback = 0
        self.last_scrollback = 0
        self.last_scroll_screen = None

    def get_input(self):
        inp = self._window.getch()
        return inp

    def send_key(self, key):
        if key == -1:
            return
        elif key in self.keymap:
            c_char = self.keymap[key]
        elif key == curses.KEY_SPREVIOUS:
            self.scrollback += 5
            return
        elif key == curses.KEY_SNEXT:
            self.scrollback -= 5
            if self.scrollback < 0:
                self.scrollback = 0
            return
        else:
            c_char = chr(key).encode('utf-8')

        self.session.write(c_char)

    def get_cursorscreen(self):
        if self.scrollback == 0:
            self.last_scrollback = 0
            return self.session.dump()
        else:
            if self.scrollback != self.last_scrollback:
                self.last_scroll_screen = self.session.dump_history(self.scrollback)
                self.last_scrollback = self.scrollback
            return self.last_scroll_screen
        
    def refresh(self):
        (cx, cy), screen = self.get_cursorscreen()

        # write the current screen to the window
        self._window.clear()
        for line_nr, line in enumerate(screen):
            text = ''
            for element in line:
                if type(element) == str:
                    text += element
            self._window.addstr(line_nr, 0, text)

        # move to currents sessions cursor pos:
        if cy != None:
            self._window.move(cy, cx)
        
        self._window.refresh()

    def get_title(self, focus=False):
        pid = self.session.pid
        try:
            proc_info.update()
            child_pids = [pid,] + proc_info.all_children(pid)

            top_pid = child_pids[-1]
            cmd = self.get_cmdline(top_pid).split(' ')[0]

            for child_pid in reversed(child_pids):
                cwd = proc_info.cwd(child_pid)
                if cwd: 
                    break
        except ProcessLookupError:
            return 'Terminal'


        if not (cwd and cmd and top_pid):
            return 'Terminal'

        if focus:
            return "{}: {} {}".format(os.path.basename(cwd), cmd, top_pid)
        else:
            return cmd

    def is_alive(self):
        return self.session.is_alive()

    def _write(self, d):
        self.session.write(d)

    def cancel(self):
        self._write(self.keymap[curses.KEY_CANCEL])

    def run(self):
        self.session.keepalive()

class TerminalContainer(object):
    def __init__(self, window):
        self._window = window
        self.terminals = []
        self.focused = None
        self.add_terminal()
        print('Container created!')

    def add_terminal(self):
        new_term = Terminal(self._window)
        self.terminals.append(new_term)
        self.focused = new_term
        self.focused.run()

    def get_input(self):
        return self.focused.get_input()
    
    def signal_handler(self, signal, stackframe):
        if signal == SIGINT:
            self.focused.cancel()

    def is_alive(self):
        if self.focused.is_alive():
            return True
        else:
            self.terminals.remove(self.focused)
            if self.terminals:
                self.focused = self.terminals[0]
                return self.is_alive()
            else:
                return False

    def focus_terminal(self, index, relative=0):
        """focus terminal from self.terminals list

        Arguments:
        index -- defines which terminal should be focused
        relative -- if this is != 0, index is replaced with
                    the focused terminals's index + the relative value
        """
        if relative != 0:
            current_index = self.terminals.index(self.focused)
            index = current_index + relative
        index = index % len(self.terminals)
        self.focused = self.terminals[index]

    def input(self, y, x, prompt, attr=0):
        self._window.nodelay(False)
        curses.echo()
        self._window.addstr(y, x, prompt, attr)
        result = self._window.getstr()
        self._window.nodelay(True)
        curses.noecho()
        return result

    def run(self):
        print('run Container... ')
        while self.is_alive():
            inp = self.focused.get_input()
            self.focused.send_key(inp)
            self.focused.refresh()
            sleep(1/30)
        
if __name__ == '__main__':
    def main(stdscr):
        try:
            # init colors:
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_RED)
    
            # create terminal:
            win = curses.newwin(100, 100, 0, 0)
            master = TerminalContainer(stdscr)

            # bin signals:
            signal(SIGINT, master.signal_handler)
            #signal(SIGTSTP, term.signal_handler)

            # run terminal:
            master.run()
        except Exception as e:
            # close all terminals if there is an bug/error in this program
            try:
                Session.close_all()
            except:
                pass
            raise e

   
        # close all sessions:
        Session.close_all()

    curses.wrapper(main)
