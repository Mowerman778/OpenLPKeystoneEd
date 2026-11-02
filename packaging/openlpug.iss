; Inno Setup script for the OpenLPUG Windows installer.
;
; Build steps (on Windows):
;   1. pyinstaller packaging\openlpug.spec        -> dist\OpenLPUG\
;   2. "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\openlpug.iss
;
; Produces Output\OpenLPUG-Setup-x.y.z.exe.

#define AppName "OpenLPUG"
#define AppPublisher "OpenLPUG (a fork of OpenLP, GPL-3.0-or-later)"
#define AppURL "https://openlp.org/"
; AppVersion is passed in by the CI build via /DAppVersion=..., default for local builds:
#ifndef AppVersion
  #define AppVersion "3.1.7"
#endif

[Setup]
AppId={{B5F3C6A2-OPENLPUG-4A1E-9C7D-000000000001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\OpenLPUG.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
OutputBaseFilename=OpenLPUG-Setup-{#AppVersion}
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\OpenLPUG\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\OpenLPUG.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\OpenLPUG.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OpenLPUG.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
; Help > Updates runs the installer with /SILENT once the app has closed: start it again, as the user, not as admin
Filename: "{app}\OpenLPUG.exe"; Flags: nowait skipifnotsilent runasoriginaluser
