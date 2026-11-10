; Instalador do ECont para Windows (Inno Setup 6).
; Instala só para o usuário, sem pedir senha de administrador.
; A versão e as pastas chegam pela linha de comando: /DVersao=1.0.0 /DOrigem=... /DSaida=...

#ifndef Versao
  #define Versao "0.0.0"
#endif

[Setup]
AppId={{6B0D2E64-6E2B-4C55-9A0B-2F7A9C1B5E10}
AppName=ECont
AppVersion={#Versao}
AppVerName=ECont {#Versao}
AppPublisher=Alison Marques
AppPublisherURL=https://github.com/alisonvmarques/econt
DefaultDirName={localappdata}\Programs\ECont
DefaultGroupName=ECont
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Saida}
OutputBaseFilename=ECont-{#Versao}-Windows-instalador
SetupIconFile={#Icone}
UninstallDisplayIcon={app}\ECont.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "pt_br"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar um atalho na Área de Trabalho"; Flags: unchecked

[Files]
Source: "{#Origem}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ECont"; Filename: "{app}\ECont.exe"
Name: "{userdesktop}\ECont"; Filename: "{app}\ECont.exe"; Tasks: atalho

[Run]
Filename: "{app}\ECont.exe"; Description: "Abrir o ECont"; Flags: nowait postinstall skipifsilent
