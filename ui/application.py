# ui/application.py
import gi  # type: ignore
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from .window import MainWindow # Usando import relativo

# Assume que _ está configurado no main.py
import gettext
_ = gettext.gettext

class Application(Adw.Application):
    def __init__(self, controller, **kwargs):
        super().__init__(**kwargs, application_id="com.exemplo.SNXConnect")
        self.controller = controller
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = MainWindow(application=app, controller=self.controller)
        win.present()
        self._check_dependencies(win)

    def _check_dependencies(self, win):
        """
        Uses the controller to check for dependencies, decoupling the view
        from the back-end logic.
        """
        dependencies = self.controller.check_dependencies()
        if not dependencies["snx_installed"]:
            # A lógica para disparar a instalação via controller iria aqui
            dialog = Adw.MessageDialog(
                transient_for=win,
                title=_("Dependencies Missing"),
                body=_("SNX is not installed. Please install it to continue."),
            )
            dialog.add_response("ok", _("OK"))
            dialog.connect("response", lambda d, r: d.close())
            dialog.present()