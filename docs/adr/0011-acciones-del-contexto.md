# ADR 0011: Acciones del contexto para el botón de acción

- **Categoría:** diseño del motor de partida. Aplica el principio **abierto/cerrado** (SOLID) y se
  apoya en el **Observer** del ADR 0006; no introduce un patrón GoF nuevo
- **Estado:** Implementado (US-11, Sprint 3). US-12 (terminales) usaría la misma interfaz
- **Fecha:** 2026-11-08
- **Relacionado:** ADR 0003 (servidor autoritativo), ADR 0006 (Observer), ADR 0005 (Adapter de las
  fuentes de entrada)

## Contexto

El control físico tiene **un solo botón de acción** (contrato de la API de hardware: `BTN ACTION`).
Lo que ese botón hace depende de dónde esté el jugador:

- junto al reactor, extrae energía y suma puntos (US-11, RF-011);
- junto a una terminal, la activa (US-12, historia *Could*);
- en el resto del mapa, no hace nada.

El motor de la partida ya es autoritativo: recibe las entradas, aplica las reglas cada 50 ms y
avisa lo que cambió (ADR 0003 y 0006). El problema era dónde poner la lógica de "qué hace el botón
aquí". Si el motor preguntara `if está_cerca_del_reactor() ... elif está_cerca_de_una_terminal()
...`, cada mecánica nueva obligaría a modificar el motor, que es la clase más delicada del
servidor, y a probarlo entero otra vez.

## Decisión

Definir una interfaz **`AccionContextual`** y una clase por mecánica. El motor recibe la lista de
acciones en el constructor, y al presionar el botón **prueba las acciones en orden y se queda con
la primera que aplica**.

| Rol | Clase en el proyecto | Archivo |
| --- | --- | --- |
| Interfaz | `AccionContextual` (`Protocol`): `clave`, `actualizar(dt)`, `intentar(jugador, tiempo)`, `a_dict()` | `server/app/realtime/acciones.py` |
| Acción concreta | `ExtraccionReactor` (US-11) | `server/app/realtime/reactor.py` |
| Resultado | `ResultadoAccion(accion, puntos)` | `server/app/realtime/acciones.py` |
| Quien las usa | `MotorPartida._accionar()` y `MotorPartida.tick()` | `server/app/realtime/motor_partida.py` |

```python
class AccionContextual(Protocol):
    clave: str

    def actualizar(self, dt: float) -> bool:
        """Avanza el tiempo de la acción. True si cambió algo que ven los jugadores."""

    def intentar(self, jugador: PosicionJugador, tiempo: float) -> ResultadoAccion | None:
        """Aplica la acción si el jugador puede hacerla ahora; si no, devuelve None."""

    def a_dict(self) -> dict:
        """El estado de la acción que se manda a los clientes."""


def _accionar(self, jugador: JugadorEnArena) -> None:
    for accion in self._acciones:
        resultado = accion.intentar(jugador, self.tiempo)
        if resultado is None:
            continue
        self.sumar_puntaje(jugador.jugador_id, resultado.puntos)
        self._eventos_pendientes.append(EventoPartida(ACCION_REALIZADA, ...))
        return
```

**Reglas de la mecánica del reactor** (`ExtraccionReactor`, valores provisionales porque el
stakeholder no dio números):

| Regla | Valor | Por qué |
| --- | --- | --- |
| Reserva del reactor | 100 de energía, **compartida** | Que los jugadores compitan cerca del reactor, como pidió el stakeholder |
| Recarga | 5 por segundo | El reactor vacío se vuelve a llenar solo; nadie queda bloqueado para siempre |
| Extracción | hasta 10 por presión | Si queda menos, saca lo que haya |
| Espera entre extracciones | 0,5 s **por jugador** | Que no gane solo quien aporree el botón más rápido |
| Alcance | radio del reactor + radio del jugador | Basta con tocarlo |

**Qué se decidió además:**

- **El servidor decide, no el cliente.** El cliente solo manda `entrada` con `control: "accion"`;
  cuánta energía se saca, si alcanza y si pasó la espera lo resuelve el servidor (ADR 0003). Un
  cliente modificado no puede sacar más energía de la que las reglas permiten.
- **El tiempo se cuenta en ticks enteros** (`self._ticks * CICLO_S`) y no sumando `dt`, para que no
  se acumule error de redondeo en una partida de 300 segundos.
- **Soltar el botón no hace nada**: el contrato de hardware dice que la acción se dispara al
  presionar (`PRESS`), y `RELEASE` se ignora.
- **La acción avisa por el Observer**, no directamente: emite `accion_realizada` con el jugador, la
  acción y los puntos. De ahí lo toman el notificador por WebSocket y, en el Sprint 3, el
  `EvaluadorLogros` de la US-27, sin que la acción conozca a ninguno de los dos (ADR 0006).
- **El estado viaja en el mensaje `estado`** bajo la clave de cada acción (`estado["reactor"]` con
  energía y capacidad), así el cliente puede dibujar la barra del reactor.

## Alternativas consideradas

| Alternativa | Por qué no |
| --- | --- |
| `if`/`elif` por zona dentro del motor | Cada mecánica nueva obliga a modificar y volver a probar el motor; es justo lo que el principio abierto/cerrado busca evitar |
| **Strategy** | En Strategy el cliente **elige** una estrategia y la usa; aquí el motor no elige nada: prueba todas y gana la que aplique según la posición. Llamarlo Strategy en la defensa sería forzar el nombre. Strategy sí se usa en la US-15 para los guardianes (ADR 0006) |
| **Chain of Responsibility** | Es lo que más se parece a "pasar la petición hasta que alguien la atienda", pero **no se vio en clase**, y además aquí el motor recorre una lista en vez de que cada acción conozca a la siguiente. Se menciona por honestidad, no se reclama como patrón aplicado |
| **Command** | Encapsularía el botón como objeto para deshacer o encolar; nada de eso hace falta y agregaría una capa sin uso |
| Que cada acción sumara el puntaje por su cuenta | El puntaje es del motor; si cada acción lo tocara, la regla quedaría repartida en varios lugares |

## Consecuencias

**Positivas**

- Agregar la US-12 (terminales) es escribir una clase nueva con la misma interfaz y pasarla en la
  lista: **el motor no se toca**.
- Cada mecánica se prueba sola, sin motor, sin red y sin base de datos: alcance, espera, reserva
  compartida y reactor vacío.
- Las reglas de la mecánica quedan en un solo archivo, con los números como parámetros del
  constructor; un escenario (US-09) podría crear el reactor con otros valores sin tocar el código.

**Negativas**

- El orden de la lista importa: si dos acciones aplicaran en el mismo punto, gana la primera. Hoy
  hay una sola, pero conviene que las zonas no se solapen.
- Una acción que tarde mucho en `intentar()` retrasa el tick, igual que un observador lento
  (ADR 0006).
- Es un mecanismo propio, no un patrón de catálogo: hay que explicarlo en la defensa en vez de
  citar un nombre conocido.

## Verificación

- Pruebas automáticas del motor y de la mecánica (`server/tests/`).
- **Probado con el control físico** el 14/11/2026: el botón de acción en **D6** del Arduino dispara
  la extracción contra el backend real.
