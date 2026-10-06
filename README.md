# agy-auto-accept

> **Auto-aceptador inteligente de peticiones de confirmación y aprobación para el agente AGY (Gemini CLI / Antigravity) dentro de [Herdr](https://github.com/).**

---

## 📌 ¿Por qué existe este proyecto?

Al trabajar con múltiples agentes de código en **Herdr** (como Claude, Codex y AGY), el agente **AGY** frecuentemente solicita confirmación antes de ejecutar comandos o editar archivos mediante un selector interactivo en terminal:

```text
Allow creation of this file?
> 1. Yes, allow creation
  2. No, deny creation
...
esc to cancel
```

A diferencia de otros agentes, **Herdr** no marca a AGY en estado `"blocked"` ante este diálogo porque su analizador busca frases genéricas en inglés (por ejemplo, `requesting permission for:`). Como resultado, AGY queda a la espera de interacción manual del usuario.

**`agy-auto-accept`** resuelve este problema:
1. Inspecciona en tiempo real la terminal del panel donde corre AGY.
2. Reconoce mediante expresiones regulares el patrón interactivo de confirmación (`> 1. Yes` y `esc to cancel`).
3. Envía automáticamente la pulsación de tecla `Enter` a través del CLI de Herdr para autorizar la acción de forma inmediata.
4. Mantiene un seguro interno (`waiting_clear`) para evitar pulsaciones duplicadas mientras el diálogo desaparece.

---

## 🚀 Requisitos

- **Python 3.8 o superior**.
- **Herdr CLI** instalado y disponible en el `PATH` del sistema (el comando `herdr` debe ser ejecutable desde la terminal).
- No requiere dependencias externas de `pip` (utiliza únicamente la librería estándar de Python).

---

## 📦 Instalación

Clona el repositorio en tu máquina:

```bash
git clone https://github.com/JsGuaman/agy-auto-accept.git
cd agy-auto-accept
```

---

## 🛠️ Instrucciones de Uso

### 1. Auto-detección (Recomendado)

Si tienes una sesión de AGY corriendo en Herdr, ejecuta el script sin argumentos. Detectará automáticamente el panel de AGY (dando prioridad al panel que tenga el foco):

```bash
python agy_auto_accept.py
```

**Salida de ejemplo:**
```text
[2026-10-06 15:05:00] Buscando agente AGY activo en Herdr...
[2026-10-06 15:05:01] Agente AGY detectado automaticamente en panel: w4:p6
[2026-10-06 15:05:01] Iniciando vigilancia en 'w4:p6' cada 1.5s. Presiona Ctrl+C para detener.
[2026-10-06 15:05:32] Dialogo de aprobacion detectado (estado Herdr: working). Enviando Enter...
[2026-10-06 15:05:32] Aprobacion enviada exitosamente (Enter sobre '1. Yes').
[2026-10-06 15:05:34] Dialogo resuelto. Detector rearmado.
```

---

### 2. Listar todos los agentes activos en Herdr

Para ver qué paneles y agentes tienes actualmente abiertos en Herdr:

```bash
python agy_auto_accept.py --list
```

**Salida de ejemplo:**
```text
=== AGENTES ACTIVOS EN HERDR ===
PANE ID    AGENTE       ESTADO     FOCO   DIR / TITULO
---------------------------------------------------------------------------
w3:p1V     codex        idle       No     C:\Users\...\GitHub
w4:p6      agy          working    Si     C:\Users\...\MALTEF-PRO
w4:pK      opencode     idle       No     C:\Users\...\MALTEF-PRO
wE:p1      agy          idle       No     C:\Users\...\MAGIC_AI
---------------------------------------------------------------------------
```

---

### 3. Vigilar un panel específico

Si tienes múltiples instancias de AGY o deseas vigilar un panel fijo específico:

```bash
python agy_auto_accept.py --target w4:p6
```

---

### 4. Ajustar el intervalo de sondeo y heartbeat

Puedes personalizar la frecuencia de revisión (en segundos) y la frecuencia del mensaje de estado periódico (*heartbeat*):

```bash
# Revisar cada 0.8 segundos y reportar estado cada 30 segundos
python agy_auto_accept.py --target w4:p6 --interval 0.8 --heartbeat 30
```

Para desactivar los mensajes periódicos de heartbeat, pasa `--heartbeat 0`:

```bash
python agy_auto_accept.py --heartbeat 0
```

---

## ⚙️ Parámetros de la Línea de Comandos

| Parámetro | Valor por defecto | Descripción |
|---|---|---|
| `--target` | `auto` | ID del panel de Herdr a vigilar (ej. `w4:p6`). Con `auto`, se detecta automáticamente. |
| `--interval` | `1.5` | Tiempo en segundos entre cada comprobación de la pantalla de terminal. |
| `--heartbeat` | `60.0` | Intervalo en segundos para mostrar mensajes de confirmación de vida en consola (`0` para deshabilitar). |
| `--list` | - | Imprime la tabla con todos los agentes activos en Herdr y sus pane IDs, luego finaliza. |
| `-h`, `--help` | - | Muestra la ayuda en pantalla con todas las opciones disponibles. |

---

## 🛑 Detener la ejecución

Para detener el watcher, simplemente pulsa `Ctrl + C` en la terminal donde se esté ejecutando. El script finaliza de forma limpia sin dejar procesos colgados.

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.
