# Package ROS2 `hydrone_supervisor` (Edição ArduPilot/MAVROS)

## Visão Geral

O `hydrone_supervisor` é um supervisor de missão de alto nível para o veículo híbrido Hydrone, projetado para integrar-se com duas ArduPilot Controllers executando **ArduPilot** via **MAVROS**. O sistema gerencia a transição autônoma entre os meios aéreo e aquático através de uma Máquina de Estados Finitos (FSM) robusta.

## Arquitetura de Comunicação

O supervisor utiliza o protocolo MAVLink através da interface MAVROS. A arquitetura obrigatória é:
`ROS2 Supervisor <-> MAVROS <-> MAVLink <-> ArduPilot (ArduPilot Controller)`

O sistema assume dois namespaces MAVROS:
*   `/aerial/mavros/`: Comunicação com a ArduPilot Controller de voo.
*   `/aquatic/mavros/`: Comunicação com a ArduPilot Controller de navegação subaquática.

## Módulos e Responsabilidades

*   **`supervisor_node.py`**: Orquestrador principal. Executa o loop de supervisão (Ler Sensores -> Verificar Failsafes -> Executar FSM -> Selecionar Controlador -> Publicar Estado).
*   **`sensor_manager.py`**: Gerencia a telemetria MAVROS, avalia a confiabilidade dos sensores (GPS, IMU, Profundidade, Bateria) e monitora timeouts de comunicação (Heartbeats).
*   **`failsafe_manager.py`**: Implementa a lógica de segurança detalhada, disparando transições de emergência em caso de falhas críticas, perda de sensores ou bateria baixa.
*   **`state_machine.py`**: Gerencia os estados operacionais (`IDLE`, `AERIAL_NAV`, `TRANSITION_DOWN`, `AQUATIC_NAV`, etc.) e as transições formais.
*   **`controller_manager.py`**: Seleciona qual controlador ArduPilot está ativo, garantindo que apenas um sistema atue sobre os motores por vez.

## Tópicos e Serviços

### Subscrições Principais
*   `/aerial/mavros/global_position/global` (NavSatFix)
*   `/aerial/mavros/imu/data` (Imu)
*   `/aerial/mavros/battery` (BatteryState)
*   `/depth` (Float32)
*   `/water_contact` (Bool)

### Publicações
*   `/hydrone/state` (String): Estado atual da FSM.
*   `/hydrone/controller_mode` (String): Status dos controladores (ENABLED/STANDBY/OFF).
*   `/hydrone/failsafe` (String): Alertas de segurança ativos.

### Serviços
*   `/arm`: Prepara o sistema para missão.
*   `/start_mission`: Inicia a progressão autônoma.
*   `/abort_mission`: Interrompe a missão e inicia protocolos de segurança.

## Como Construir

```bash
# No seu workspace ROS2
colcon build --packages-select hydrone_supervisor
source install/setup.bash
```

## Como Executar

```bash
ros2 launch hydrone_supervisor supervisor.launch.py
```

## Autor
Manus AI - Especialista em Sistemas Embarcados e Autônomos.
