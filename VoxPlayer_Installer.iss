; VoxPlayer Windows Installer Script for Inno Setup
; Download Inno Setup from: https://jrsoftware.org/isinfo.php

#define MyAppName "VoxPlayer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VoxPlayer Team"
#define MyAppURL "https://github.com/voxhash/voxplayer"
#define MyAppExeName "VoxPlayer.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=VoxPlayer_Setup_v{#MyAppVersion}
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "fileassociations"; Description: "Associate VoxPlayer with media files"; GroupDescription: "File Associations"; Flags: checked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Video file associations
Root: HKCR; Subkey: ".mp4"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.MP4"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MP4"; ValueType: string; ValueName: ""; ValueData: "MP4 Video File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MP4\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MP4\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".avi"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.AVI"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.AVI"; ValueType: string; ValueName: ""; ValueData: "AVI Video File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.AVI\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.AVI\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".mkv"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.MKV"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MKV"; ValueType: string; ValueName: ""; ValueData: "MKV Video File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MKV\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MKV\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".mov"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.MOV"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MOV"; ValueType: string; ValueName: ""; ValueData: "MOV Video File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MOV\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MOV\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".wmv"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.WMV"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WMV"; ValueType: string; ValueName: ""; ValueData: "WMV Video File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WMV\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WMV\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".flv"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.FLV"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.FLV"; ValueType: string; ValueName: ""; ValueData: "FLV Video File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.FLV\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.FLV\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".webm"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.WEBM"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WEBM"; ValueType: string; ValueName: ""; ValueData: "WebM Video File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WEBM\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WEBM\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".m4v"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.M4V"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.M4V"; ValueType: string; ValueName: ""; ValueData: "M4V Video File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.M4V\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.M4V\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

; Audio file associations
Root: HKCR; Subkey: ".mp3"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.MP3"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MP3"; ValueType: string; ValueName: ""; ValueData: "MP3 Audio File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MP3\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.MP3\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".flac"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.FLAC"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.FLAC"; ValueType: string; ValueName: ""; ValueData: "FLAC Audio File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.FLAC\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.FLAC\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".wav"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.WAV"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WAV"; ValueType: string; ValueName: ""; ValueData: "WAV Audio File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WAV\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WAV\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".ogg"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.OGG"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.OGG"; ValueType: string; ValueName: ""; ValueData: "OGG Audio File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.OGG\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.OGG\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".m4a"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.M4A"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.M4A"; ValueType: string; ValueName: ""; ValueData: "M4A Audio File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.M4A\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.M4A\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".aac"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.AAC"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.AAC"; ValueType: string; ValueName: ""; ValueData: "AAC Audio File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.AAC\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.AAC\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

Root: HKCR; Subkey: ".wma"; ValueType: string; ValueName: ""; ValueData: "VoxPlayer.WMA"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WMA"; ValueType: string; ValueName: ""; ValueData: "WMA Audio File"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WMA\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"; Tasks: fileassociations
Root: HKCR; Subkey: "VoxPlayer.WMA\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassociations

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Check if the application is already running
  if CheckForMutexes('VoxPlayerMutex') then
  begin
    if MsgBox('VoxPlayer is currently running. Please close it before continuing the installation.', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  // Check if the application is running during uninstall
  if CheckForMutexes('VoxPlayerMutex') then
  begin
    if MsgBox('VoxPlayer is currently running. Please close it before continuing the uninstallation.', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;
