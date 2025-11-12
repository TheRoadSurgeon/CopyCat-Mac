# Project Setup (Python + Virtual Environment)

This project uses a local Python **virtual environment** so everyone’s packages stay isolated.

---

macOS / Linux

```bash
# 1) Check Python 3 is installed
python3 --version

# 2) Create a local virtual environment in the project folder
python3 -m venv .venv

# 3) Activate the virtual environment (you should see (.venv) in your prompt)
source .venv/bin/activate

# 4) Upgrade pip (optional but recommended)
python -m pip install --upgrade pip

# 5) Install project dependencies
#    Make sure requirements.txt is in the project root
pip install -r requirements.txt

# (Optional) When done working, deactivate the venv
# deactivate


Windows (PowerShell)


# 1) Check Python is installed
py --version

# 2) Create a local virtual environment in the project folder
py -m venv .venv

# 3) Activate the virtual environment (you should see (.venv) in your prompt)
. .\.venv\Scripts\Activate.ps1

#   If activation is blocked, run this once in the same PowerShell window:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 4) Upgrade pip (optional but recommended)
python -m pip install --upgrade pip

# 5) Install project dependencies
pip install -r requirements.txt

# (Optional) When done working, deactivate the venv
# deactivate
```

## Creating Installation Executable (Windows)
Execute `pyinstaller --noconsole --onefile --name CopyCat main.py` to create a CopyCat.exe

Use `installCopyCat.iss` to create a installation exe in Ino Setup Compiler

## NOTES/TIPS
Tkinter Key Rule for Our App

Only one Tk() root per program – creating another causes crashes, freezes, or silent failures.

Use Toplevel(root) for any extra windows (popups, dialogs).

Do not call mainloop() on Toplevel – the main root already runs it.

GUI must run on the main thread – use a queue or root.after() to safely trigger popups from background threads (like hotkeys).

✅ This ensures all windows share the same event loop and data (like clipboard_history).

