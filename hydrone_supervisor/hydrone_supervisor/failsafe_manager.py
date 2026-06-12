from .state_machine import State, TransitionTrigger
from .sensor_manager import SensorStatus

class FailsafeManager:
    """
    Monitora o sistema para condições de falha e determina os gatilhos de transição apropriados.
    Centraliza toda a lógica de segurança e failsafes.
    """
    def __init__(self):
        self._last_failsafe_reason = ""

    def evaluate(self, current_state: State, sensor_status: SensorStatus) -> list[TransitionTrigger]:
        """
        Avalia o estado atual e os sensores para determinar se algum gatilho de failsafe deve ser disparado.
        Retorna uma lista de gatilhos (priorizados).
        """
        triggers = []

        # 1. Verificações Críticas Globais (EMERGENCY_STOP)
        if not sensor_status.imu_valid and current_state != State.IDLE:
            self._last_failsafe_reason = "Perda de IMU fora de IDLE"
            triggers.append(TransitionTrigger.CRITICAL_FAILURE)
            return triggers

        # 2. Verificações de Bateria
        if not sensor_status.battery_valid:
            self._last_failsafe_reason = "Bateria Crítica"
            triggers.append(TransitionTrigger.BATTERY_CRITICAL)

        # 3. Verificações por Estado
        if current_state == State.AERIAL_NAV:
            if not sensor_status.gps_valid:
                self._last_failsafe_reason = "GPS perdido em voo"
                triggers.append(TransitionTrigger.GPS_LOST)

        elif current_state == State.AQUATIC_NAV:
            if not sensor_status.depth_valid:
                self._last_failsafe_reason = "Sensor de profundidade falhou submerso"
                triggers.append(TransitionTrigger.DEPTH_SENSOR_FAILURE)

        elif current_state == State.TRANSITION_DOWN_PREPARE or current_state == State.TRANSITION_DOWN:
            # Se houver instabilidade ou falha de sensor durante mergulho
            if not sensor_status.imu_valid:
                self._last_failsafe_reason = "Instabilidade na transição de descida"
                triggers.append(TransitionTrigger.TRANSITION_INSTABILITY)

        elif current_state == State.TRANSITION_UP_PREPARE:
            if not sensor_status.gps_valid:
                # Conforme especificação: permanecer em TRANSITION_UP_PREPARE
                triggers.append(TransitionTrigger.GPS_UNAVAILABLE)

        return triggers

    @property
    def last_reason(self) -> str:
        return self._last_failsafe_reason
