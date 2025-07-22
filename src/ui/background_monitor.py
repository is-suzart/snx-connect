# background_monitor.py
import gi  # type: ignore
gi.require_version('Notify', '0.7')
from gi.repository import Notify
import time
import subprocess
import os
import sys

def is_vpn_connected():
    """Verifica se a interface de rede 'tunsnx' da VPN existe."""
    try:
        # Usar 'ip addr show' é uma forma fiável de verificar se a interface está ativa.
        # Redirecionamos a saída para /dev/null para não poluir o terminal.
        subprocess.run(
            ['ip', 'addr', 'show', 'tunsnx'],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Se o comando falhar ou 'ip' não for encontrado, a interface não existe.
        return False

def main():
    """
    O loop principal do monitor. Verifica a conexão a cada 5 segundos.
    """
    # Inicializa o sistema de notificações com o nome da nossa aplicação.
    Notify.init("SNX Connect")
    
    # Assume que, quando o monitor começa, a VPN está conectada.
    was_connected = True
    
    while True:
        currently_connected = is_vpn_connected()
        
        # Deteta a transição de 'conectado' para 'desconectado'.
        if was_connected and not currently_connected:
            print("VPN Disconnected! Sending notification.")
            notification = Notify.Notification.new(
                "SNX VPN Disconnected",
                "The VPN connection was lost.",
                "network-vpn-acquiring-symbolic" # Um ícone apropriado
            )
            notification.set_urgency(Notify.Urgency.CRITICAL)
            notification.show()
            
            # Como a conexão caiu, o trabalho do monitor terminou.
            break
            
        was_connected = currently_connected
        # Espera 5 segundos antes de verificar novamente.
        time.sleep(5)

if __name__ == "__main__":
    # Garante que o script não seja executado se for importado por engano.
    main()
