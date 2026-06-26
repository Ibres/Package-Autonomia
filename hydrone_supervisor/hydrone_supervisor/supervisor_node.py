import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool, Float32
from sensor_msgs.msg import NavSatFix, Imu, BatteryState
from std_srvs.srv import Trigger
import time

from .state_machine import StateMachine, State, TransitionTrigger
from .sensor_manager import SensorManager
from .controller_manager import ControllerManager
from .failsafe_manager import FailsafeManager

class SupervisorNode(Node):
    """
    Nó Supervisor Principal do Hydrone.
    Responsável pela orquestração de alto nível entre ArduPilot Aéreo e Aquático via MAVROS.
    """
    def __init__(self):
        super().__init__('hydrone_supervisor')
        
        # Inicialização dos Módulos Core
        self.state_machine = StateMachine()
        self.sensor_manager = SensorManager()
        self.controller_manager = ControllerManager()
        self.failsafe_manager = FailsafeManager()
        
        # --- CONFIGURAÇÃO DE SUBS CRIÇÕES (MAVROS) ---
        
        # ArduPilot Aéreo (Namespace: /aerial)
        self.create_subscription(NavSatFix, '/aerial/mavros/global_position/global', self.sensor_manager.update_gps, 10)
        self.create_subscription(Imu, '/aerial/mavros/imu/data', self.sensor_manager.update_imu, 10)
        self.create_subscription(BatteryState, '/aerial/mavros/battery', self.sensor_manager.update_battery, 10)
        
        # Sensores Específicos/Aquáticos
        self.create_subscription(Float32, '/depth', self.sensor_manager.update_depth, 10)
        self.create_subscription(Bool, '/water_contact', self.sensor_manager.update_water_contact, 10)
        
        # Heartbeats (Simulados via recepção de dados para este exemplo)
        self.create_subscription(String, '/aerial/mavros/state', lambda m: self.sensor_manager.update_heartbeat_air(time.time()), 10)
        self.create_subscription(String, '/aquatic/mavros/state', lambda m: self.sensor_manager.update_heartbeat_water(time.time()), 10)

        # --- CONFIGURAÇÃO DE PUBLICAÇÕES ---
        self.state_pub = self.create_publisher(String, '/hydrone/state', 10)
        self.ctrl_mode_pub = self.create_publisher(String, '/hydrone/controller_mode', 10)
        self.failsafe_pub = self.create_publisher(String, '/hydrone/failsafe', 10)
        
        # --- CONFIGURAÇÃO DE SERVIÇOS ---
        self.create_service(Trigger, '/arm', self.handle_arm)
        self.create_service(Trigger, '/disarm', self.handle_disarm)
        self.create_service(Trigger, '/start_mission', self.handle_start_mission)
        self.create_service(Trigger, '/abort_mission', self.handle_abort_mission)
        
        # Loop de Supervisão (10Hz)
        self.timer = self.create_timer(0.1, self.supervision_loop)
        
        self.get_logger().info("Hydrone Supervisor Node (ArduPilot/MAVROS) Inicializado.")

    def supervision_loop(self):
        """
        Execução sequencial do ciclo de supervisão conforme especificação técnica.
        """
        # 1. LER SENSORES E VERIFICAR TIMEOUTS
        self.sensor_manager.check_communication_timeouts(time.time())

        # 2. VERIFICAR FAILSAFES
        self.evaluate_failsafes()

        # 3. EXECUTAR FSM (Transições Automáticas)
        self.evaluate_fsm_transitions()

        # 4. SELECIONAR CONTROLADOR
        self.update_active_controller()

        # 5. PUBLICAR ESTADO
        self.publish_system_status()

    def evaluate_failsafes(self):
        """Avalia condições de segurança e dispara gatilhos de failsafe."""
        triggers = self.failsafe_manager.evaluate(
            self.state_machine.current_state, 
            self.sensor_manager.status
        )
        
        for trigger in triggers:
            if self.state_machine.process_trigger(trigger):
                self.get_logger().error(f"FAILSAFE ATIVADO: {trigger.name}. Motivo: {self.failsafe_manager.last_reason}")
                self.failsafe_pub.publish(String(data=f"FAILSAFE: {trigger.name} - {self.failsafe_manager.last_reason}"))

    def evaluate_fsm_transitions(self):
        """Avalia gatilhos automáticos de missão baseados nos sensores."""
        current = self.state_machine.current_state
        status = self.sensor_manager.status
        
        if current == State.TRANSITION_DOWN_PREPARE:
            # DIVE_READY: Comunicação aquática OK e prontidão para mergulho
            if status.comm_water_valid:
                self.state_machine.process_trigger(TransitionTrigger.DIVE_READY)
                
        elif current == State.TRANSITION_DOWN:
            if status.water_detected:
                self.state_machine.process_trigger(TransitionTrigger.WATER_DETECTED)
                
        elif current == State.TRANSITION_UP_PREPARE:
            if status.gps_valid and self.sensor_manager.get_current_depth() < 0.2:
                self.state_machine.process_trigger(TransitionTrigger.SURFACE_READY)
                
        elif current == State.TRANSITION_UP:
            if not status.water_detected and status.gps_valid:
                self.state_machine.process_trigger(TransitionTrigger.FLIGHT_STABLE)

    def update_active_controller(self):
        """Seleciona o controlador ArduPilot ativo com base no estado da FSM."""
        state = self.state_machine.current_state
        
        # Estados Aéreos
        if state in [State.IDLE, State.AERIAL_NAV, State.TRANSITION_DOWN_PREPARE, State.LAND, State.FAILSAFE_RETURN, State.FAILSAFE_ABORT_DIVE]:
            self.controller_manager.activate_aerial_controller()
            
        # Estados Aquáticos
        elif state in [State.AQUATIC_NAV, State.FAILSAFE_SURFACE]:
            self.controller_manager.activate_aquatic_controller()
            
        # Estados de Transição Gradual
        elif state == State.TRANSITION_DOWN:
            self.controller_manager.set_aerial_standby()
            self.controller_manager.set_aquatic_standby()
            
        elif state == State.TRANSITION_UP:
            self.controller_manager.set_aerial_standby()
            self.controller_manager.set_aquatic_standby()
            
        # Estados de Parada/Recuperação
        elif state in [State.EMERGENCY_STOP, State.RECOVERY_WAIT]:
            self.controller_manager.disable_aerial()
            self.controller_manager.disable_aquatic()

    def publish_system_status(self):
        """Publica a telemetria consolidada do supervisor."""
        self.state_pub.publish(String(data=self.state_machine.current_state.name))
        ctrl_status = self.controller_manager.get_status_dict()
        self.ctrl_mode_pub.publish(String(data=str(ctrl_status)))

    # --- HANDLERS DE SERVIÇOS ---
    def handle_arm(self, request, response):
        if self.state_machine.process_trigger(TransitionTrigger.ARM_MISSION):
            response.success = True
            response.message = "Veículo Armado (ArduPilot Aerial Ativo)"
        else:
            response.success = False
            response.message = "Falha ao armar: Condições de segurança não atendidas"
        return response

    def handle_disarm(self, request, response):
        self.controller_manager.disable_aerial()
        self.controller_manager.disable_aquatic()
        response.success = True
        response.message = "Veículo Desarmado"
        return response

    def handle_start_mission(self, request, response):
        self.state_machine.process_trigger(TransitionTrigger.START_MISSION)
        response.success = True
        return response

    def handle_abort_mission(self, request, response):
        self.state_machine.process_trigger(TransitionTrigger.ABORT_MISSION)
        response.success = True
        return response

def main(args=None):
    rclpy.init(args=args)
    node = SupervisorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
