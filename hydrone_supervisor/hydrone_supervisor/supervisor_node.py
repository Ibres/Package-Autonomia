import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool, Float32
from sensor_msgs.msg import NavSatFix, Imu, BatteryState
from std_srvs.srv import Trigger

from .state_machine import StateMachine, State, TransitionTrigger
from .sensor_manager import SensorManager
from .controller_manager import ControllerManager
from .failsafe_manager import FailsafeManager

class SupervisorNode(Node):
    """
    Nó principal do Supervisor do Hydrone.
    Orquestra a FSM, Sensores, Controladores e Failsafes.
    """
    def __init__(self):
        super().__init__('hydrone_supervisor')
        
        # Inicialização dos Componentes Core
        self.state_machine = StateMachine()
        self.sensor_manager = SensorManager()
        self.controller_manager = ControllerManager()
        self.failsafe_manager = FailsafeManager()
        
        # Configuração de Tópicos (Subscrições)
        self.create_subscription(NavSatFix, '/gps/fix', self.sensor_manager.update_gps, 10)
        self.create_subscription(Imu, '/imu/data', self.sensor_manager.update_imu, 10)
        self.create_subscription(Float32, '/depth', self.sensor_manager.update_depth, 10)
        self.create_subscription(BatteryState, '/battery', self.sensor_manager.update_battery, 10)
        self.create_subscription(Bool, '/water_contact', self.sensor_manager.update_water_contact, 10)
        
        # Configuração de Tópicos (Publicações)
        self.state_pub = self.create_publisher(String, '/hydrone/state', 10)
        self.ctrl_mode_pub = self.create_publisher(String, '/hydrone/controller_mode', 10)
        self.failsafe_pub = self.create_publisher(String, '/hydrone/failsafe', 10)
        
        # Configuração de Serviços
        self.create_service(Trigger, '/arm', self.handle_arm)
        self.create_service(Trigger, '/disarm', self.handle_disarm)
        self.create_service(Trigger, '/start_mission', self.handle_start_mission)
        self.create_service(Trigger, '/abort_mission', self.handle_abort_mission)
        
        # Timer Principal (Loop de Supervisão)
        self.timer = self.create_timer(0.1, self.supervision_loop) # 10Hz
        
        self.get_logger().info("Hydrone Supervisor Node Inicializado.")

    def supervision_loop(self):
        """
        Loop principal de execução conforme especificação:
        1. ler sensores (feito via callbacks)
        2. verificar failsafes
        3. executar FSM
        4. selecionar controlador
        5. publicar estado
        """
        # 2. Verificar Failsafes
        failsafe_triggers = self.failsafe_manager.evaluate(
            self.state_machine.current_state, 
            self.sensor_manager.status
        )
        
        for trigger in failsafe_triggers:
            if self.state_machine.process_trigger(trigger):
                self.get_logger().warn(f"Failsafe Ativado: {trigger.name}. Motivo: {self.failsafe_manager.last_reason}")
                self.failsafe_pub.publish(String(data=f"FAILSAFE: {trigger.name} - {self.failsafe_manager.last_reason}"))

        # 3. Executar FSM (Lógica de transição automática baseada em sensores)
        self.evaluate_automatic_transitions()

        # 4. Selecionar Controlador baseado no estado atual
        self.update_controller_selection()

        # 5. Publicar Estado
        self.publish_system_status()

    def evaluate_automatic_transitions(self):
        """Avalia gatilhos automáticos baseados em sensores para a FSM."""
        current = self.state_machine.current_state
        status = self.sensor_manager.status
        
        if current == State.TRANSITION_DOWN_PREPARE:
            # Lógica para DIVE_READY: Velocidade baixa e thrusters prontos (simplificado)
            self.state_machine.process_trigger(TransitionTrigger.DIVE_READY)
            
        elif current == State.TRANSITION_DOWN:
            if status.water_detected:
                self.state_machine.process_trigger(TransitionTrigger.WATER_DETECTED)
                
        elif current == State.TRANSITION_UP_PREPARE:
            # Lógica para SURFACE_READY: GPS válido e próximo da superfície
            if status.gps_valid and self.sensor_manager.get_current_depth() < 0.2:
                self.state_machine.process_trigger(TransitionTrigger.SURFACE_READY)
                
        elif current == State.TRANSITION_UP:
            # Lógica para FLIGHT_STABLE (simplificada)
            if not status.water_detected and status.gps_valid:
                self.state_machine.process_trigger(TransitionTrigger.FLIGHT_STABLE)

    def update_controller_selection(self):
        """Atualiza a ativação dos controladores baseada no estado da FSM."""
        state = self.state_machine.current_state
        
        if state in [State.IDLE, State.AERIAL_NAV, State.TRANSITION_DOWN_PREPARE, State.LAND, State.FAILSAFE_RETURN, State.FAILSAFE_ABORT_DIVE]:
            self.controller_manager.activate_aerial_controller()
        elif state in [State.AQUATIC_NAV, State.FAILSAFE_SURFACE]:
            self.controller_manager.activate_aquatic_controller()
        elif state == State.TRANSITION_DOWN:
            self.controller_manager.set_aerial_standby()
            self.controller_manager.set_aquatic_standby()
        elif state == State.TRANSITION_UP:
            self.controller_manager.set_aerial_standby()
            self.controller_manager.set_aquatic_standby()
        elif state in [State.EMERGENCY_STOP, State.RECOVERY_WAIT]:
            self.controller_manager.disable_aerial()
            self.controller_manager.disable_aquatic()

    def publish_system_status(self):
        """Publica o estado atual do sistema nos tópicos ROS2."""
        self.state_pub.publish(String(data=self.state_machine.current_state.name))
        
        ctrl_status = self.controller_manager.get_status_dict()
        self.ctrl_mode_pub.publish(String(data=str(ctrl_status)))

    # Handlers de Serviços
    def handle_arm(self, request, response):
        if self.state_machine.current_state == State.IDLE:
            if self.state_machine.process_trigger(TransitionTrigger.ARM_MISSION):
                response.success = True
                response.message = "Veículo Armado e em AERIAL_NAV"
            else:
                response.success = False
                response.message = "Falha ao armar: transição negada pela FSM"
        else:
            response.success = False
            response.message = f"Não é possível armar no estado {self.state_machine.current_state.name}"
        return response

    def handle_disarm(self, request, response):
        # Lógica simplificada para desarmar voltando para IDLE se seguro
        response.success = True
        response.message = "Comando de desarmar recebido"
        return response

    def handle_start_mission(self, request, response):
        self.state_machine.process_trigger(TransitionTrigger.START_MISSION)
        response.success = True
        return response

    def handle_abort_mission(self, request, response):
        self.state_machine.process_trigger(TransitionTrigger.ABORT_MISSION)
        response.success = True
        response.message = "Missão Abortada"
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
