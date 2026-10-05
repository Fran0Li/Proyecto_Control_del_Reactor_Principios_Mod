# Estrategia de ramas

Se usa un flujo basado en Git Flow simplificado.

| Rama | Para qué | Quién escribe |
| --- | --- | --- |
| `main` | Solo versiones entregadas al final de cada sprint | Merge desde `develop` al entregar |
| `develop` | Integración del sprint; siempre debe compilar y pasar el CI | Solo por Pull Request |
| `feature/US-XX-descripcion` | Una historia de usuario o tarea técnica | El responsable de la tarea |
| `fix/descripcion` | Corrección de un bug | Quien lo corrige |

## Flujo de trabajo

1. Actualizar `develop` (Fetch / Pull).
2. Crear la rama desde `develop`: `feature/US-01-registro`.
3. Hacer commits pequeños y frecuentes.
4. Publicar la rama y abrir un Pull Request hacia `develop`.
5. Otro integrante revisa y aprueba; el CI debe estar en verde.
6. Merge y borrar la rama.
7. Al cierre del sprint: Pull Request de `develop` a `main` y tag `sprint-2`.

## Mensajes de commit

Formato: `tipo(área): descripción AB#ID`

- `feat`: funcionalidad nueva.
- `fix`: corrección.
- `test`: pruebas.
- `docs`: documentación.
- `chore`: configuración, dependencias, CI.

Ejemplo: `feat(auth): valida correo duplicado en registro AB#45`

`AB#ID` vincula el commit con el work item de Azure Boards.
