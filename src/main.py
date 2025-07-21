# main.py
import sys
import locale
import gettext

# Importações da nova estrutura de UI e do back-end
from ui.application import Application
from controller import Controller
from back_end import VpnManager # Assumindo uma classe que unifica o back-end

# --- Configuração da Tradução ---
# A configuração de i18n permanece como o ponto de partida global
LOCALE_DIR = "i18n"
APP_NAME = "snx_connect"
try:
    locale.setlocale(locale.LC_ALL, "")
    gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
    gettext.textdomain(APP_NAME)
    _ = gettext.gettext
except Exception as e:
    print(f"Failed to load translations: {e}")
    _ = lambda s: s


if __name__ == "__main__":
    """
    Application entry point.
    Responsible for creating and injecting dependencies (Model, Controller, View).
    """
    # 1. Cria o Model (aqui estamos assumindo uma classe unificada VpnManager)
    model = {
        "manager": VpnManager()
    }

    # 2. Cria o Controller, injetando o Model
    controller = Controller(model)

    # 3. Cria a Aplicação (View principal), injetando o Controller
    app = Application(controller=controller)

    # 4. Executa a aplicação
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)