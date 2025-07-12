# back_end.py
import subprocess
import re
import io
import json
import os
import logging
import shutil
import pexpect
import sys

# --- Exceções Customizadas ---
# É uma boa prática criar exceções específicas para o seu domínio.
# Isso torna o tratamento de erros no Controller muito mais claro.
class VpnError(Exception):
    """Base exception for all VPN related errors."""
    pass

class ConnectionError(VpnError):
    """Raised for errors during the connection process."""
    pass

class DisconnectionError(VpnError):
    """Raised for errors during the disconnection process."""
    pass

class RouteError(VpnError):
    """Raised for errors related to managing routes."""
    pass

class DependencyError(VpnError):
    """Raised for errors related to system dependencies."""
    pass

# --- Classe de Utilitários (Dependência Interna do Model) ---
class Utils:
    """Utility functions for reading/writing JSON configuration."""
    def __init__(self):
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "snx-connect")
        os.makedirs(config_dir, exist_ok=True)
        self.config_file = os.path.join(config_dir, "snx-data.json")

    def read_json(self):
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def write_json(self, data):
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=4)

    def extract_ip_addresses(self, nslookup_output_lines):
        ips = set()
        address_pattern = re.compile(r"^\s*Address:\s*([0-9a-fA-F.:]+)")
        for i, line in enumerate(nslookup_output_lines):
            if line.lstrip().startswith("Name:"):
                if i + 1 < len(nslookup_output_lines):
                    next_line = nslookup_output_lines[i + 1]
                    match = address_pattern.match(next_line)
                    if match:
                        ip = match.group(1)
                        if ":" not in ip: # Filtra endereços IPv6
                            ips.add(ip)
        return list(ips)

# --- O Model Principal ---
class VpnManager:
    """
    The main Model class. Encapsulates all business logic for interacting
    with the SNX VPN and managing configuration.
    This class is synchronous and thread-unaware.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.utils = Utils()
        self.office_mode_ip = self.utils.read_json().get("ip")
        self.server = None
        self.username = None
        self.password = None
        self.keep_info = False

    # --- Dependency Management ---
    def check_dependencies(self):
        """Checks for required system dependencies."""
        return {
            "snx_installed": shutil.which("snx") is not None,
            "pkexec_installed": shutil.which("pkexec") is not None,
        }
    
    def set_keep_routes(self, keep):
        """Sets whether to keep routes on disconnect."""
        data = self.utils.read_json()
        print(f"Setting keep routes to: {keep}")
        data["keepAddr"] = keep
        self.utils.write_json(data)
        self.logger.info(f"Keep routes set to: {keep}")

    def install_snx(self):
        """Attempts to install SNX using the local script. Synchronous."""
        self.logger.info("Attempting to install SNX via local script...")
        dirname = os.path.dirname(__file__)
        script_path = os.path.join(dirname, "bin", "snx_install_linux30.sh")

        if not os.path.exists(script_path):
            raise DependencyError("Installation script not found.")
        
        try:
            process = subprocess.run(
                ["pkexec", "sh", script_path], 
                check=True, capture_output=True, text=True
            )
            self.logger.info(f"SNX installation script successful. Output: {process.stdout}")
            return {"status": True, "message": "Installation successful!"}
        except FileNotFoundError:
            raise DependencyError("pkexec command not found.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"SNX installation script failed: {e.stderr}")
            raise DependencyError(f"Installation failed or was cancelled.\nDetail: {e.stderr}")

    # --- Connection Logic ---
    def connect(self, server, username, password, keep_info):
        """Connects to the VPN. This is a blocking, synchronous method."""
        self.server = server
        self.username = username
        self.password = password
        self.keep_info = keep_info
        
        if not all([server, username, password]):
            raise ConnectionError("Server, username, and password must be provided.")
        
        command = f"snx -s {server} -u {username}"
        try:
            child = pexpect.spawn(command, encoding='utf-8', logfile=sys.stdout)
            
            child.expect("[Pp]assword:", timeout=15)
            child.sendline(password)
            
            index = child.expect(['accept?', 'Office', pexpect.EOF], timeout=30)
            
            if index == 0: # 'accept?'
                child.sendline("y")
                child_index = child.expect(['Office','denied'], timeout=20)
                if child_index == 1: # 'denied'
                    raise ConnectionError("Connection denied by SNX. Check your credentials or server settings.")
                elif child_index == 0: # 'Office'
                    self.logger.info("Accepted connection request.")
                    result = self.get_ip_and_connect(child.buffer)
                    return result
                    
            elif index == 2: # EOF
                raise ConnectionError("SNX process ended unexpectedly after password.")
            
            else: # 'Office'
                self.logger.info("Connected to SNX without needing to accept terms.")
                result = self.get_ip_and_connect(child.buffer, None)
                return result
            
            child.expect(pexpect.EOF) # Wait for the process to finish

        except pexpect.exceptions.TIMEOUT:
            raise ConnectionError("Connection timed out waiting for a response from SNX.")
        except pexpect.exceptions.EOF:
            output = child.before
            if "Another session" in output:
                storage_ip = self.utils.read_json()['ip']
                if storage_ip:
                    self.office_mode_ip = storage_ip
                    self.logger.info(f"Using stored Office Mode IP: {self.office_mode_ip}")
                    return self.get_ip_and_connect(output, storage_ip)
                else:
                    raise ConnectionError("Another session detected, but no stored IP found.")
            else:
                raise ConnectionError("SNX process terminated unexpectedly before connection.")
        finally:
            if 'child' in locals() and child.isalive():
                child.close()
                
    def get_ip_and_connect(self,output,ip):
        if not ip:
            pattern = r"Mode IP\s+:\s+([0-9\.]+)"
            match = re.search(pattern, output)
            if not match:
                raise ConnectionError("Office Mode IP not found in SNX output.")
        else:
            match = ip
        if not self.office_mode_ip:
            self.office_mode_ip = match.group(1).strip()
            self.logger.info(f"Office Mode IP obtained: {self.office_mode_ip}")
            
        # Persist data if requested
        self._update_connection_data(self.server, self.username, self.password, self.keep_info)
        
        config = self.utils.read_json()
        if config.get("keepAddr", False):
            self.logger.info("Keeping routes on disconnect as per user settings.")
            self._auto_add_saved_routes()
        else:
            self.logger.info("Not keeping routes on disconnect as per user settings.")
            
        return {"status": True, "office_ip": self.office_mode_ip}
        
    def _update_connection_data(self, server, username, password, keep_info):
        """Saves connection info to the JSON file."""
        data = self.utils.read_json()
        data["ip"] = self.office_mode_ip
        if keep_info:
            data["server"] = server
            data["username"] = username
            data["password"] = password
            data["keepinfo"] = True
        self.utils.write_json(data)
    
    def _auto_add_saved_routes(self):
        """Internal method to add all saved routes after connecting."""
        if not self.office_mode_ip:
            self.logger.error("Cannot auto-add routes, Office Mode IP is not available.")
            return

        routes_data = self.utils.read_json()
        commands = []
        for key, value in routes_data.items():
            if key.endswith("Address") and isinstance(value, list):
                for ip in value:
                    commands.append(f"ip route add {ip} via {self.office_mode_ip}")
        
        if commands:
            self.logger.info("Executing auto-add route script.")
            try:
                self._run_privileged_commands(commands)
                self.logger.info("Successfully auto-added saved routes.")
            except VpnError as e:
                # Log the error but don't crash the connection process
                self.logger.error(f"Failed to auto-add routes: {e}")
        else:
            self.logger.info("No saved routes to auto-add.")
        
    # --- Disconnection Logic ---
    def disconnect(self):
        """Disconnects from the VPN. Synchronous."""
        try:
            self.logger.info("Attempting VPN disconnection using 'snx -d'.")
            subprocess.run("snx -d", shell=True, check=True, text=True, capture_output=True)
            self._delete_saved_routes()
            self._update_json_on_disconnect()
            self.office_mode_ip = None
            return {"message": "Disconnected successfully."}
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"'snx -d' failed. This might be normal. Stderr: {e.stderr}")
            # Assume disconnection anyway and proceed with cleanup
            self._delete_saved_routes()
            self._update_json_on_disconnect()
            return {"message": "Disconnected, 'snx -d' reported an error (might be ok)."}
        except Exception as e:
            raise DisconnectionError(f"A critical error occurred: {e}")

    def _update_json_on_disconnect(self):
        """Cleans up the JSON file on disconnect based on user settings."""
        data = self.utils.read_json()
        final_data = {}
        if data.get("keepinfo", False):
            final_data = {
                "server": data.get("server"),
                "username": data.get("username"),
                "password": data.get("password"),
                "keepinfo": True
            }
            if data.get("keepAddr", False):
                final_data["keepAddr"] = True
                for key, value in data.items():
                    if key.endswith("Address"):
                        final_data[key] = value
        self.utils.write_json(final_data)

    # --- Route Management Logic ---
    def get_saved_routes(self):
        """Retrieves saved routes from the configuration file."""
        data = self.utils.read_json()
        routes = []
        for key, value in data.items():
            if key.endswith("Address") and isinstance(value, list):
                domain = key.replace("Address", "")
                for ip in value:
                    routes.append({"domain": domain, "ip": ip})
        return routes

    def add_route(self, domain):
        """Resolves a domain and adds system routes for it. Synchronous."""
        if not self.office_mode_ip:
            raise RouteError("Cannot add route: Office Mode IP is not set.")
        
        try:
            process = subprocess.run(
                f"nslookup {domain}", shell=True, capture_output=True, text=True, check=True
            )
            addresses = self.utils.extract_ip_addresses(process.stdout.splitlines())
            if not addresses:
                raise RouteError(f"No valid IPv4 addresses found for {domain}.")
        except subprocess.CalledProcessError:
            raise RouteError(f"Failed to resolve domain: {domain}")
            
        commands = [f"ip route add {addr} via {self.office_mode_ip}" for addr in addresses]
        self._run_privileged_commands(commands)
        
        # Persist the new route
        data = self.utils.read_json()
        route_key = f"{domain}Address"
        if route_key not in data:
            data[route_key] = []
        for addr in addresses:
            if addr not in data[route_key]:
                data[route_key].append(addr)
        self.utils.write_json(data)

        return {"status": True, "addresses": addresses}
        
    def remove_route(self, domain, ip_address):
        """Removes a specific system route. Synchronous."""
        if not self.office_mode_ip:
            raise RouteError("Cannot remove route: Office Mode IP is not set.")
        
        commands = [f"ip route del {ip_address} via {self.office_mode_ip}"]
        self._run_privileged_commands(commands)
        
        # Remove from JSON
        data = self.utils.read_json()
        route_key = f"{domain}Address"
        if route_key in data and ip_address in data[route_key]:
            data[route_key].remove(ip_address)
            if not data[route_key]: # Remove key if list is empty
                del data[route_key]
        self.utils.write_json(data)

        return {"status": True}
        
    def _delete_saved_routes(self):
        """Internal method to delete all saved routes on disconnect."""
        if not self.office_mode_ip:
            return
        routes = self.get_saved_routes()
        commands = [f"ip route del {route['ip']} via {self.office_mode_ip}" for route in routes]
        if commands:
            try:
                self._run_privileged_commands(commands)
            except Exception as e:
                self.logger.error(f"Failed to delete all routes on disconnect: {e}")

    def _run_privileged_commands(self, commands):
        """Helper to run a list of commands using pkexec."""
        script = "\n".join(commands)
        try:
            process = subprocess.Popen(
                ["pkexec", "bash"], stdin=subprocess.PIPE, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            _, stderr = process.communicate(input=script)
            if process.returncode != 0:
                raise VpnError(f"Privileged command failed: {stderr.strip()}")
        except FileNotFoundError:
            raise DependencyError("pkexec command not found.")