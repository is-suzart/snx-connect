SNX Connect GUI
<p align="center">
<img src="assets/snx-icon.png" alt="SNX Connect Icon" width="128"/>
</p>

<p align="center">
A modern, simple, and elegant GTK4/Libadwaita GUI client for the Check Point SNX VPN, designed for Linux desktops.
</p>

<p align="center">
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
<img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="License">
<img src="https://img.shields.io/badge/status-active-success.svg" alt="Project Status">
</p>

<!-- Sugestão: Adicione um screenshot do seu app aqui -->

✨ Features
Modern Interface: Built with GTK4 and Libadwaita for a clean look and feel that integrates perfectly with modern Linux desktops.

Easy Connection: Simply enter your server, username, and password to connect.

Session Management: Save your login credentials securely for quick access.

Route Management: Easily add and remove specific IP routes that should go through the VPN tunnel.

Theme Aware: Automatically adapts its appearance (including the logo) to your system's light or dark theme preference.

Internationalization: Available in multiple languages (English, Portuguese, Spanish, French).

Auto-Installer: If the snx binary is not found, the app will offer to install it for you (requires pkexec).

📦 Installation
There are two ways to install and run SNX Connect.

1. From the Arch Linux Package (Recommended for Arch Users)
This is the easiest method if you are on Arch Linux or a derivative.

a) Enable the multilib repository:
The SNX binary is 32-bit, so you need to enable the multilib repository. Edit your /etc/pacman.conf file:

[multilib]
Include = /etc/pacman.d/mirrorlist

Then, update your system:

sudo pacman -Syu

b) Build and Install the Package:
Clone this repository and run makepkg from the project's root directory.

git clone https://github.com/igorsuzart/snx-connect.git
cd snx-connect
makepkg -si

The -s flag will automatically install all required dependencies from the official repositories, and the -i flag will install the package after a successful build.

You can then find "SNX Connect" in your applications menu.

2. From Source (For other distributions)
a) Install Dependencies:
You will need to install the required dependencies for your specific distribution.

SNX Binary: The snx binary and its 32-bit libraries are required. You can try running the included installation script:

sudo sh bin/snx_install_linux30.sh

You may also need to install 32-bit compatibility libraries. On Debian/Ubuntu, this would be:

sudo dpkg --add-architecture i386
sudo apt update
sudo apt install libc6:i386 libstdc++5:i386

Python & GTK Dependencies:
On Debian/Ubuntu:

sudo apt install python3 python3-pip python3-gobject gir1.2-gtk-4.0 gir1.2-adw-1

On Arch Linux:

sudo pacman -S python python-pip python-gobject gtk4 libadwaita

On Fedora:

sudo dnf install python3 python3-pip pygobject3 gtk4 libadwaita

Python Libraries:

pip install pexpect

b) Run the Application:
After installing all dependencies, you can run the application directly from the source code:

python3 main.py

🚀 Usage
Launch the "SNX Connect" application from your menu.

Enter your VPN server address, username, and password.

Click "Connect".

Once connected, you can manage specific IP routes that should be tunneled through the VPN.

🤝 Contributing
Contributions are welcome! If you have ideas for new features, bug fixes, or improvements, feel free to open an issue or submit a pull request.

📄 License
This project is licensed under the GPLv3 License - see the LICENSE file for details.