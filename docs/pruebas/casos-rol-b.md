# Casos de prueba — Rol B (US-07, US-08, US-21, US-25, US-09, US-13, US-14, US-15 y US-16)

Cada caso está automatizado con pytest, salvo los de tipo **A**, que se ejecutan a mano con el juego; la
columna **Prueba** dice dónde. Los del servidor corren contra PostgreSQL en el CI y los del cliente con
pygame sin ventana y el servidor simulado.

**Tipos:** **U** unitaria (una pieza sola, sin base de datos ni red), **I** integración (varias piezas
juntas, con la base de datos real o con un servidor real) y **A** aceptación (el juego completo, a mano).

**Resultado obtenido:** todas las pruebas automáticas pasan: 186 del servidor y 166 del cliente, en
Python 3.12 y 3.14 (en el CI el servidor corre contra PostgreSQL 16). Para repetirlas: `pytest` dentro de
`server/` y de `client/`. Los casos de tipo **A** se ejecutaron a mano; su evidencia está en la columna **Prueba** o en la Wiki.

Archivos: `s/` = `server/tests/`, `c/` = `client/tests/`. La numeración sigue a la del Rol A (CP-01 a CP-46); los casos de la pantalla de la arena se agregaron al final del sprint como CP-160 a CP-164.

**Sprint 3:** el rol B agrega los escenarios (US-09), las celdas (US-13), los obstáculos (US-14),
los guardianes (US-15, CP-245 a CP-264) y los eventos especiales (US-16). Su rango del Sprint 3 es
CP-215 a CP-264. Como los guardianes ya ocupan CP-245 a CP-264, escenarios, celdas y obstáculos usan
CP-215 a CP-244, y los eventos especiales y la arena visual siguen desde CP-346 (el rol C llegó a
CP-345). Los casos de tipo **A** del Sprint 3 se ejecutaron a mano en la demo interna del 25/11 (ver
[Cómo ejecutar los casos de aceptación](#cómo-ejecutar-los-casos-de-aceptación)).

## Resumen

| Historia | Casos | OK | Pendiente |
| --- | --- | --- | --- |
| US-07 Creación de partida | 12 | 12 | — |
| US-08 Unirse a una partida | 27 | 27 | — |
| US-21 Guardado persistente de datos | 10 | 10 | — |
| US-25 Movimiento por el mapa | 35 | 35 | — |
| US-15 Guardianes y estados del jugador (CP-245 a CP-264) | 20 | 20 | — |
| US-09 Escenarios (CP-215 a CP-223) | 9 | 9 | — |
| US-13 Celdas de energía (CP-224 a CP-232) | 9 | 9 | — |
| US-14 Obstáculos (CP-233 a CP-244) | 12 | 12 | — |
| US-16 Eventos especiales (CP-346 a CP-359) | 14 | 14 | — |
| Arena visual (CP-360 y CP-361) | 2 | 2 | — |
| **Total** | **150** | **150** | **0** |


## US-07 Creación de partida

**Criterios de aceptación (Board):** el jugador puede iniciar una nueva partida; la partida creada queda disponible para que otros jugadores se unan; el sistema asigna un identificador único a la partida.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-47 | Crear una partida | Jugador 1 existe y no está en otra partida | `POST /partidas` con `{"creador_id": 1}` | 201; la partida queda en estado `esperando` con escenario, tiempo límite y puntuación objetivo | OK | I | `s/test_partidas.py::test_post_partidas_crea_la_partida` |
| CP-48 | La partida recibe un identificador | — | Crear una partida | Tiene `id`, asignado por la clave primaria de la base de datos | OK | I | `s/test_repositories.py::test_partida_nueva_queda_en_esperando` |
| CP-49 | Elegir el escenario | — | `escenario: "laboratorio"` | 201 con ese escenario | OK | I | `s/test_partidas.py::test_post_partidas_con_escenario_indicado` |
| CP-50 | Escenario sin indicar | — | Sin `escenario` | Se sortea uno del catálogo | OK | U | `s/test_partidas.py::test_factory_elige_un_escenario_del_catalogo_si_no_se_indica` |
| CP-51 | Escenario inválido | — | `escenario: "marte"` | 422 | OK | I | `s/test_partidas.py::test_post_partidas_escenario_invalido_da_422`, `s/test_partidas.py::test_factory_rechaza_un_escenario_invalido` |
| CP-52 | Jugador inexistente | — | `creador_id: 999` | 404 | OK | I | `s/test_partidas.py::test_post_partidas_jugador_inexistente_da_404` |
| CP-53 | Un jugador no puede estar en dos partidas (RN-04) | Jugador con una partida activa | Crear otra partida | 409 "ya está en una partida activa" | OK | I | `s/test_partidas.py::test_post_partidas_jugador_en_partida_activa_da_409`, `s/test_partidas.py::test_servicio_rechaza_a_un_jugador_en_partida_activa_rn04` |
| CP-54 | Crear otra al terminar la anterior | Su partida anterior está `finalizada` | Crear una partida | Se crea una partida nueva | OK | I | `s/test_partidas.py::test_servicio_permite_crear_otra_si_la_anterior_finalizo` |
| CP-55 | El creador entra como primer participante | — | Crear una partida | El creador queda como participante de la partida | OK | I | `s/test_partidas.py::test_servicio_crea_la_partida_y_agrega_al_creador` |
| CP-56 | La Factory arma la partida | — | `PartidaFactory().crear()`, con y sin escenario | Estado `esperando`, tiempo y puntuación objetivo mayores que 0, escenario pedido o del catálogo | OK | U | `s/test_partidas.py::test_factory_crea_partida_en_esperando`, `s/test_partidas.py::test_factory_usa_el_escenario_indicado` |
| CP-57 | Lobby: crear partida | Sesión iniciada | Clic en "Crear partida" | Muestra "Partida #N creada" y abre el canal; si falla, muestra el error y no abre el canal; dos clics seguidos crean una sola | OK | U | `c/test_pantallas_partidas.py::test_lobby_crear_partida_muestra_el_resultado_y_abre_el_canal`, `c/test_pantallas_partidas.py::test_lobby_con_error_no_abre_el_canal`, `c/test_pantallas_partidas.py::test_lobby_no_duplica_la_peticion_con_dos_clics_seguidos` |
| CP-58 | Crear una partida desde el juego | Servidor corriendo; jugador con sesión | Clic en "Crear partida" | Mensaje verde "Partida #N creada - escenario: …" y "Canal: conectado - jugadores en línea: [id]" | OK | A | Manual (captura en la Wiki) |

## US-08 Unirse a una partida

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-59 | Listar sin partidas | No hay partidas en espera | `GET /partidas` | 200 y lista vacía | OK | I | `s/test_unirse_partidas.py::test_get_partidas_sin_partidas_devuelve_lista_vacia` |
| CP-60 | Listar con el número de jugadores | Dos partidas en espera, una con 2 jugadores | `GET /partidas` | Cada partida con `id`, `escenario`, `jugadores`, `tiempo_limite_segundos` y `puntuacion_objetivo` | OK | I | `s/test_unirse_partidas.py::test_get_partidas_lista_las_que_esperan_con_su_conteo`, `s/test_unirse_partidas.py::test_listar_disponibles_cuenta_los_jugadores_de_cada_partida` |
| CP-61 | Solo las que esperan jugadores | Una partida `en_curso` | `GET /partidas` | No aparece la que ya empezó | OK | I | `s/test_unirse_partidas.py::test_listar_disponibles_no_incluye_las_que_ya_empezaron` |
| CP-62 | Unirse a una partida | Partida en espera con 1 jugador | `POST /partidas/1/unirse` con `{"jugador_id": 2}` | 200 con la partida y `jugadores: 2` | OK | I | `s/test_unirse_partidas.py::test_unirse_devuelve_la_partida_con_el_conteo_actualizado`, `s/test_unirse_partidas.py::test_unirse_agrega_al_jugador_y_devuelve_cuantos_hay` |
| CP-63 | Partida inexistente | — | `POST /partidas/999/unirse` | 404 "La partida 999 no existe" | OK | I | `s/test_unirse_partidas.py::test_unirse_a_partida_inexistente_da_404`, `s/test_unirse_partidas.py::test_unirse_a_una_partida_inexistente` |
| CP-64 | Jugador inexistente | Partida en espera | `jugador_id: 999` | 404 "Jugador no encontrado" | OK | I | `s/test_unirse_partidas.py::test_unirse_con_un_jugador_inexistente_da_404` |
| CP-65 | Partida llena | Partida con el máximo de jugadores (4) | Otro jugador intenta unirse | 409 "La partida … está llena"; no se agrega | OK | I | `s/test_unirse_partidas.py::test_unirse_a_una_partida_llena_da_409`, `s/test_unirse_partidas.py::test_unirse_rechaza_cuando_la_partida_esta_llena` |
| CP-66 | Un jugador no puede estar en dos partidas (RN-04) | Jugador con una partida activa | Unirse a otra partida | 409 "ya está en una partida activa" | OK | I | `s/test_unirse_partidas.py::test_unirse_estando_en_otra_partida_da_409_rn04`, `s/test_unirse_partidas.py::test_unirse_rechaza_a_quien_ya_esta_en_otra_partida_rn04` |
| CP-67 | No unirse dos veces a la misma | Jugador ya dentro de la partida | Unirse otra vez | Se rechaza | OK | I | `s/test_unirse_partidas.py::test_unirse_a_la_misma_partida_dos_veces_tambien_se_rechaza` |
| CP-68 | Partida que ya empezó | Partida `en_curso` | Unirse | 409 "ya no acepta jugadores" | OK | I | `s/test_unirse_partidas.py::test_unirse_a_una_partida_en_curso_da_409`, `s/test_unirse_partidas.py::test_unirse_a_una_partida_que_ya_empezo` |
| CP-69 | Falta el jugador | — | Cuerpo `{}` | 422 | OK | I | `s/test_unirse_partidas.py::test_unirse_sin_indicar_el_jugador_da_422` |
| CP-70 | Saber quién está dentro | — | Consultar si un jugador participa | Verdadero solo para los participantes | OK | I | `s/test_unirse_partidas.py::test_es_participante_distingue_a_quien_esta_dentro` |
| CP-71 | Canal: avisar la entrada | Jugador dentro de la partida | Conectar a `/ws/partidas/{id}` | Recibe `jugador_conectado` con `conectados: [id]` | OK | I | `s/test_unirse_partidas.py::test_canal_avisa_al_jugador_que_entra` |
| CP-72 | Canal: avisar a los demás | Dos jugadores dentro | Uno entra y luego sale | El otro recibe `jugador_conectado` y `jugador_desconectado` con la lista al día | OK | I | `s/test_unirse_partidas.py::test_canal_avisa_a_los_demas_cuando_alguien_entra_y_sale` |
| CP-73 | Canal: rechazar a quien no pertenece | Jugador que no se unió; partida o jugador inexistente | Conectar al canal | Se cierra con código 1008 y no queda conectado | OK | I | `s/test_unirse_partidas.py::test_canal_rechaza_a_quien_no_esta_en_la_partida`, `s/test_unirse_partidas.py::test_canal_rechaza_una_partida_inexistente`, `s/test_unirse_partidas.py::test_canal_rechaza_un_jugador_inexistente` |
| CP-74 | Canal: reconexión | Jugador ya conectado | Se conecta otra vez | La conexión anterior se cierra (1000) y la nueva queda | OK | I | `s/test_unirse_partidas.py::test_canal_reconexion_cierra_la_conexion_anterior` |
| CP-75 | Canal: no dejar conexiones abiertas | Dos jugadores conectados | Ambos se desconectan | La lista de conectados queda vacía | OK | I | `s/test_unirse_partidas.py::test_canal_no_deja_conexiones_abiertas_al_terminar` |
| CP-76 | Pantalla de buscar: mostrar la lista | Partidas en espera | Abrir la pantalla | Una fila por partida con su botón "Unirse"; con más de 6, avisa cuántas faltan; sin partidas, un aviso | OK | U | `c/test_pantallas_partidas.py::test_al_mostrarse_carga_las_partidas_y_crea_un_boton_por_fila`, `c/test_pantallas_partidas.py::test_sin_partidas_muestra_un_aviso`, `c/test_pantallas_partidas.py::test_solo_muestra_las_primeras_filas_y_avisa_del_resto`, `c/test_pantallas_partidas.py::test_actualizar_vuelve_a_pedir_la_lista` |
| CP-77 | Pantalla de buscar: unirse | Partida en espera | Clic en "Unirse" | Envía la partida y el jugador, y abre el canal; si falla, muestra el mensaje del servidor y no abre el canal | OK | U | `c/test_pantallas_partidas.py::test_unirse_envia_la_partida_y_el_jugador_y_abre_el_canal`, `c/test_pantallas_partidas.py::test_unirse_con_error_muestra_el_mensaje_y_no_abre_el_canal` |
| CP-78 | Pantalla de buscar: no duplicar | Una petición en curso | Segundo clic | No se repite la petición; una vez unido, los botones ya no hacen nada | OK | U | `c/test_pantallas_partidas.py::test_un_segundo_clic_mientras_espera_no_duplica_la_peticion`, `c/test_pantallas_partidas.py::test_despues_de_unirse_los_botones_de_unirse_ya_no_hacen_nada` |
| CP-79 | Error de red al listar | Servidor sin conexión | Abrir la pantalla | Mensaje en rojo, sin lista | OK | U | `c/test_pantallas_partidas.py::test_error_al_cargar_muestra_el_mensaje_en_rojo` |
| CP-80 | Llamadas del cliente al servidor | — | Listar y unirse | `GET /partidas` y `POST /partidas/{id}/unirse` con el jugador; el detalle del error del servidor llega al mensaje; sin conexión da un error claro | OK | U | `c/test_api_client.py::test_listar_partidas_disponibles`, `c/test_api_client.py::test_unirse_a_partida_envia_el_jugador`, `c/test_api_client.py::test_unirse_a_partida_llena_muestra_el_detalle_del_servidor`, `c/test_api_client.py::test_unirse_a_partida_sin_conexion` |
| CP-81 | Panel del canal | Canal abierto | Mensajes `jugador_conectado` / `desconectado` | Muestra los jugadores en línea y el estado de la conexión; abrir un canal nuevo cierra el anterior | OK | U | `c/test_pantallas_partidas.py::test_el_panel_actualiza_los_conectados_con_los_mensajes`, `c/test_pantallas_partidas.py::test_abrir_un_canal_nuevo_cierra_el_anterior`, `c/test_pantallas_partidas.py::test_el_panel_traduce_el_estado_del_canal` |
| CP-82 | WebSocket de escritorio contra un servidor real | Servidor WebSocket local | Conectar, enviar y cerrar | Recibe y envía mensajes; un mensaje que no es JSON se ignora; al cerrar, el servidor lo ve; no congela el ciclo del juego | OK | I | `c/test_red_websocket.py::test_recibe_los_mensajes_del_servidor`, `c/test_red_websocket.py::test_envia_al_servidor_y_recibe_la_respuesta`, `c/test_red_websocket.py::test_un_mensaje_que_no_es_json_se_ignora_y_la_conexion_sigue`, `c/test_red_websocket.py::test_cerrar_cierra_la_conexion_del_lado_del_servidor`, `c/test_red_websocket.py::test_no_congela_el_ciclo_mientras_espera` |
| CP-83 | Servidor caído | Sin servidor | Conectar al canal | Estado de error sin lanzar excepciones | OK | I | `c/test_red_websocket.py::test_servidor_caido_deja_el_estado_en_error` |
| CP-84 | Compatibilidad con el navegador (ADR 0002) | — | Cargar las pantallas y el canal | No importa `requests` ni `websockets` al cargar; el WebSocket del navegador arma su JavaScript correctamente | OK | U | `c/test_canal_partida.py::test_cargar_las_pantallas_no_importa_librerias_de_escritorio`, `c/test_red_websocket.py::test_navegador_abre_el_websocket_nativo`, `c/test_red_websocket.py::test_navegador_lee_el_estado_y_los_mensajes`, `c/test_red_websocket.py::test_navegador_envia_el_mensaje_como_literal_de_javascript`, `c/test_red_websocket.py::test_navegador_cerrar_cierra_el_websocket` |
| CP-85 | Unirse desde el juego con dos ventanas | Servidor corriendo; jugador 1 creó una partida; jugador 2 con sesión | Jugador 2: "Buscar partidas" y "Unirse" | Ambas ventanas muestran "Canal: conectado - jugadores en línea: [1, 2]" | OK | A | Manual (captura en la Wiki) |

## US-21 Guardado persistente de datos

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-86 | Las migraciones crean el esquema | Base de datos vacía | `alembic upgrade head` | Se crean `usuarios`, `partidas`, `participaciones`, `eventos`, `ranking_global` y `tokens_usuario` | OK | I | CI: paso `alembic upgrade head` del job del servidor |
| CP-87 | Guardar y buscar un usuario | — | Crear un usuario y buscarlo por correo | Se guarda con su `id` y se recupera | OK | I | `s/test_repositories.py::test_crear_y_buscar_usuario_por_correo` |
| CP-88 | Correo y usuario únicos | Usuario ya guardado | Preguntar si existen el correo y el nombre | Verdadero para los guardados, falso para otros | OK | I | `s/test_repositories.py::test_existe_correo_y_nombre_usuario` |
| CP-89 | Buscar algo que no existe | — | Buscar el `id` 999 o un correo desconocido | Devuelve `None`, sin error | OK | I | `s/test_repositories.py::test_usuario_inexistente_devuelve_none` |
| CP-90 | Guardar una partida | — | Crear una partida | Se guarda en estado `esperando` | OK | I | `s/test_repositories.py::test_partida_nueva_queda_en_esperando` |
| CP-91 | Listar las partidas en espera | Una `esperando` y una `en_curso` | Listar disponibles | Solo aparece la que espera | OK | I | `s/test_repositories.py::test_listar_disponibles_solo_incluye_esperando` |
| CP-92 | Guardar participantes | Una partida y dos jugadores | Agregar a ambos | Se cuentan y se listan 2 participaciones | OK | I | `s/test_repositories.py::test_agregar_participante_y_contar` |
| CP-93 | Registrar las fechas de inicio y fin | Partida nueva | Pasar a `en_curso` y luego a `finalizada` | Se guardan `fecha_inicio` y `fecha_fin` | OK | I | `s/test_repositories.py::test_cambiar_estado_registra_fechas` |
| CP-94 | Consultar la RN-04 en la base | Jugador en una partida activa | Preguntar si está en una partida activa | Verdadero mientras la partida esté `esperando` o `en_curso`; falso al `finalizar` | OK | I | `s/test_repositories.py::test_jugador_en_partida_activa_rn04` |
| CP-95 | Los datos sobreviven al reinicio del servidor | Partidas y jugadores guardados, Docker corriendo | `docker compose restart server`, y luego `docker compose down` + `docker compose up -d` | Los mismos datos siguen disponibles | OK | A | Manual, 23/10/2026: la partida 1 sigue en `GET /partidas` después de los dos reinicios ([antes](evidencias/cp-95-partida-creada.png), [comandos](evidencias/cp-95-restart-down-up.png), [después](evidencias/cp-95-partida-despues-de-down-up.png)) |

## US-25 Movimiento por el mapa

**Criterios de aceptación (Board):** los controles permiten moverse en 8 direcciones según la tecla que se presione; el jugador se mueve mientras nada lo obstruya (obstáculos o el límite del mapa); el movimiento se ve en pantalla en menos de 500 ms desde que se presiona la tecla y se detiene al soltarla.

**Alcance en este sprint:** solo hay colisión con los límites del mapa; los obstáculos todavía no están implementados.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-96 | Moverse en una dirección | Jugador en la arena | `derecha` presionada 1 s (20 ciclos de 50 ms) | Avanza 120 px a la derecha | OK | U | `s/test_motor_partida.py::test_una_direccion_presionada_mueve_al_jugador_a_la_velocidad_del_motor` |
| CP-97 | Las 4 direcciones | Jugador en la arena | Arriba, abajo, izquierda o derecha durante 0,5 s | Avanza 60 px hacia ese lado | OK | U | `s/test_motor_partida.py::test_cada_direccion_mueve_hacia_su_lado` |
| CP-98 | Las 8 direcciones: diagonales | Jugador en la arena | Dos direcciones a la vez (derecha y abajo) | Avanza en diagonal; 120 px en total, no más rápido que en recta | OK | U | `s/test_motor_partida.py::test_en_diagonal_avanza_la_misma_distancia_que_en_recta` |
| CP-99 | Direcciones opuestas | Jugador en la arena | Izquierda y derecha a la vez | No se mueve | OK | U | `s/test_motor_partida.py::test_direcciones_opuestas_se_cancelan` |
| CP-100 | Se detiene al soltar | Jugador moviéndose | Liberar la dirección | Se queda donde está | OK | U | `s/test_motor_partida.py::test_soltar_el_control_detiene_al_jugador` |
| CP-101 | Límite del mapa | Jugador en la arena | Mantener una dirección contra cada pared | Se detiene a 20 px del borde (el radio del jugador) y no lo atraviesa | OK | U | `s/test_motor_partida.py::test_el_jugador_no_atraviesa_los_limites_de_la_arena` |
| CP-102 | Deslizarse por la pared | Jugador pegado a la pared izquierda | Izquierda y abajo | Sigue bajando sin salir de la arena | OK | U | `s/test_motor_partida.py::test_contra_la_pared_se_desliza_por_el_otro_eje` |
| CP-103 | Punto de inicio | — | Entran dos jugadores | Cada uno aparece en su punto de inicio | OK | U | `s/test_motor_partida.py::test_los_jugadores_nuevos_aparecen_en_sus_puntos_de_inicio` |
| CP-104 | La acción no mueve | Jugador en la arena | `accion` presionada | No se mueve (la acción es del Sprint 3) | OK | U | `s/test_motor_partida.py::test_la_accion_no_mueve_al_jugador_en_este_sprint`, `s/test_motor_partida.py::test_las_entradas_de_un_jugador_que_no_esta_se_ignoran` |
| CP-105 | Reconexión | Jugador moviéndose | Se vuelve a conectar | Conserva su posición y el servidor le suelta todos los controles | OK | U e I | `s/test_motor_partida.py::test_quien_vuelve_a_entrar_conserva_su_posicion_y_suelta_los_controles`, `s/test_movimiento_ws.py::test_al_reconectar_el_servidor_suelta_los_controles_del_jugador` |
| CP-106 | El motor avisa los cambios (Observer) | Motor con un observador suscrito | Ciclos con y sin cambios | Un evento `estado_actualizado` con las posiciones cuando algo cambia; nada si no cambia; un observador que falla no detiene a los demás; al desuscribirlo deja de recibir | OK | U | `s/test_motor_partida.py::test_avisa_el_estado_cuando_algo_cambia`, `s/test_motor_partida.py::test_no_avisa_si_nada_cambio`, `s/test_motor_partida.py::test_un_observador_que_falla_no_detiene_a_los_demas`, `s/test_motor_partida.py::test_desuscribir_deja_de_avisar`, `s/test_motor_partida.py::test_en_la_pared_deja_de_avisar` |
| CP-107 | Ciclo del motor | — | Iniciar, esperar y detener | Ejecuta ciclos solo mientras está iniciado; iniciar dos veces no duplica el ciclo | OK | U | `s/test_motor_partida.py::test_el_ciclo_ejecuta_ticks_solo_hasta_que_se_detiene` |
| CP-108 | Validar la entrada (contrato) | — | `control: "saltar"`, un estado desconocido o un `seq` que no es entero | Error con el detalle del contrato, por ejemplo `control desconocido: saltar` | OK | U | `s/test_entradas.py::test_un_control_desconocido_da_el_detalle_del_contrato`, `s/test_entradas.py::test_un_estado_desconocido_es_invalido`, `s/test_entradas.py::test_un_seq_que_no_es_entero_es_invalido`, `s/test_entradas.py::test_interpreta_una_entrada_valida` |
| CP-109 | Descartar entradas repetidas o atrasadas | Entrada con `seq` 5 ya recibida | `seq` 5 y `seq` 3 | Se descartan; `seq` 6 sí se admite | OK | U | `s/test_entradas.py::test_descarta_las_repetidas_y_las_atrasadas` |
| CP-110 | Límite de 30 entradas por segundo | — | 35 entradas en un segundo | Se admiten 30 y se descartan 5; pasado un segundo vuelve a admitir | OK | U | `s/test_entradas.py::test_descarta_lo_que_pasa_de_30_entradas_por_segundo`, `s/test_entradas.py::test_pasado_un_segundo_vuelve_a_admitir`, `s/test_entradas.py::test_una_entrada_descartada_por_el_limite_no_gasta_su_numero_de_secuencia` |
| CP-111 | Posición inicial por el canal | Jugador dentro de la partida | Conectarse al canal | Recibe `estado` con su posición inicial y el tamaño de la arena | OK | I | `s/test_movimiento_ws.py::test_el_jugador_recibe_su_posicion_inicial_al_entrar` |
| CP-112 | Moverse por el canal | Jugador conectado | Mensaje `entrada` con `derecha` y `presionado` | Recibe `estado` con la `x` mayor | OK | I | `s/test_movimiento_ws.py::test_presionar_una_direccion_mueve_al_jugador_y_avisa` |
| CP-113 | Soltar por el canal | Jugador moviéndose | Mensaje `entrada` con `liberado` | El jugador deja de moverse | OK | I | `s/test_movimiento_ws.py::test_soltar_el_control_detiene_al_jugador` |
| CP-114 | Todos ven el movimiento | Dos jugadores conectados | Uno se mueve | El otro recibe su nueva posición | OK | I | `s/test_movimiento_ws.py::test_todos_los_jugadores_ven_el_movimiento_de_los_demas` |
| CP-115 | Menos de 500 ms (RNF-02) | Jugador conectado | Tecla presionada hasta recibir la posición nueva | Pasan menos de 500 ms | OK | I | `s/test_movimiento_ws.py::test_la_posicion_llega_a_los_clientes_en_menos_de_500_ms` |
| CP-116 | Quien se va desaparece | Dos jugadores conectados | Uno se desconecta | El otro recibe el estado sin él | OK | I | `s/test_movimiento_ws.py::test_quien_se_va_desaparece_del_estado_de_los_demas` |
| CP-117 | Entrada inválida por el canal | Jugador conectado | `control: "saltar"` o un texto que no es JSON | Responde `error` con `entrada_invalida` o `json_invalido` | OK | I | `s/test_movimiento_ws.py::test_una_entrada_invalida_recibe_el_error_del_contrato`, `s/test_movimiento_ws.py::test_un_mensaje_que_no_es_json_recibe_error` |
| CP-118 | Mensajes de otro tipo | Jugador conectado | `tipo: "dispositivo"` | Se ignora y el canal sigue funcionando | OK | I | `s/test_movimiento_ws.py::test_los_mensajes_de_otro_tipo_se_ignoran_sin_romper_el_canal` |
| CP-119 | Entrada atrasada por el canal | Jugador moviéndose con `seq` 5 | `liberado` con `seq` 3 | Se descarta y el jugador sigue moviéndose | OK | I | `s/test_movimiento_ws.py::test_una_entrada_atrasada_se_descarta_y_el_jugador_sigue_moviendose` |
| CP-120 | El motor se libera | Dos jugadores conectados | Se van los dos | El motor de la partida se detiene | OK | I | `s/test_movimiento_ws.py::test_el_motor_se_detiene_cuando_se_van_todos_los_jugadores` |
| CP-121 | Teclado en el cliente | — | Flechas, WASD y espacio | Se mapean a los 5 controles; con dos teclas del mismo control no se suelta hasta soltar ambas; al perder el foco se suelta todo | OK | U | `c/test_entradas_jugador.py::test_teclado_mapea_flechas_wasd_y_espacio`, `c/test_entradas_jugador.py::test_teclado_dos_teclas_del_mismo_control_sueltan_al_final`, `c/test_entradas_jugador.py::test_teclado_suelta_todo_al_perder_el_foco`, `c/test_entradas_jugador.py::test_teclado_no_repite_presionado_con_repeticion_de_teclas` |
| CP-122 | Mensaje de entrada del cliente | — | Cambios de cualquier fuente | Se envía el mensaje `entrada` del contrato con `seq` creciente | OK | U | `c/test_entradas_jugador.py::test_controles_envian_el_mensaje_del_contrato_con_seq_creciente` |
| CP-123 | Fuente indistinta | — | Misma pulsación por teclado y por el control físico | El servidor recibe el mismo mensaje; solo cambia `origen` | OK | U | `c/test_entradas_jugador.py::test_mismo_mensaje_desde_teclado_y_desde_el_control_fisico` |
| CP-124 | Botones táctiles | — | Tocar con el mouse o con dos dedos | Presiona y suelta cada botón; dos dedos a la vez no se confunden | OK | U | `c/test_entradas_jugador.py::test_tactil_presiona_y_suelta_con_el_mouse`, `c/test_entradas_jugador.py::test_tactil_dos_dedos_a_la_vez` |
| CP-125 | Ver el movimiento en pantalla | Dos ventanas con la pantalla de la arena | W, A, S y D en una ventana | El personaje se mueve y se ve en la otra ventana en menos de 500 ms; se detiene al soltar la tecla | OK | A | Manual: la ventana del jugador 1 mueve su círculo rojo con WASD y la del jugador 2 lo ve moverse; al soltar la tecla se detiene ([captura](evidencias/cp-125-dos-ventanas.png)) |
| CP-160 | La arena dibuja a los jugadores | Panel del canal con el estado de la partida | Estado con dos jugadores | Fondo blanco y un círculo rojo por jugador, en su posición y con el radio que manda el servidor; sin estado o sin canal, solo el fondo y sin errores | OK | U | `c/test_arena.py::test_el_fondo_es_blanco`, `c/test_arena.py::test_dibuja_un_circulo_rojo_por_jugador_en_su_posicion`, `c/test_arena.py::test_el_circulo_tiene_el_radio_que_manda_el_servidor`, `c/test_arena.py::test_sin_estado_solo_hay_fondo_blanco_y_no_falla`, `c/test_arena.py::test_sin_canal_no_falla_ni_manda_teclas` |
| CP-161 | Movimiento suave en pantalla | Un jugador dibujado | El servidor manda una posición nueva | El círculo se acerca poco a poco y no salta; quien se va deja de dibujarse | OK | U | `c/test_arena.py::test_la_primera_vez_aparece_en_su_lugar_y_despues_se_acerca_sin_saltar`, `c/test_arena.py::test_quien_se_va_deja_de_dibujarse` |
| CP-162 | Teclas desde la arena | Arena abierta con el canal | Presionar y soltar D | Se envían `entrada` `derecha` con `presionado` y luego `liberado`, con `origen` `teclado` y `seq` creciente | OK | U | `c/test_arena.py::test_las_teclas_se_envian_por_el_canal` |
| CP-163 | Volver de la arena con Esc | Arena abierta, con una tecla apretada | Esc | Vuelve a la pantalla de origen; se sueltan los 5 controles para que el servidor no siga moviendo al jugador; después no se envía nada más; se puede entrar de nuevo limpio; sin canal también funciona | OK | U | `c/test_arena.py::test_escape_vuelve_a_la_pantalla_de_origen`, `c/test_arena.py::test_al_salir_se_sueltan_todos_los_controles_aunque_haya_una_tecla_apretada`, `c/test_arena.py::test_despues_de_salir_no_se_envia_nada_mas`, `c/test_arena.py::test_volver_a_preparar_empieza_limpio`, `c/test_arena.py::test_sin_canal_escape_tambien_funciona` |
| CP-164 | Botón "Entrar a la arena" y estado en el panel | Canal abierto | Llegan mensajes `estado`; clic en el botón | El panel guarda el último estado y lo olvida al cerrar; el botón pide entrar a la arena solo si hay canal; el panel puede dibujarse sin el botón | OK | U | `c/test_arena.py::test_el_panel_guarda_el_ultimo_estado_de_la_arena`, `c/test_arena.py::test_el_panel_olvida_el_estado_al_abrir_otro_canal_o_cerrar`, `c/test_arena.py::test_el_boton_de_la_arena_pide_entrar`, `c/test_arena.py::test_sin_canal_el_boton_de_la_arena_no_hace_nada`, `c/test_arena.py::test_el_panel_puede_dibujarse_sin_el_boton` |

## US-15 Guardianes y estados del jugador

**Criterios de aceptación (ERS):** los guardianes se mueven solos por el mapa (patrullan una ruta o
persiguen al jugador que se acerca); al alcanzar a un jugador lo aturden y le restan puntos; el
jugador queda protegido unos segundos antes de poder ser golpeado otra vez (CU-11).

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-245 | Jugador normal | — | Estado `Normal` | Se mueve y es vulnerable a los guardianes | OK | U | `s/test_estados_jugador.py::test_normal_se_mueve_y_es_vulnerable` |
| CP-246 | Un golpe aturde al jugador normal | Jugador `Normal` | Golpe de un guardián | Pasa a `Aturdido`; `Normal` no cambia solo con el tiempo | OK | U | `s/test_estados_jugador.py::test_un_golpe_aturde_al_jugador_normal`, `s/test_estados_jugador.py::test_normal_no_cambia_con_el_tiempo` |
| CP-247 | Aturdido no se mueve ni se golpea otra vez | Jugador `Aturdido` | Otro golpe | No se mueve, no es vulnerable y sigue igual | OK | U | `s/test_estados_jugador.py::test_aturdido_no_se_mueve_y_no_se_golpea_otra_vez` |
| CP-248 | Aturdido dura 3 s y pasa a Escudado | Jugador `Aturdido` | Pasan 3 s | Antes de los 3 s sigue aturdido; al cumplirse pasa a `Escudado` | OK | U | `s/test_estados_jugador.py::test_aturdido_sigue_igual_antes_de_terminar_su_tiempo`, `s/test_estados_jugador.py::test_aturdido_pasa_a_escudado_al_terminar_su_tiempo` |
| CP-249 | Escudado se mueve pero no es vulnerable (CU-11, E1) | Jugador `Escudado` | Golpe de un guardián | Se mueve y el golpe no lo cambia | OK | U | `s/test_estados_jugador.py::test_escudado_se_mueve_pero_no_es_vulnerable` |
| CP-250 | Escudado vuelve a Normal a los 2 s | Jugador `Escudado` | Pasan 2 s | Antes de los 2 s sigue escudado; al cumplirse pasa a `Normal`; las duraciones se pueden cambiar | OK | U | `s/test_estados_jugador.py::test_escudado_vuelve_a_normal_al_terminar_su_tiempo`, `s/test_estados_jugador.py::test_la_duracion_se_puede_cambiar` |
| CP-251 | Ruta fija: el guardián recorre un circuito | Guardián con `RutaFija` | Pasa el tiempo | Avanza al primer punto sin pasarse, recorre todos los puntos y vuelve al primero; sin puntos da error; `mover` dice si se movió | OK | U | `s/test_guardianes.py::TestRutaFija::test_avanza_hacia_el_primer_punto`, `s/test_guardianes.py::TestRutaFija::test_no_se_pasa_del_punto`, `s/test_guardianes.py::TestRutaFija::test_recorre_el_circuito_y_vuelve_al_primer_punto`, `s/test_guardianes.py::TestRutaFija::test_sin_puntos_falla`, `s/test_guardianes.py::TestRutaFija::test_mover_dice_si_se_movio` |
| CP-252 | Patrulla: ida y vuelta | Guardián con `Patrulla` | Pasa el tiempo | Llega al extremo y se devuelve; con tres puntos pasa otra vez por el medio; un solo punto no falla; sin puntos da error | OK | U | `s/test_guardianes.py::TestPatrulla::test_va_y_vuelve_sin_saltarse_el_camino`, `s/test_guardianes.py::TestPatrulla::test_con_tres_puntos_hace_ida_y_vuelta`, `s/test_guardianes.py::TestPatrulla::test_un_solo_punto_no_falla`, `s/test_guardianes.py::TestPatrulla::test_sin_puntos_falla` |
| CP-253 | Perseguir al jugador cercano | Guardián con `Perseguir` | Jugador dentro y fuera del radio de detección | Va hacia el jugador cercano y, con dos, hacia el más cercano; ignora al lejano y sin jugadores se queda quieto | OK | U | `s/test_guardianes.py::TestPerseguir::test_va_hacia_el_jugador_que_esta_cerca`, `s/test_guardianes.py::TestPerseguir::test_elige_al_mas_cercano`, `s/test_guardianes.py::TestPerseguir::test_ignora_al_jugador_que_esta_lejos`, `s/test_guardianes.py::TestPerseguir::test_sin_jugadores_se_queda_quieto` |
| CP-254 | Alcance del guardián | — | Jugador a distancia igual a la suma de radios, y uno un píxel más lejos | Lo alcanza al tocarse los círculos y no lo alcanza si hay un píxel de más; `a_dict` redondea la posición | OK | U | `s/test_guardianes.py::TestGuardian::test_alcanza_cuando_los_circulos_se_tocan`, `s/test_guardianes.py::TestGuardian::test_a_dict` |
| CP-255 | Un guardián lejos no penaliza | Guardián lejos del jugador | 10 ticks del motor | El jugador sigue `normal` | OK | I | `s/test_guardianes.py::TestPenalizacionEnElMotor::test_un_guardian_lejos_no_penaliza`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_el_jugador_empieza_normal` |
| CP-256 | Penalización: aturdimiento y pérdida de puntos | Guardián encima del jugador | 1 tick | Queda `aturdido` y pierde 5 puntos; con menos de 5 baja a 0, nunca a negativo | OK | I | `s/test_guardianes.py::TestPenalizacionEnElMotor::test_el_guardian_que_alcanza_al_jugador_lo_aturde`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_pierde_la_penalizacion_completa_si_tiene_puntos`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_pierde_puntos_pero_no_baja_de_cero` |
| CP-257 | Aturdido no se puede mover | Jugador aturdido | Presionar `derecha` durante 1 s | La posición no cambia | OK | I | `s/test_guardianes.py::TestPenalizacionEnElMotor::test_aturdido_no_se_puede_mover` |
| CP-258 | Penaliza una sola vez y luego se protege | Guardián encima del jugador | Pasan varios segundos | Aturdido no se descuenta otra vez; después queda `escudado`; al terminar el escudo, si el guardián sigue encima, lo vuelve a golpear | OK | I | `s/test_guardianes.py::TestPenalizacionEnElMotor::test_un_guardian_encima_no_lo_penaliza_varias_veces`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_despues_del_aturdimiento_queda_escudado_y_luego_normal`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_al_salir_del_escudo_un_guardian_encima_lo_vuelve_a_golpear` |
| CP-259 | Escudado no es penalizado (CU-11, E1) | Jugador `escudado`, guardián encima | 1 tick | No pierde puntos | OK | I | `s/test_guardianes.py::TestPenalizacionEnElMotor::test_el_jugador_escudado_no_es_penalizado` |
| CP-260 | El estado y el aviso llegan a los clientes | Partida con guardianes | Un guardián se mueve y alcanza a un jugador | El `estado` trae `guardianes` y `jugadores[].estado`; se emite `jugador_penalizado` con jugador, guardián, puntos y estado; sin guardianes no hay estados de más | OK | I | `s/test_guardianes.py::TestPenalizacionEnElMotor::test_el_estado_trae_la_lista_de_guardianes`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_sin_guardianes_la_lista_va_vacia`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_los_guardianes_se_mueven_y_avisan_a_los_clientes`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_la_penalizacion_se_avisa_como_evento`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_sin_guardianes_no_hay_cambios_ni_avisos`, `s/test_guardianes.py::TestPenalizacionEnElMotor::test_un_guardian_que_patrulla_termina_alcanzando_al_jugador` |
| CP-261 | El cliente dibuja guardianes y estados | Estado con guardianes y jugadores en distintos estados | Dibujar la arena | Guardián como círculo morado con borde oscuro; jugador rojo normal, gris aturdido y azul escudado; sin guardianes no falla | OK | U | `c/test_dibujo_guardianes.py::test_el_guardian_es_un_circulo_morado_con_borde_oscuro`, `c/test_dibujo_guardianes.py::test_no_dibuja_fuera_del_radio`, `c/test_dibujo_guardianes.py::test_dibuja_varios_guardianes`, `c/test_dibujo_guardianes.py::test_sin_guardianes_no_falla`, `c/test_dibujo_guardianes.py::test_el_jugador_normal_es_rojo`, `c/test_dibujo_guardianes.py::test_el_jugador_aturdido_es_gris`, `c/test_dibujo_guardianes.py::test_el_jugador_escudado_es_azul` |
| CP-262 | Ver al guardián moverse en el juego | Servidor con base nueva; dos jugadores en la arena; un guardián en la partida | Entrar a la arena | Un círculo morado se mueve solo por su ruta y los dos jugadores lo ven en el mismo lugar | OK (demo 25/11) | A | Manual (ver prueba punta a punta, paso 6) |
| CP-263 | Ser alcanzado por un guardián en el juego | Jugador con puntos | Caminar hasta tocar al guardián | El círculo del jugador se pone gris, no se mueve 3 s y su puntaje baja 5; el otro jugador lo ve gris | OK (demo 25/11) | A | Manual (ver prueba punta a punta, pasos 7 y 8) |
| CP-264 | Recuperarse del golpe en el juego | Jugador aturdido | Esperar | A los 3 s el círculo se pone azul y puede moverse; el guardián no lo vuelve a penalizar durante 2 s; después vuelve a rojo | OK (demo 25/11) | A | Manual (ver prueba punta a punta, paso 9) |
## US-09 Escenarios

**Criterios de aceptación (enunciado):** el juego tiene cinco escenarios (laboratorio, estación
espacial, planta industrial, centro de investigación y complejo militar), cada uno con su
distribución de obstáculos, celdas y guardianes. El mapa es simétrico para que ningún jugador parta
con ventaja.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-215 | Están los cinco escenarios y la fábrica de partidas los conoce | — | Pedir el catálogo y compararlo con el de `PartidaFactory` | Los cinco nombres del enunciado, iguales en los dos catálogos | OK | U | `s/test_escenarios.py::test_estan_los_cinco_escenarios_del_enunciado`, `s/test_escenarios.py::test_la_factory_de_partidas_usa_los_mismos_nombres`, `s/test_escenarios.py::test_los_escenarios_estan_registrados_por_su_nombre` |
| CP-216 | Un escenario que no existe se rechaza | — | `crear_escenario("selva")` y `obtener` del gestor con ese nombre | Error de escenario desconocido | OK | U e I | `s/test_escenarios.py::test_un_escenario_desconocido_se_rechaza`, `s/test_escenarios.py::test_el_gestor_rechaza_un_escenario_desconocido` |
| CP-217 | El reactor queda al centro y los obstáculos dentro de la arena sin tocarlo | Cada escenario | Crear el escenario | Reactor en (480, 270); obstáculos dentro de 960 x 540 y con espacio libre alrededor del reactor | OK | U | `s/test_escenarios.py::test_el_reactor_queda_al_centro`, `s/test_escenarios.py::test_todo_obstaculo_queda_dentro_de_la_arena`, `s/test_escenarios.py::test_ningun_obstaculo_toca_el_reactor` |
| CP-218 | Los cuatro puntos de inicio están libres | Cada escenario | Crear el escenario | Ningún obstáculo cubre un punto de inicio | OK | U | `s/test_escenarios.py::test_los_cuatro_puntos_de_inicio_estan_libres` |
| CP-219 | El mapa es simétrico | Cada escenario | Reflejar los obstáculos | Los cuatro cuadrantes son iguales, así ningún jugador parte con ventaja | OK | U | `s/test_escenarios.py::test_el_mapa_es_simetrico` |
| CP-220 | Siempre hay camino a los otros inicios, al reactor y a las celdas | Cada escenario | Buscar camino en una cuadrícula | Hay camino desde cada inicio a los demás, al reactor y a todas las celdas | OK | U | `s/test_escenarios.py::test_siempre_hay_camino_a_los_otros_puntos_de_inicio_y_al_reactor`, `s/test_escenarios.py::test_todas_las_celdas_se_pueden_alcanzar` |
| CP-221 | El motor manda el escenario, el mapa y los guardianes | Motor con escenario | Pedir el estado | El estado trae `escenario`, `arena.obstaculos` y `guardianes` del escenario; sin escenario no trae el campo | OK | I | `s/test_escenarios.py::test_el_motor_manda_el_escenario_el_mapa_y_los_guardianes`, `s/test_escenarios.py::test_sin_escenario_el_estado_no_trae_el_campo` |
| CP-222 | El gestor crea el motor con el escenario pedido y cada partida tiene sus guardianes | Gestor de motores | `obtener(id, escenario)` en dos partidas del mismo escenario | Cada motor usa su escenario y los guardianes no se comparten | OK | I | `s/test_escenarios.py::test_el_gestor_crea_el_motor_con_el_escenario_pedido`, `s/test_escenarios.py::test_dos_partidas_del_mismo_escenario_no_comparten_guardianes` |
| CP-223 | Jugar en cada uno de los cinco mapas | Servidor y cliente corriendo, dos jugadores | Crear una partida con cada escenario y jugarla un rato | Se ve el fondo, los obstáculos, las celdas y los guardianes de ese mapa, y los mapas se distinguen entre sí | OK (demo 25/11) | A | Manual (ver prueba punta a punta, paso 10) |

## US-13 Celdas de energía

**Criterios de aceptación (ERS, CU-10):** hay celdas de energía repartidas en el mapa; el jugador que
toca una la recoge y recibe puntos; la celda reaparece después de un tiempo. Decisión del equipo
(RN-06): una celda da **5 puntos**, menos que una extracción del reactor (10).

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-224 | Cada mapa tiene 8 celdas, ninguna dentro de un obstáculo ni sobre el reactor | Cada escenario | Crear el escenario | 8 celdas con id distinto, fuera de obstáculos y del reactor | OK | U | `s/test_escenarios.py::test_hay_ocho_celdas_y_ninguna_dentro_de_un_obstaculo`, `s/test_escenarios.py::test_ninguna_celda_toca_el_reactor` |
| CP-225 | Toda celda vale 5 puntos, menos que una extracción del reactor | Cada escenario | Leer el valor de las celdas | Todas valen 5 y 5 es menor que la energía por extracción (10) | OK | U | `s/test_escenarios.py::test_toda_celda_vale_cinco_puntos`, `s/test_escenarios.py::test_una_celda_vale_menos_que_una_extraccion_del_reactor` |
| CP-226 | Tocar una celda la recoge; una celda lejos no | Jugador sobre la celda y jugador lejos | Recoger | La primera se recoge (también justo en el borde) y la lejana no | OK | U | `s/test_celdas.py::test_tocar_una_celda_la_recoge`, `s/test_celdas.py::test_una_celda_lejos_no_se_recoge`, `s/test_celdas.py::test_justo_en_el_borde_se_recoge` |
| CP-227 | Dos jugadores tocan la misma celda | Dos jugadores sobre la celda | Recoger | Solo se la lleva el primero; una recogida no se puede recoger otra vez | OK | U | `s/test_celdas.py::test_si_dos_jugadores_tocan_la_misma_celda_se_la_lleva_el_primero`, `s/test_celdas.py::test_una_celda_recogida_no_se_puede_recoger_otra_vez` |
| CP-228 | La celda vuelve cuando pasa el tiempo de reposición (10 s) | Celda recogida | Avanzar el tiempo | Vuelve al mapa y se puede recoger otra vez | OK | U | `s/test_celdas.py::test_una_celda_recogida_vuelve_cuando_pasa_el_tiempo_de_reposicion`, `s/test_celdas.py::test_una_celda_repuesta_se_puede_volver_a_recoger`, `s/test_celdas.py::test_reponer_sin_celdas_recogidas_no_cambia_nada` |
| CP-229 | Recoger una celda suma sus puntos y se acumulan | Partida en el motor | El jugador toca una celda y luego otras | El puntaje sube lo que vale cada celda; cada jugador recoge la suya | OK | I | `s/test_celdas.py::test_el_jugador_que_toca_una_celda_suma_sus_puntos`, `s/test_celdas.py::test_los_puntos_se_acumulan_con_varias_celdas`, `s/test_celdas.py::test_cada_jugador_recoge_su_celda` |
| CP-230 | La celda recogida desaparece del estado, vuelve y se avisa a los observadores | Partida con celdas | Recoger y esperar la reposición | `arena.celdas` pierde la celda y luego la recupera; se avisa al recoger y al volver, aunque nadie se mueva | OK | I | `s/test_celdas.py::test_la_celda_recogida_desaparece_del_estado`, `s/test_celdas.py::test_la_celda_vuelve_al_estado_despues_de_la_reposicion`, `s/test_celdas.py::test_recoger_una_celda_avisa_a_los_observadores`, `s/test_celdas.py::test_que_la_celda_vuelva_tambien_avisa_aunque_nadie_se_mueva` |
| CP-231 | El cliente dibuja las celdas | Cliente | Estado con celdas y sin ellas | Se dibujan todas con su sprite (o círculo amarillo sin imagen); una recogida deja de dibujarse; sin celdas solo se ve el fondo | OK | U | `c/test_arena_celdas.py::test_se_dibujan_todas_las_celdas`, `c/test_arena_celdas.py::test_una_celda_recogida_deja_de_dibujarse`, `c/test_arena_sprites.py::test_la_celda_se_dibuja_con_su_sprite` |
| CP-232 | Recoger una celda en el juego | Partida iniciada en la arena | Caminar hasta tocar una celda | La celda desaparece, el puntaje sube 5, a los 10 s reaparece y el otro jugador lo ve igual | OK (demo 25/11) | A | Manual (ver prueba punta a punta, paso 11) |

## US-14 Obstáculos

**Criterios de aceptación (ERS):** los obstáculos del mapa afectan al jugador: las barreras bloquean,
las trampas frenan y las puertas se abren y se cierran. Además hay barreras móviles que recorren el
mapa y empujan al jugador.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-233 | Una barrera bloquea el paso y el jugador puede rodearla | Barrera delante del jugador | Caminar hacia ella y en diagonal | No la atraviesa; se desliza por el lado libre y puede rodearla | OK | U | `s/test_obstaculos.py::TestBarrera::test_bloquea_el_paso`, `s/test_obstaculos.py::TestBarrera::test_no_se_mete_dentro_de_la_barrera`, `s/test_obstaculos.py::TestBarrera::test_se_desliza_por_el_lado_libre_en_diagonal`, `s/test_obstaculos.py::TestBarrera::test_puede_rodear_la_barrera` |
| CP-234 | La trampa no bloquea pero frena al 40 % | Trampa | Caminar sobre ella y salir | Pasa más lento y al salir recupera la velocidad | OK | U | `s/test_obstaculos.py::TestTrampa::test_no_bloquea_el_paso`, `s/test_obstaculos.py::TestTrampa::test_frena_al_jugador`, `s/test_obstaculos.py::TestTrampa::test_al_salir_de_la_trampa_recupera_la_velocidad`, `s/test_obstaculos.py::TestTrampa::test_factor_de_velocidad` |
| CP-235 | La puerta empieza cerrada, se abre y se cierra (4 s y 4 s) | Puerta | Avanzar el tiempo | Cerrada bloquea; abierta deja pasar; vuelve a cerrarse; si se cierra encima, el jugador puede salir | OK | U | `s/test_obstaculos.py::TestPuerta::test_empieza_cerrada_y_bloquea`, `s/test_obstaculos.py::TestPuerta::test_abierta_deja_pasar`, `s/test_obstaculos.py::TestPuerta::test_se_cierra_otra_vez`, `s/test_obstaculos.py::TestPuerta::test_si_se_cierra_encima_el_jugador_puede_salir` |
| CP-236 | El estado de la puerta llega a los clientes | Partida con puerta | Esperar a que cambie | El estado trae `abierta` y se avisa el cambio solo cuando cambia | OK | I | `s/test_obstaculos.py::TestPuerta::test_el_estado_dice_si_esta_abierta`, `s/test_obstaculos.py::TestPuerta::test_actualizar_avisa_solo_cuando_cambia`, `s/test_obstaculos.py::TestPuerta::test_el_cambio_de_puerta_se_notifica_a_los_clientes` |
| CP-237 | La barrera móvil recorre su camino y vuelve | Barrera móvil (30 px/s) | Avanzar el tiempo | Va al destino, da la vuelta, completa el ciclo y nunca sale de su recorrido | OK | U | `s/test_obstaculos.py::TestBarreraMovil::test_avanza_hacia_el_destino_a_su_velocidad`, `s/test_obstaculos.py::TestBarreraMovil::test_en_el_destino_da_la_vuelta`, `s/test_obstaculos.py::TestBarreraMovil::test_completa_el_ciclo_y_vuelve_al_inicio`, `s/test_obstaculos.py::TestBarreraMovil::test_nunca_sale_del_recorrido` |
| CP-238 | La barrera móvil bloquea donde está ahora y el motor avisa su posición | Barrera móvil en marcha | Caminar hacia ella y avanzar el motor | No la atraviesa; el estado trae su posición actual y avisa en cada ciclo | OK | U e I | `s/test_obstaculos.py::TestBarreraMovil::test_bloquea_el_paso_donde_esta_ahora`, `s/test_obstaculos.py::TestBarreraMovil::test_el_estado_trae_la_posicion_actual`, `s/test_obstaculos.py::TestBarreraMovil::test_el_motor_la_mueve_y_avisa_a_los_clientes` |
| CP-239 | La barrera móvil empuja a un jugador quieto | Jugador quieto en su camino | Avanzar el motor | El jugador queda fuera de la barrera, por el lado más cercano | OK | U e I | `s/test_obstaculos.py::TestEmpujeDeLaBarreraMovil::test_sacar_deja_al_circulo_libre_por_el_lado_mas_cercano`, `s/test_obstaculos.py::TestEmpujeDeLaBarreraMovil::test_empuja_a_un_jugador_quieto`, `s/test_obstaculos.py::TestEmpujeDeLaBarreraMovil::test_en_el_motor_la_barrera_empuja_al_jugador_quieto` |
| CP-240 | Nunca la atraviesa si camina hacia ella | Jugador caminando hacia la barrera | Avanzar el motor | Nunca queda dentro de la barrera | OK | I | `s/test_obstaculos.py::TestEmpujeDeLaBarreraMovil::test_en_el_motor_nunca_la_atraviesa_si_el_jugador_camina_hacia_ella`, `s/test_obstaculos.py::TestBarreraMovil::test_el_jugador_choca_con_ella_en_el_motor` |
| CP-241 | El jugador puede moverse mientras lo empujan; solo la barrera móvil empuja | Jugador empujado | Presionar una dirección; una puerta y una barrera fija encima | Se sigue moviendo; las puertas y las barreras fijas no empujan; quien ya está libre no se toca | OK | I | `s/test_obstaculos.py::TestEmpujeDeLaBarreraMovil::test_el_jugador_puede_moverse_mientras_lo_empujan`, `s/test_obstaculos.py::TestEmpujeDeLaBarreraMovil::test_las_puertas_y_barreras_fijas_no_empujan`, `s/test_obstaculos.py::TestEmpujeDeLaBarreraMovil::test_no_toca_a_los_que_ya_estan_libres` |
| CP-242 | Cada mapa trae sus obstáculos y las barreras móviles no estorban | Los cinco escenarios | Revisar los tipos y recorrer el ciclo de las barreras móviles | Laboratorio y centro tienen barreras móviles, la estación tiene puertas y la planta trampas; las móviles nunca salen de la arena ni tapan el reactor, un inicio o una celda | OK | U | `s/test_escenarios.py::test_laboratorio_y_centro_de_investigacion_tienen_barreras_moviles`, `s/test_escenarios.py::test_la_estacion_espacial_tiene_puertas_y_la_planta_industrial_trampas`, `s/test_escenarios.py::test_las_barreras_moviles_nunca_salen_de_la_arena`, `s/test_escenarios.py::test_las_barreras_moviles_nunca_tocan_el_reactor`, `s/test_escenarios.py::test_las_barreras_moviles_nunca_tapan_un_punto_de_inicio_ni_una_celda` |
| CP-243 | El cliente dibuja muro, trampa y puerta con sus sprites; la puerta abierta se ve oscura | Cliente | Dibujar cada tipo | Muro en cuadros de 30 px, trampa con su sprite, puerta normal si está cerrada y oscura si está abierta (mismo rectángulo); sin imagen vuelve a sus colores | OK | U | `c/test_dibujo_obstaculos.py::test_la_barrera_se_rellena_con_el_sprite_del_muro_en_cuadros_de_30`, `c/test_dibujo_obstaculos.py::test_la_trampa_se_rellena_con_su_sprite_en_cuadros_de_30`, `c/test_dibujo_obstaculos.py::test_la_puerta_abierta_es_el_mismo_sprite_pero_mas_oscuro`, `c/test_dibujo_obstaculos.py::test_sin_imagen_la_puerta_vuelve_a_sus_colores` |
| CP-244 | Ver los obstáculos en el juego | Partida en la arena con barreras móviles, trampas y puertas | Caminar por el mapa | La barrera bloquea, la trampa frena, la puerta se oscurece al abrirse y la barrera móvil empuja aunque uno esté quieto o camine hacia ella | OK (demo 25/11) | A | Manual (ver prueba punta a punta, paso 12) |

## US-16 Eventos especiales

**Criterios de aceptación (enunciado):** durante la partida ocurren eventos especiales que cambian las
reglas por unos segundos. El equipo implementó dos: **puntos dobles** e **invasión**. El primero sale a
los 30 s de iniciada la partida, cada uno dura 10 s y el siguiente llega entre 30 y 45 s después. Nunca
hay dos a la vez ni el mismo dos veces seguidas. El nombre del evento y los segundos que le quedan se
ven en el cuadro de posiciones. Numeración desde CP-346 porque el rango CP-215 a CP-264 ya está lleno.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-346 | La fábrica conoce los dos eventos | — | Pedir las claves, crear cada evento y uno al azar excluyendo otro | `puntos_dobles` e `invasion` con su nombre; una clave desconocida falla; el excluido no sale | OK | U | `s/test_eventos_especiales.py::TestFabrica` |
| CP-347 | El primer evento sale a los 30 s, dura 10 s y después desaparece | Partida en curso | Avanzar 29,9 s, 30 s y 10 s más | A los 29,9 s no hay evento; después trae `restante` 10, luego 5, luego 1, y al final no hay `evento` | OK | I | `s/test_eventos_especiales.py::TestTiempos::test_el_primer_evento_sale_a_los_30_segundos`, `s/test_eventos_especiales.py::TestTiempos::test_dura_10_segundos_y_despues_desaparece` |
| CP-348 | El estado trae clave, nombre y segundos, y la cuenta regresiva baja de a uno | Evento de 10 s | Avanzar el motor tick a tick | `restante` pasa por 10, 9, 8 ... 1; no hay `evento` antes de iniciar ni sin programador | OK | I | `s/test_eventos_especiales.py::TestTiempos::test_el_evento_trae_clave_nombre_y_segundos`, `s/test_eventos_especiales.py::TestTiempos::test_la_cuenta_regresiva_baja_de_a_un_segundo`, `s/test_eventos_especiales.py::TestTiempos::test_no_hay_eventos_antes_de_iniciar_la_partida`, `s/test_eventos_especiales.py::TestTiempos::test_sin_programador_no_hay_eventos` |
| CP-349 | El siguiente evento llega entre 30 y 45 s después y nunca se repite el mismo seguido | Varias semillas | Avanzar una partida completa | Entre un fin y el siguiente inicio pasan de 30 a 45 s; las claves consecutivas son distintas y los avisos alternan inicio y fin | OK | I | `s/test_eventos_especiales.py::TestTiempos::test_el_siguiente_evento_llega_entre_30_y_45_segundos_despues`, `s/test_eventos_especiales.py::TestTiempos::test_nunca_se_repite_el_mismo_evento_seguido_y_solo_hay_uno_a_la_vez` |
| CP-350 | Se avisa a los clientes y se guarda en la base cuando empieza y termina un evento | Observador suscrito | Avanzar un evento completo | Llegan estados con `evento` y un último estado sin él, más `evento_especial_iniciado` y `evento_especial_finalizado`, que están en los tipos que se guardan; el gestor crea los motores con eventos | OK | I | `s/test_eventos_especiales.py::TestTiempos::test_se_avisa_a_los_clientes_cuando_empieza_y_cuando_termina`, `s/test_eventos_especiales.py::TestTiempos::test_el_registro_guarda_cuando_empieza_y_termina_un_evento`, `s/test_eventos_especiales.py::TestTiempos::test_el_gestor_crea_los_motores_con_eventos` |
| CP-351 | Puntos dobles: lo que se gana vale el doble | Evento activo | Sumar 5 puntos, recoger una celda y extraer del reactor | Suma 10; la celda da 10; el reactor da 20 en el puntaje, pero el registro de la acción cuenta la energía normal (10) | OK | I | `s/test_eventos_especiales.py::TestPuntosDobles::test_durante_el_evento_lo_que_se_gana_vale_el_doble`, `s/test_eventos_especiales.py::TestPuntosDobles::test_una_celda_vale_el_doble_durante_el_evento`, `s/test_eventos_especiales.py::TestPuntosDobles::test_extraer_del_reactor_vale_el_doble_pero_el_registro_cuenta_la_energia_normal` |
| CP-352 | Puntos dobles: las penalizaciones no se duplican y al terminar todo vuelve a lo normal | Evento activo y evento terminado | Perder 5 puntos; sumar 5 antes, durante y después | Pierde 5 (no 10); antes y después del evento 5 puntos valen 5 | OK | I | `s/test_eventos_especiales.py::TestPuntosDobles::test_las_penalizaciones_no_se_duplican`, `s/test_eventos_especiales.py::TestPuntosDobles::test_al_terminar_el_evento_los_puntos_vuelven_a_valer_lo_normal`, `s/test_eventos_especiales.py::TestPuntosDobles::test_antes_del_evento_tampoco_se_duplica`, `s/test_eventos_especiales.py::TestPuntosDobles::test_directo_pone_y_quita_el_multiplicador` |
| CP-353 | Invasión: aparecen dos guardianes cerca del reactor, en lados opuestos | Evento de invasión | Avanzar al inicio del evento | Dos guardianes con ids 100 y 101 a 100 px del borde del reactor, opuestos; los del mapa siguen | OK | I | `s/test_eventos_especiales.py::TestInvasion::test_al_empezar_aparecen_dos_guardianes_extra`, `s/test_eventos_especiales.py::TestInvasion::test_aparecen_cerca_del_reactor_y_en_lados_opuestos` |
| CP-354 | Invasión: no aparecen sobre paredes ni encima de un jugador | Mapa con paredes y un jugador cerca | Varias semillas | Ningún invasor toca una pared ni a un jugador | OK | I | `s/test_eventos_especiales.py::TestInvasion::test_no_aparecen_sobre_paredes`, `s/test_eventos_especiales.py::TestInvasion::test_no_aparecen_encima_de_un_jugador` |
| CP-355 | Invasión: persiguen aunque el jugador esté lejos y lo penalizan | Jugador lejos (más de 150 px) | Avanzar el motor | Se acercan al jugador y, al alcanzarlo, `jugador_penalizado` con -5 puntos | OK | I | `s/test_eventos_especiales.py::TestInvasion::test_persiguen_aunque_el_jugador_este_lejos`, `s/test_eventos_especiales.py::TestInvasion::test_si_alcanzan_al_jugador_lo_penalizan` |
| CP-356 | Los efectos desaparecen al terminar el evento o la partida | Invasión y puntos dobles en marcha | Esperar el fin del evento; terminar la partida a la mitad | Los invasores se van y quedan los guardianes del mapa; el multiplicador vuelve a 1; sin `evento`; una invasión nueva no acumula invasores | OK | I | `s/test_eventos_especiales.py::TestInvasion::test_al_terminar_el_evento_desaparecen_y_quedan_los_del_mapa`, `s/test_eventos_especiales.py::TestInvasion::test_si_la_partida_termina_en_plena_invasion_los_invasores_se_van`, `s/test_eventos_especiales.py::TestInvasion::test_cada_invasion_trae_invasores_nuevos_sin_acumularse`, `s/test_eventos_especiales.py::TestPuntosDobles::test_si_la_partida_termina_con_el_evento_activo_se_deshace`, `s/test_eventos_especiales.py::TestPuntosDobles::test_si_el_evento_dura_mas_que_la_partida_no_vuelve_a_salir`, `s/test_eventos_especiales.py::TestTiempos::test_una_partida_nueva_vuelve_a_esperar_los_30_segundos` |
| CP-357 | El cuadro de posiciones muestra el nombre del evento y los segundos | Cliente | Dibujar el HUD con y sin `partida.evento` | Con evento el cuadro crece con una fila (nombre y "N s"); sin evento queda igual | OK | U | `c/test_hud_partida.py::test_el_evento_se_escribe_con_su_nombre_y_los_segundos`, `c/test_hud_partida.py::test_el_cuadro_crece_solo_cuando_hay_un_evento` |
| CP-358 | Cada evento se pinta de su color | Cliente | Dibujar el HUD con cada evento | Verde para puntos dobles, rojo para invasión y celeste para otro; sin evento no hay color de evento | OK | U | `c/test_hud_partida.py::test_cada_evento_se_pinta_de_su_color`, `c/test_hud_partida.py::test_un_evento_desconocido_usa_el_color_por_defecto`, `c/test_hud_partida.py::test_sin_evento_no_hay_color_de_evento` |
| CP-359 | Ver los dos eventos en una partida real | Partida iniciada con el cuadro de posiciones visible | Jugar más de 90 s | Sale "Puntos dobles" (verde) o "Invasión" (rojo) con los segundos; con puntos dobles una celda da 10 y el reactor 20; con invasión aparecen dos guardianes que persiguen; al terminar el evento todo vuelve a lo normal | OK (demo 25/11) | A | Manual (ver prueba punta a punta, paso 13) |

## Arena visual

**Alcance:** los fondos de cada escenario, el fondo de los menús y los sprites de la arena. Los de
obstáculos, celdas y guardianes están en sus historias (CP-231, CP-243 y CP-261).

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-360 | Cada escenario tiene su fondo y se ajusta a la arena | Cliente con las imágenes | Dibujar el fondo de cada escenario, con una imagen pequeña, una faltante y una dañada | Cada escenario dibuja la suya a 960 x 540; si falta o está dañada no dibuja nada y no se rompe | OK | U | `c/test_dibujo_fondo.py::test_cada_escenario_tiene_su_fondo`, `c/test_dibujo_fondo.py::test_el_fondo_se_ajusta_al_tamano_de_la_arena`, `c/test_dibujo_fondo.py::test_cada_escenario_dibuja_su_propia_imagen`, `c/test_dibujo_fondo.py::test_si_falta_la_imagen_no_dibuja_nada_y_no_falla`, `c/test_arena_sprites.py::test_la_arena_dibuja_el_fondo_del_escenario_de_la_partida` |
| CP-361 | Las pantallas que no son de partida usan el fondo de los menús | Cliente | Dibujar cada pantalla (login, registro, perfil, lobby y demás) | Cubre toda la ventana con un velo oscuro; sin imagen queda el color liso | OK | U | `c/test_dibujo_fondo.py::test_el_fondo_de_los_menus_cubre_toda_la_ventana`, `c/test_dibujo_fondo.py::test_toda_pantalla_que_no_es_de_partida_dibuja_el_fondo_de_los_menus`, `c/test_dibujo_fondo.py::test_toda_pantalla_sin_imagen_sigue_con_el_color_liso` |

## Cómo ejecutar los casos de aceptación

Los casos de tipo **A** del Sprint 3 se hacen con una sola prueba punta a punta:

1. En la raíz del repo: `docker compose up` y esperar `Application startup complete`.
2. En `client/`: `python main.py`, dos veces (dos ventanas), o una ventana y otra en el celular.
3. Iniciar sesión con dos cuentas. La primera crea una partida con el escenario que se quiera probar
   y la segunda se une.
4. Las dos entran a la arena.
5. Iniciar la partida.
6. **CP-262:** ver el círculo morado del guardián moverse solo por su ruta; los dos jugadores lo ven en
   el mismo lugar.
7. **CP-263 (parte 1):** el jugador 1, con puntos, camina hasta tocar al guardián.
8. **CP-263 (parte 2):** su círculo se pone gris, no se mueve durante 3 s y su puntaje baja 5; el
   jugador 2 lo ve gris.
9. **CP-264:** a los 3 s el círculo se pone azul y se puede mover; el guardián no lo penaliza durante
   2 s; después vuelve a rojo.
10. **CP-223:** repetir los pasos 3 a 5 con cada uno de los cinco escenarios (laboratorio, estación
    espacial, planta industrial, centro de investigación y complejo militar) y revisar fondo,
    obstáculos, celdas y guardianes.
11. **CP-232:** caminar hasta una celda: desaparece, el puntaje sube 5 y a los 10 s reaparece.
12. **CP-244:** en el laboratorio o el centro de investigación, probar la barrera móvil (quieto,
    caminando hacia ella y en su misma dirección); en la estación espacial, esperar a que una puerta
    se abra (se ve más oscura); en la planta industrial, pisar una trampa.
13. **CP-359:** dejar correr la partida más de 90 s y mirar el cuadro de posiciones: aparece el
    evento con sus segundos. Para repetirlo sin esperar 30 s se puede bajar `PRIMER_EVENTO_S` en
    `server/app/realtime/eventos_especiales.py` mientras se prueba (hay que devolverlo después).

Evidencia (demo del 25/11): capturas de la arena en `../manual/img/` y consultas de la base en
`evidencias/demo-25-11/`; el resultado de cada caso está en la Wiki, página "Casos de prueba Sprint 3".

## Regresión

Las pruebas automáticas de este documento corren en cada Pull Request en el CI. Ejecución del
24/11/2026 con los eventos especiales y las celdas a 5 puntos: **575 pruebas del servidor pasan** y
las del cliente también. Para repetirlas: `python -m pytest -q` dentro de `server/` y de `client/`
(el cliente con `SDL_VIDEODRIVER=dummy`).

## Pendientes

Ninguno. Los siete casos de aceptación (CP-223, CP-232, CP-244, CP-262, CP-263, CP-264 y CP-359) se
ejecutaron en la demo interna del 25/11 en la nube, con 4 jugadores (2 en computadora y 2 en
celular): los 150 casos están en OK. Evidencia: capturas de la arena con Puntos dobles e Invasión
(`../manual/img/arena-puntos-dobles.jpg`, `../manual/img/arena-invasion.jpg`) y consultas de la base
al terminar la partida (`evidencias/demo-25-11/`).
