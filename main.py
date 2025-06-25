import sys
import gi
import gettext
import locale
from back_end import Utils, VpnCon, VpnConWeb, VpnDiss

# Requer as versões necessárias do Gtk e Adw
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject

# --- Configuração da Tradução ---
LOCALE_DIR = "i18n"
APP_NAME = "snx_connect"
try:
    locale.setlocale(locale.LC_ALL, '')
    gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
    gettext.textdomain(APP_NAME)
    _ = gettext.gettext
except Exception as e:
    print(f"Não foi possível carregar as traduções: {e}")
    _ = lambda s: s

class RouteRow(Gtk.ListBoxRow):
    """
    Representa uma linha customizada na lista de rotas, com um botão de remover.
    """
    def __init__(self, domain, address, on_remove_request):
        super().__init__()
        self.domain = domain
        self.address = address
        self.on_remove_request = on_remove_request

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=12, margin_end=12)
        
        label = Gtk.Label(hexpand=True, xalign=0)
        label.set_markup(f"<b>{domain}</b> → {address}")
        
        self.remove_button = Gtk.Button.new_from_icon_name("edit-delete-symbolic")
        self.remove_button.get_style_context().add_class("destructive-action")
        self.remove_button.set_tooltip_text(_("Remove this route"))
        self.remove_button.connect("clicked", self.on_remove_clicked)
        
        self.spinner = Gtk.Spinner()
        
        box.append(label)
        box.append(self.spinner)
        box.append(self.remove_button)
        self.set_child(box)

    def on_remove_clicked(self, widget):
        self.remove_button.set_sensitive(False)
        self.spinner.start()
        # Chama a função que foi passada pelo pai (TelaPrincipal)
        self.on_remove_request(self)

    def on_remove_success(self):
        self.get_parent().remove(self)

    def on_remove_error(self, error_message):
        self.spinner.stop()
        self.remove_button.set_sensitive(True)
        dialog = Adw.MessageDialog(transient_for=self.get_root(), title=_("Error Removing Route"), body=str(error_message))
        dialog.add_response("ok", _("OK"))
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()


class TelaPrincipal(Gtk.Box):
    """
    A tela principal da aplicação, para gerenciar as rotas da VPN.
    """
    __gsignals__ = {
        'disconnected': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, office_ip=""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12); self.set_margin_bottom(12); self.set_margin_start(12); self.set_margin_end(12)

        self.utils = Utils()
        self.vpn_web = VpnConWeb()

        add_frame = Gtk.Frame(label=_("Add New Route"))
        add_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        add_frame.set_child(add_box)
        caixa_entrada = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entrada_dominio = Gtk.Entry(hexpand=True, placeholder_text=_("Enter a domain (e.g., bitbucket.org)"))
        self.botao_adicionar = Gtk.Button(label=_("Add"))
        self.spinner_add = Gtk.Spinner(spinning=False)
        caixa_entrada.append(self.entrada_dominio); caixa_entrada.append(self.botao_adicionar); add_box.append(caixa_entrada); add_box.append(self.spinner_add)

        routes_frame = Gtk.Frame(label=_("Active Routes"))
        self.lista_rotas = Gtk.ListBox()
        self.lista_rotas.set_selection_mode(Gtk.SelectionMode.NONE)
        janela_rolagem = Gtk.ScrolledWindow(child=self.lista_rotas, vexpand=True, min_content_height=200)
        routes_frame.set_child(janela_rolagem)
        
        self.append(add_frame)
        self.append(routes_frame)

        self.botao_adicionar.connect("clicked", self.on_add_route_clicked)
        self.load_saved_routes()

    def load_saved_routes(self):
        data = self.utils.readJson()
        for key, value in data.items():
            # Garante que a chave termina com "Address" E que o valor é uma lista
            if key.endswith("Address") and isinstance(value, list):
                domain = key.replace("Address", "")
                for addr in value: # Agora 'value' é garantidamente uma lista
                    self.add_route_to_list(domain, addr)

    def add_route_to_list(self, domain, address):
        row = RouteRow(domain, address, self.on_remove_route_request)
        self.lista_rotas.append(row)

    def on_add_route_clicked(self, widget):
        domain = self.entrada_dominio.get_text().strip()
        if not domain: return
        self.botao_adicionar.set_sensitive(False)
        self.spinner_add.start()
        self.vpn_web.add_route(domain, self.handle_route_add_success, self.handle_route_add_error)

    def on_remove_route_request(self, route_row):
        # Esta função é chamada pela RouteRow quando o botão de remover é clicado.
        self.vpn_web.remove_route(
            route_row.domain,
            route_row.address,
            lambda msg: route_row.on_remove_success(), # Passa a função de sucesso da própria linha
            lambda err: route_row.on_remove_error(err) # Passa a função de erro da própria linha
        )

    def handle_route_add_success(self, message, addresses):
        self.spinner_add.stop()
        self.botao_adicionar.set_sensitive(True)
        domain = self.entrada_dominio.get_text().strip()
        self.entrada_dominio.set_text("")
        for addr in addresses: self.add_route_to_list(domain, addr)
        self.show_info_dialog(_("Success"), message)
        
    def handle_route_add_error(self, error_message):
        self.spinner_add.stop()
        self.botao_adicionar.set_sensitive(True)
        self.show_error_dialog(_("Failed to Add Route"), error_message)

    def show_info_dialog(self, title, message):
        dialog = Adw.MessageDialog(transient_for=self.get_root(), title=title, body=message)
        dialog.add_response("ok", _("OK")); dialog.connect("response", lambda d, r: d.close()); dialog.present()
        
    def show_error_dialog(self, title, message):
        dialog = Adw.MessageDialog(transient_for=self.get_root(), title=title, body=message)
        dialog.add_response("ok", _("OK")); dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: d.close()); dialog.present()

class TelaLogin(Gtk.Box):
    __gsignals__ = { 'login-sucesso': (GObject.SignalFlags.RUN_FIRST, None, (str,)) }
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.utils = Utils(); data = self.utils.readJson(); self.isChecked = data.get("keepinfo", False); self.last_office_ip = None
        self.set_margin_top(24); self.set_margin_bottom(24); self.set_margin_start(24); self.set_margin_end(24)
        project_logo = Gtk.Image.new_from_file("./assets/logo.png"); project_logo.set_pixel_size(150)
        self.entrada_website = Gtk.Entry(placeholder_text=_("Site address"))
        self.entrada_usuario = Gtk.Entry(placeholder_text=_("Your username"))
        self.entrada_senha = Gtk.Entry(placeholder_text=_("Password"), visibility=False, input_purpose=Gtk.InputPurpose.PASSWORD)
        checkbox = Gtk.CheckButton(label=_("Keep Info")); checkbox.connect("toggled", self.on_checkbox_toggled)
        self.botao_entrar = Gtk.Button(label=_("Connect"), halign=Gtk.Align.CENTER)
        self.botao_entrar.get_style_context().add_class("suggested-action")
        self.botao_entrar.connect("clicked", self.on_botao_entrar_clicado)
        self.spinner = Gtk.Spinner(spinning=False, halign=Gtk.Align.CENTER)
        if self.isChecked:
            self.entrada_website.set_text(data.get("server", "")); self.entrada_usuario.set_text(data.get("username", ""))
            self.entrada_senha.set_text(data.get("password", "")); checkbox.set_active(True)
        self.append(project_logo); self.append(Gtk.Separator(height_request=10, opacity=0)); self.append(Gtk.Label(label=_("Site"), xalign=0))
        self.append(self.entrada_website); self.append(Gtk.Label(label=_("User"), xalign=0)); self.append(self.entrada_usuario)
        self.append(Gtk.Label(label=_("Password"), xalign=0)); self.append(self.entrada_senha); self.append(checkbox)
        self.append(self.botao_entrar); self.append(self.spinner)
    def on_botao_entrar_clicado(self, widget):
        self.botao_entrar.set_sensitive(False); self.spinner.start()
        vpn = VpnCon(self.entrada_website.get_text(), self.entrada_usuario.get_text(), self.entrada_senha.get_text(), self.isChecked)
        vpn.connect(on_success=self.on_login_success, on_error=self.on_login_error)
    def on_checkbox_toggled(self, widget): self.isChecked = widget.get_active()
    def on_login_success(self, office_mode_ip):
        self.last_office_ip = office_mode_ip; self.spinner.stop()
        modal = Adw.MessageDialog(transient_for=self.get_root(), title=_("Login Successful"), body=_("You are now connected!"))
        modal.add_response("ok", _("OK")); modal.connect("response", self.on_dialog_response); modal.present()
    def on_dialog_response(self, dialog, response): dialog.close(); self.emit('login-sucesso', self.last_office_ip)
    def on_login_error(self, error_message):
        self.botao_entrar.set_sensitive(True); self.spinner.stop()
        if "Another session" in error_message: self.emit('login-sucesso', ""); return
        modal = Adw.MessageDialog(transient_for=self.get_root(), title=_("Login Failed"), body=str(error_message))
        modal.add_response("ok", _("OK")); modal.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        modal.connect("response", lambda d, r: d.close()); modal.present()

class JanelaPrincipal(Gtk.ApplicationWindow):
    """ A janela principal da aplicação, que gerencia as telas. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(450, 550)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        self.header = Adw.HeaderBar()
        self.header.set_title_widget(Adw.WindowTitle(title="SNX Connect"))
        self.disconnect_button = Gtk.Button(label=_("Disconnect"))
        self.disconnect_button.get_style_context().add_class("destructive-action")
        self.disconnect_button.connect("clicked", self.on_disconnect_clicked)
        self.header.pack_end(self.disconnect_button)

        # --- CORREÇÃO DO HEADER DUPLO ---
        # 1. Define o header como a barra de título da janela.
        self.set_titlebar(self.header)

        # 2. O box principal agora só contém o stack de telas.
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # A linha main_box.append(self.header) foi REMOVIDA.
        main_box.append(self.stack)
        self.set_child(main_box)

        self.tela_login = TelaLogin()
        self.tela_login.connect('login-sucesso', self.mostrar_tela_principal)
        self.stack.add_named(self.tela_login, "login")
        self.header.get_title_widget().set_subtitle(_("Login"))
        self.disconnect_button.set_visible(False)

    def mostrar_tela_principal(self, widget, office_ip):
        if self.stack.get_child_by_name("principal"): self.stack.remove(self.stack.get_child_by_name("principal"))
        self.tela_principal = TelaPrincipal(office_ip)
        self.tela_principal.connect('disconnected', self.mostrar_tela_login)
        self.stack.add_named(self.tela_principal, "principal")
        self.stack.set_visible_child_name("principal")
        self.header.get_title_widget().set_subtitle(_("Connected"))
        self.disconnect_button.set_visible(True)

    def mostrar_tela_login(self, widget=None):
        self.stack.set_visible_child_name("login"); self.header.get_title_widget().set_subtitle(_("Login"))
        self.disconnect_button.set_visible(False)

    def on_disconnect_clicked(self, widget):
        self.disconnect_button.set_sensitive(False)
        VpnDiss(on_success=self.on_disconnect_success, on_error=self.on_disconnect_error)

    def on_disconnect_success(self, message):
        self.disconnect_button.set_sensitive(True); self.mostrar_tela_login()
        
    def on_disconnect_error(self, error_message):
        self.disconnect_button.set_sensitive(True); self.mostrar_tela_login()

class SNXConnectApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, application_id="com.exemplo.SNXConnect")
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        win = JanelaPrincipal(application=app)
        win.present()

if __name__ == "__main__":
    app = SNXConnectApp()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)