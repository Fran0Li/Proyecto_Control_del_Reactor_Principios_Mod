# Casos de prueba del Sprint 3 — Rol A (US-22, US-17, US-24, US-18, US-19, US-20 y US-28)

Cubre el reloj de la partida (US-22), iniciar y terminar la partida con sus ganadores (US-17), el
HUD con la tabla de posiciones (US-24), la ceremonia de victoria (US-18), el ranking global
(US-19), el historial del jugador (US-20), el rol de administrador (US-28) y la deuda técnica del
rol (crear y unirse con el token, teclado en el celular). Tasks del Board: AB#129 a AB#142.
La numeración del rol A en el Sprint 3 va de CP-165 a CP-214 (rol B: CP-215 a CP-264; rol C:
CP-265 a CP-314).

**Tipos:** **U** unitaria (una pieza sola, sin base de datos ni red), **I** integración (varias
piezas juntas: la API o el canal WebSocket con el motor y la base de datos) y **A** aceptación (el
juego completo, a mano). Todas las U e I corren en el CI en cada Pull Request.

Archivos: `s/` = `server/tests/`, `c/` = `client/tests/`.

## Resumen

| Historia | Casos | OK | Pendiente |
| --- | --- | --- | --- |
| US-22 Temporizador en partida | CP-165 a CP-170 (6) | 6 | 0 |
| US-17 Criterios de victoria | CP-171 a CP-184 (14) | 14 | 0 |
| US-24 Tabla de posiciones en tiempo real | CP-185 a CP-188 (4) | 4 | 0 |
| US-18 Ceremonia de victoria | CP-189 a CP-195 (7) | 7 | 0 |
| US-19 Ranking global | CP-196 a CP-199 (4) | 4 | 0 |
| US-20 Historial y estadísticas | CP-200 a CP-203 (4) | 4 | 0 |
| US-28 Rol de administrador | CP-204 a CP-211 (8) | 8 | 0 |
| Deuda técnica | CP-212 a CP-214 (3) | 3 | 0 |
| **Total** | **50** | **50** | **0** |

Los cuatro casos de aceptación que quedaban (CP-170, CP-195, CP-211 y CP-214) se ejecutaron a mano
en la demo interna del 25/11 en la nube, con dos jugadores en computadora y dos en celular: los 50
están en OK (ver [Cómo ejecutar los casos de aceptación](#cómo-ejecutar-los-casos-de-aceptación)).

## US-22 Temporizador en partida

**Criterios de aceptación:** el temporizador es visible para todos los jugadores; cuenta hacia atrás
desde el tiempo límite; al llegar a cero la partida termina sola.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-165 | Antes de iniciar no corre el reloj | Motor con jugadores, sin iniciar | Pasan los ciclos | Estado `esperando`, sin tiempo restante | OK | U | `s/test_fin_de_partida.py::test_la_partida_empieza_esperando_y_sin_reloj`, `::test_antes_de_iniciar_no_termina_aunque_pase_el_tiempo` |
| CP-166 | El reloj baja y avisa cada segundo | Partida iniciada con 300 s | Pasan 2 s | `tiempo_restante` baja 300, 299, 298 y se manda un estado por segundo | OK | U | `s/test_fin_de_partida.py::test_el_reloj_baja_y_se_avisa_una_vez_por_segundo` |
| CP-167 | El estado lleva el reloj y las reglas a todos | Partida iniciada | `estado()` | `partida` trae `estado`, `tiempo_limite`, `puntaje_objetivo` y `tiempo_restante` | OK | U | `s/test_fin_de_partida.py::test_el_estado_trae_el_reloj_y_las_reglas` |
| CP-168 | Al llegar a cero termina sola | Partida de 1 s | Pasa 1 s | `partida_finalizada` con motivo `tiempo` | OK | U | `s/test_fin_de_partida.py::test_termina_cuando_se_acaba_el_tiempo`, `s/test_reglas_victoria.py::test_termina_cuando_se_acaba_el_tiempo` |
| CP-169 | El reloj se ve como minutos y segundos | — | 300, 61, 9 y 0 s | `5:00`, `1:01`, `0:09`, `0:00`; "Esperando inicio" antes de empezar | OK | U | `c/test_hud_partida.py::test_el_reloj_se_muestra_en_minutos_y_segundos`, `::test_el_reloj_dice_si_la_partida_no_empezo_o_ya_termino` |
| CP-170 | Los dos jugadores ven el mismo reloj | Backend local, dos clientes en la misma partida | Iniciar la partida | Los dos relojes bajan igual (diferencia ≤ 1 s) y en los últimos 30 s se ponen en rojo | OK (demo 25/11) | A | Manual |

## US-17 Criterios de victoria

**Criterios de aceptación:** la partida termina al alcanzar el tiempo límite o la puntuación
objetivo, lo que ocurra primero; el sistema ordena a los jugadores por puntaje; se definen primer,
segundo y tercer lugar.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-171 | Termina al llegar a 500 puntos | Partida en curso | Un jugador llega al objetivo | Fin con motivo `puntaje`; si pasan las dos cosas a la vez cuenta el puntaje | OK | U | `s/test_reglas_victoria.py::test_termina_al_llegar_a_la_puntuacion_objetivo`, `::test_si_pasan_las_dos_cosas_a_la_vez_cuenta_el_puntaje`, `s/test_fin_de_partida.py::test_termina_al_llegar_a_la_puntuacion_objetivo` |
| CP-172 | Ordena por puntaje y los empates comparten puesto | — | Puntajes 300, 120, 120, 50 | Puestos 1, 2, 2, 4 | OK | U | `s/test_reglas_victoria.py::test_ordena_de_mayor_a_menor_puntaje`, `::test_los_empatados_comparten_el_puesto` |
| CP-173 | Con empate arriba no hay ganador único | — | Dos jugadores con el mayor puntaje | `ganador_id` = `None` | OK | U | `s/test_reglas_victoria.py::test_con_empate_en_el_primer_lugar_no_hay_ganador`, `s/test_fin_de_partida.py::test_con_empate_arriba_no_hay_ganador` |
| CP-174 | Al iniciar todos arrancan iguales | Jugadores que se movieron en la espera | `iniciar_partida` | Todos en su punto de inicio con 0 puntos y aviso `partida_iniciada` | OK | U | `s/test_fin_de_partida.py::test_al_iniciar_todos_vuelven_al_inicio_con_cero_puntos`, `::test_al_iniciar_avisa_partida_iniciada_con_las_reglas` |
| CP-175 | Termina una sola vez y la arena se queda quieta | Partida terminada | Más ciclos y entradas | Un solo `partida_finalizada`; nadie se mueve | OK | U | `s/test_fin_de_partida.py::test_termina_una_sola_vez`, `::test_terminada_la_arena_se_queda_quieta` |
| CP-176 | Quien se desconecta cuenta en el resultado | Partida en curso | Un jugador se va y otro vuelve | El que se fue aparece en las posiciones; el que vuelve conserva sus puntos | OK | U | `s/test_fin_de_partida.py::test_quien_se_va_en_plena_partida_cuenta_en_el_resultado`, `::test_el_que_se_fue_puede_volver_con_sus_puntos` |
| CP-177 | El creador inicia la partida | Partida con 2 jugadores | `POST /partidas/{id}/iniciar` con el token del creador | 200, estado `en_curso` | OK | I | `s/test_iniciar_partida.py::test_el_creador_inicia_la_partida` |
| CP-178 | Solo el creador, con sesión y con 2 jugadores | Partida esperando | Otro jugador; sin token; con 1 jugador | 403; 401; 409 | OK | I | `s/test_iniciar_partida.py::test_solo_el_creador_puede_iniciarla`, `::test_sin_sesion_no_se_puede_iniciar`, `::test_hacen_falta_al_menos_dos_jugadores` |
| CP-179 | No se inicia dos veces ni una que no existe | Partida en curso | Iniciar otra vez; id 999 | 409; 404 | OK | I | `s/test_iniciar_partida.py::test_no_se_inicia_dos_veces`, `::test_una_partida_que_no_existe` |
| CP-180 | Una partida iniciada no acepta jugadores | Partida en curso | `GET /partidas` y unirse | No aparece en la lista; unirse da 409 | OK | I | `s/test_iniciar_partida.py::test_iniciada_ya_no_aparece_ni_acepta_jugadores` |
| CP-181 | Al terminar se guardan puntajes, puestos y estado | Observador `CierrePartida` | `partida_finalizada` | Partida `finalizada`; cada participación con su puntaje y puesto; el jugador puede crear otra | OK | I | `s/test_resultados_partida.py::test_al_terminar_la_partida_queda_finalizada_con_puntajes_y_puestos`, `::test_al_terminar_un_jugador_puede_crear_otra_partida` |
| CP-182 | Se guardan los eventos importantes | Observador `RegistroEventos` | Inicio, acciones, estados y fin | En `eventos` quedan inicio, acciones y fin, no cada estado | OK | I | `s/test_resultados_partida.py::test_guarda_inicio_acciones_y_fin_pero_no_cada_estado` |
| CP-183 | El ranking global suma cada partida | Observador `ActualizadorRanking` | Dos partidas; una con empate | Suma puntos; la victoria solo al ganador único | OK | I | `s/test_resultados_partida.py::test_el_ranking_suma_puntos_y_la_victoria_al_ganador`, `::test_el_ranking_acumula_partida_tras_partida`, `::test_con_empate_nadie_suma_victoria` |
| CP-184 | Partida completa por el canal, del inicio al ranking | Dos jugadores conectados por WebSocket | Iniciar con 1 s, sumar puntos y esperar | Los dos reciben `partida_iniciada` y `partida_finalizada` con el orden; la base queda finalizada y con ranking | OK | I | `s/test_iniciar_partida.py::test_partida_completa_del_inicio_al_ranking`; cliente: `c/test_inicio_partida.py` (botón de iniciar, paso a la arena y posiciones) |

## US-24 Tabla de posiciones en tiempo real

**Criterios de aceptación:** la tabla muestra la posición y el puntaje de cada jugador durante la
partida; se actualiza en tiempo real; la ven todos los jugadores.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-185 | La tabla ordena por puntaje con empates | — | 4 jugadores, dos con 40 | 1 beto 120, 2 ana 40, 2 Jugador 3 40, 4 dani 10 | OK | U | `c/test_hud_partida.py::test_la_tabla_ordena_por_puntaje_y_los_empates_comparten_puesto` |
| CP-186 | La tabla cambia cuando cambian los puntajes | — | Un jugador pasa al otro | El orden se invierte | OK | U | `c/test_hud_partida.py::test_la_tabla_cambia_cuando_cambian_los_puntajes` |
| CP-187 | El estado trae el nombre de cada jugador | Dos jugadores por el canal | Mensaje `estado` | Cada jugador con su `nombre` de usuario | OK | I | `s/test_iniciar_partida.py::test_el_estado_trae_el_nombre_de_cada_jugador`, `s/test_movimiento_ws.py::test_el_jugador_recibe_su_posicion_inicial_al_entrar` |
| CP-188 | El HUD se dibuja en cada estado de la partida | — | Esperando, en curso y finalizada; sin jugadores | Tabla arriba a la derecha y reloj arriba a la izquierda; sin jugadores no hay tabla | OK | U | `c/test_hud_partida.py::test_el_hud_se_dibuja_en_cada_estado_de_la_partida`, `::test_sin_jugadores_no_dibuja_la_tabla` |

## US-18 Ceremonia de victoria

**Criterios de aceptación:** al finalizar se muestra una pantalla de victoria con el podio y un
resumen de estadísticas, con animaciones o efectos visuales, y que sea atractiva.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-189 | El resultado trae podio y estadísticas | Partida terminada con eventos | `GET /partidas/{id}/resultado` | Puestos, puntajes, acciones y penalizaciones de cada jugador, motivo y duración | OK | I | `s/test_resultado_partida.py::test_devuelve_el_podio_con_las_estadisticas_de_cada_jugador` |
| CP-190 | Logros y récords alcanzados en la partida | Logro ganado; partidas anteriores | `GET /partidas/{id}/resultado` | Lista los logros (US-27) y marca `record_personal` solo si supera sus partidas anteriores | OK | I | `s/test_resultado_partida.py::test_incluye_los_logros_que_se_desbloquearon_en_la_partida`, `::test_marca_el_record_personal_solo_si_supera_sus_partidas_anteriores`, `::test_la_primera_partida_con_puntos_es_record_y_sin_puntos_no` |
| CP-191 | Errores del resultado | Partida en curso; id 999; sin token | `GET /partidas/{id}/resultado` | 409; 404; 401 | OK | I | `s/test_resultado_partida.py::test_una_partida_que_sigue_en_curso_da_409`, `::test_una_partida_que_no_existe_da_404`, `::test_sin_sesion_no_se_puede_ver` |
| CP-192 | Podio con el primero en el medio y título | — | 4 posiciones; empate; 2 jugadores | Orden 2°, 1°, 3°; "¡beto gana!" o "¡Empate!" | OK | U | `c/test_ceremonia.py::test_el_podio_pone_al_primero_en_el_medio`, `::test_con_dos_jugadores_el_podio_tiene_dos_escalones`, `::test_el_titulo_nombra_al_ganador_o_avisa_el_empate` |
| CP-193 | Efectos: confeti y fanfarria | — | Confeti que llega abajo; armar el sonido | El papel vuelve a salir arriba; la fanfarria dura más de 0,5 s o, sin audio, no falla | OK | U | `c/test_ceremonia.py::test_el_confeti_cae_y_vuelve_a_salir_por_arriba`, `::test_la_fanfarria_se_arma_o_no_falla_sin_audio` |
| CP-194 | La pantalla carga las estadísticas y llega desde la arena | Resultado guardándose (409) | Fin de partida | La arena muestra las posiciones 3 s y pasa a la ceremonia; reintenta mientras da 409; con otro error deja el podio | OK | U | `c/test_ceremonia.py::test_la_arena_pasa_a_la_ceremonia_unos_segundos_despues_del_fin`, `::test_si_el_resultado_se_esta_guardando_vuelve_a_intentar`, `::test_si_falla_de_otra_forma_muestra_el_error_y_deja_el_podio`, `::test_volver_lleva_al_lobby_con_el_boton_o_con_esc` |
| CP-195 | La ceremonia se ve bien en escritorio y en el celular | Partida real de 2 jugadores | Terminarla | Podio que sube, trofeo, confeti, fanfarria y estadísticas legibles; "Volver al lobby" funciona | OK (demo 25/11) | A | Manual |

## US-19 Ranking global

**Criterios de aceptación:** el jugador puede consultar el ranking histórico; muestra como mínimo el
Top 10; se actualiza solo al terminar cada partida.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-196 | Ordena por puntos y luego por victorias | Tres jugadores con partidas | `GET /ranking` | carla 140 (1 v.), beto 140 (0 v.), ana 100 | OK | I | `s/test_ranking_historial.py::test_el_ranking_ordena_por_puntos_y_luego_por_victorias` |
| CP-197 | Top 10 y el puesto propio | 12 jugadores en el ranking | `GET /ranking` del último | 10 filas y `yo` con el puesto 12; quien no jugó no tiene puesto | OK | I | `s/test_ranking_historial.py::test_el_ranking_muestra_solo_los_diez_mejores_y_el_puesto_propio`, `::test_quien_nunca_jugo_no_tiene_puesto` |
| CP-198 | Se actualiza al terminar otra partida | Ranking con ana arriba | Otra partida que gana beto | beto pasa al primer lugar | OK | I | `s/test_ranking_historial.py::test_el_ranking_cambia_al_terminar_otra_partida` |
| CP-199 | La pantalla del ranking | Lobby | Botón "Ranking" | Muestra el top con medallas y el puesto propio; vacío o error avisan | OK | U | `c/test_ranking_historial.py::test_el_lobby_lleva_al_ranking_y_al_historial`, `::test_el_ranking_carga_el_top_y_el_puesto_propio`, `::test_el_ranking_vacio_avisa`, `::test_el_ranking_muestra_el_error_del_servidor` |

## US-20 Historial y estadísticas de partidas

**Criterios de aceptación:** el jugador puede consultar su historial de partidas; ve sus
estadísticas acumuladas (puntos, victorias, logros); solo se muestra lo del jugador autenticado.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-200 | El historial trae las partidas terminadas | Dos partidas terminadas y una en curso | `GET /historial` | Las dos terminadas, de la más nueva a la más vieja, con puesto, puntaje y jugadores | OK | I | `s/test_ranking_historial.py::test_el_historial_trae_las_partidas_terminadas_del_jugador` |
| CP-201 | Estadísticas acumuladas | Partidas y logros | `GET /historial` | Partidas, victorias, puntos, mejor puntaje y cantidad de logros | OK | I | `s/test_ranking_historial.py::test_el_historial_trae_las_estadisticas_acumuladas` |
| CP-202 | Cada jugador ve solo lo suyo | Partida de otro jugador; sin token | `GET /historial` | Historial vacío; 401 sin sesión | OK | I | `s/test_ranking_historial.py::test_cada_jugador_ve_solo_su_historial`, `::test_sin_sesion_no_hay_ranking_ni_historial` |
| CP-203 | La pantalla del historial | Lobby | Botón "Historial" | Cajas de estadísticas, logros desbloqueados y una línea por partida (en verde las ganadas) | OK | U | `c/test_ranking_historial.py::test_el_historial_carga_las_partidas_el_resumen_y_los_logros`, `::test_cada_partida_se_describe_en_una_linea`, `::test_el_historial_vacio_avisa` |

## US-28 Rol de administrador

**Criterios de aceptación:** solo una cuenta administradora accede a estas funciones y un jugador
recibe acceso denegado; el administrador consulta estadísticas globales; puede bloquear o
desbloquear la cuenta de un jugador.

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-204 | Un jugador recibe acceso denegado | Cuenta de jugador | Los 6 endpoints de `/admin` | 403 "Solo un administrador puede hacer esto"; sin sesión 401 | OK | I | `s/test_administrador.py::test_un_jugador_recibe_acceso_denegado`, `::test_sin_sesion_pide_iniciar_sesion` |
| CP-205 | Estadísticas globales | Usuarios y partidas | `GET /admin/estadisticas` | Usuarios, bloqueados, partidas jugadas y activas y mejores puntajes | OK | I | `s/test_administrador.py::test_el_admin_ve_las_estadisticas_globales`, `::test_el_admin_lista_los_usuarios`, `::test_el_admin_ve_las_partidas_activas` |
| CP-206 | Bloquear corta la sesión y el login | Jugador con sesión abierta | Bloquear y luego desbloquear | El token viejo da 401; el login da 423 hasta desbloquear | OK | I | `s/test_administrador.py::test_bloquear_corta_la_sesion_abierta_del_jugador`, `::test_una_cuenta_bloqueada_no_puede_entrar_hasta_que_la_desbloquean`, `::test_una_cuenta_bloqueada_tampoco_entra_con_google` |
| CP-207 | No se bloquea a un administrador ni a quien no existe | Dos admins | Bloquear a otro admin, a sí mismo y al id 9999 | 409, 409 y 404 | OK | I | `s/test_administrador.py::test_no_se_puede_bloquear_a_un_administrador`, `::test_bloquear_a_alguien_que_no_existe_da_404` |
| CP-208 | Cerrar partidas colgadas | Partida en curso con y sin motor | `POST /admin/partidas/{id}/cerrar` | Con motor termina con motivo `administrador`; sin motor queda `finalizada`; terminada o inexistente da 409 / 404 | OK | I | `s/test_administrador.py::test_cerrar_una_partida_en_curso_la_termina_en_el_motor`, `::test_cerrar_una_partida_sin_motor_la_marca_como_finalizada`, `::test_no_se_puede_cerrar_una_partida_terminada_o_que_no_existe`, `s/test_fin_de_partida.py::test_un_administrador_puede_cerrarla_antes` |
| CP-209 | La cuenta de admin se crea con el script | Base con o sin la cuenta | `python -m app.scripts.crear_admin` | Crea la cuenta verificada o promueve la existente; rechaza una contraseña débil; el login informa el `rol` | OK | I | `s/test_administrador.py::test_el_script_crea_la_cuenta_de_administrador_verificada`, `::test_el_script_promueve_una_cuenta_que_ya_existe`, `::test_el_script_rechaza_una_contrasena_debil`, `::test_el_login_dice_el_rol_de_la_cuenta` |
| CP-210 | Pantalla de administración | Sesión de admin | Lobby → "Administración"; bloquear, desbloquear, cerrar | El botón solo sirve con rol admin; las acciones llaman al servidor y recargan la lista | OK | U | `c/test_admin.py::test_el_boton_de_administracion_solo_sirve_para_un_admin`, `::test_bloquear_y_desbloquear_desde_la_lista`, `::test_cerrar_una_partida_colgada`, `::test_si_el_servidor_niega_el_acceso_se_muestra_el_motivo` |
| CP-211 | Administrar de punta a punta | Backend con la cuenta creada por el script | Entrar como admin, bloquear a un jugador conectado y cerrar su partida | El jugador queda fuera (401 en su próxima petición) y la partida desaparece de las activas | OK (demo 25/11) | A | Manual |

## Deuda técnica

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Tipo | Prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-212 | Crear y unirse toman al jugador del token | Jugadores con sesión | `POST /partidas` y `/unirse` con token; un `jugador_id` ajeno en el cuerpo | Se usa el jugador del token; sin sesión 401 | OK | I | `s/test_unirse_partidas.py::test_unirse_usa_el_jugador_del_token_y_no_el_del_cuerpo`, `::test_unirse_sin_sesion_da_401`, `s/test_partidas.py::test_post_partidas_sin_sesion_da_401`, `c/test_api_client.py::test_crear_partida_no_manda_el_creador` |
| CP-213 | Teclado del celular en los campos de texto | Navegador táctil (simulado) | Tocar un campo, cancelar, contraseña | Se escribe lo del cuadro del navegador; cancelar deja lo que había; la contraseña no se muestra; en escritorio no cambia nada | OK | U | `c/test_teclado_celular.py` (6 pruebas) |
| CP-214 | Escribir en el celular real | Juego en la nube abierto en un celular | Tocar usuario y contraseña en el login | Sale el teclado del celular y se puede iniciar sesión | OK (demo 25/11) | A | Manual |

## Cómo ejecutar los casos de aceptación

1. Levantar el backend (`docker compose up`) y crear el admin:
   `docker compose exec server python -m app.scripts.crear_admin --usuario admin --correo admin@reactor.cr`.
2. **CP-170 y CP-195:** abrir dos clientes (`python main.py` en dos terminales) con dos cuentas;
   uno crea la partida, el otro se une y el creador toca "Iniciar partida". Comparar los relojes,
   jugar hasta el final y revisar la ceremonia. Repetir la ceremonia desde el celular.
3. **CP-211:** con una partida en curso, entrar como admin, bloquear a uno de los jugadores y
   cerrar la partida desde "Partidas activas".
4. **CP-214:** abrir el juego publicado en un celular y escribir en el login.
5. Anotar fecha y resultado en la columna "Obtenido" y guardar capturas en `docs/pruebas/evidencias/`.
