# controller.py
import threading
import logging

# Importa as exceções customizadas do nosso Model para um tratamento de erro limpo
from back_end import VpnError 

class Controller:
    """
    The Controller layer in the MVC architecture.
    Its responsibilities are:
    1. Receive user actions from the View.
    2. Orchestrate long-running tasks in background threads.
    3. Call the Model to perform business logic.
    4. Use callbacks to inform the View of the result.
    It is completely decoupled from the UI framework (no GTK/GLib imports).
    """
    def __init__(self, model):
        """
        Initializes the Controller with its dependencies (the Model).
        This is called Dependency Injection.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model["manager"] # Recebe a instância do VpnManager

    def _run_in_thread(self, target, on_success, on_error, *args):
        """Helper function to run a model method in a background thread."""
        def worker():
            try:
                # Chama o método síncrono do Model
                result = target(*args)
                # Em caso de sucesso, chama o callback de sucesso com o resultado
                if on_success:
                    # Desempacota o dicionário de resultado para os callbacks
                    on_success(**result)
            except VpnError as e:
                # Em caso de erro, chama o callback de erro com a mensagem da exceção
                self.logger.error(f"An error occurred in the worker thread: {e}")
                if on_error:
                    on_error(str(e))
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

    # --- Public API for the View ---

    def request_login(self, login_info, on_success, on_error):
        """Handles the user's request to log in."""
        self.logger.info(f"Login requested for user: {login_info['name']}")
        self._run_in_thread(
            self.model.connect,
            on_success,
            on_error,
            login_info["website"],
            login_info["name"],
            login_info["password"],
            login_info["keep"]
        )

    def request_disconnect(self, on_success, on_error):
        """Handles the user's request to disconnect."""
        self.logger.info("Disconnect requested.")
        self._run_in_thread(self.model.disconnect, on_success, on_error)
    
    def on_keep_routes_check_toggled (self, widget):
        """
        Handles the toggling of the 'keep routes' checkbox.
        This is called from the View when the user changes the state of the checkbox.
        """
        self.logger.info(f"Keep routes checkbox toggled: {widget.get_active()}")
        self.model.set_keep_routes(widget.get_active())

    def request_load_routes(self, view):
        """
        Handles the request to load saved routes into the view.
        This is a synchronous call as it should be fast.
        """
        self.logger.info("Loading saved routes for the view.")
        try:
            routes = self.model.get_saved_routes()
            for route in routes:
                # O Controller comanda a View para se atualizar
                view.add_route_to_list(route["domain"], route["ip"])
        except VpnError as e:
            self.logger.error(f"Failed to load routes: {e}")
            view.show_error_dialog("Error Loading Routes", str(e))
            
    def request_add_route(self, domain, on_success, on_error):
        """Handles the user's request to add a new route."""
        self.logger.info(f"Route addition requested for domain: {domain}")
        self._run_in_thread(self.model.add_route, on_success, on_error, domain)

    def request_remove_route(self, domain, ip_address, on_success, on_error):
        """Handles the user's request to remove a route."""
        self.logger.info(f"Route removal requested for: {domain} ({ip_address})")
        self._run_in_thread(self.model.remove_route, on_success, on_error, domain, ip_address)

    def check_dependencies(self):
        """Synchronously checks for system dependencies."""
        return self.model.check_dependencies()

    def request_install_snx(self, on_success, on_error):
        """Handles the request to install SNX."""
        self.logger.info("SNX installation requested.")
        self._run_in_thread(self.model.install_snx, on_success, on_error)