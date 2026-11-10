# Instalação

No Ubuntu, no Linux Mint e no Debian, o ECont se instala e se atualiza pelo gerenciador de
pacotes do sistema. Nos outros sistemas, baixe o instalador na página de
[versões do ECont](https://github.com/alisonvmarques/econt/releases). O ECont não precisa de
internet para funcionar.

## Windows

1. Baixe `ECont-1.0.0-Windows-instalador.exe`.
2. Abra o arquivo. Se aparecer "O Windows protegeu o computador", clique em
   **Mais informações** e depois em **Executar assim mesmo**. O aviso aparece porque o
   instalador não tem assinatura digital paga; o arquivo é o mesmo publicado aqui.
3. Siga o instalador. Ele instala só para o seu usuário e não pede senha de administrador.
4. Abra o ECont pelo menu Iniciar.

Para desinstalar, use **Configurações › Aplicativos**. Os dados não são apagados.

## Ubuntu, Linux Mint e Debian

No Ubuntu (22.04 ou mais novo), no Linux Mint (21 ou mais novo) e no Debian (12 ou mais novo),
o ECont se instala pelo repositório de pacotes dele. Assim, as versões novas aparecem no
**Atualizador de software**, junto com as atualizações do sistema, e você escolhe quando
instalar. Quem baixa a atualização é o sistema: o ECont continua sem acessar a internet.

Uma vez só, no terminal:

```bash
wget -qO- https://alisonvmarques.github.io/econt/econt.gpg \
  | sudo tee /usr/share/keyrings/econt.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/econt.gpg] https://alisonvmarques.github.io/econt/apt/ ./" \
  | sudo tee /etc/apt/sources.list.d/econt.list
sudo apt update
sudo apt install econt
```

Depois, abra o ECont pelo menu de aplicativos. Para atualizar sem esperar o Atualizador:
`sudo apt update && sudo apt upgrade`. Para desinstalar: `sudo apt remove econt` (os dados
não são apagados).

O primeiro comando guarda a chave pública que assina os pacotes: o sistema só aceita uma
atualização assinada por ela.

## Outras distribuições Linux (AppImage)

Para Fedora e outras distribuições, há o AppImage: um arquivo só, que roda sem instalar. Ele
não se atualiza sozinho; para uma versão nova, baixe o arquivo novo.

1. Baixe `ECont-1.0.0-Linux-x86_64.AppImage`.
2. Dê permissão para executar: clique com o botão direito no arquivo, **Propriedades ›
   Permissões › Permitir executar como programa**. Ou, no terminal:

   ```bash
   chmod +x ECont-1.0.0-Linux-x86_64.AppImage
   ```

3. Dê dois cliques no arquivo para abrir.

Se aparecer um erro sobre **FUSE**, abra pelo terminal assim:

```bash
./ECont-1.0.0-Linux-x86_64.AppImage --appimage-extract-and-run
```

## macOS

1. Baixe `ECont-1.0.0-macOS.dmg` e abra.
2. Arraste o ECont para a pasta **Aplicativos**.
3. Na primeira vez, o macOS pode dizer que não consegue verificar o desenvolvedor. Abra
   **Ajustes do Sistema › Privacidade e Segurança** e clique em **Abrir Mesmo Assim** ao lado
   do aviso do ECont.

## Onde ficam os dados

| Sistema | Pasta |
|---|---|
| Windows | `%APPDATA%\ECont` |
| Linux | `~/.local/share/econt` |
| macOS | `~/Library/Application Support/ECont` |

Até novembro de 2026 o sistema se chamava Baliza e guardava os dados em outra pasta (`Baliza`
ou `baliza`, no mesmo lugar). Na primeira vez que abre, o ECont copia os dados e os backups de
lá, com a mesma senha e a mesma chave de recuperação. A pasta antiga fica como estava; depois
de conferir que está tudo no ECont, você pode apagá-la.

O arquivo `dados.econt` é criptografado e só abre com a senha ou a chave de recuperação. Os
backups automáticos ficam na subpasta `backups`. Veja [Configurações](configuracoes.md#backup).
