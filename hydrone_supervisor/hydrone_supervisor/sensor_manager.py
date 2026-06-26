from dataclasses import dataclass
from typing import Optional
import rclpy

@dataclass
class SensorStatus:
    """
    Representa o estado de confiabilidade dos sensores conforme especificação.
    """
    gps_valid: bool = False
    depth_valid: bool = False
    imu_valid: bool = False
    water_detected: bool = False
    battery_valid: bool = False
    aerial_navigation_available: bool = False
    aquatic_navigation_available: bool = False
    comm_air_valid: bool = False
    comm_water_valid: bool = False

class SensorManager:
    """
    Gerencia a confiabilidade dos sensores e decide quais são confiáveis no meio atual.
    Integra-se com telemetria MAVROS/ArduPilot.
    """
    def __init__(self, battery_threshold=20.0, depth_threshold=0.2):
        self._status = SensorStatus()
        self._battery_threshold = battery_threshold
        self._depth_threshold = depth_threshold
        
        # Dados brutos para monitoramento interno
        self._last_gps = None
        self._last_imu = None
        self._last_depth = 0.0
        self._last_battery_pct = 100.0
        self._last_water_contact = False
        
        # Timestamps para monitoramento de comunicação (Heartbeat)
        self._last_air_heartbeat = 0.0
        self._last_water_heartbeat = 0.0
        self._comm_timeout = 2.0 # segundos

    def update_gps(self, msg):
        """Atualiza estado do GPS baseado na mensagem NavSatFix do MAVROS."""
        self._last_gps = msg
        # Status >= 0 indica fix válido no MAVROS
        self._status.gps_valid = (msg.status.status >= 0)
        self._evaluate_navigation_availability()

    def update_imu(self, msg):
        """Atualiza estado da IMU."""
        self._last_imu = msg
        # Verifica se os dados da IMU são numericamente válidos
        self._status.imu_valid = (
            abs(msg.linear_acceleration.x) < 50.0 and 
            abs(msg.linear_acceleration.y) < 50.0 and 
            abs(msg.linear_acceleration.z) < 50.0
        )
        self._evaluate_navigation_availability()

    def update_depth(self, msg):
        """Atualiza profundidade (sensor externo ou barômetro aquático)."""
        self._last_depth = msg.data
        # Profundidade válida se dentro de limites operacionais (ex: 0 a 100m)
        self._status.depth_valid = (0.0 <= msg.data <= 100.0)
        self._evaluate_navigation_availability()

    def update_battery(self, msg):
        """Atualiza estado da bateria via BatteryState do MAVROS."""
        # ArduPilot via MAVROS fornece 'percentage' de 0.0 a 1.0
        self._last_battery_pct = msg.percentage * 100.0
        self._status.battery_valid = (self._last_battery_pct > self._battery_threshold)
        self._evaluate_navigation_availability()

    def update_water_contact(self, msg):
        """Atualiza sensor de contato com água."""
        self._last_water_contact = msg.data
        self._status.water_detected = self._last_water_contact

    def update_heartbeat_air(self, current_time):
        """Monitora a comunicação com o ArduPilot Aéreo."""
        self._last_air_heartbeat = current_time
        self._status.comm_air_valid = True

    def update_heartbeat_water(self, current_time):
        """Monitora a comunicação com o ArduPilot Aquático."""
        self._last_water_heartbeat = current_time
        self._status.comm_water_valid = True

    def check_communication_timeouts(self, current_time):
        """Verifica se houve perda de comunicação com os controladores."""
        if current_time - self._last_air_heartbeat > self._comm_timeout:
            self._status.comm_air_valid = False
        if current_time - self._last_water_heartbeat > self._comm_timeout:
            self._status.comm_water_valid = False

    def _evaluate_navigation_availability(self):
        """Avalia se a navegação aérea ou aquática está disponível baseado nos sensores."""
        # Navegação Aérea: GPS + IMU + Bateria + Comunicação Aérea
        self._status.aerial_navigation_available = (
            self._status.gps_valid and 
            self._status.imu_valid and 
            self._status.battery_valid and
            self._status.comm_air_valid
        )
        
        # Navegação Aquática: Profundidade + IMU + Bateria + Comunicação Aquática
        self._status.aquatic_navigation_available = (
            self._status.depth_valid and 
            self._status.imu_valid and 
            self._status.battery_valid and
            self._status.comm_water_valid
        )

    @property
    def status(self) -> SensorStatus:
        return self._status

    def get_current_depth(self) -> float:
        return self._last_depth

    def get_battery_percentage(self) -> float:
        return self._last_battery_pct
