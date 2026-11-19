# sony_bridge.exe (not built yet)

Fully automatic mode needs a small program that talks to the a7 IV through Sony's official
**Camera Remote SDK** (free, supports the a7 IV / ILCE-7M4). Download the SDK from Sony yourself
(you accept Sony's license), then build this bridge on your Windows PC, ideally with Claude Code
running there so it can test with the camera plugged in.

Camera: MENU -> Network -> PC Remote Function -> PC Remote: On, connection: USB.

## Contract (JSON lines on stdin/stdout, run as `sony_bridge.exe --serve`)
| Request | Reply |
|---|---|
| `{"cmd":"hello"}` | `{"ok":true}` (after connecting to the camera) |
| `{"cmd":"get"}` | `{"ok":true,"iso":400,"fnumber":4.0,"shutter":"1/50","kelvin":5600}` |
| `{"cmd":"set","iso":800,"fnumber":4.0,"shutter":"1/50","kelvin":3800}` | `{"ok":true}` |
| `{"cmd":"liveview","path":"C:\\...\\lv.jpg"}` | `{"ok":true}` (writes the live-view JPEG) |
| `{"cmd":"record","action":"start"}` / `"stop"` | `{"ok":true}` |
| `{"cmd":"bye"}` | `{"ok":true}` then exit |
| any failure | `{"ok":false,"error":"..."}` |

Start from the SDK's RemoteCli sample. Exposure control from the PC needs the priority-key
setting switched to PC Remote; ISO, F-number, shutter, white balance / colour temperature and
movie record are all SDK device properties or commands. Check names against your SDK version.
