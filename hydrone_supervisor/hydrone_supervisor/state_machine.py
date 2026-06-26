from enum import Enum, auto

class State(Enum):
    """
    Representa os estados possíveis do veículo Hydrone conforme especificação técnica.
    """
    # Estados Normais
    IDLE = auto()
    AERIAL_NAV = auto()
    TRANSITION_DOWN_PREPARE = auto()
    TRANSITION_DOWN = auto()
    AQUATIC_NAV = auto()
    TRANSITION_UP_PREPARE = auto()
    TRANSITION_UP = auto()
    LAND = auto()

    # Estados de Failsafe e Emergência
    EMERGENCY_STOP = auto()
    EMERGENCY_HOLD = auto()
    RECOVERY_WAIT = auto()
    FAILSAFE_SURFACE = auto()
    FAILSAFE_RETURN = auto()
    FAILSAFE_ABORT_DIVE = auto()

class TransitionTrigger(Enum):
    """
    Gatilhos que causam mudanças de estado na FSM.
    """
    ARM_MISSION = auto()
    START_MISSION = auto()
    ABORT_MISSION = auto()
    MISSION_COMPLETE = auto()
    DIVE_POINT_REACHED = auto()
    DIVE_READY = auto()
    WATER_DETECTED = auto()
    SURFACE_POINT_REACHED = auto()
    SURFACE_READY = auto()
    FLIGHT_STABLE = auto()
    HOME_REACHED = auto()
    LANDING_COMPLETE = auto()
    SENSOR_FAILURE = auto()
    COMMUNICATION_FAILURE = auto()
    GPS_LOST = auto()
    GPS_UNAVAILABLE = auto()
    BATTERY_CRITICAL = auto()
    AIR_CONTROLLER_FAILURE = auto()
    AQUATIC_CONTROLLER_FAILURE = auto()
    TRANSITION_INSTABILITY = auto()
    DEPTH_SENSOR_FAILURE = auto()
    LANDING_FAILURE = auto()
    AIR_CONTROL_RESTORED = auto()
    RETURN_REQUIRED = auto()
    CRITICAL_FAILURE = auto()
    PROPULSION_FAILURE = auto()
    SYSTEM_RECOVERED = auto()
    RECOVERY_FAILED = auto()
    AQUATIC_RECOVERY_FAILED = auto()
    OPERATOR_AUTHORIZATION = auto()
    OPERATOR_RESET = auto()
    MISSION_ABORTED = auto()

class StateMachine:
    """
    Gerencia a lógica de transição de estados do Hydrone.
    Implementa a tabela formal de transições da especificação técnica.
    """
    def __init__(self, initial_state=State.IDLE):
        self._current_state = initial_state
        self._previous_state = None
        
        # Tabela formal de transições
        self._transitions = {
            State.IDLE: {
                TransitionTrigger.ARM_MISSION: State.AERIAL_NAV,
                TransitionTrigger.SENSOR_FAILURE: State.IDLE,
                TransitionTrigger.COMMUNICATION_FAILURE: State.IDLE
            },
            State.AERIAL_NAV: {
                TransitionTrigger.DIVE_POINT_REACHED: State.TRANSITION_DOWN_PREPARE,
                TransitionTrigger.GPS_LOST: State.FAILSAFE_RETURN,
                TransitionTrigger.BATTERY_CRITICAL: State.FAILSAFE_RETURN,
                TransitionTrigger.AIR_CONTROLLER_FAILURE: State.EMERGENCY_STOP
            },
            State.TRANSITION_DOWN_PREPARE: {
                TransitionTrigger.DIVE_READY: State.TRANSITION_DOWN,
                TransitionTrigger.AQUATIC_CONTROLLER_FAILURE: State.FAILSAFE_ABORT_DIVE,
                TransitionTrigger.COMMUNICATION_FAILURE: State.FAILSAFE_RETURN
            },
            State.TRANSITION_DOWN: {
                TransitionTrigger.WATER_DETECTED: State.AQUATIC_NAV,
                TransitionTrigger.AQUATIC_CONTROLLER_FAILURE: State.FAILSAFE_ABORT_DIVE,
                TransitionTrigger.TRANSITION_INSTABILITY: State.FAILSAFE_ABORT_DIVE
            },
            State.AQUATIC_NAV: {
                TransitionTrigger.SURFACE_POINT_REACHED: State.TRANSITION_UP_PREPARE,
                TransitionTrigger.DEPTH_SENSOR_FAILURE: State.FAILSAFE_SURFACE,
                TransitionTrigger.COMMUNICATION_FAILURE: State.FAILSAFE_SURFACE,
                TransitionTrigger.BATTERY_CRITICAL: State.FAILSAFE_SURFACE
            },
            State.TRANSITION_UP_PREPARE: {
                TransitionTrigger.SURFACE_READY: State.TRANSITION_UP,
                TransitionTrigger.AIR_CONTROLLER_FAILURE: State.FAILSAFE_SURFACE,
                TransitionTrigger.GPS_UNAVAILABLE: State.TRANSITION_UP_PREPARE
            },
            State.TRANSITION_UP: {
                TransitionTrigger.FLIGHT_STABLE: State.AERIAL_NAV,
                TransitionTrigger.MISSION_COMPLETE: State.LAND,
                TransitionTrigger.AIR_CONTROLLER_FAILURE: State.FAILSAFE_SURFACE
            },
            State.LAND: {
                TransitionTrigger.LANDING_COMPLETE: State.IDLE,
                TransitionTrigger.LANDING_FAILURE: State.EMERGENCY_STOP
            },
            State.FAILSAFE_ABORT_DIVE: {
                TransitionTrigger.AIR_CONTROL_RESTORED: State.AERIAL_NAV,
                TransitionTrigger.RETURN_REQUIRED: State.FAILSAFE_RETURN,
                TransitionTrigger.CRITICAL_FAILURE: State.EMERGENCY_STOP
            },
            State.FAILSAFE_SURFACE: {
                TransitionTrigger.SURFACE_REACHED: State.TRANSITION_UP_PREPARE,
                TransitionTrigger.MISSION_ABORTED: State.RECOVERY_WAIT,
                TransitionTrigger.PROPULSION_FAILURE: State.EMERGENCY_STOP
            },
            State.FAILSAFE_RETURN: {
                TransitionTrigger.HOME_REACHED: State.LAND,
                TransitionTrigger.GPS_LOST: State.EMERGENCY_HOLD
            },
            State.EMERGENCY_HOLD: {
                TransitionTrigger.SYSTEM_RECOVERED: None, # Especial: retorna ao anterior
                TransitionTrigger.RECOVERY_FAILED: State.FAILSAFE_RETURN,
                TransitionTrigger.AQUATIC_RECOVERY_FAILED: State.FAILSAFE_SURFACE,
                TransitionTrigger.CRITICAL_FAILURE: State.EMERGENCY_STOP
            },
            State.EMERGENCY_STOP: {
                TransitionTrigger.OPERATOR_AUTHORIZATION: State.RECOVERY_WAIT
            },
            State.RECOVERY_WAIT: {
                TransitionTrigger.OPERATOR_RESET: State.IDLE
            }
        }

    @property
    def current_state(self) -> State:
        return self._current_state

    def process_trigger(self, trigger: TransitionTrigger) -> bool:
        """Processa um gatilho e realiza a transição de estado se válida."""
        if self._current_state in self._transitions:
            possible_transitions = self._transitions[self._current_state]
            if trigger in possible_transitions:
                next_state = possible_transitions[trigger]
                
                # Caso especial: EMERGENCY_HOLD -> PREVIOUS_STATE
                if self._current_state == State.EMERGENCY_HOLD and trigger == TransitionTrigger.SYSTEM_RECOVERED:
                    next_state = self._previous_state if self._previous_state else State.IDLE
                
                if next_state is not None:
                    self._previous_state = self._current_state
                    self._current_state = next_state
                    return True
        
        # Gatilho Global de Falha Crítica
        if trigger == TransitionTrigger.CRITICAL_FAILURE and self._current_state != State.EMERGENCY_STOP:
            self._previous_state = self._current_state
            self._current_state = State.EMERGENCY_STOP
            return True
            
        return False
