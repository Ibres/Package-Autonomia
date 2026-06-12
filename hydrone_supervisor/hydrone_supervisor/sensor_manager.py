from dataclasses import dataclass
from typing import Optional

@dataclass
class SensorStatus:
    """
    Representa o estado de confiabilidade dos sensores.
    """
    gps_valid: bool = False
    depth_valid: bool = False
    imu_valid: bool = False
    water_detected: bool = False
    battery_valid: bool = False
    aerial_navigation_available: bool = False
    aquatic_navigation_available: bool = False

class SensorManager:
    """
    Gerencia a confiabilidade dos sensores e decide quais são confiáveis no meio atual.
    Responsável por processar dados brutos e gerar o SensorStatus.
    """
    def __init__(self, battery_threshold=20.0, depth_threshold=0.5):
        self._status = SensorStatus()
        self._battery_threshold = battery_threshold
        self._depth_threshold = depth_threshold
        
        # Dados brutos internos (cache)
        self._last_gps = None
        self._last_imu = None
        self._last_depth = 0.0
        self._last_battery = 100.0
        self._last_water_contact = False

    def update_gps(self, msg):
        """Atualiza estado do GPS baseado na mensagem NavSatFix."""
        self._last_gps = msg
        # Lógica simplificada: status >= 0 significa fix válido
        self._status.gps_valid = (msg.status.status >= 0)
        self._evaluate_navigation_availability()

    def update_imu(self, msg):
        """Atualiza estado da IMU."""
        self._last_imu = msg
        # Lógica simplificada: presença de dados
        self._status.imu_valid = True 
        self._evaluate_navigation_availability()

    def update_depth(self, msg):
        """Atualiza profundidade."""
        # Assume msg.data como profundidade em metros
        self._last_depth = msg.data
        self._status.depth_valid = True # Lógica de validação pode ser mais complexa
        self._evaluate_navigation_availability()

    def update_battery(self, msg):
        """Atualiza estado da bateria."""
        self._last_battery = msg.percentage * 100.0 if hasattr(msg, 'percentage') else msg.data
        self._status.battery_valid = (self._last_battery > self._battery_threshold)

    def update_water_contact(self, msg):
        """Atualiza sensor de contato com água."""
        self._last_water_contact = msg.data
        self._status.water_detected = self._last_water_contact

    def _evaluate_navigation_availability(self):
        """Avalia se a navegação aérea ou aquática está disponível baseado nos sensores."""
        # Aérea: GPS + IMU + Bateria
        self._status.aerial_navigation_available = (
            self._status.gps_valid and 
            self._status.imu_valid and 
            self._status.battery_valid
        )
        
        # Aquática: Profundidade + IMU + Bateria
        self._status.aquatic_navigation_available = (
            self._status.depth_valid and 
            self._status.imu_valid and 
            self._status.battery_valid
        )

    @property
    def status(self) -> SensorStatus:
        return self._status

    def get_current_depth(self) -> float:
        return self._last_depth

    def is_battery_critical(self) -> bool:
        return not self._status.battery_valid
