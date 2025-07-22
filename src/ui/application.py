# ui/application.py
import gi  # type: ignore
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk,GLib
from .window import MainWindow # Importa MainWindow, que não depende mais deste arquivo

import gettext
_ = gettext.gettext

class Application(Adw.Application):
    def __init__(self, controller, **kwargs):
        super().__init__(**kwargs, application_id="com.exemplo.SNXConnect")
        self.controller = controller
        self.connect("activate", self.on_activate)

    def do_startup(self):
        Adw.Application.do_startup(self)
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_path("./style.css")
            print("Carregando CSS personalizado...")
        except Exception as e:
            print(f"Erro ao carregar CSS: {e}")
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def on_activate(self, app):
        self.win = MainWindow(application=app, controller=self.controller)
        self.win.present()
        self._check_dependencies()

    def _check_dependencies(self):
        """
        Verifica as dependências e, se necessário, oferece a instalação ao usuário.
        """
        dependencies = self.controller.check_dependencies()
        if not dependencies["snx_installed"]:
            
            def on_dialog_response(dialog, response_id):
                if response_id == "install":
                    self.controller.request_install_snx(
                        on_success=self.on_install_success,
                        on_error=self.on_install_error
                    )
                dialog.close()

            dialog_body = _("SNX is not installed. This is required for the application to work.")
            if dependencies["pkexec_installed"]:
                dialog_body += "\n\n" + _("Do you want to try to install it now?")
            
            dialog = Adw.MessageDialog(
                transient_for=self.win,
                title=_("Dependency Missing"),
                body=dialog_body,
            )
            
            if dependencies["pkexec_installed"]:
                dialog.add_response("install", _("Install"))
                dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
                dialog.add_response("cancel", _("Cancel"))
            else:
                dialog.add_response("ok", _("OK"))

            dialog.connect("response", on_dialog_response)
            dialog.present()
    
    # Callbacks que são chamados pela thread do Controller
    def on_install_success(self, status, message):
        GLib.idle_add(self._show_install_success_dialog, message)

    def on_install_error(self, error_message):
        GLib.idle_add(self._show_install_error_dialog, error_message)

    # Funções auxiliares que fazem o trabalho real na UI
    def _show_install_success_dialog(self, message):
        dialog = Adw.MessageDialog(
            transient_for=self.win,
            title=_("Installation Successful"),
            body=message,
        )
        dialog.add_response("ok", _("OK"))
        # Conecta a resposta do diálogo para fechar a aplicação
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()
        return False

    def _show_install_error_dialog(self, error_message):
        dialog = Adw.MessageDialog(
            transient_for=self.win,
            title=_("Installation Failed"),
            body=str(error_message),
        )
        dialog.add_response("ok", _("OK"))
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()
        return False