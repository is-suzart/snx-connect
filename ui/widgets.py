# ui/widgets.py
import gi  # type: ignore
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import gettext
_ = gettext.gettext

class ThemeSwitcher(Gtk.Box):
    """Um widget que replica o seletor de tema do Editor de Texto do GNOME."""
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        
        self.add_css_class("themeselector")
        self.set_orientation(Gtk.Orientation.HORIZONTAL)

        # --- Botão de Tema Claro ---
        self.light_button = Gtk.CheckButton()
        self.light_button.add_css_class("theme-button")
        self.light_button.add_css_class("light")
        self.light_button.set_tooltip_text(_("Light Style"))
        self.light_button.connect("toggled", self.on_theme_button_toggled, Adw.ColorScheme.FORCE_LIGHT)
        self.append(self.light_button)

        # --- Botão de Tema do Sistema (Follow) ---
        self.system_button = Gtk.CheckButton(group=self.light_button)
        self.system_button.add_css_class("theme-button")
        self.system_button.add_css_class("follow")
        self.system_button.set_tooltip_text(_("Follow System Style"))
        self.system_button.connect("toggled", self.on_theme_button_toggled, Adw.ColorScheme.DEFAULT)
        self.append(self.system_button)

        # --- Botão de Tema Escuro ---
        self.dark_button = Gtk.CheckButton(group=self.light_button)
        self.dark_button.add_css_class("theme-button")
        self.dark_button.add_css_class("dark")
        self.dark_button.set_tooltip_text(_("Dark Style"))
        self.dark_button.connect("toggled", self.on_theme_button_toggled, Adw.ColorScheme.FORCE_DARK)
        self.append(self.dark_button)
        
        # Define o botão ativo com base no tema atual
        current_scheme = self.app.get_style_manager().get_color_scheme()
        if current_scheme == Adw.ColorScheme.FORCE_LIGHT:
            self.light_button.set_active(True)
        elif current_scheme == Adw.ColorScheme.FORCE_DARK:
            self.dark_button.set_active(True)
        else:
            self.system_button.set_active(True)

    def on_theme_button_toggled(self, button, scheme):
        if button.get_active():
            self.app.get_style_manager().set_color_scheme(scheme)

