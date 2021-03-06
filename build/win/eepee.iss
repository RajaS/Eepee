; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{F988B6E2-27FF-4E61-A72C-B94DEBD1A843}
AppName=eepee
AppVerName=eepee 0.9.5
AppPublisherURL=http://code.google.com/p/eepee
AppSupportURL=http://code.google.com/p/eepee
AppUpdatesURL=http://code.google.com/p/eepee
DefaultDirName={pf}\eepee
DefaultGroupName=eepee
AllowNoIcons=yes
OutputBaseFilename=setup
SetupIconFile=F:\eepee-0.9.5\win_build\icon32.ico
Compression=lzma
SolidCompression=yes

[Languages]
Name: english; MessagesFile: compiler:Default.isl

[Tasks]
Name: desktopicon; Description: {cm:CreateDesktopIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked
Name: quicklaunchicon; Description: {cm:CreateQuickLaunchIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked

[Files]
Source: F:\eepee-0.9.5\win_build\eepee.exe; DestDir: {app}; Flags: ignoreversion
Source: F:\eepee-0.9.5\win_build\samples\1.jpg; DestDir: {app}\samples
Source: F:\eepee-0.9.5\win_build\samples\2.jpg; DestDir: {app}\samples
Source: F:\eepee-0.9.5\win_build\samples\.1.pkl; DestDir: {app}\samples

; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: {group}\eepee; Filename: {app}\eepee.exe
Name: {group}\{cm:UninstallProgram,eepee}; Filename: {uninstallexe}
Name: {commondesktop}\eepee; Filename: {app}\eepee.exe; Tasks: desktopicon
Name: {userappdata}\Microsoft\Internet Explorer\Quick Launch\eepee; Filename: {app}\eepee.exe; Tasks: quicklaunchicon

[Run]
Filename: {app}\eepee.exe; Description: {cm:LaunchProgram,eepee}; Flags: nowait postinstall skipifsilent
