# Logros y retos (US-27): cómo se obtiene cada uno

Guía para probar la US-27 desde afuera (caja negra): qué hay que hacer en el juego para obtener
cada logro y cada reto, y dónde se ve el resultado.

## Diferencia entre logros y retos

| | Logros | Retos |
| --- | --- | --- |
| Cuándo se evalúan | Al **terminar** la partida | **Durante** la partida, en el momento en que se cumplen |
| Qué dan | Un logro guardado para siempre en el perfil | **Puntos extra** en esa partida (cuentan para ganar) |
| Cuántas veces | Una vez por jugador, para siempre | Una vez por jugador en cada partida |
| Dónde se ven | Ceremonia de victoria, historial, `GET /logros`, tabla `logros_jugador` | El puntaje del HUD sube; tabla `eventos` con tipo `reto_completado` |
| Código | `server/app/realtime/logros.py` y `evaluador_logros.py` | `server/app/realtime/retos.py` |

**Regla común:** lo que pasa **antes de iniciar la partida** (cuando los jugadores practican en
la sala de espera) **no cuenta** ni para logros ni para retos.

## Datos del juego que sirven para probarlos

- Cada presión del botón de acción **tocando el reactor** saca hasta **10 de energía**, que se
  suman al puntaje. Cada jugador tiene que esperar **0,5 s** entre extracciones.
- Cada **celda de energía** que se recoge da **5 puntos** (no cuenta como energía del reactor).
- El reactor empieza con **100 de energía**, compartida entre todos, y se recarga **5 por segundo**.
  Por eso, sacar mucha energía toma tiempo: un jugador solo llega a 300 en unos 45 segundos.
- La partida dura **300 segundos** o termina cuando alguien llega a **500 puntos**.
- El jugador aparece en (240, 135) y el reactor está en el centro de la arena (480, 270).

## Logros

| Logro (clave) | Nombre en el juego | Cómo se obtiene |
| --- | --- | --- |
| `primera_partida` | Bautizo nuclear | Estar en una partida cuando termina (por tiempo, por puntaje o porque el administrador la cierra) |
| `primera_victoria` | Primera victoria | Ganar una partida: quedar solo en el primer lugar. Con empate arriba nadie lo gana |
| `energia_300` | Sobrecarga | Sacar **300 de energía del reactor** en una misma partida, después de iniciarla. Solo cuenta la energía del reactor: no cuentan las celdas ni los puntos de los retos |
| `intocable` | Intocable | Terminar la partida **con puntos** sin que te alcance **ningún guardián** desde que empezó. Con 0 puntos no se gana |

Un logro que ya se tiene no se vuelve a dar. La ceremonia de victoria muestra los logros nuevos de
esa partida.

## Retos

| Reto (clave) | Nombre | Puntos | Cómo se cumple |
| --- | --- | --- | --- |
| `primera_chispa` | Primera chispa | +10 | Ser **el primero** de la partida en sacar energía del reactor después de iniciar |
| `racha_nuclear` | Racha nuclear | +25 | Sacar **50 de energía del reactor en 15 segundos** (5 extracciones seguidas tocando el reactor) |
| `sin_rasgunos` | Sin rasguños | +30 | Pasar **60 segundos seguidos** sin que te alcance un guardián. Si un guardián te alcanza, la cuenta empieza de nuevo |

Los puntos de los retos se suman al momento y cuentan para el ganador y para llegar a 500.

## Efecto de los eventos especiales (US-16)

Durante el evento **Puntos dobles** todo lo que se gana vale el doble, y eso incluye los puntos de
los retos y la energía que se saca del reactor. Los **logros** no cambian: `energia_300` cuenta la
energía real que sale del reactor, sin duplicar. La invasión agrega guardianes: si uno te alcanza
se reinicia la cuenta de **Sin rasguños** y se pierde **Intocable**, igual que con cualquier otro
guardián.

## Guion de prueba con dos jugadores

1. Iniciar sesión con dos cuentas (una con el control físico y otra con el teclado) y entrar a la
   misma partida.
2. **Antes de iniciar**, el jugador 1 va al reactor y presiona acción varias veces: el puntaje
   puede subir, pero al iniciar todos vuelven a 0 y esa práctica no cuenta.
3. Iniciar la partida. El jugador 1 va al reactor y presiona acción:
   - En la primera extracción suma **10 + 10** (energía + **Primera chispa**).
   - Si sigue presionando cada medio segundo, a la quinta extracción suma **+25** de
     **Racha nuclear** (en total 50 de energía + 35 de retos = 85).
4. A los 60 segundos de iniciada, a cada jugador que no haya alcanzado un guardián se le suman
   **+30** de **Sin rasguños**.
5. El jugador 1 sigue sacando energía hasta pasar los 300 (unos 45 s pegado al reactor).
6. Al terminar la partida (por tiempo o al llegar a 500), la ceremonia muestra:
   - Jugador 1 (si ganó): **Bautizo nuclear**, **Primera victoria**, **Sobrecarga** e **Intocable**
     (si ningún guardián lo alcanzó).
   - Jugador 2: **Bautizo nuclear** e **Intocable** si terminó con puntos y sin golpes.

Los eventos especiales empiezan a los 30 s: si un reto se cumple justo durante **Puntos dobles**,
los números del paso 3 al 4 salen multiplicados por 2 mientras dure el evento.

## Dónde verlo en la base de datos (demo local)

Con `docker compose up` corriendo:

```sql
-- logros de cada jugador
SELECT jugador_id, logro, partida_id, obtenido_en FROM logros_jugador ORDER BY jugador_id;

-- retos cumplidos en la última partida
SELECT jugador_id, datos->>'nombre' AS reto, datos->>'puntos' AS puntos, timestamp
FROM eventos WHERE tipo = 'reto_completado' ORDER BY id DESC;

-- eventos especiales de la última partida (US-16)
SELECT tipo, datos->>'nombre' AS evento, timestamp
FROM eventos WHERE tipo LIKE 'evento_especial%' ORDER BY id DESC;
```

(Por terminal: `docker compose exec db psql -U reactor -d reactor`.)

`GET /logros` (con la sesión del jugador, en `http://localhost:8000/docs`) devuelve todo el
catálogo con `obtenido` en true o false para ese jugador.

## Pruebas automáticas

- Logros: `server/tests/test_logros.py` (catálogo, evaluación al terminar, sin duplicados, lo de
  antes de iniciar no cuenta, Intocable y una prueba de punta a punta con el motor real).
- Retos: `server/tests/test_retos.py` (cada reto con sus límites, una vez por partida, nada antes
  de iniciar ni después de terminar, una prueba de punta a punta con el motor real, que los puntos
  cuentan para ganar y que quedan en la tabla `eventos`).
- Eventos especiales: `server/tests/test_eventos_especiales.py` (tiempos, puntos dobles, invasión
  y que los efectos se deshacen al terminar).