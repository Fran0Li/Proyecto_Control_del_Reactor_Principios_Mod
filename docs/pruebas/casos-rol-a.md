# Casos de prueba — Rol A (US-01 a US-06)

Cada caso está automatizado con pytest; la columna **Prueba** dice dónde. Los del servidor corren
contra PostgreSQL en el CI y los del cliente con pygame sin ventana y el servidor simulado.

**Resultado obtenido:** todos pasan en el CI de la rama `feature/US-06-perfil`
([backend](https://github.com/Fran0Li/Proyecto_Control_del_Reactor_Principios_Mod/actions/runs/39344021989/job/118372161384),
[cliente](https://github.com/Fran0Li/Proyecto_Control_del_Reactor_Principios_Mod/actions/runs/39344021989/job/118372160867)).
Para repetirlos: `pytest` dentro de `server/` y de `client/`.

Archivos: `s/` = `server/tests/`, `c/` = `client/tests/`.

## US-01 Registro de usuario

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Prueba |
| --- | --- | --- | --- | --- | --- | --- |
| CP-01 | Registrar una cuenta | Correo y usuario libres | `luis`, `luis@mail.com`, `Secreta123` | 201, cuenta sin verificar | OK | `s/test_auth_api.py::test_registro_exitoso_devuelve_201_y_cuenta_sin_verificar` |
| CP-02 | No exponer la contraseña | — | Registro válido | La respuesta no trae contraseña ni hash | OK | `s/test_auth_api.py::test_la_respuesta_no_expone_la_contrasena` |
| CP-03 | Correo único (RN-01) | Ya existe `luis@mail.com` | Otro usuario con `LUIS@mail.com` | 409 | OK | `s/test_auth_api.py::test_correo_duplicado_devuelve_409` |
| CP-04 | Usuario único | Ya existe `luis` | `luis` con otro correo | 409 | OK | `s/test_auth_api.py::test_nombre_de_usuario_duplicado_devuelve_409` |
| CP-05 | Validar formato | — | Correo sin `@`, clave corta o sin números, usuario de 2 letras | 422 | OK | `s/test_auth_api.py::test_datos_invalidos_devuelven_422` |
| CP-06 | Contraseña guardada con hash (RNF-03) | — | `Secreta123` | Se guarda `scrypt$...`, nunca el texto | OK | `s/test_security.py`, `s/test_registro_service.py` |
| CP-07 | Validar en el cliente antes de enviar | — | Datos inválidos | Mensaje de error sin llamar al servidor | OK | `c/test_validaciones.py` |

## US-02 Verificación de correo

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Prueba |
| --- | --- | --- | --- | --- | --- | --- |
| CP-08 | Mandar el enlace al registrarse | — | Registro válido | Llega un correo con `/auth/verificar?token=` | OK | `s/test_verificacion.py::test_al_registrarse_llega_un_correo_con_el_enlace` |
| CP-09 | Verificar con el enlace | Cuenta sin verificar | Token del correo | 200, cuenta verificada | OK | `s/test_verificacion.py::test_abrir_el_enlace_verifica_la_cuenta` |
| CP-10 | Sin verificar no se entra | Cuenta sin verificar | Login correcto | 403; después de verificar, 200 | OK | `s/test_verificacion.py::test_despues_de_verificar_puede_iniciar_sesion` |
| CP-11 | Enlace de un solo uso | Enlace ya usado | Mismo token | 400 | OK | `s/test_verificacion.py::test_el_enlace_solo_sirve_una_vez` |
| CP-12 | Enlace vencido | Token con más de 24 h | Token vencido | 400 "Enlace vencido" | OK | `s/test_verificacion.py::test_un_enlace_vencido_no_sirve` |
| CP-13 | Reenviar el correo | Cuenta sin verificar | Correo de la cuenta | 202, enlace nuevo; el anterior ya no sirve | OK | `s/test_verificacion.py::test_reenviar_manda_otro_enlace_y_el_anterior_deja_de_servir` |
| CP-14 | No revelar cuentas | — | Correo no registrado | 202 y no se manda nada | OK | `s/test_verificacion.py::test_reenviar_a_un_correo_que_no_existe_responde_igual_y_no_manda_nada` |
| CP-15 | Falla del servicio de correo | SMTP caído | Registro válido | La cuenta se crea igual (201) | OK | `s/test_verificacion.py::test_si_falla_el_correo_la_cuenta_igual_se_crea` |
| CP-16 | Pantalla de verificación | — | Registro exitoso / login 403 | Pasa a "Verificá tu correo" con el correo listo para reenviar | OK | `c/test_verificar_correo.py` |

## US-03 Inicio de sesión

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Prueba |
| --- | --- | --- | --- | --- | --- | --- |
| CP-17 | Entrar con usuario o correo | Cuenta verificada | `luis` / `LUIS@Mail.com` + clave | 200 con token JWT | OK | `s/test_login.py::test_login_con_nombre_de_usuario_devuelve_el_token` |
| CP-18 | Clave incorrecta | Cuenta verificada | Clave equivocada | 401 "Usuario o contraseña incorrectos" | OK | `s/test_login.py::test_contrasena_incorrecta_devuelve_401` |
| CP-19 | Mismo mensaje si el usuario no existe | — | Usuario inexistente | 401 con el mismo mensaje | OK | `s/test_login.py::test_usuario_que_no_existe_da_el_mismo_mensaje` |
| CP-20 | Bloqueo por intentos | Cuenta verificada | 5 claves incorrectas | 423 por 15 min, ni con la clave correcta | OK | `s/test_login.py::test_se_bloquea_despues_de_varios_intentos_fallidos` |
| CP-21 | Fin del bloqueo | Bloqueo vencido | Clave correcta | 200 | OK | `s/test_login.py::test_cuando_vence_el_bloqueo_puede_entrar` |
| CP-22 | Rutas protegidas | — | Sin token / token alterado / vencido | 401 | OK | `s/test_login.py` (`test_yo_*`, `test_token_vencido_no_sirve`) |
| CP-23 | Sesión en el cliente | — | Login exitoso | Guarda el token y entra al lobby; "Cerrar sesión" la borra | OK | `c/test_login.py` |

## US-04 Inicio de sesión con Google

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Prueba |
| --- | --- | --- | --- | --- | --- | --- |
| CP-24 | Ir a Google | Credenciales configuradas | `/auth/google/iniciar?sesion=...` | Redirige a accounts.google.com con la sesión | OK | `s/test_google.py::test_iniciar_manda_a_google_con_la_sesion` |
| CP-25 | Cuenta nueva | Correo no registrado | Perfil de Google verificado | Cuenta verificada, sin contraseña, nombre a partir del correo | OK | `s/test_google.py::test_primera_vez_crea_la_cuenta_verificada` |
| CP-26 | Vincular con cuenta existente (RN-01) | Cuenta local verificada con ese correo | Perfil de Google | Misma cuenta, la clave anterior sigue sirviendo | OK | `s/test_google.py::test_si_ya_existe_una_cuenta_con_ese_correo_se_vincula` |
| CP-27 | Conflicto con cuenta sin verificar | Cuenta local sin verificar con ese correo | Perfil de Google | Se vincula y la clave anterior deja de servir | OK | `s/test_google.py::test_cuenta_sin_verificar_con_ese_correo_pierde_la_contrasena` |
| CP-28 | Correo no verificado en Google | — | Perfil con `email_verified=false` | 400, no se crea la cuenta | OK | `s/test_google.py::test_correo_sin_verificar_en_google_no_entra` |
| CP-29 | El jugador cancela | — | Callback con `error=access_denied` | 400 "Se canceló..." | OK | `s/test_google.py::test_si_el_jugador_cancela_en_google` |
| CP-30 | Resultado de un solo uso | Login terminado | Pedir el resultado dos veces | 200 la primera, 202 la segunda | OK | `s/test_google.py::test_el_resultado_se_entrega_una_sola_vez` |
| CP-31 | Botón en el cliente | — | Clic en "Entrar con Google" | Abre el navegador y entra al lobby cuando termina | OK | `c/test_login_google.py` |

## US-05 Recuperación de contraseña

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Prueba |
| --- | --- | --- | --- | --- | --- | --- |
| CP-32 | Pedir el código | Cuenta existente | Correo | 202, llega un código de 8 caracteres | OK | `s/test_recuperacion.py::test_pedir_recuperacion_manda_un_codigo_al_correo` |
| CP-33 | No revelar cuentas | — | Correo no registrado | 202 y no se manda nada | OK | `s/test_recuperacion.py::test_correo_que_no_existe_responde_igual_y_no_manda_nada` |
| CP-34 | Cambiar la contraseña | Código pedido | Código + `Nueva12345` | 200; entra con la nueva y no con la vieja | OK | `s/test_recuperacion.py::test_con_el_codigo_se_cambia_la_contrasena` |
| CP-35 | Código de un solo uso | Código ya usado | Mismo código | 400 | OK | `s/test_recuperacion.py::test_el_codigo_solo_sirve_una_vez` |
| CP-36 | Código vencido | Código con más de 15 min | Código | 400 "El código venció..." | OK | `s/test_recuperacion.py::test_un_codigo_vencido_no_sirve` |
| CP-37 | Código de otra cuenta | Dos cuentas | Código de Ana con el correo de Luis | 400, la clave de Luis no cambia | OK | `s/test_recuperacion.py::test_el_codigo_de_otra_cuenta_no_sirve` |
| CP-38 | Invalidar sesiones | Sesión abierta | Cambio de contraseña | El token anterior da 401 | OK | `s/test_recuperacion.py::test_cambiar_la_contrasena_cierra_las_sesiones_abiertas` |
| CP-39 | Pantallas del cliente | — | Correo, código y clave nueva | Paso 1 y paso 2; valida que coincidan las claves | OK | `c/test_recuperar.py` |

## US-06 Edición del perfil

| ID | Objetivo | Precondiciones | Entrada | Resultado esperado | Obtenido | Prueba |
| --- | --- | --- | --- | --- | --- | --- |
| CP-40 | Perfil protegido | — | Sin token | 401 | OK | `s/test_perfil.py::test_sin_sesion_no_se_puede_ver_el_perfil` |
| CP-41 | Ver estadísticas | 3 partidas, 2 victorias, 850 puntos | Token | Esos valores en el perfil | OK | `s/test_perfil.py::test_el_perfil_muestra_las_estadisticas` |
| CP-42 | Editar descripción y avatar | Sesión iniciada | `descripcion`, `avatar=verde` | 200 y quedan guardados | OK | `s/test_perfil.py::test_editar_descripcion_y_avatar` |
| CP-43 | Cambiar nombre de usuario | Sesión iniciada | `luis_07` | 200 y se puede entrar con el nombre nuevo | OK | `s/test_perfil.py::test_cambiar_el_nombre_de_usuario` |
| CP-44 | Nombre ocupado | Existe `ana` | `nombre_usuario=ana` | 409, no cambia | OK | `s/test_perfil.py::test_no_se_puede_usar_un_nombre_ocupado` |
| CP-45 | Datos inválidos | — | Avatar inexistente, descripción de 201 caracteres | 422 | OK | `s/test_perfil.py::test_datos_invalidos_devuelven_422` |
| CP-46 | Pantalla de perfil | Sesión iniciada | Abrir, cambiar avatar, guardar | Carga, guarda y actualiza el nombre de la sesión | OK | `c/test_perfil.py` |
