# Netbird Waybar Manager - Installation Guide

## Prerequisites

Install the required dependencies:

```bash
sudo pacman -S python-gobject libappindicator-gtk3 gtk3 libnotify
```

## Installation Steps

### 1. Save the Python Script

```bash
# Create a directory for the script
mkdir -p ~/.local/bin

# Save the script (copy the Python code to this file)
nano ~/.local/bin/netbird-manager.py

# Make it executable
chmod +x ~/.local/bin/netbird-manager.py
```

### 2. Create Desktop Entry

Create a desktop entry so the app appears in your application menu:

```bash
mkdir -p ~/.local/share/applications
nano ~/.local/share/applications/netbird-manager.desktop
```

Add this content:

```ini
[Desktop Entry]
Name=Netbird Manager
Comment=Manage Netbird VPN Profiles
Exec=/home/YOUR_USERNAME/.local/bin/netbird-manager.py
Icon=network-vpn
Terminal=false
Type=Application
Categories=Network;
StartupNotify=false
```

Replace `YOUR_USERNAME` with your actual username.

### 3. Auto-start on Login (Optional)

To start the app automatically when you log in:

```bash
mkdir -p ~/.config/autostart
cp ~/.local/share/applications/netbird-manager.desktop ~/.config/autostart/
```

### 4. Running the Application

Start the application:

```bash
~/.local/bin/netbird-manager.py
```

Or launch it from your application menu.

## Usage

- The app will appear in your system tray (Waybar)
- **Right-click** on the icon to see the menu
- Select a profile to connect or disconnect
- The icon changes based on connection status:
  - Connected: VPN icon
  - Disconnected: Disconnected VPN icon

## Menu Options

- **Connect: Hinemoa** - Runs `netbird up --profile hinemoa`
- **Connect: Stella** - Runs `netbird up --profile stella`
- **Disconnect** - Runs `netbird down`
- **Show Status** - Displays current Netbird status
- **Quit** - Closes the application

## Troubleshooting

### App doesn't appear in system tray

1. Make sure Waybar is configured to show system tray icons
2. Check your Waybar config (`~/.config/waybar/config`) has a tray module:

```json
"modules-right": ["tray", ...],
"tray": {
    "spacing": 10
}
```

### Permission issues

If you get permission errors running netbird commands, you may need to configure sudo or set up proper permissions for netbird.

### Icon not showing

If the VPN icons don't show, install an icon theme:

```bash
sudo pacman -S papirus-icon-theme
```

## Customization

You can edit the script to:
- Add more profiles
- Change notification behavior
- Customize menu items
- Add more netbird commands

Just edit `~/.local/bin/netbird-manager.py` and restart the application.
