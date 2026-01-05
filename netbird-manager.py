#!/usr/bin/env python3
"""
Netbird Profile Manager for Waybar/Hyprland
A system tray application for managing Netbird VPN profiles
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib, Gdk
import subprocess
import os
import re
import json
import threading

class NetbirdManager:
    def __init__(self):
        # Wait for StatusNotifierWatcher to be available
        self.wait_for_status_notifier_watcher()
        
        # Create the indicator
        self.indicator = AppIndicator3.Indicator.new(
            "netbird-manager",
            "network-vpn",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Fetch available profiles
        self.profiles = self.fetch_profiles()
        
        self.indicator.set_menu(self.build_menu())
        
        self.status_window = None
        self.current_notification_id = None
        
        # Check initial status and set up a timer for periodic checks
        self.status_updating = False
        self.update_status()
        GLib.timeout_add_seconds(300, self.on_timeout)  # Increased to 5 minutes for lightweight operation

    def wait_for_status_notifier_watcher(self, max_wait=10):
        """Wait for StatusNotifierWatcher to be available on D-Bus"""
        import time
        from gi.repository import Gio
        
        for i in range(max_wait):
            try:
                bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
                proxy = Gio.DBusProxy.new_sync(
                    bus,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    'org.kde.StatusNotifierWatcher',
                    '/StatusNotifierWatcher',
                    'org.kde.StatusNotifierWatcher',
                    None
                )
                if proxy:
                    print("StatusNotifierWatcher found!")
                    return
            except Exception as e:
                if i < max_wait - 1:
                    print(f"Waiting for StatusNotifierWatcher... ({i+1}/{max_wait})")
                    time.sleep(1)
                else:
                    print(f"Warning: Could not find StatusNotifierWatcher after {max_wait} seconds")
                    print("Make sure Waybar is running with a tray module configured")

    def fetch_profiles(self):
        """Fetch available Netbird profiles using 'netbird profile list'"""
        try:
            result = subprocess.run(
                ["netbird", "profile", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            profiles = []
            # Skip the first line "Found X profiles:"
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:
                # Line format: "✗ name" or "✓ name"
                parts = line.strip().split(' ', 1)
                if len(parts) > 1:
                    profiles.append(parts[1])
            return profiles
        except Exception as e:
            print(f"Error fetching profiles: {e}")
            return []

    def build_menu(self):
        menu = Gtk.Menu()
        
        # Add status option
        item_status = Gtk.MenuItem(label="Show Status")
        item_status.connect('activate', self.show_status)
        menu.append(item_status)

        # Add separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # Add profile options
        for profile in self.profiles:
            item = Gtk.MenuItem(label=f"Connect: {profile}")
            item.connect('activate', self.connect_profile, profile)
            menu.append(item)
        
        # Add separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # Add disconnect option
        item_down = Gtk.MenuItem(label="Disconnect")
        item_down.connect('activate', self.disconnect)
        menu.append(item_down)
        
        # Add separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # Add quit option
        menu.append(Gtk.SeparatorMenuItem())
        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)
        
        menu.show_all()
        return menu

    def run_command(self, command, success_msg=None):
        """Run a netbird command in a separate thread"""
        def command_thread():
            try:
                subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True
                )
                if success_msg:
                    GLib.idle_add(self.show_notification, "Netbird", success_msg, True)
                GLib.idle_add(self.update_status)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                error_msg = f"Error: {e.stderr.strip() if hasattr(e, 'stderr') and e.stderr else str(e)}"
                GLib.idle_add(self.show_notification, "Netbird Error", error_msg, True)

        thread = threading.Thread(target=command_thread)
        thread.daemon = True
        thread.start()

    def connect_profile(self, _, profile_name):
        """Connect to a specific Netbird profile"""
        self.show_notification("Netbird", f"Connecting to {profile_name} profile...")
        self.run_command(
            f"netbird up --profile {profile_name}", 
            success_msg=f"Connected to {profile_name}"
        )

    def disconnect(self, _):
        """Disconnect from Netbird"""
        self.show_notification("Netbird", "Disconnecting...")
        self.run_command(
            "netbird down", 
            success_msg="Disconnected"
        )

    def refresh_status(self, dialog, textview):
        """Refresh the status dialog in a separate thread"""
        def refresh_thread():
            try:
                # Get status in JSON format (single call)
                result = subprocess.run(
                    ["netbird", "status", "--json"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                status_data = json.loads(result.stdout)
                
                # Construct lines manually to match CLI output style
                lines = []
                lines.append(f"OS: {self.get_os_info()}")
                lines.append(f"Daemon version: {status_data.get('daemonVersion', 'Unknown')}")
                lines.append(f"CLI version: {status_data.get('cliVersion', 'Unknown')}")
                
                mgmt = status_data.get('management', {})
                lines.append(f"Management: {'Connected' if mgmt.get('connected') else 'Disconnected'}")
                
                signal = status_data.get('signal', {})
                lines.append(f"Signal: {'Connected' if signal.get('connected') else 'Disconnected'}")
                
                relays = status_data.get('relays', {})
                lines.append(f"Relays: {relays.get('available', 0)}/{relays.get('total', 0)} Available")
                
                nameservers = status_data.get('dnsServers', [])
                lines.append(f"Nameservers: {len(nameservers)} Available") # Simplified as JSON just gives list
                
                lines.append(f"FQDN: {status_data.get('fqdn', '')}")
                lines.append(f"NetBird IP: {status_data.get('netbirdIp', '')}")
                lines.append(f"Interface type: {'Kernel' if status_data.get('usesKernelInterface') else 'Userspace'}")
                lines.append(f"Quantum resistance: {'true' if status_data.get('quantumResistance') else 'false'}")
                lines.append(f"Lazy connection: {'true' if status_data.get('lazyConnectionEnabled') else 'false'}")
                
                ssh = status_data.get('sshServer', {})
                lines.append(f"SSH Server: {'Enabled' if ssh.get('enabled') else 'Disabled'}")
                
                lines.append(f"Peers count: {status_data.get('peers', {}).get('connected', 0)}/{status_data.get('peers', {}).get('total', 0)} Connected")

                # Get exit node status from events
                exit_node_name = "N/A"
                events = status_data.get("events", [])
                for event in reversed(events):
                    if event.get("userMessage") == "Exit node connected.":
                        exit_node_name = event.get("metadata", {}).get("id", "Unknown")
                        break
                    if event.get("userMessage") == "Exit node connection lost.":
                         # Only reset if we haven't found a newer connect event (which we assume due to 'reversed')
                         # But actually if the last relevant event is disconnect, we should show N/A
                         # Simple logic: first relevant event wins
                         exit_node_name = "Disconnected"
                         break
                
                # If the loop finished and we found "Disconnected", set back to N/A
                if exit_node_name == "Disconnected":
                    exit_node_name = "N/A"

                GLib.idle_add(self.update_status_view, textview, lines, exit_node_name)

            except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error getting status: {e}")
                GLib.idle_add(self.update_status_view_error, textview, str(e))

        thread = threading.Thread(target=refresh_thread)
        thread.daemon = True
        thread.start()

    def get_os_info(self):
        try:
            with open("/etc/os-release") as f:
                d = {}
                for line in f:
                    if "=" in line:
                         k,v = line.rstrip().split("=", 1)
                         d[k] = v.strip('"')
                return f"{d.get('ID', 'linux')}/{subprocess.check_output(['uname', '-m']).decode().strip()}"
        except:
             return "linux/unknown"

    def update_status_view(self, textview, lines, exit_node_name):
        """Update the status text view from the main thread"""
        buffer = textview.get_buffer()
        buffer.set_text("")  # Clear existing content

        for line in lines:
            # Red dot conditions
            if "0/" in line or "N/A" in line or "Disabled" in line or "false" in line or "Disconnected" in line:
                line = f"🔴 {line}"
            # Green dot conditions
            elif "Connected" in line or re.search(r'[1-99]\d*/', line) or "Enabled" in line or "true" in line:
                line = f"🟢 {line}"
            buffer.insert(buffer.get_end_iter(), line + '\n')

        buffer.insert(buffer.get_end_iter(), f"Exit Node: {exit_node_name}\n")

    def update_status_view_error(self, textview, error_message):
        """Update the status text view with an error message"""
        buffer = textview.get_buffer()
        buffer.set_text(f"Error getting status: {error_message}\n")

    def show_status(self, _):
        """Show current Netbird status"""
        try:
            # Check if window already exists and close it if so
            if self.status_window:
                self.status_window.destroy()
                self.status_window = None

            # Create a custom dialog
            dialog = Gtk.Dialog(
                title="Netbird Status",
                transient_for=None,
                flags=Gtk.DialogFlags.DESTROY_WITH_PARENT
            )
            self.status_window = dialog  # Keep reference
            
            dialog.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            dialog.set_modal(False)  # Changed to False so it doesn't block the UI if we want to interact with other things, though logical for a dialog to be modal often. User asked for single instance.
            dialog.set_default_size(600, 400)
            
            
            # Add buttons
            dialog.add_buttons(
                "Refresh", Gtk.ResponseType.APPLY,
                "OK", Gtk.ResponseType.OK
            )

            # Create a scrolled window
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_hexpand(True)
            scrolled_window.set_vexpand(True)
            
            # Create a text view
            textview = Gtk.TextView()
            textview.set_editable(False)
            textview.set_cursor_visible(False)
            
            # Initial status load
            self.refresh_status(dialog, textview)

            scrolled_window.add(textview)
            dialog.get_content_area().add(scrolled_window)
            
            
            dialog.show_all()

            def on_dialog_response(dialog, response_id):
                if response_id == Gtk.ResponseType.APPLY:
                    self.refresh_status(dialog, textview)
                else:
                    dialog.destroy()
                    self.status_window = None

            dialog.connect("response", on_dialog_response)
            
            # Also handle destroy event directly in case user closes via X button
            def on_destroy(widget):
                self.status_window = None
            
            dialog.connect("destroy", on_destroy)
            
        except Exception as e:
            print(f"Error getting status: {e}")

    def on_timeout(self):
        """Callback for periodic status updates"""
        self.update_status()
        return True

    def update_status(self, data=None):
        """Update the indicator icon based on connection status using JSON for efficiency"""
        if self.status_updating:
            return False
            
        def status_thread():
            self.status_updating = True
            base_path = os.path.abspath(os.path.dirname(__file__))
            connected_icon_path = os.path.join(base_path, "netbird.png")
            disconnected_icon_path = os.path.join(base_path, "netbird-grey.png")
            
            try:
                result = subprocess.run(
                    ["netbird", "status", "--json"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10 # Add timeout to prevent hanging
                )
                try:
                    data = json.loads(result.stdout)
                    connected = data.get("management", {}).get("connected", False)
                    
                    if connected:
                        print("Status: Connected (Management)")
                        GLib.idle_add(self.indicator.set_icon_full, connected_icon_path, "Netbird Connected")
                    else:
                        print("Status: Disconnected (Management)")
                        GLib.idle_add(self.indicator.set_icon_full, disconnected_icon_path, "Netbird Disconnected")
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                    GLib.idle_add(self.indicator.set_icon_full, disconnected_icon_path, "Netbird Status Error")

            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                print(f"Error getting status: {e}")
                GLib.idle_add(self.indicator.set_icon_full, disconnected_icon_path, "Netbird Status Unknown")
            finally:
                self.status_updating = False
        
        thread = threading.Thread(target=status_thread)
        thread.daemon = True
        thread.start()
        return False

    def show_notification(self, title, message, replace=False):
        """Show a desktop notification and update current_notification_id"""
        try:
            command = [
                "notify-send",
                "-a", "Netbird Manager",
                "-p"
            ]
            if replace and self.current_notification_id:
                command.extend(["-r", str(self.current_notification_id)])
            
            command.extend([title, message])
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            self.current_notification_id = result.stdout.strip()
        except Exception as e:
            print(f"Error showing notification: {e}")

    def quit(self, _):
        """Quit the application"""
        Gtk.main_quit()

    def run(self):
        """Start the application"""
        Gtk.main()

if __name__ == "__main__":
    app = NetbirdManager()
    app.run()
