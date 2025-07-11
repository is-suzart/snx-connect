# ui/routes_view.py
import gi  # type: ignore
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib # Importar GLib é essencial

# Assume que _ está configurado no main.py
import gettext
_ = gettext.gettext

class RouteRow(Gtk.ListBoxRow):
    """
    Represents a custom row in the routes list, with a remove button.
    """
    def __init__(self, domain, address, on_remove_request):
        super().__init__()
        self.domain = domain
        self.address = address
        self.on_remove_request = on_remove_request

        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
            margin_top=6, margin_bottom=6, margin_start=12, margin_end=12,
        )
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
        self.on_remove_request(self)

    # Callbacks que são chamados pela thread do Controller
    def on_remove_success(self, **kwargs):
        GLib.idle_add(self._update_ui_on_remove_success)

    def on_remove_error(self, error_message):
        GLib.idle_add(self._update_ui_on_remove_error, error_message)

    # Funções auxiliares que fazem o trabalho real na UI
    def _update_ui_on_remove_success(self):
        # O get_parent() pode não funcionar se a linha já estiver sendo removida,
        # uma abordagem mais segura é o pai remover o filho.
        # Mas para simplificar, vamos manter assim por enquanto.
        parent = self.get_parent()
        if parent:
            parent.remove(self)
        return False

    def _update_ui_on_remove_error(self, error_message):
        self.spinner.stop()
        self.remove_button.set_sensitive(True)
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            title=_("Error Removing Route"), body=str(error_message),
        )
        dialog.add_response("ok", _("OK"))
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()
        return False


class RoutesView(Gtk.Box):
    """
    The main screen of the application for managing VPN routes.
    """
    __gsignals__ = {"disconnected": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.controller = controller
        
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        add_frame = Gtk.Frame(label=_("Add New Route"))
        add_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=6,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )
        add_frame.set_child(add_box)
        
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.domain_entry = Gtk.Entry(
            hexpand=True, placeholder_text=_("Enter a domain (e.g., bitbucket.org)")
        )
        self.add_button = Gtk.Button(label=_("Add"))
        self.add_spinner = Gtk.Spinner(spinning=False)
        
        entry_box.append(self.domain_entry)
        entry_box.append(self.add_button)
        add_box.append(entry_box)
        add_box.append(self.add_spinner)

        routes_frame = Gtk.Frame(label=_("Active Routes"))
        self.routes_listbox = Gtk.ListBox()
        self.routes_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled_window = Gtk.ScrolledWindow(
            child=self.routes_listbox, vexpand=True, min_content_height=200
        )
        routes_frame.set_child(scrolled_window)

        self.append(add_frame)
        self.append(routes_frame)

        self.add_button.connect("clicked", self.on_add_button_clicked)

    def add_route_to_list(self, domain, address):
        row = RouteRow(domain, address, self.on_remove_route_request)
        self.routes_listbox.append(row)

    def on_add_button_clicked(self, widget):
        domain = self.domain_entry.get_text().strip()
        if not domain:
            return
        self.add_button.set_sensitive(False)
        self.add_spinner.start()
        
        self.controller.request_add_route(
            domain,
            on_success=self.handle_route_add_success,
            on_error=self.handle_route_add_error
        )

    def on_remove_route_request(self, route_row):
        self.controller.request_remove_route(
            route_row.domain,
            route_row.address,
            on_success=route_row.on_remove_success,
            on_error=route_row.on_remove_error
        )
    
    def clear_routes_list(self):
        """Remove todas as rotas da lista visual."""
        # Itera sobre os filhos da ListBox e os remove um por um
        # É mais seguro fazer isso em um loop while, pois a lista muda a cada remoção
        child = self.routes_listbox.get_first_child()
        while child:
            self.routes_listbox.remove(child)
            child = self.routes_listbox.get_first_child()
        print("Lista de rotas visuais foi limpa.")

    # Callbacks que são chamados pela thread do Controller
    def handle_route_add_success(self, status, addresses):
        # Usa GLib.idle_add para garantir que a UI seja atualizada na thread principal
        GLib.idle_add(self._update_ui_on_add_success, addresses)

    def handle_route_add_error(self, error_message):
        GLib.idle_add(self._update_ui_on_add_error, error_message)
        
    # Funções auxiliares que fazem o trabalho real na UI
    def _update_ui_on_add_success(self, addresses):
        self.add_spinner.stop()
        self.add_button.set_sensitive(True)
        domain = self.domain_entry.get_text().strip() # Pega o texto de novo aqui dentro
        self.domain_entry.set_text("")
        for addr in addresses:
            self.add_route_to_list(domain, addr)
        return False # Remove a tarefa da fila do GLib

    def _update_ui_on_add_error(self, error_message):
        self.add_spinner.stop()
        self.add_button.set_sensitive(True)
        self.show_error_dialog(_("Failed to Add Route"), error_message)
        return False # Remove a tarefa da fila do GLib

    def show_info_dialog(self, title, message):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(), title=title, body=message
        )
        dialog.add_response("ok", _("OK"))
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()

    def show_error_dialog(self, title, message):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(), title=title, body=message
        )
        dialog.add_response("ok", _("OK"))
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()