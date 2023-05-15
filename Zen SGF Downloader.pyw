#!/usr/bin/env pythonw

"""
A widget to download SGF files from OGS
without information about the rank of the players
"""

__author__="Juan A. Vargas Mesén (Leira)"
__copyright__ = "© 2023, Leira"
__date__="2023/5/15"
__version__ = "1.0.1"
__license__="MIT"
__status__ = "Release"

"""
MIT License

Copyright 2023 Juan A. Vargas Mesén (Leira)

Permission is hereby granted, free of charge,
to any person obtaining a copy of this software
and associated documentation files (the “Software”),
to deal in the Software without restriction,
including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice
shall be included in all copies or substantial
portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”,
WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import requests
import re
from functools import lru_cache
import tkinter as tk
from tkinter.filedialog import asksaveasfile

APP_NAME="Zen SGF Downloader"

################
## Downloader ##
################

URL="https://online-go.com/termination-api/game/{}"
SGF="https://online-go.com/api/v1/games/{}/sgf"
ORDINARY_URL="https://online-go.com/game/{}"
NaN=float('nan')

# Characters that shouldn't be used in a file path
def forbidden_char(ch):
    s='/\\<>:"|?*'
    return ch in s or ord(ch)<=31

# Remove undesired characters from a file name.
def sanitize_filename(s):
    return "".join(ch for ch in s if not forbidden_char(ch))

# Does not really check where the url comes from
# just that the final bit is a valid game number.
def url_to_number(s):
    try:
        components=reversed(s.split("/"))
        x=next(components)
        while x=="":
            x=next(components)
        return int(x)
    except StopIteration:
        raise ValueError("Invalid url string") from None


# Modified from function by jooom
def remove_ranks(sgf):
    regex = '[BW]R\\[.+\\]\n?'
    return re.sub(regex, '', sgf)
    

# Main class to retrieve games from OGS
class Game:
    @lru_cache(maxsize=1)
    def __new__(cls, game_id):
        print("Game object created: {}".format(game_id))
        return super().__new__(cls)

    @lru_cache(maxsize=1)
    def __init__(self, game_id):
        print("Requesting game info from server: {}".format(game_id))
        r=requests.get(URL.format(game_id))
        r.raise_for_status()
        d=r.json()
        self.id=game_id
        self.name=d['game_name']
        self.black=d['players']['black']['username']
        self.white=d['players']['white']['username']
        self.width=d.get('width',NaN)
        self.height=d.get('height',NaN)
        self.phase=d.get('phase','unknown')
        move_list=d.get('moves')
        if move_list is None:
            self.moves=NaN
        else:
            self.moves=len(move_list)
        default_filename="Game{}-{}_{}-vs-{}.sgf".format(
            self.id, self.moves, self.black, self.white)
        self.default_filename=sanitize_filename(default_filename)
        self.finished=(self.phase == "finished")
        self.downloadable=(
            self.finished or
            not d.get('original_disable_analysis', False))
        print("Game info retrieved: {}".format(game_id))

    def __repr__(self):
        return "{}({})".format(type(self).__name__,self.id)

    @lru_cache(maxsize=1)
    def get_sgf(self):
        print("Requesting SGF from server: {}".format(self.id))
        r=requests.get(SGF.format(self.id))
        r.raise_for_status()
        sgf=r.text
        print("SGF retrieved: {}".format(self.id))
        return sgf

    def save_sgf(self, open_file=lambda x: None):
        print("Saving file: {}".format(self.id))
        sgf=self.get_sgf()
        file=open_file(self.default_filename)
        if file is not None:
            with file as stream:
                stream.write(remove_ranks(sgf))
            print("File saved: {}".format(self.id))
            return True
        else:
            print("File not saved: {}".format(self.id))
            return False

#########
## GUI ##
#########

MAIN_GAME=None
ERROR_HANDLERS={}

string_welcome="🌸 Welcome to the Zen SGF Downloader 🌸"
string_opening='''\
Thank you for using the {} (v{}).
You may employ this tool to download any public game from the Online Go Server
(https://online-go.com)
Information about ranking will not be copied into the game file.
'''.format(APP_NAME,__version__)
string_about="Version {} --- {}.\n{} License, distribute freely.".format(
    __version__, __copyright__, __license__)
string_url="URL or Game No."
string_ok="🔎 Find Game!"
string_noai="☺  Please don't use A.I. (game unfinished) ☺"
string_noanalysis="⚠ This game cannot be downloaded (analysis disabled)"
string_card="""\
{name}
◆  {black}   vs   ◇  {white}
Size {w}×{h}
Status: {phase} (move {m})
{warning}"""
string_download="⇩ Download SGF"
string_filesaved="\n🥂  Cheers! Your file has been saved  🥂"
string_oops="Oops!"
string_error="An error has occurred.\n\n{}"


# For error reporting
def callback_wrapper(f):
    def wrapped():
        try:
            f()
        except Exception as e:
            explanation="{}: {}".format(type(e).__name__, str(e))
            tk.messagebox.showerror(
                title=string_oops,
                message=string_error.format(explanation),
                parent=root)
            handler=ERROR_HANDLERS.get(wrapped,lambda error: None)
            handler(e)
            raise e from None
    return wrapped

def get_savefile(filename):
    return asksaveasfile(
        parent=root,
        mode='w',
        filetypes=[("Smart Game Format", ".sgf")],
        defaultextension=".sgf",
        initialfile=filename,)


@callback_wrapper
def callback_ok():
    global MAIN_GAME
    s=entry_url.get()
    button_ok.focus()
    n=url_to_number(s)
    entry_url.delete(0,tk.END)
    entry_url.insert(0,ORDINARY_URL.format(n))
    
    g=Game(n)

    warning_str=string_noai
    if not g.downloadable:
        warning_str=string_noanalysis
    elif g.phase=="finished":
        warning_str=""

    info=string_card.format(
        name=g.name,
        black=g.black,
        white=g.white,
        w=g.width,
        h=g.height,
        phase=g.phase,
        m=g.moves,
        warning=warning_str)

    text_card.config(state=tk.NORMAL)
    text_card.delete("1.0",tk.END)
    text_card.insert("1.0",info)
    text_card.tag_add("justify_center", "1.0", "end")
    text_card.config(state=tk.DISABLED)

    MAIN_GAME=g

    if g.downloadable:
        button_download.config(state=tk.NORMAL)
    else:
        button_download.config(state=tk.DISABLED)

def callback_ok_error(error):
    global MAIN_GAME
    MAIN_GAME=None
    text_card.config(state=tk.NORMAL)
    text_card.delete("1.0",tk.END)
    text_card.config(state=tk.DISABLED)
    button_download.config(state=tk.DISABLED)

ERROR_HANDLERS[callback_ok]=callback_ok_error


@callback_wrapper
def callback_download():
    button_download.focus()
    success=MAIN_GAME.save_sgf(open_file=get_savefile)
    if success:
        text_card.config(state=tk.NORMAL)
        text_card.delete("5.0",tk.END)
        text_card.insert("5.0",string_filesaved)
        text_card.tag_add("justify_center", "1.0", "end")
        text_card.config(state=tk.DISABLED)
        


root = tk.Tk()

root.geometry("800x530")
root.title(APP_NAME)

frame0=tk.Frame(root)
frame0.pack(pady=0)

label_welcome = tk.Label(
    frame0, text=string_welcome, font=('Gabriola', 36))
label_welcome.pack()
label_opening = tk.Label(
    frame0, text=string_opening, font=('Calibri', 12))
label_opening.pack()
label_about = tk.Label(
    frame0, text=string_about, font=('Calibri', 10))
label_about.pack()

frame1=tk.Frame(root, relief=tk.GROOVE, bd=1)
frame1.pack(pady=10)

label_url = tk.Label(
    frame1, text=string_url, font=('Calibri', 13))
label_url.grid(column=0,row=0, sticky=tk.NS)
entry_url = tk.Entry(
    frame1, font=('Consolas', 12), width=40, justify=tk.CENTER)
entry_url.grid(column=1,row=0, sticky=tk.NS, padx=5)
button_ok = tk.Button(
    frame1, text=string_ok,font=('Times New Roman', 12), width=13,
    command=callback_ok, cursor="hand2")
button_ok.grid(column=2,row=0, sticky=tk.NS)

frame2=tk.Frame(root, relief=tk.GROOVE, bd=1)
frame2.pack(pady=5)

text_card= tk.Text(
    frame2, font=('Calibri Light', 15, 'italic'), height=5, width=50,
    spacing1=5,spacing2=5, spacing3=5, bg="#FCF5E5", cursor="arrow")
text_card.tag_configure("justify_center", justify='center')
text_card.grid(column=0,row=0)
button_download = tk.Button(
    frame2, text=string_download, font=('Times New Roman', 12),
    command=callback_download, cursor="hand2")
button_download.grid(column=0,row=1, sticky=tk.EW)
button_download.config(state=tk.DISABLED)


root.mainloop()
