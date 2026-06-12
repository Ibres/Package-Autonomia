# Package ROS2 `hydrone_supervisor`

## Visão Geral

O `hydrone_supervisor` é um package ROS2 Humble desenvolvido em Python (rclpy) que atua como um supervisor de missão de alto nível para o veículo híbrido Hydrone. O Hydrone é capaz de operar em ambientes aéreos (drone com Pixhawk PX4) e subaquáticos (ROV com Pixhawk PX4), alternando entre os modos de navegação conforme a missão. Este supervisor é responsável por gerenciar a máquina de estados (FSM), avaliar sensores, selecionar o controlador ativo, gerenciar transições entre meios e executar failsafes, além de publicar os estados do sistema.

**Importante**: Este package NÃO implementa controle PID, controle de atitude, controle de motores ou planejamento de trajetória. Essas responsabilidades são exclusivas dos controladores Pixhawk.

## Arquitetura

A arquitetura do `hydrone_supervisor` segue os princípios SOLID e Single Responsibility Principle (SRP), garantindo modularidade, extensibilidade e facilidade de manutenção. Os componentes principais são:

*   **`supervisor_node.py`**: O nó ROS2 principal que orquestra a interação entre os outros módulos.
*   **`state_machine.py`**: Implementa a Máquina de Estados Finitos (FSM) do Hydrone, gerenciando as transições entre os estados de missão e failsafe.
*   **`sensor_manager.py`**: Gerencia os dados dos sensores, processa-os e determina a confiabilidade de cada sensor no contexto do meio atual.
*   **`controller_manager.py`**: Gerencia a ativação e desativação dos controladores Pixhawk (aéreo e aquático), garantindo que apenas um esteja ativo por vez.
*   **`failsafe_manager.py`**: Monitora o sistema para condições de falha e inicia as ações de failsafe apropriadas.

Para uma descrição detalhada da arquitetura, consulte o arquivo `hydrone_supervisor_architecture.md`.

## Estrutura do Package

```
hydrone_supervisor_ws/src/hydrone_supervisor
├── launch
│   └── supervisor.launch.py
├── config
│   └── supervisor_params.yaml
├── msg
├── srv
├── hydrone_supervisor
│   ├── __init__.py
│   ├── supervisor_node.py
│   ├── state_machine.py
│   ├── sensor_manager.py
│   ├── controller_manager.py
│   └── failsafe_manager.py
├── tests
├── resource
│   └── hydrone_supervisor
├── setup.py
└── package.xml
```

## Tópicos e Serviços ROS2

### Subscrições

*   `/gps/fix` (sensor_msgs/NavSatFix)
*   `/imu/data` (sensor_msgs/Imu)
*   `/depth` (sensor_msgs/Float32) - *Assumido Float32 para profundidade, pode ser custom msg.*
*   `/battery` (sensor_msgs/BatteryState)
*   `/water_contact` (std_msgs/Bool)

### Publicações

*   `/hydrone/state` (std_msgs/String) - Estado atual da FSM (ex: `IDLE`, `AERIAL_NAV`).
*   `/hydrone/controller_mode` (std_msgs/String) - Informações sobre o controlador ativo (ex: `{'px4_air': 'ENABLED', 'px4_water': 'OFF', 'active': 'PX4_AIR'}`).
*   `/hydrone/failsafe` (std_msgs/String) - Razão do failsafe ativo (ex: `FAILSAFE: GPS_LOST - GPS perdido em voo`).

### Serviços

*   `/arm` (std_srvs/Trigger) - Armar o veículo e iniciar a missão aérea.
*   `/disarm` (std_srvs/Trigger) - Desarmar o veículo.
*   `/start_mission` (std_srvs/Trigger) - Iniciar a missão (se em estado `IDLE`).
*   `/abort_mission` (std_srvs/Trigger) - Abortar a missão e iniciar um failsafe de retorno ou superfície.

## Como Construir e Rodar

### Pré-requisitos

*   ROS2 Humble instalado.
*   Python 3.10.

### Construção

1.  Crie um workspace ROS2 (se ainda não tiver um):

    ```bash
    mkdir -p ~/ros2_ws/src
    cd ~/ros2_ws
    ```

2.  Copie o package `hydrone_supervisor` para a pasta `src` do seu workspace:

    ```bash
    cp -r /home/ubuntu/hydrone_supervisor_ws/src/hydrone_supervisor ~/ros2_ws/src/
    ```

3.  Construa o package:

    ```bash
    cd ~/ros2_ws
    colcon build --packages-select hydrone_supervisor
    ```

4.  Faça o `source` do ambiente ROS2:

    ```bash
    source install/setup.bash
    ```

### Rodando o Supervisor

Para iniciar o nó supervisor com os parâmetros padrão:

```bash
ros2 launch hydrone_supervisor supervisor.launch.py
```

Você pode inspecionar os tópicos publicados:

```bash
ros2 topic echo /hydrone/state
ros2 topic echo /hydrone/controller_mode
ros2 topic echo /hydrone/failsafe
```

E chamar os serviços:

```bash
ros2 service call /arm std_srvs/srv/Trigger "{}"
```

## Extensibilidade e Validação

O design modular facilita a extensão do package para incluir novos sensores, estados de missão ou lógicas de failsafe. A validação pode ser realizada em ambientes de simulação como SITL (Software-in-the-Loop) com PX4 e Gazebo, simulando os tópicos de sensores e chamando os serviços para testar as transições de estado e o comportamento dos failsafes antes da integração com hardware real.

## Autor

Manus AI

## Licença

Apache License 2.0
