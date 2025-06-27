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

        # Setup Header
        self.header = Adw.HeaderBar()
        self.header.set_title_widget(Adw.WindowTitle(title="SNX Connect"))
        self.disconnect_button = Gtk.Button(label=_("Disconnect"))
        self.disconnect_button.get_style_context().add_class("destructive-action")
        self.header.pack_end(self.disconnect_button)
        self.set_titlebar(self.header)

        # Setup Stack
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(self.stack)
        self.set_child(main_box)

        # Create views, injecting the controller
        self.login_view = LoginView(self.controller)
        self.routes_view = RoutesView(self.controller)

        # Add views to the stack
        self.stack.add_named(self.login_view, "login")
        self.stack.add_named(self.routes_view, "routes")
        
        # Connect signals
        self.login_view.connect("login-success", self.show_routes_view)
        self.disconnect_button.connect("clicked", self.on_disconnect_clicked)
        self.routes_view.connect("disconnected", self.show_login_view)

        # Initial state
        self.show_login_view()

    def show_routes_view(self, widget, office_ip):
        self.stack.set_visible_child_name("routes")
        self.header.get_title_widget().set_subtitle(_("Connected"))
        self.disconnect_button.set_visible(True)
        # Tell the controller to load data for the routes view
        self.controller.request_load_routes(self.routes_view)

    def show_login_view(self, widget=None):
        self.stack.set_visible_child_name("login")
        self.header.get_title_widget().set_subtitle(_("Login"))
        self.disconnect_button.set_visible(False)

    def on_disconnect_clicked(self, widget):
        self.disconnect_button.set_sensitive(False)
        self.controller.request_disconnect(
            on_success=self.on_disconnect_success,
            on_error=self.on_disconnect_error
        )

    def on_disconnect_success(self, message):
        self.disconnect_button.set_sensitive(True)
        self.show_login_view()

    def on_disconnect_error(self, error_message):
        # Aqui, você pode mostrar um diálogo de erro, se desejar
        self.disconnect_button.set_sensitive(True)
        self.show_login_view()