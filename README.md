# CopyCat-Mac

CopyCat is a desktop clipboard manager built with Python and Tkinter.

This repository contains the macOS-focused version of CopyCat, including setup steps, build instructions, and packaging notes.

## Features

* Clipboard history tracking
* Tkinter-based desktop interface
* macOS app packaging with PyInstaller
* Windows executable build notes
* Lightweight local setup using a Python virtual environment

## Project Setup

This project uses a local Python virtual environment so dependencies stay isolated from your system Python installation.

### macOS / Linux

```bash
# 1) Check that Python 3 is installed
python3 --version

# 2) Create a virtual environment in the project folder
python3 -m venv .venv

# 3) Activate the virtual environment
source .venv/bin/activate

# 4) Upgrade pip
python -m pip install --upgrade pip

# 5) Install project dependencies
pip install -r requirements.txt
```

When you are done working:

```bash
deactivate
```

### Windows PowerShell

```powershell
# 1) Check that Python is installed
py --version

# 2) Create a virtual environment in the project folder
py -m venv .venv

# 3) Activate the virtual environment
. .\.venv\Scripts\Activate.ps1

# 4) Upgrade pip
python -m pip install --upgrade pip

# 5) Install project dependencies
pip install -r requirements.txt
```

If PowerShell blocks activation, run this in the same PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

When you are done working:

```powershell
deactivate
```

## Building the macOS App

Make sure `CopyCat_mac.spec` exists in the project root before building.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Install or update dependencies
python3 -m pip install -U -r requirements.txt

# Remove old build files
rm -rf build dist

# Build the macOS app
pyinstaller CopyCat_mac.spec
```

The built app should appear in:

```txt
dist/CopyCat.app
```

### Copy the App to Applications

```bash
# Stop any currently running version of CopyCat
killall CopyCat 2>/dev/null || true

# Copy the new app into the Applications folder
cp -R dist/CopyCat.app /Applications/
```

### Run the App from the Terminal

This is useful for debugging because errors will show directly in the terminal.

```bash
"/Applications/CopyCat.app/Contents/MacOS/CopyCat"
```

## Building the Windows Executable

Use PyInstaller to create a Windows executable:

```powershell
pyinstaller --noconsole --onefile --name CopyCat main.py
```

This creates:

```txt
dist/CopyCat.exe
```

To create a Windows installer, open `installCopyCat.iss` in Inno Setup Compiler and build the installer from there.

## Tkinter Notes

This app uses Tkinter, so window management needs to follow a few important rules:

* Use only one `Tk()` root per program.
* Use `Toplevel(root)` for additional windows, popups, and dialogs.
* Do not call `mainloop()` on a `Toplevel` window. The main root already runs the event loop.
* Keep GUI updates on the main thread.
* Use a queue or `root.after()` when background threads, such as hotkey listeners, need to trigger GUI updates.

Following these rules helps prevent crashes, freezes, silent failures, and event loop bugs.

## Developer Notes

If the app behaves differently after packaging, run it from the terminal first. This usually makes missing files, import errors, or Tkinter issues easier to see.
