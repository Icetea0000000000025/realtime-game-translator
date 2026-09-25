#define MyAppName "Realtime Game Translator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Realtime Translator Team"
#define MyAppExeName "RealtimeGameTranslator.exe"
#define MyAppDebugExeName "RealtimeGameTranslator_Debug.exe"
#define MyAppIcon "C:\Users\ASUS\realtime-game-translator\app_icon.ico"
#define SourceDir "C:\Users\ASUS\realtime-game-translator\dist\RealtimeGameTranslator"

[Setup]
AppId={{E8A42D77-3B21-4F1A-B82C-1E43D8F5C9A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir="C:\Users\ASUS\realtime-game-translator\dist"
OutputBaseFilename=RealtimeGameTranslator_Setup
SetupIconFile={#MyAppIcon}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{autoprograms}\{#MyAppName} (Debug Console)"; Filename: "{app}\{#MyAppDebugExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
