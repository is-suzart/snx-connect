import subprocess
import re
import json
import threading
import os
import logging
from gi.repository import GLib, Gtk, Adw, Gio, GObject

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,  # Set to logging.DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Utils:
    def __init__(self):
        # Define o caminho do arquivo de configuração no diretório de configuração do usuário
        config_dir = os.path.join(GLib.get_user_config_dir(), "snx-connect")
        os.makedirs(config_dir, exist_ok=True) # Cria o diretório se não existir
        self.config_file = os.path.join(config_dir, "snx-data.json")

    def readJson(self):
        try:
            with open(self.config_file, "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            # Se o arquivo não existe ou está corrompido/vazio, retorna um dicionário vazio.
            return {}

    def writeJson(self, changes):
        with open(self.config_file, "w") as file:
            json.dump(changes, file, indent=4)

    def extract_addresses(self, nslookup_output_lines, desired_prefix=None):
        """
        Extracts IP addresses from nslookup output lines.
        Filters by desired_prefix if provided.
        Attempts to ignore DNS server's own address by looking for "Name:" -> "Address:" patterns.
        Returns a list of unique IP addresses.
        """
        resolved_ips = set() # Use um conjunto para lidar automaticamente com duplicatas
        # Regex para encontrar linhas como "Address: <ip_address>"
        address_pattern = re.compile(r"^\s*Address:\s*([0-9a-fA-F.:]+)")

        for i, line_content in enumerate(nslookup_output_lines):
            # Procuramos por uma linha "Name:" seguida por uma linha "Address:"
            if line_content.lstrip().startswith("Name:"):
                if i + 1 < len(nslookup_output_lines): # Verifica se existe uma próxima linha
                    next_line = nslookup_output_lines[i+1]
                    match = address_pattern.match(next_line)
                    if match:
                        ip = match.group(1)
                        if ":" not in ip:  # Verifica se NÃO é um endereço IPv6 (para pegar IPv4)
                            resolved_ips.add(ip)
        return list(resolved_ips) # Retorna uma lista de IPs únicos


class VpnCon:
    def __init__(self, server, username, password, keepinfo):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.utils = Utils() # Mantenha sua classe de utilidades
        self.server = server
        self.username = username
        self.password = password
        self.keepinfo = keepinfo
        self.should_auto_add_routes_on_connect = False # Initialize flag
        self.office_mode_ip = None # Initialize office_mode_ip

        if self.keepinfo:
            # Se keepinfo for True, salva as informações no JSON
            data_to_save = self.utils.readJson()
            data_to_save["server"] = self.server
            data_to_save["username"] = self.username
            data_to_save["password"] = self.password
            data_to_save["keepinfo"] = self.keepinfo # Ensure keepinfo itself is saved
            try:
                self.utils.writeJson(data_to_save)
                self.logger.info("Credentials saved to snx-data.json as keepinfo is true.")
            except Exception as e:
                self.logger.error(f"Error writing credentials to snx-data.json: {e}")

        # Check 'keepAddress' flag from JSON to decide if routes should be auto-added on connect
        current_json_data = self.utils.readJson()
        if current_json_data.get("keepAddress", False):
            self.should_auto_add_routes_on_connect = True
            self.logger.info("VpnCon initialized: 'keepAddress' is true. Routes will be auto-added on successful connection.")
        else:
            self.logger.info("VpnCon initialized: 'keepAddress' is false or not set. Routes will not be auto-added.")

    def _auto_add_saved_routes(self):
        """
        Adds routes that are saved in snx-data.json.
        This method is intended to be called after a successful VPN connection
        if 'keepAddress' was true.
        """
        if not self.office_mode_ip:
            self.logger.error("Office Mode IP not available for auto-adding routes.")
            return

        json_data_routes = self.utils.readJson()
        commands_to_run = []
        found_routes_to_add = False

        for key, value in json_data_routes.items():
            if key.endswith("Address") and isinstance(value, list): # Filters for entries like "domain.comAddress": [...]
                domain_name = key.replace("Address", "")
                addresses = value

                if not addresses:
                    self.logger.info(f"No addresses found for domain {domain_name} in snx-data.json, skipping auto-add for this domain.")
                    continue

                for addr in addresses:
                    commands_to_run.append(f"ip route add {addr} via {self.office_mode_ip} dev tunsnx")
                if addresses:
                    found_routes_to_add = True
                    self.logger.info(f"Scheduled auto-add for domain: {domain_name} with IPs: {addresses}")

        if not found_routes_to_add:
            self.logger.info("No saved routes to auto-add based on snx-data.json entries.")
            return

        command_script = "\n".join(commands_to_run)
        self.logger.info(f"Attempting to auto-add saved routes via pkexec. Script:\n{command_script}")
        try:
            process = subprocess.Popen(
                ["pkexec", "bash"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=command_script)
            
            if process.returncode == 0:
                self.logger.info("Successfully auto-added saved routes.")
                if stdout and stdout.strip(): 
                    self.logger.debug(f"pkexec stdout for auto-add routes: {stdout.strip()}")
            else:
                error_msg = f"Error auto-adding saved routes. pkexec Return code: {process.returncode}"
                if stderr and stderr.strip(): 
                    error_msg += f"\npkexec stderr: {stderr.strip()}"
                self.logger.error(error_msg)
        except FileNotFoundError:
            self.logger.error("pkexec command not found. Cannot auto-add routes. Please ensure 'pkexec' and 'bash' are installed and in PATH.")
        except Exception as e:
            self.logger.exception("Exception while auto-adding saved routes.")

    # O método que o front-end irá chamar
    def connect(self, on_success, on_error):
        """
        Inicia a conexão em uma thread, recebendo os callbacks do front-end.
        """
        thread = threading.Thread(target=self._run_connection_thread, args=(on_success, on_error))
        thread.daemon = True
        thread.start()

    # O método privado que executa na thread
    def _run_connection_thread(self, on_success, on_error):
        command_str = f"snx -s {self.server} -u {self.username}"
        try:
            process = subprocess.Popen(
                command_str, shell=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True
            )
            stdout, stderr = process.communicate(input=f"{self.password}\n", timeout=15)

            if process.returncode == 0:
                pattern = r"Office Mode IP\s+:\s+(.+)"
                match = re.search(pattern, stdout)
                if match:
                    self.office_mode_ip = match.group(1).strip()
                    self.logger.info(f"Office Mode IP obtained: {self.office_mode_ip}")
                    
                    # Update JSON with the new IP
                    data_for_ip_update = self.utils.readJson()
                    data_for_ip_update["ip"] = self.office_mode_ip
                    try:
                        self.utils.writeJson(data_for_ip_update)
                    except Exception as e:
                        self.logger.error(f"Error writing IP to snx-data.json: {e}")

                    # Now, check if we need to auto-add routes
                    if self.should_auto_add_routes_on_connect:
                        self.logger.info("Connection successful. Proceeding to auto-add saved routes.")
                        self._auto_add_saved_routes() # Call the new method
                    else:
                        self.logger.info("Connection successful. Auto-adding routes is disabled ('keepAddress' is false or was not readable).")
                    
                    GLib.idle_add(on_success, self.office_mode_ip)
                else:
                    error_message_no_ip = "SNX connected, but Office Mode IP not found in output."
                    if stdout: error_message_no_ip += f"\nOutput: {stdout}"
                    self.logger.error(error_message_no_ip)
                    GLib.idle_add(on_error, error_message_no_ip)
            else:
                error_message = stderr.strip() if stderr else "Unknown error during VPN connection."
                self.logger.error(f"VPN connection failed. SNX Return code: {process.returncode}. Error: {error_message}")
                GLib.idle_add(on_error, error_message)
        except subprocess.TimeoutExpired:
            timeout_msg = "VPN connection command timed out."
            self.logger.error(timeout_msg)
            if process: process.kill() # Ensure process is killed
            GLib.idle_add(on_error, timeout_msg)
        except Exception as e:
            exception_msg = f"An exception occurred during VPN connection: {e}"
            self.logger.exception("An exception occurred during VPN connection.")
            GLib.idle_add(on_error, str(e))
class VpnConWeb:
    def __init__(self):
        self.utils = Utils() # Instancia sua classe de utilidades
        data = self.utils.readJson()
        self.office_mode_ip = data.get("ip")
    
    # Note: VpnConWeb uses GLib.idle_add for UI feedback, not direct print for logging.
    def add_route(self, domain, on_success, on_error):
        """
        Inicia a adição de rota em uma thread, recebendo os callbacks do front-end.
        Este é o único método que o seu front-end precisa chamar.
        """
        if not self.office_mode_ip:
            GLib.idle_add(on_error, "IP da VPN não encontrado. Conecte-se primeiro.")
            return

        thread = threading.Thread(target=self._run_add_route_thread, args=(domain, on_success, on_error))
        thread.daemon = True
        thread.start()

    def _run_add_route_thread(self, domain, on_success, on_error):
        try:
            process = subprocess.run(
                f"nslookup {domain}", shell=True, capture_output=True, text=True, check=True
            )
            addresses = self.utils.extract_addresses(process.stdout.splitlines())
            if not addresses:
                GLib.idle_add(on_error, f"Nenhum endereço encontrado para o domínio: {domain}")
                return
        except Exception as e:
            GLib.idle_add(on_error, f"Falha ao resolver o domínio '{domain}': {e}")
            return

        # --- CORREÇÃO PRINCIPAL AQUI ---
        # 1. Construir uma lista de todos os comandos a serem executados
        commands_to_run = [
            f"ip route add {address} via {self.office_mode_ip}" for address in addresses
        ]
        # Transforma a lista em uma única string, com cada comando em uma nova linha
        command_script = "\n".join(commands_to_run)

        try:
            # 2. Executa pkexec UMA VEZ, passando todos os comandos para o bash
            process = subprocess.Popen(
                ["pkexec", "bash"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=command_script)
            
            # 3. Verifica se o script bash foi executado com sucesso
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, "bash", stderr)

            # Se teve sucesso, salva tudo no JSON
            json_data = self.utils.readJson()
            if f"{domain}Address" not in json_data:
                json_data[f"{domain}Address"] = []
            
            successful_addresses = []
            for address in addresses:
                if address not in json_data[f"{domain}Address"]:
                    json_data[f"{domain}Address"].append(address)
                successful_addresses.append(address)
            self.utils.writeJson(json_data)

            # 4. Notifica a UI do sucesso
            success_message = f"Rotas para '{domain}' adicionadas com sucesso."
            GLib.idle_add(on_success, success_message, successful_addresses)

        except subprocess.CalledProcessError:
            GLib.idle_add(on_error, f"Falha ao adicionar rotas. Permissão negada ou erro.")
        except Exception as e:
            GLib.idle_add(on_error, str(e))
class VpnDiss:
    def __init__(self, on_success=None, on_error=None):
        self.utils = Utils()
        self.logger = logging.getLogger(self.__class__.__name__)
        thread = threading.Thread(target=self._perform_disconnect_actions, args=(on_success, on_error))
        thread.daemon = True
        thread.start()

    def _perform_disconnect_actions(self, on_success, on_error):
        try:
            self.logger.info("Attempting VPN disconnection using 'snx -d'.")
            snx_process = subprocess.run("snx -d", shell=True, text=True, capture_output=True)
            if snx_process.returncode == 0:
                self.logger.info("'snx -d' command executed successfully.")
            else:
                self.logger.warning(f"'snx -d' command failed or returned non-zero (RC: {snx_process.returncode}). "
                                    f"Stdout: '{snx_process.stdout.strip()}', Stderr: '{snx_process.stderr.strip()}'. "
                                    "This might be normal if already disconnected.")

            # Optional: Disable IPv6 (Consider if this is always necessary on disconnect)
            self._delete_saved_routes()

            # Update snx-data.json based on keepinfo and keepAddress
            self._update_json_on_disconnect()

            if on_success:
                GLib.idle_add(on_success, "VPN disconnection process completed.")

        except Exception as e: # Catch-all for the entire disconnect process
            self.logger.exception("An critical error occurred during the VPN disconnection process.")
            if on_error:
                GLib.idle_add(on_error, f"Disconnection failed critically: {str(e)}")

    def _delete_saved_routes(self):
        """Lê o arquivo JSON e tenta remover todas as rotas salvas."""
        try:
            current_data_for_routes = self.utils.readJson()
            office_ip_for_deletion = current_data_for_routes.get("ip")
            route_deletion_commands = []

            if office_ip_for_deletion:
                for key, value in current_data_for_routes.items():
                    if key.endswith("Address") and isinstance(value, list):
                        domain_name = key.replace("Address", "")
                        for addr in value:
                            # Assuming 'tunsnx' is the device. This might need to be confirmed or made dynamic.
                            route_deletion_commands.append(f"ip route del {addr} via {office_ip_for_deletion} dev tunsnx")
                        if value:
                            self.logger.info(f"Scheduled deletion of routes for {domain_name} (IPs: {value}) via {office_ip_for_deletion}")
            else:
                self.logger.warning("No 'ip' found in snx-data.json; cannot specifically delete routes via VPN gateway.")

            if route_deletion_commands:
                script = "\n".join(route_deletion_commands)
                self.logger.info(f"Executing route deletion script with pkexec:\n{script}")
                pk_proc = subprocess.Popen(["pkexec", "bash"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                s_out, s_err = pk_proc.communicate(input=script)
                if pk_proc.returncode == 0:
                    self.logger.info("Route deletion script executed successfully via pkexec.")
                    if s_out.strip(): self.logger.debug(f"pkexec stdout for route deletion: {s_out.strip()}")
                else:
                    self.logger.error(f"Route deletion script via pkexec failed. RC: {pk_proc.returncode}. Stderr: {s_err.strip()}")
            else:
                self.logger.info("No routes found to delete or no VPN IP was available for deletion commands.")
        except Exception as e_route_del_logic:
            self.logger.error(f"Unexpected error during route deletion logic: {e_route_del_logic}", exc_info=True)

    def _update_json_on_disconnect(self):
        """Atualiza o arquivo JSON com base nas flags 'keepinfo' e 'keepAddress'."""
        try:
            data_before_final_write = self.utils.readJson()
            final_data_to_write = {}

            if data_before_final_write.get("keepinfo", False):
                self.logger.info("'keepinfo' is true. Preserving server, username, password, and keepinfo flag.")
                final_data_to_write["server"] = data_before_final_write.get("server")
                final_data_to_write["username"] = data_before_final_write.get("username")
                final_data_to_write["password"] = data_before_final_write.get("password")
                final_data_to_write["keepinfo"] = True

                if data_before_final_write.get("keepAddress", False):
                    self.logger.info("'keepAddress' is also true. Preserving *Address entries and keepAddress flag.")
                    final_data_to_write["keepAddress"] = True
                    for key, value in data_before_final_write.items():
                        if key.endswith("Address"):
                            final_data_to_write[key] = value
                else:
                    self.logger.info("'keepAddress' is false (while 'keepinfo' is true). Route addresses and keepAddress flag will not be preserved.")
            else:
                self.logger.info("'keepinfo' is false. Clearing all persistent data (server, user, pass, keepinfo, keepAddress, routes).")
            
            # 'ip' field is always removed on disconnect, regardless of flags.
            self.utils.writeJson(final_data_to_write)
            self.logger.info(f"snx-data.json updated after disconnect. Final data written: {final_data_to_write}")
        except Exception as e_final_update_logic:
            self.logger.error(f"Error during final update logic of snx-data.json: {e_final_update_logic}", exc_info=True)

# --- Main function (commented out, for command-line use if ever needed) ---
#     parser = argparse.ArgumentParser(description='Lidando com a VPN SNX')
#     parser.add_argument("action", choices=['on','off'], help="On para conectar a vpn, Off para desconectar")
#     parser.add_argument("-s", "--server", help="Endereço do servidor VPN")
#     parser.add_argument("-u", "--username", help="Nome de usuário para a VPN")
#     parser.add_argument("-p", "--password", help="Senha para a VPN")
#     args = parser.parse_args()

#     if args.action == "on":
#         if not all([args.server, args.username, args.password]):
#             parser.error("Para a ação 'on', os argumentos --server, --username, e --password são obrigatórios.")
#         VpnCon(server=args.server, username=args.username, password=args.password)
#     elif args.action == "off":
#         VpnDiss()
#     #def connectSNX(self, ip):


# main()
