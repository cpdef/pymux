#!/usr/bin/env python3
import curses
import sys
import os

from signal import signal, SIGTSTP, SIGINT

from time import sleep
from backend import Session

from enum import Enum

_print = print

def print(*args):
    raise NotImplementedError('print is not supported in curses', args)

def debug_print(*args, t=1):
    _print(*args)
    sleep(t)

class CursesTerminalMultiplexer(object):
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
    
    MODE_MASTER = 1 # here u see the current sessions screen
    MODE_TERMINAL = 2  # in this mode u can control all sessions
 
    def __init__(self, window, hidden=True):
        window.nodelay(1) #don't block with window.getch()
        
        # set w, h
        self.height, self.width = window.getmaxyx()
        self.width -= 1; self.height -= 1; #max is max-1
        
        self.sessions = []
        self._window = window
        self.add_session()
        self._alive = True

        self.scrollback = 0
        self.last_scrollback = 0
        self.last_scroll_screen = None


        self.mode = self.MODE_TERMINAL


    def add_session(self):
        # height-1 because of status_bar in last line
        new_session = Session(width=self.width, height=self.height-1)
        self.sessions.append(new_session)
        self.focused = new_session
        new_session.keepalive()

    def current_session(self):
        return self.sessions[self.sessions.index(self.focused)]

    def get_input(self):
        inp = self._window.getch()
        
        if inp == -1:
            return
        elif inp in self.keymap:
            c_char = self.keymap[inp]
        elif inp == curses.KEY_SPREVIOUS:
            self.scrollback += 5
            return
        elif inp == curses.KEY_SNEXT:
            self.scrollback -= 5
            if self.scrollback < 0:
                self.scrollback = 0
            return
        else:
            c_char = chr(inp).encode('utf-8')

        if self.mode == self.MODE_TERMINAL:
            self.current_session().write(c_char)
            self.scrollback = 0
        else:
            self.master_send_key(inp)

    def master_send_key(self, inp):
        if inp == ord('n'): 
            self.add_session()
            self.mode = self.MODE_TERMINAL
        elif inp == ord('i'):
            index = self.input(self.height-1, 0, 'enter index:')
            try:
                self.focus_session(int(index.decode('ascii'))) 
            except ValueError:
                pass
        elif inp in [ord('e'), ord('q')]:
            Session.close_all()
        elif inp == curses.KEY_RIGHT:
            self.focus_session(0, 1)
        elif inp == curses.KEY_LEFT:
            self.focus_session(0, -1)

    def input(self, y, x, prompt, attr=0):
        self._window.nodelay(False)
        curses.echo()
        self._window.addstr(y, x, prompt, attr)
        result = self._window.getstr()
        self._window.nodelay(True)
        curses.noecho()
        return result

    def focus_session(self, index, relative=0):
        """focus session from self.session list

        Arguments:
        index -- defines which session should be focused
        relative -- if this is != 0, index is replaced with
                    the focused session's index + the relative value
        """
        if relative != 0:
            current_index = self.sessions.index(self.current_session())
            index = current_index + relative
        index = index % len(self.sessions)
        self.focused = self.sessions[index]
        self.mode = self.MODE_TERMINAL

    def get_cursorscreen(self):
        if self.mode == self.MODE_TERMINAL:
            if self.scrollback == 0:
                self.last_scrollback = 0
                return self.current_session().dump()
            else:
                if self.scrollback != self.last_scrollback:
                    self.last_scroll_screen = self.current_session()\
                        .dump_history(self.scrollback)
                    self.last_scrollback = self.scrollback
                return self.last_scroll_screen
        else:
            screen = [
                        ['MASTER MODE'],
                        ['=============='],
                        ['ctrl+c: send ctrl+c (cancel) to focused session'],
                        ['right/left: focus next/previous session'],
                        ['n: create new session and focus it'],
                        ['i: focus session by index'],
                        ['e/q: exit']
                    ]
            return (None, None), screen

    def write_on_window(self):
        (cx, cy), screen = self.get_cursorscreen()

        # write the current screen to the window
        self._window.clear()
        for line_nr, line in enumerate(screen):
            text = ''
            for element in line:
                if type(element) == str:
                    text += element
            self._window.addstr(line_nr, 0, text)

        # write statusbar:
        bar_text = ''
        for session in self.sessions:
            if session is self.current_session():
                bar_text += '_{}_ '.format(session.pid())
            else:
                bar_text += '{} '.format(session.pid())
        bar_text += ' '*(self.width-len(bar_text))

        self._window.addstr(self.height-1, 0, bar_text[:self.width], curses.color_pair(1))

        # move to currents sessions cursor pos:
        if cy != None:
            self._window.move(cy, cx)
        
        self._window.refresh()

    def is_alive(self):
        if self.current_session().is_alive():
            return True
        else:
            try:
                #change focus to first session
                self.sessions.remove(self.current_session())
                self.focused = self.sessions[0]
                return self.is_alive()
            except IndexError:
                # no session in self.sessions anymore
                return False

    def _write(self, d):
        self.current_session().write(d)

    def cancel(self):
        if self.mode == self.MODE_TERMINAL:
            self.mode = self.MODE_MASTER
        else:
            self.mode = self.MODE_TERMINAL
            self._write(self.keymap[curses.KEY_CANCEL])

    def signal_handler(self, signal, stackframe):
        if signal == SIGINT:
            self.cancel()
        elif signal == SIGTSTP:
            self._write(self.keymap['SIGTSTP'])




def main(stdscr):
    try:
        # init colors:
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_RED)
    
        # create terminal:
        win = curses.newwin(100, 100, 0, 0)
        term = CursesTerminalMultiplexer(stdscr, False)

        # bin signals:
        signal(SIGINT, term.signal_handler)
        signal(SIGTSTP, term.signal_handler)

        # run terminal:
        while term.is_alive():
            term.get_input()
            term.write_on_window()
    except Exception as e:
        # close all terminals if there is an bug/error in this program
        Session.close_all()
        raise e

   
    # close all sessions:
    Session.close_all()

curses.wrapper(main)
