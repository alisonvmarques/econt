#!/usr/bin/env bash
# Monta o repositório de pacotes do Ubuntu (formato simples, sem distribuições) com o .deb
# da versão atual e assina com a chave já importada no GnuPG.
# Uso: bash scripts/repositorio_apt.sh <pasta com o .deb> <pasta do repositório>
set -euo pipefail
origem="$1"
destino="$2"
mkdir -p "$destino"
cp "$origem"/econt_*_amd64.deb "$destino"/
cd "$destino"
apt-ftparchive packages . > Packages
gzip -9 -k -f Packages
apt-ftparchive \
  -o APT::FTPArchive::Release::Origin=ECont \
  -o APT::FTPArchive::Release::Label=ECont \
  -o "APT::FTPArchive::Release::Description=Pacotes do ECont" \
  release . > ../Release.novo
# Gerado fora da pasta: senão o Release listaria a si mesmo, ainda pela metade.
mv ../Release.novo Release
gpg --batch --yes --clearsign -o InRelease Release
gpg --batch --yes --armor --detach-sign -o Release.gpg Release
ls -l
