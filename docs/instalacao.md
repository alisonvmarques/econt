# Instalação

Baixe o instalador do seu sistema na página de
[versões do Baliza](https://github.com/alisonvmarques/baliza/releases). Depois de instalado, o
Baliza não precisa de internet.

## Windows

1. Baixe `Baliza-1.0.0-Windows-instalador.exe`.
2. Abra o arquivo. Se aparecer "O Windows protegeu o computador", clique em
   **Mais informações** e depois em **Executar assim mesmo**. O aviso aparece porque o
   instalador não tem assinatura digital paga; o arquivo é o mesmo publicado aqui.
3. Siga o instalador. Ele instala só para o seu usuário e não pede senha de administrador.
4. Abra o Baliza pelo menu Iniciar.

Para desinstalar, use **Configurações › Aplicativos**. Os dados não são apagados.

## Linux

O Baliza para Linux é um AppImage: um arquivo só, que roda sem instalar, na maioria das
distribuições (Ubuntu, Linux Mint, Debian, Fedora e outras).

1. Baixe `Baliza-1.0.0-Linux-x86_64.AppImage`.
2. Dê permissão para executar: clique com o botão direito no arquivo, **Propriedades ›
   Permissões › Permitir executar como programa**. Ou, no terminal:

   ```bash
   chmod +x Baliza-1.0.0-Linux-x86_64.AppImage
   ```

3. Dê dois cliques no arquivo para abrir.

Se aparecer um erro sobre **FUSE**, abra pelo terminal assim:

```bash
./Baliza-1.0.0-Linux-x86_64.AppImage --appimage-extract-and-run
```

Guarde o AppImage numa pasta fixa (por exemplo, `~/Aplicativos`). Para uma versão nova, troque
o arquivo pelo novo; os dados ficam em outro lugar e continuam os mesmos.

## macOS

1. Baixe `Baliza-1.0.0-macOS.dmg` e abra.
2. Arraste o Baliza para a pasta **Aplicativos**.
3. Na primeira vez, o macOS pode dizer que não consegue verificar o desenvolvedor. Abra
   **Ajustes do Sistema › Privacidade e Segurança** e clique em **Abrir Mesmo Assim** ao lado
   do aviso do Baliza.

## Onde ficam os dados

| Sistema | Pasta |
|---|---|
| Windows | `%APPDATA%\Baliza` |
| Linux | `~/.local/share/baliza` |
| macOS | `~/Library/Application Support/Baliza` |

O arquivo `dados.baliza` é criptografado e só abre com a senha ou a chave de recuperação. Os
backups automáticos ficam na subpasta `backups`. Veja [Configurações](configuracoes.md#backup).
