import os
import PyInstaller.__main__
from win32com.client import Dispatch

from swinlnk.swinlnk import SWinLnk
from config import testing, first_run


def create_exe():
    PyInstaller.__main__.run(["scrape.py", "--onefile", "--icon=.\\logo192.webp"])


def create_shortcut():
    shortcut_name = "manga-scraper.lnk"
    swl = SWinLnk()
    startup = os.path.expandvars(
        r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    )
    shortcut_path = f"{startup}\\{shortcut_name}"

    shortcut_target = f"{os.path.abspath('./dist/scrape.exe')}"
    swl.create_lnk(shortcut_target, shortcut_path)


def shrtcut():
    import os

    shortcut_name = "manga-scraper.lnk"
    startup = os.path.expandvars(
        r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    )
    shortcut_path = f"{startup}\\{shortcut_name}"

    path = shortcut_path  # Path to be saved (shortcut)
    # The shortcut target file or folder
    target = f"{os.path.abspath('./dist/scrape.exe')}"
    work_dir = f"{os.path.abspath('./dist')}"  # The parent folder of your file

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = target
    shortcut.WorkingDirectory = work_dir
    shortcut.save()


if __name__ == "__main__":
    try:
        if testing or not first_run:
            print("testing is set to true muppet")
            raise Exception
        create_exe()
        shrtcut()
    except:
        pass
    # move_to_startup()
    # print('done')
    # sys.exit(0)
