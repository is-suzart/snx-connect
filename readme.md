# SNX Connect GUI

<p align="center"> <img src="src/assets/snx-icon.png" alt="SNX Connect Icon" width="128"/> </p>

<p align="center"> A modern, simple, and elegant GTK4/Libadwaita GUI client for the Check Point SNX VPN, designed for Linux desktops. </p>

<p align="center">
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
<img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="License">
<img src="https://img.shields.io/badge/status-active-success.svg" alt="Project Status">
</p>

<!-- Suggestion: Add a screenshot of your app here! -->

## ✨ Features

- **Modern Interface:** Built with GTK4 and Libadwaita for a clean look and feel that integrates perfectly with modern Linux desktops.
    
- **Easy Connection:** Simply enter your server, username, and password to connect.
    
- **Session Management:** Save your login credentials securely for quick access.
    
- **Route Management:** Easily add and remove specific IP routes that should go through the VPN tunnel.
    
- **Theme Aware:** Automatically adapts its appearance (including the logo) to your system's light or dark theme preference.
    
- **Internationalization:** Available in multiple languages (English, Portuguese, Spanish, French).
    
- **Auto-Installer:** If the `snx` binary is not found, the app will offer to install it for you (requires `pkexec`).
    

## 📦 Installation

Choose the installation method that best suits your Linux distribution.

### 1. Debian / Ubuntu and derivatives (.deb package)

This is the recommended method for Debian-based systems.

**a) Critical Prerequisite: Enable 32-bit Architecture** The SNX binary is 32-bit and will not work on a 64-bit system without multi-arch support. This is a mandatory first step.

```
sudo dpkg --add-architecture i386
sudo apt update
```

**b) Install the Package** Download the latest `.deb` file from the [Releases page](https://www.google.com/search?q=https://github.com/igorsuzart/snx-connect/releases "null") and install it using `apt`. `apt` will automatically handle all required dependencies.

```
# Replace with the actual downloaded file name
sudo apt install ./snx-connect-gui_1.0.0-1_amd64.deb
```

You can now find "SNX Connect" in your applications menu.

### 2. Arch Linux and derivatives (AUR)

This is the easiest method if you are on Arch Linux or a derivative like Manjaro.

**a) Enable the `multilib` repository:** The SNX binary is 32-bit, so you need to enable the `multilib` repository. Edit your `/etc/pacman.conf` file:

```
[multilib]
Include = /etc/pacman.d/mirrorlist
```

Then, update your system:

```
sudo pacman -Syu
```

**b) Build and Install the Package:** Clone this repository and run `makepkg` from the project's root directory.

```
git clone https://github.com/igorsuzart/snx-connect.git
cd snx-connect
makepkg -si
```

The `-s` flag will automatically install all required dependencies from the official repositories, and the `-i` flag will install the package after a successful build.

You can then find "SNX Connect" in your applications menu.

## 🚀 Usage

1. Launch the "SNX Connect" application from your menu.
    
2. Enter your VPN server address, username, and password.
    
3. Click "Connect".
    
4. Once connected, you can manage specific IP routes that should be tunneled through the VPN via the header menu.
    

## 🤝 Let's Connect & Collaborate!

This project was a fantastic learning journey, and I'm always excited to connect with other developers. Have an idea for this app? Found a bug? Or just want to chat about code and build cool things together?

Find me on Discord: **https://discord.gg/jTTwQKwnAb**

Let's build more awesome projects!

## 📄 License

This project is licensed under the GPLv3 License - see the [LICENSE](https://www.google.com/search?q=LICENSE "null") file for details.