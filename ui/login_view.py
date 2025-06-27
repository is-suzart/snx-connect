# ui/login_view.py
import gi  # type: ignore
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib # Importar GLib
from back_end import Utils

# Assume que _ está configurado no main.py
import gettext
_ = gettext.gettext

class LoginView(Gtk.Box):
    __gsignals__ = {"login-success": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self, controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.controller = controller
        self.utils = Utils()

        self.set_css_name("login-view")
        
        data = self.utils.read_json()
        self.is_checked = data.get("keepinfo", False)
        self.last_office_ip = None

        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)

        project_logo = Gtk.Image.new_from_file("./assets/logo.png")
        project_logo.set_pixel_size(150)

        self.website_entry = Gtk.Entry(placeholder_text=_("Site address"))
        self.user_entry = Gtk.Entry(placeholder_text=_("Your username"))
        self.password_entry = Gtk.Entry(
            placeholder_text=_("Password"),
            visibility=False,
            input_purpose=Gtk.InputPurpose.PASSWORD,
        )

        self.keep_info_check = Gtk.CheckButton(label=_("Keep Info"))
        self.keep_info_check.connect("toggled", self.on_checkbox_toggled)

        self.connect_button = Gtk.Button(label=_("Connect"), halign=Gtk.Align.CENTER)
        self.connect_button.add_css_class("connect-button")
        self.connect_button.connect("clicked", self.on_connect_button_clicked)
        
        self.spinner = Gtk.Spinner(spinning=False, halign=Gtk.Align.CENTER)

        if self.is_checked:
            self.website_entry.set_text(data.get("server", ""))
            self.user_entry.set_text(data.get("username", ""))
            self.password_entry.set_text(data.get("password", ""))
            self.keep_info_check.set_active(True)

        self.append(project_logo)
        self.append(Gtk.Separator(height_request=10, opacity=0))
        self.append(Gtk.Label(label=_("Site"), xalign=0))
        self.append(self.website_entry)
        self.append(Gtk.Label(label=_("User"), xalign=0))
        self.append(self.user_entry)
        self.append(Gtk.Label(label=_("Password"), xalign=0))
        self.append(self.password_entry)
        self.append(self.keep_info_check)
        self.append(self.connect_button)
        self.append(self.spinner)

    def on_connect_button_clicked(self, widget):
        self.connect_button.set_sensitive(False)
        self.spinner.start()
        
        login_info = {
            "website": self.website_entry.get_text(),
            "name": self.user_entry.get_text(),
            "password": self.password_entry.get_text(),
            "keep": self.is_checked,
        }
        
        self.controller.request_login(
            login_info, 
            on_success=self.on_login_success, 
            on_error=self.on_login_error
        )

    def on_checkbox_toggled(self, widget):
        self.is_checked = widget.get_active()

    def on_login_success(self, status, office_ip):
        GLib.idle_add(self._update_ui_on_success, office_ip)

    def on_login_error(self, error_message):
        GLib.idle_add(self._update_ui_on_error, error_message)

    def _update_ui_on_success(self, office_ip):
        self.last_office_ip = office_ip
        self.spinner.stop()
        self.connect_button.set_sensitive(True)
        self.emit("login-success", self.last_office_ip)
        return False # Remove a tarefa da fila do GLib

    def _update_ui_on_error(self, error_message):
        self.connect_button.set_sensitive(True)
        self.spinner.stop()
        if "Another session" in error_message:
            self.emit("login-success", "")
            return False

        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            title=_("Login Failed"),
            body=str(error_message),
        )
        dialog.add_response("ok", _("OK"))
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()
        return False # Remove a tarefa da fila do GLib