# Casos de prueba — Rol B (US-07, US-08, US-21 y US-25)

Cada caso está automatizado con pytest, salvo los de tipo **A**, que se ejecutan a mano con el juego; la
columna **Prueba** dice dónde. Los del servidor corren contra PostgreSQL en el CI y los del cliente con
pygame sin ventana y el servidor simulado.

**Tipos:** **U** unitaria (una pieza sola, sin base de datos ni red), **I** integración (varias piezas
juntas, con la base de datos real o con un servidor real) y **A** aceptación (el juego completo, a mano).

**Resultado obtenido:** todas las pruebas automáticas pasan: 186 del servidor y 148 del cliente, en
Python 3.12 y 3.14 (en el CI el servidor corre contra PostgreSQL 16). Para repetirlas: `pytest` dentro de
`server/` y de `client/`. Los casos **Pendiente** esperan a que exista lo que prueban (ver el final).

Archivos: `s/` = `server/tests/`, `c/` = `client/tests/`. La numeración sigue a la del Rol A (CP-01 a CP-46).


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
| CP-95 | Los datos sobreviven al reinicio del servidor | Partidas y jugadores guardados, Docker corriendo | `docker compose restart server` | Los mismos datos siguen disponibles | Pendiente | A | Manual: sin ejecutar todavía |

## US-25 Movimiento por el mapa

**Criterios de aceptación (Board):** los controles permiten moverse en 8 direcciones según la tecla que se presione; el jugador se mueve mientras nada lo obstruya (obstáculos o el límite del mapa); el movimiento se ve en pantalla en menos de 500 ms desde que se presiona la tecla y se detiene al soltarla.

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
| CP-125 | Ver el movimiento en pantalla | Dos ventanas con la pantalla de la arena | W, A, S y D en una ventana | El personaje se mueve y se ve en la otra ventana en menos de 500 ms; se detiene al soltar la tecla | Pendiente | A | Manual: falta la pantalla de la arena |

## Pendientes

- **CP-95** (Los datos sobreviven al reinicio del servidor): se prueba con `docker compose restart server` y mirando que los datos sigan ahí.
- **CP-125** (Ver el movimiento en pantalla): depende de la pantalla de la arena, que todavía no existe.