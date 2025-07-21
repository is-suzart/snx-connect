# Maintainer: Seu Nome <seu.email@exemplo.com>
pkgname=snx-connect-gui
pkgver=1.0.0
pkgrel=1
pkgdesc="Cliente de GUI para a VPN Check Point SNX"
arch=('x86_64')
url="https://github.com/igorsuzart/snx-connect" # Altere se for diferente
license=('GPL3')

# Dependências necessárias para a aplicação correr
depends=(
    'gtk4'
    'libadwaita'
    'python-gobject'
    'python-pexpect'
    'polkit'
    'glibc'
)

# Dependências de 32 bits necessárias para o binário 'snx'
# Estas vêm do repositório 'multilib' do Arch.
depends_x86_64=(
    'lib32-gcc-libs' # Fornece a libstdc++.so.5
    'lib32-glibc'
)

# --- FONTE ---
# Esta configuração copia todos os ficheiros do diretório atual
# para o ambiente de construção. Perfeito para desenvolvimento.
source=("$pkgname-$pkgver.tar.gz::https://github.com/igorsuzart/snx-connect/archive/refs/tags/v$pkgver.tar.gz")
# Para desenvolvimento local, pode usar:
# source=("$pkgname-$pkgver::local_source_dir")

# Checksums para garantir a integridade dos ficheiros-fonte
sha256sums=('SKIP') # Use 'SKIP' para testes locais. Para um lançamento real, geraria o hash.

# Esta função prepara os ficheiros-fonte (se necessário)


# Esta é a função principal: ela instala os ficheiros no pacote.
package() {
    

    # 1. Instalar os ficheiros da aplicação Python
    install -d "$pkgdir/opt/$pkgname"
    cp -r ui back_end.py controller.py main.py style.css "$pkgdir/opt/$pkgname/"

    # 2. Instalar assets, ícones e traduções
    install -d "$pkgdir/opt/$pkgname/assets"
    cp -r assets/* "$pkgdir/opt/$pkgname/assets/"

    install -d "$pkgdir/opt/$pkgname/bin"
    cp -r bin/* "$pkgdir/opt/$pkgname/bin/"
    
    install -d "$pkgdir/usr/share/icons/hicolor/128x128/apps"
    install -m644 "assets/snx-icon.png" "$pkgdir/usr/share/icons/hicolor/128x128/apps/$pkgname.png"
    
    install -d "$pkgdir/opt/$pkgname/i18n"
    cp -r i18n/* "$pkgdir/opt/$pkgname/i18n/"
    

    # 3. Instalar o binário SNX e o script de desinstalação
    # Usamos o próprio script de instalação do SNX, mas direcionamos a instalação para dentro do nosso pacote
    # A variável de ambiente DESTDIR faz com que o script instale em $pkgdir em vez do sistema real.
    DESTDIR="$pkgdir" sh ./bin/snx_install_linux30.sh

    
    # 4. Instalar o ficheiro .desktop
    install -d "$pkgdir/usr/share/applications"
    install -m644 "snx-connect.desktop" "$pkgdir/usr/share/applications/"

    # 5. Instalar um script wrapper para lançar a aplicação
    install -d "$pkgdir/usr/bin"
    echo "#!/bin/sh" > "$pkgdir/usr/bin/$pkgname"
    echo "cd /opt/$pkgname && python3 main.py" >> "$pkgdir/usr/bin/$pkgname"
    chmod +x "$pkgdir/usr/bin/$pkgname"
}
