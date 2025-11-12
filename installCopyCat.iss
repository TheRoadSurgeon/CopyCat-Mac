; -----------------------------
; CopyCat Installer Script
; -----------------------------

[Setup]
AppName=CopyCat
AppVersion=1.0
DefaultDirName={pf}\CopyCat
DefaultGroupName=CopyCat
DisableProgramGroupPage=yes
OutputBaseFilename=CopyCatInstaller
Compression=lzma
SolidCompression=yes

[Files]
; Copy everything from your PyInstaller dist folder
Source: "dist\CopyCat.exe"; DestDir: "{app}"; Flags: ignoreversion

; (Optional) include any resources your app needs:
; Source: "resources\*"; DestDir: "{app}\resources"; Flags: recursesubdirs ignoreversion

[Run]
; Create the scheduled task on install
Filename: "schtasks.exe"; \
  Parameters: "/Create /TN ""CopyCat Background"" /SC ONLOGON /RL HIGHEST /TR ""{app}\CopyCat.exe"" /F"; \
  Flags: runhidden; \
  StatusMsg: "Registering background startup task..."

[UninstallRun]
; Kill any running instances of CopyCat.exe
Filename: "taskkill.exe"; \
  Parameters: "/IM CopyCat.exe /F"; \
  Flags: runhidden ignoreerrors;

; Stop the task
Filename: "schtasks.exe"; \
  Parameters: "/End /TN ""CopyCat Background"""; \
  Flags: runhidden ignoreerrors;

; Delete the task
Filename: "schtasks.exe"; \
  Parameters: "/Delete /TN ""CopyCat Background"" /F"; \
  Flags: runhidden ignoreerrors;

[Icons]
Name: "{group}\CopyCat"; Filename: "{app}\CopyCat.exe"
Name: "{group}\Uninstall CopyCat"; Filename: "{uninstallexe}"
