from back_end import Utils, VpnCon,VpnConWeb, VpnDiss
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import GLib, Gtk, Adw, Gio, GObject
from main import TelaPrincipal


class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.utils = Utils()
        self.vpn_web = VpnConWeb()
        
        self.login_infos = {}
        
    def load_saved_routes(self):
        data = self.utils.readJson()
        for key, value in data.items():
            # Garante que a chave termina com "Address" E que o valor é uma lista
            if key.endswith("Address") and isinstance(value, list):
                domain = key.replace("Address", "")
                for addr in value: # Agora 'value' é garantidamente uma lista
                    self.add_route_to_list(domain, addr)
    
    def get_user_login_info(self,website,name, password,keep):
        self.login_infos = {
            "website": website,
            "name": name,
            "password": password,
            "keep": keep
        }
        return self.login_infos
        
    
    def connect_user(self, on_success, on_error):
        if not self.login_infos:
            GLib.idle_add(on_error, "Informações de login não fornecidas.")
            return
        else:
            vpn = VpnCon(
                self.login_infos["website"],
                self.login_infos["name"],
                self.login_infos["password"],
                self.login_infos["keep"]
            )
            result = vpn.connect()
            if result.get("status", False):
                GLib.idle_add(on_success, result.get("message"), result.get("office_mode_ip"))
            else:
                GLib.idle_add(on_error, result.get("message"))
            
    
    def add_route_to_list(self, domain,on_success, on_error):
        result = self.vpn_web.add_route(domain,on_success, on_error)
        if result & result.get("status", False):
            GLib.idle_add(on_success, result.get("message"))
        else:
            GLib.idle_add(on_error, result.get("message"))
    
    def return_install_snx_status(self,status,msg):
        if status:
            print(msg)
        else:
            print(f"Error: {msg}")
            GLib.idle_add(self.view.display_error_message, msg)
    
    def disconnect_user(self, on_success, on_error):
        vpn = VpnDiss()
        result = vpn.disconnect()
        if result.get("status", False):
            GLib.idle_add(on_success, result.get("message"))
        else:
            GLib.idle_add(on_error, result.get("message"))
    
        

    def run(self):
        self.view.display_welcome_message()