# ui/window.py
import gi  # type: ignore
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from .login_view import LoginView
from .routes_view import RoutesView
from .widgets import ThemeSwitcher # <-- A IMPORTAÇÃO FOI CORRIGIDA AQUI
from back_end import Utils

import gettext
_ = gettext.gettext

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        utils = Utils()
        self.controller = controller
        self.set_default_size(450, 550)

        self.create_header_menu()
        self.set_titlebar(self.header)
        self.set_css_name("main-window")
        self.set_name("main-window")
        self.connect("close-request", self.on_close_request)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(self.stack)
        self.set_child(main_box)

        self.login_view = LoginView(self.controller)
        self.routes_view = RoutesView(self.controller)

        self.stack.add_named(self.login_view, "login")
        self.stack.add_named(self.routes_view, "routes")
        
        self.login_view.connect("login-success", self.show_routes_view)
        self.routes_view.connect("disconnected", self.show_login_view)

        self.show_login_view()
    
    def on_close_request(self, window):
        """Chamado quando o utilizador clica no 'X' da janela."""
        print("oi!")
        # Esconde a janela em vez de a fechar
        self.hide()
        # Retorna True para dizer ao GTK para não continuar com a ação padrão (fechar)
        return True

    def create_header_menu(self):
        """Cria o MenuButton e seu Popover com as opções."""
        self.header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(title="", subtitle="")
        self.header.set_title_widget(self.title_widget)

        self.set_icon_name("snx-connect-gui")

        popover = Gtk.Popover()
        menu_button = Gtk.MenuButton(icon_name="view-more-symbolic", popover=popover)
        self.header.pack_end(menu_button)
        self.menu_button = menu_button

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10, margin_bottom=10)
        popover.set_child(content_box)
        
        theme_switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_start=12, margin_end=12)
        theme_label = Gtk.Label(label=_("Theme"), xalign=0, hexpand=True)
        
        theme_switcher = ThemeSwitcher(self.get_application()) 
        
        #theme_switcher_box.append(theme_label)
        theme_switcher_box.append(theme_switcher)
        content_box.append(theme_switcher_box)

        content_box.append(Gtk.Separator())
        check_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_start=12, margin_end=12)
        check_label = Gtk.Label(label=_("Save routes on exit"), xalign=0, hexpand=True)
        self.keep_routes_check = Gtk.Switch()
        self.keep_routes_check.set_valign(Gtk.Align.CENTER)
        
        # Conecta o sinal e GUARDA O ID do manipulador
        self.keep_routes_handler_id = self.keep_routes_check.connect("notify::active", self.on_keep_routes_toggled)

        check_box.append(check_label)
        check_box.append(self.keep_routes_check)

        check_box.set_margin_top(12)
        check_box.set_margin_bottom(12)
        content_box.append(check_box)

        content_box.append(Gtk.Separator())

        disconnect_button = Gtk.Button(label=_("Disconnect"))
        disconnect_button.add_css_class("flat")
        disconnect_button.connect("clicked", self.on_disconnect_clicked)
        content_box.append(disconnect_button)

    def show_routes_view(self, widget, office_ip):
        self.stack.set_visible_child_name("routes")
        self.header.get_title_widget().set_title(_("Connected"))
        self.menu_button.set_visible(True)
        self.controller.request_load_routes(self.routes_view)

    def show_login_view(self, widget=None):
        self.stack.set_visible_child_name("login")
        self.title_widget.set_title(_("Login"))
        self.menu_button.set_visible(False)

    def on_disconnect_clicked(self, widget):
        # Primeiro, fecha o popover para uma experiência mais fluida
        self.menu_button.get_popover().popdown()
        self.menu_button.set_sensitive(False)
        self.controller.request_disconnect(
            on_success=self.on_disconnect_success,
            on_error=self.on_disconnect_error
        )

    def on_disconnect_success(self, message):
        self.menu_button.set_sensitive(True)
        self.routes_view.clear_routes_list()
        self.show_login_view()

    def on_keep_routes_toggled(self, switch, gparam):
        """Chamado quando o usuário clica no switch 'Save routes on exit'."""
        is_active = switch.get_active()
        # Notifica o controller sobre a mudança de estado para que ele possa salvar.
        self.controller.set_keep_routes_status(is_active)


    def on_disconnect_error(self, error_message):
        self.menu_button.set_sensitive(True)
        self.show_login_view()