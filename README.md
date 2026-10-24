# pendant-selfhost

Fork de [sdelcore/pendant-cli](https://github.com/sdelcore/pendant-cli), orientado a un objetivo concreto:
**reaprovechar un Limitless Pendant que se ha quedado sin servicio** tras la adquisición de Limitless.ai por
Meta, y sustituir la nube del fabricante por un servidor propio (self-hosted).

> **Estado: experimental.** El código base (CLI BLE) viene del proyecto original y está documentado como
> funcional contra un dispositivo real. Todo lo que aparece bajo [Roadmap](#roadmap) todavía **no está
> implementado ni probado** en este fork.

## Objetivo

Tener un pipeline privado de *lifelogging* con el hardware que ya tengo:

```
Pendant ──BLE──> Gateway (Raspberry Pi / mini PC / Mac con BlueZ o CoreBluetooth)
                    │  sync por lotes + decodificación Opus
                    ▼
              faster-whisper / whisper.cpp ──> diarización ──> LLM local (Ollama)
                    ▼
              almacenamiento + búsqueda (lifelogs propios)
```

El Pendant graba en su flash interna, así que no hace falta streaming continuo: el gateway sincroniza
cuando el dispositivo está al alcance.

## Qué hay hoy (heredado del upstream)

- Emparejamiento y gestión de conexión BLE (`bluetoothctl` / D-Bus; backend `bleak` alternativo).
- Descarga por lotes de las grabaciones almacenadas en flash.
- Decodificación de Opus crudo a WAV.
- Estado e información del dispositivo (batería, grabación, almacenamiento, firmware).
- **Inyección de clave pública X25519** para que las grabaciones nuevas se cifren con *tu* clave.
- Comandos de ajustes: LED, umbral VAD, nombre del dispositivo y credenciales Wi-Fi
  (`pendant settings ...`; ver nota sobre Wi-Fi más abajo).
- Escucha de mensajes (`pendant listen`) y borrado de almacenamiento (`pendant clear`).

## Qué sabemos y qué no

**Confirmado por el upstream** (protocolo obtenido descompilando la app Android de Limitless v2.1.6):

| Tema | Detalle |
|------|---------|
| Transporte | Protocol Buffers sobre características GATT de BLE |
| Bonding | El dispositivo ignora todo comando hasta estar *bonded* (Just Works, sin I/O). Se recomienda `bluetoothctl`; `bleak` no empareja bien |
| Audio | Opus, 16 kHz, mono, frames de ~60 ms concatenados **sin** contenedor Ogg |
| Streams | El protobuf prevé micrófono omni, direccional y beamforming, y dirección de llegada del sonido |
| Metadatos | Los chunks incluyen batería, botón, Wi-Fi, BLE, IMU, CPU y almacenamiento |
| Cifrado | X25519 + ChaCha20-Poly1305. Por defecto con la clave del servidor de Limitless; se puede inyectar la propia |
| Conexión | Exclusiva: la app de Limitless no puede estar conectada a la vez |

**Limitaciones y lagunas conocidas:**

- Iniciar/parar grabación por BLE puede no funcionar (parece depender solo del botón físico).
- Algunos chunks solo traen metadatos, sin audio.
- **Wi-Fi:** el protobuf define `AddWifiCredentials`, `ConnectToWifi` y `DisconnectWifi`, y el CLI los expone,
  pero **no hay documentación de a qué endpoint sube el dispositivo ni con qué protocolo**. Reapuntar la
  sincronización Wi-Fi a un servidor propio es una incógnita abierta (y una línea de investigación).
- No hay información confirmada del microcontrolador, ni firmware abierto, ni forma conocida de flashearlo.
  El enfoque es reutilizar el dispositivo **tal cual**, no reprogramarlo.
- Proyecto upstream pequeño (2 commits). Toda la documentación procede de una única fuente.

## Aviso crítico: grabaciones existentes

Las grabaciones que el Pendant ya tenga almacenadas están cifradas con la clave del servidor de Limitless y
**no se pueden descifrar sin su clave privada**. Si quedan datos importantes en el dispositivo:

1. Expórtalos por los canales oficiales mientras sigan disponibles.
2. Haz `pendant crypto keygen` + `pendant crypto setkey` **antes** de que el dispositivo se quede sin
   servicio, para que todo lo nuevo se cifre con tu clave.

Haz copia de seguridad de `keys/`: perder la clave privada equivale a perder las grabaciones.

## Requisitos

- Linux con BlueZ (`bluetoothctl`) — es el único entorno soportado por el upstream.
- Python 3.11 o 3.12 (según `pyproject.toml`).
- [uv](https://docs.astral.sh/uv/) o Nix (recomendado por el upstream).
- Dependencias del sistema para Opus (`libopus`) y D-Bus/GObject.

## Quick Start

```bash
# Entorno (Nix) — o `uv sync` si prefieres uv
nix develop

# Dirección del dispositivo
export PENDANT_ADDRESS="XX:XX:XX:XX:XX:XX"

pendant bt scan             # localizar el Pendant
pendant bt pair             # emparejar (solo la primera vez)
pendant status              # batería, grabación, almacenamiento

pendant crypto keygen       # tu par X25519 (se guarda en keys/)
pendant crypto setkey       # enviar clave pública al dispositivo

pendant download -d         # descargar y decodificar a WAV
```

## Comandos

```bash
# Dispositivo
pendant status              # Batería, estado de grabación, almacenamiento
pendant info                # Firmware, hardware, número de serie
pendant listen              # Escuchar mensajes del dispositivo

# Audio
pendant download            # Descargar grabaciones
pendant download -d         # Descargar y decodificar a WAV
pendant decode file.opus    # Opus crudo -> WAV
pendant record              # Iniciar grabación (puede no funcionar por BLE)
pendant stop                # Parar grabación (puede no funcionar por BLE)
pendant clear               # Borrar almacenamiento del dispositivo

# Bluetooth
pendant bt scan | pair | connect | disconnect | status

# Cifrado
pendant crypto keygen       # Generar par X25519
pendant crypto setkey       # Enviar clave pública al dispositivo

# Ajustes
pendant settings led <0|1>
pendant settings brightness <0-100>
pendant settings vad <0.0-1.0>
pendant settings name <nombre>
pendant settings wifi-add <ssid> <password>
pendant settings wifi-connect <ssid>
pendant settings wifi-disconnect

# Depuración
pendant explore             # Explorar servicios GATT
pendant debug               # Descarga con inspección de flash pages
```

> `pendant clear` borra datos del dispositivo. No lo uses hasta haber confirmado que tienes copia de lo que
> te interesa.

## Roadmap

Nada de esto está implementado todavía.

- [ ] **Verificar el hardware real**: bonding, `status`, `download` y `setkey` contra mi unidad.
- [ ] **Gateway de sincronización**: demonio que detecta el Pendant al alcance, sincroniza por lotes, guarda
      los WAV con su timestamp y borra del dispositivo solo tras confirmar la copia.
- [ ] **Transcripción local**: faster-whisper / whisper.cpp sobre los WAV.
- [ ] **Diarización** (quién habla) y uso de `degree_of_arrival` como pista adicional.
- [ ] **Resumen y extracción** con LLM local (Ollama); modelo configurable por variable de entorno.
- [ ] **Almacenamiento y búsqueda** de lifelogs (SQLite/Postgres + búsqueda de texto y semántica).
- [ ] **Investigar el canal Wi-Fi**: capturar el tráfico del dispositivo en una red controlada para ver a
      qué host y con qué protocolo sube los datos, y si es reapuntable (DNS local / servidor propio).
- [ ] Soporte de gateway en macOS/otros (hoy solo Linux/BlueZ).
- [ ] Streaming en tiempo real (`real_time_mode_enabled` existe en el protobuf, pero el CLI solo usa
      el modo por lotes).

## Documentación técnica

- [PROTOCOL.md](PROTOCOL.md) — protocolo BLE completo (framing, flash pages, audio, cifrado, comandos).
- `proto/pendant.proto` — definiciones protobuf derivadas de la app Android descompilada.
- [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) — guía para agentes de código (heredado del upstream).

### Formato de audio

| Propiedad | Valor |
|-----------|-------|
| Códec | Opus |
| Frecuencia | 16000 Hz |
| Canales | Mono |
| Profundidad | 16 bits |
| Frame | ~960 muestras (60 ms) |
| Contenedor | Ninguno (frames crudos concatenados) |

ffmpeg y VLC no reproducen este formato directamente; usa `pendant decode`.

### Características BLE

| UUID | Uso | Dirección |
|------|-----|-----------|
| `632de002-604c-446b-a80f-7963e950f3fb` | Control | Teléfono → Pendant (Write) |
| `632de003-604c-446b-a80f-7963e950f3fb` | Datos | Pendant → Teléfono (Notify) |

## Solución de problemas

- **El dispositivo no responde:** comprueba que está emparejado **y** bonded (`bluetoothctl info $PENDANT_ADDRESS`),
  toca el Pendant para despertarlo; como último recurso, reset de fábrica (mantener el botón 10+ s).
- **Falla la conexión / "Device not found":** asegúrate de que no está conectado al teléfono (conexión
  exclusiva), que no está dormido y reintenta `pendant bt scan`; si persiste, elimina el emparejamiento y
  repite `pendant bt pair`.
- **Sin audio:** `pendant status`; si el almacenamiento está al 0 %, no hay nada que descargar.
  `pendant debug` ayuda a inspeccionar las flash pages.
- **El audio no suena:** es Opus crudo; usa `pendant decode`.

## Desarrollo

```bash
protoc --python_out=proto proto/pendant.proto   # regenerar protobuf
uv run pytest                                    # tests
```

```
src/pendant/
  cli.py             - Entrada Click
  commands/          - Implementación de comandos CLI
  core/              - Protocolo, clientes BLE (D-Bus/bleak), decodificador Opus
proto/               - pendant.proto (pendant_pb2.py generado, no versionado)
keys/                - Claves de cifrado generadas (no versionado; haz backup)
PROTOCOL.md          - Documentación del protocolo
```

## Origen y licencia

Fork de [sdelcore/pendant-cli](https://github.com/sdelcore/pendant-cli). El remoto `upstream` apunta al
proyecto original para poder traer sus cambios.

El upstream **no incluye fichero de licencia**; su README indica *uso personal / investigación únicamente*,
porque el protocolo se obtuvo por ingeniería inversa de software propietario. Este fork mantiene esa misma
restricción: **uso personal y de investigación sobre hardware propio**. Antes de redistribuir o publicar
derivados conviene contactar con el autor original para aclarar la licencia.

Este proyecto no está afiliado a Limitless ni a Meta.
