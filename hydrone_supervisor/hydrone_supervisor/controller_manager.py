from enum import Enum

class ControllerMode(Enum):
    OFF = 0
    STANDBY = 1
    ENABLED = 2

class ControllerManager:
    """
    Gerencia a ativação e seleção dos controladores Pixhawk (Aéreo e Aquático).
    Garante que apenas um controlador esteja ativo por vez.
    """
    def __init__(self):
        self._px4_air_mode = ControllerMode.OFF
        self._px4_water_mode = ControllerMode.OFF
        self._active_controller = "NONE"

    def enable_aerial(self):
        self._px4_air_mode = ControllerMode.ENABLED
        self._px4_water_mode = ControllerMode.OFF
        self._active_controller = "PX4_AIR"

    def disable_aerial(self):
        self._px4_air_mode = ControllerMode.OFF
        self._active_controller = "NONE"

    def enable_aquatic(self):
        self._px4_water_mode = ControllerMode.ENABLED
        self._px4_air_mode = ControllerMode.OFF
        self._active_controller = "PX4_WATER"

    def disable_aquatic(self):
        self._px4_water_mode = ControllerMode.OFF
        self._active_controller = "NONE"

    def set_aerial_standby(self):
        self._px4_air_mode = ControllerMode.STANDBY

    def set_aquatic_standby(self):
        self._px4_water_mode = ControllerMode.STANDBY

    def activate_aerial_controller(self):
        self.enable_aerial()

    def activate_aquatic_controller(self):
        self.enable_aquatic()

    @property
    def current_controller(self) -> str:
        return self._active_controller

    def get_status_dict(self):
        return {
            "px4_air": self._px4_air_mode.name,
            "px4_water": self._px4_water_mode.name,
            "active": self._active_controller
        }
