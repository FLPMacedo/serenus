; serenus.iss — Inno Setup Script do Serenus
;
; Pré-requisito: rodar "pyinstaller serenus.spec" na raiz do projeto
; antes de compilar este script. O instalador empacota o executável
; gerado em dist\Serenus.exe.
;
; Como compilar:
;   iscc instalador\serenus.iss
; Ou abrir este arquivo no Inno Setup IDE e pressionar F9.
;
; O instalador final será gerado em: instalador\output\SerenusSetup.exe

#define MyAppName      "Serenus"
#define MyAppVersion   "2.1.0"
#define MyAppPublisher "Serenus"
#define MyAppURL       "https://github.com/seu-usuario/serenus"
#define MyAppExeName   "Serenus.exe"
#define MyAppIcon      "..\imagens\logo.ico"
#define DistDir        "..\dist"

[Setup]
AppId={{8A3F2C1D-4B7E-4F9A-BC23-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=SerenusSetup
SetupIconFile={#MyAppIcon}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na Área de Trabalho"; GroupDescription: "Ícones adicionais:"; Flags: unchecked
Name: "startupicon"; Description: "Iniciar com o Windows";            GroupDescription: "Ícones adicionais:"; Flags: unchecked

[Files]
Source: "{#DistDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";             Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";       Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#MyAppName}"; \
  ValueData: """{app}\{#MyAppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
  Description: "Iniciar {#MyAppName} agora"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Dados do usuário em %APPDATA%\Serenus são preservados na desinstalação
