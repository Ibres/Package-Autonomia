from .state_machine import State, TransitionTrigger
from .sensor_manager import SensorStatus

class FailsafeManager:
    """
    Monitora o sistema para condições de falha e determina os gatilhos de transição apropriados.
    Centraliza toda a lógica de segurança e failsafes conforme a especificação técnica.
    """
    def __init__(self):
        self._last_reason = ""

    def evaluate(self, current_state: State, sensor_status: SensorStatus) -> list[TransitionTrigger]:
        """
        Avalia o estado atual e os sensores para determinar gatilhos de failsafe.
        Retorna uma lista de gatilhos priorizados.
        """
        triggers = []

        # 1. FALHAS CATASTRÓFICAS (EMERGENCY_STOP)
        # Perda simultânea de sensores críticos ou IMU falhando fora de IDLE
        if not sensor_status.imu_valid and current_state != State.IDLE:
            self._last_reason = "Falha Crítica de IMU detectada"
            triggers.append(TransitionTrigger.CRITICAL_FAILURE)
            return triggers

        # Perda de comunicação total
        if not sensor_status.comm_air_valid and not sensor_status.comm_water_valid:
            if current_state not in [State.IDLE, State.RECOVERY_WAIT]:
                self._last_reason = "Perda total de comunicação com ArduPilot Controllers"
                triggers.append(TransitionTrigger.CRITICAL_FAILURE)
                return triggers

        # 2. FALHAS DE COMUNICAÇÃO ESPECÍFICAS
        if current_state in [State.AERIAL_NAV, State.LAND, State.FAILSAFE_RETURN]:
            if not sensor_status.comm_air_valid:
                self._last_reason = "Perda de comunicação com ArduPilot Aéreo"
                triggers.append(TransitionTrigger.COMMUNICATION_FAILURE)

        if current_state in [State.AQUATIC_NAV, State.FAILSAFE_SURFACE]:
            if not sensor_status.comm_water_valid:
                self._last_reason = "Perda de comunicação com ArduPilot Aquático"
                triggers.append(TransitionTrigger.COMMUNICATION_FAILURE)

        # 3. FALHAS DE SENSORES POR MEIO
        # GPS em Navegação Aérea
        if current_state == State.AERIAL_NAV and not sensor_status.gps_valid:
            self._last_reason = "GPS perdido durante navegação aérea"
            triggers.append(TransitionTrigger.GPS_LOST)

        # Profundidade em Navegação Aquática
        if current_state == State.AQUATIC_NAV and not sensor_status.depth_valid:
            self._last_reason = "Sensor de profundidade falhou submerso"
            triggers.append(TransitionTrigger.DEPTH_SENSOR_FAILURE)

        # 4. BATERIA CRÍTICA
        if not sensor_status.battery_valid:
            self._last_reason = "Bateria abaixo do limite operacional"
            triggers.append(TransitionTrigger.BATTERY_CRITICAL)

        # 5. FALHAS DURANTE TRANSIÇÃO
        if current_state == State.TRANSITION_DOWN_PREPARE:
            if not sensor_status.comm_water_valid:
                self._last_reason = "Pixhawk aquática indisponível para mergulho"
                triggers.append(TransitionTrigger.AQUATIC_CONTROLLER_FAILURE)

        if current_state == State.TRANSITION_UP_PREPARE:
            if not sensor_status.gps_valid:
                self._last_reason = "GPS indisponível para emersão"
                triggers.append(TransitionTrigger.GPS_UNAVAILABLE)

        return triggers

    @property
    def last_reason(self) -> str:
        return self._last_reason
