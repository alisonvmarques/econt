; Instalador do Baliza para Windows (Inno Setup 6).
; Instala só para o usuário, sem pedir senha de administrador.
; A versão e as pastas chegam pela linha de comando: /DVersao=1.0.0 /DOrigem=... /DSaida=...

#ifndef Versao
  #define Versao "0.0.0"
#endif

[Setup]
AppId={{6B0D2E64-6E2B-4C55-9A0B-2F7A9C1B5E10}
AppName=Baliza
AppVersion={#Versao}
AppVerName=Baliza {#Versao}
AppPublisher=Alison Marques
AppPublisherURL=https://github.com/alisonvmarques/baliza
DefaultDirName={localappdata}\Programs\Baliza
DefaultGroupName=Baliza
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Saida}
OutputBaseFilename=Baliza-{#Versao}-Windows-instalador
SetupIconFile={#Icone}
UninstallDisplayIcon={app}\Baliza.exe
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
Name: "{group}\Baliza"; Filename: "{app}\Baliza.exe"
Name: "{userdesktop}\Baliza"; Filename: "{app}\Baliza.exe"; Tasks: atalho

[Run]
Filename: "{app}\Baliza.exe"; Description: "Abrir o Baliza"; Flags: nowait postinstall skipifsilent
