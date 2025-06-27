# ui/window.py
import gi  # type: ignore
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from .login_view import LoginView
from .routes_view import RoutesView

# Assume que _ está configurado no main.py
import gettext
_ = gettext.gettext

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller
        self.set_default_size(450, 550)

        # --- Setup do Header e do NOVO MenuButton ---
        self.header = Adw.HeaderBar()
        self.header.set_title_widget(Adw.WindowTitle(title="SNX Connect"))

        # Cria o menu que será exibido pelo botão
        self.create_header_menu()

        self.set_titlebar(self.header)

        # Setup do Stack
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(self.stack)
        self.set_child(main_box)

        # Cria as telas
        self.login_view = LoginView(self.controller)
        self.routes_view = RoutesView(self.controller)

        # Adiciona as telas ao stack
        self.stack.add_named(self.login_view, "login")
        self.stack.add_named(self.routes_view, "routes")
        
        # Conecta os sinais
        self.login_view.connect("login-success", self.show_routes_view)
        self.routes_view.connect("disconnected", self.show_login_view)

        # Estado inicial
        self.show_login_view()

    def create_header_menu(self):
        """Cria o MenuButton e seu Popover com as opções."""
        # O Popover é a "janelinha" que aparece
        popover = Gtk.Popover()
        
        # O MenuButton é o botão com o ícone que aciona o popover
        # O ícone 'view-more-symbolic' são os três pontos verticais
        menu_button = Gtk.MenuButton(icon_name="view-more-symbolic", popover=popover)
        self.header.pack_end(menu_button)
        self.menu_button = menu_button # Guarda a referência

        # O Gtk.Box vai organizar os itens dentro do popover
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        popover.set_child(content_box)

        # --- Opção 1: Checkbox ---
        # Um box para alinhar o label e o checkbox
        check_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_start=12, margin_end=12)
        check_label = Gtk.Label(label=_("Save routes on exit"), xalign=0)
        self.keep_routes_check = Gtk.CheckButton()
        # self.keep_routes_check.connect("toggled", self.on_keep_routes_toggled) # Conectaria ao controller
        check_box.append(check_label)
        check_box.append(self.keep_routes_check)
        content_box.append(check_box)

        # Um separador para organizar
        content_box.append(Gtk.Separator())

        # --- Opção 2: Desconectar ---
        disconnect_button = Gtk.Button(label=_("Disconnect"))
        disconnect_button.add_css_class("flat") # Classe para parecer um item de menu
        disconnect_button.connect("clicked", self.on_disconnect_clicked)
        content_box.append(disconnect_button)

    def show_routes_view(self, widget, office_ip):
        self.stack.set_visible_child_name("routes")
        self.header.get_title_widget().set_subtitle(_("Connected"))
        self.menu_button.set_visible(True)
        self.controller.request_load_routes(self.routes_view)

    def show_login_view(self, widget=None):
        self.stack.set_visible_child_name("login")
        self.header.get_title_widget().set_subtitle(_("Login"))
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
        self.show_login_view()

    def on_disconnect_error(self, error_message):
        self.menu_button.set_sensitive(True)
        self.show_login_view()