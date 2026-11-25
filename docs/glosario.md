# Glosario de términos técnicos

Explicación en español sencillo de los términos en inglés que aparecen en el proyecto.

## Trabajo en equipo

| Término | Qué significa |
|---|---|
| Commit | Guardar un cambio en el repositorio, con un mensaje que dice qué se hizo. |
| Branch (rama) | Copia del proyecto donde se trabaja una historia sin afectar a las demás. |
| Pull Request (PR) | Solicitud para que los cambios de una rama se revisen y se unan a `develop`. |
| Merge | Unir los cambios de una rama con otra. |
| CI | Revisión automática (ruff y pytest) que corre en GitHub cada vez que se sube código. |
| Sprint | Periodo de trabajo con entregas definidas. |
| Backlog | Lista de historias de usuario pendientes. |

## Servidor y juego

| Término | Qué significa |
|---|---|
| Servidor autoritativo | El servidor decide lo que pasa en la partida; el cliente solo muestra. |
| Tick | Un paso del juego. En este proyecto ocurre cada 50 ms. |
| Endpoint | Dirección del servidor a la que se le pide o se le envía información. |
| WebSocket | Conexión que se mantiene abierta para enviar mensajes en tiempo real. |
| Cliente | El programa del jugador (Pygame). |
| HUD | La información que se dibuja sobre la partida: puntos, tiempo, evento. |

## Pruebas

| Término | Qué significa |
|---|---|
| CP (caso de prueba) | Una prueba escrita con entrada y resultado esperado. |
| pytest | Herramienta que ejecuta las pruebas automáticas. |
| ruff | Herramienta que revisa el estilo del código. |

## Patrones de diseño

| Término | Qué significa en el proyecto |
|---|---|
| Factory | Una clase que crea escenarios o eventos sin que el motor conozca los detalles. |
| Strategy | Cada guardián tiene su propia forma de moverse y se puede cambiar. |
| Observer | El motor avisa a quien le interese cuando pasa algo (por ejemplo, un evento). |
| State | El jugador cambia de comportamiento: normal, aturdido o escudado. |