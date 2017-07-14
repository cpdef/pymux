#Pymux - a Python terminal multiplexer

This multiplexer is in a realy early state, but it is already useable. I have taken the backend from pyqterm-0.2 and changed it for my issues.

----------------

To see what i changed look in the commit history, maybe i made some changes before the first commit, which are not mentioned there

###What i'll add later:

* Make a Terminal split mode
* add colors (already supported by the backend)
* change the usage, so that i don't need the master-screen to change between sessions
* add the ability to copy text from one session to on other, or into a file
* ....
* ....
* make it useable as an opponent to GNU screen or tmux

###Features:

* start many sessions in a single console (multiplexer)
* scroll the history also if u use it on a linux console

###Setup:
* install linux
* Download the source
* install ncurses
* install python3

(most linux distributions have already python3 and ncurses)

* change into the source directory
* run: python3 frontend.py
