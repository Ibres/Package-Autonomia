from enum import Enum

class ControllerMode(Enum):
    OFF = 0
    STANDBY = 1
    ENABLED = 2

class ControllerManager:
    """
    Gerencia a ativação e seleção dos controladores ArduPilot (Aéreo e Aquático).
    Garante que apenas um controlador esteja ativo por vez através da interface MAVROS.
    """
    def __init__(self):
        self._ardupilot_air_mode = ControllerMode.OFF
        self._ardupilot_water_mode = ControllerMode.OFF
        self._active_controller = "NONE"

    def enable_aerial(self):
        """Habilita o controlador ArduPilot Aéreo."""
        self._ardupilot_air_mode = ControllerMode.ENABLED
        self._ardupilot_water_mode = ControllerMode.OFF
        self._active_controller = "ARDUPILOT_AIR"

    def disable_aerial(self):
        """Desabilita o controlador ArduPilot Aéreo."""
        self._ardupilot_air_mode = ControllerMode.OFF
        if self._active_controller == "ARDUPILOT_AIR":
            self._active_controller = "NONE"

    def enable_aquatic(self):
        """Habilita o controlador ArduPilot Aquático."""
        self._ardupilot_water_mode = ControllerMode.ENABLED
        self._ardupilot_air_mode = ControllerMode.OFF
        self._active_controller = "ARDUPILOT_WATER"

    def disable_aquatic(self):
        """Desabilita o controlador ArduPilot Aquático."""
        self._ardupilot_water_mode = ControllerMode.OFF
        if self._active_controller == "ARDUPILOT_WATER":
            self._active_controller = "NONE"

    def activate_aerial_controller(self):
        """Ativa o controlador aéreo como o principal."""
        self.enable_aerial()

    def activate_aquatic_controller(self):
        """Ativa o controlador aquático como o principal."""
        self.enable_aquatic()

    def set_aerial_standby(self):
        """Coloca o sistema aéreo em modo de prontidão (Standby)."""
        self._ardupilot_air_mode = ControllerMode.STANDBY

    def set_aquatic_standby(self):
        """Coloca o sistema aquático em modo de prontidão (Standby)."""
        self._ardupilot_water_mode = ControllerMode.STANDBY

    @property
    def current_controller(self) -> str:
        return self._active_controller

    def get_status_dict(self):
        """Retorna o estado atual dos controladores para publicação."""
        return {
            "ardupilot_air": self._ardupilot_air_mode.name,
            "ardupilot_water": self._ardupilot_water_mode.name,
            "active": self._active_controller
        }
