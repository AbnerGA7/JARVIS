; Instalador de J.A.R.V.I.S. (lo compila compilar_exe.bat con Inno Setup)
#define AppVer "2.8"

[Setup]
AppId={{9794BCDA-6E0F-4F74-B1AA-230D94D787B7}
AppName=J.A.R.V.I.S.
AppVersion={#AppVer}
AppVerName=J.A.R.V.I.S. {#AppVer}
AppPublisher=Stark Industries (edición casera)
DefaultDirName={localappdata}\Programs\JARVIS
DefaultGroupName=JARVIS
PrivilegesRequired=lowest
OutputDir=salida
OutputBaseFilename=JARVIS_Setup
SetupIconFile=jarvis.ico
UninstallDisplayIcon={app}\JARVIS.exe
UninstallDisplayName=J.A.R.V.I.S.
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear acceso directo en el escritorio"

[Files]
Source: "dist\JARVIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "jarvis.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\JARVIS"; Filename: "{app}\JARVIS.exe"; IconFilename: "{app}\jarvis.ico"
Name: "{group}\Desinstalar JARVIS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\JARVIS"; Filename: "{app}\JARVIS.exe"; IconFilename: "{app}\jarvis.ico"; Tasks: escritorio

[Registry]
; JARVIS se inicia solo al encender la PC (se puede desactivar desde su menú)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "JARVIS"; ValueData: """{app}\JARVIS.exe"" --inicio"; Flags: uninsdeletevalue

[Run]
Filename: "https://console.groq.com/keys"; Description: "Abrir Groq para crear mi clave gratuita (cerebro en la nube)"; Flags: shellexec postinstall skipifsilent unchecked
Filename: "{app}\JARVIS.exe"; Description: "Iniciar JARVIS ahora"; Flags: nowait postinstall

[UninstallRun]
Filename: "taskkill"; Parameters: "/IM JARVIS.exe /F"; Flags: runhidden; RunOnceId: "CerrarJarvis"
