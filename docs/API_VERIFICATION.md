# BluOS API Notes

## Device Architecture

The BluOS API (v1.7) is device-specific. Each device has its own IP and responds independently on port 11000. There are no broadcast or multi-device endpoints — multi-device control is implemented client-side by iterating over discovered devices.

## Endpoints Used

| Category | Endpoints | Notes |
|----------|-----------|-------|
| Playback | `/Play`, `/Pause`, `/Stop`, `/Skip`, `/Back` | Per-device, safe to call concurrently |
| Queue | `/Queue`, `/Queue?clear=1`, `/Queue?move=<from>&to=<to>` | Per-device queues |
| Inputs | `/AudioInputs`, `/AudioInput?input=<name>` | Per-device input selection |
| Bluetooth | `/AudioModes`, `/audiomodes?bluetoothAutoplay=<mode>` | Per-device config |
| Presets | `/Presets`, `/Preset?id=<id>` | Per-device presets |
| Sync | `/Sync?slave=<ip>`, `/Sync?remove=<ip>`, `/SyncStatus` | Master controls group |
| Status | `/Status` | Volume, state, track info |
| System | `/Reboot` (POST), `/diagnostics` | Per-device |

## Sync Group Behavior

Sync groups are managed through the master device:
- Playback commands on the master propagate to all slaves automatically
- Playback commands on a slave may break the sync group
- When controlling "all devices", synced devices may receive redundant commands — the API handles this gracefully

## Implementation Pattern

1. Discover devices (mDNS/LSDP)
2. Filter by name pattern if specified
3. Call endpoint on each matching device's IP via `ThreadPoolExecutor`
4. Report per-device success/failure

Each device call is independent — one failure doesn't affect others.
