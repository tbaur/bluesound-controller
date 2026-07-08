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
| Sync | `/AddSlave`, `/RemoveSlave`, `/SyncStatus` | Primary controls runtime group |
| Status | `/Status` | Volume, state, track info |
| System | `/Reboot` (POST), `/diagnostics` | Per-device |

Legacy sync endpoints (`/Sync?slave=`, `/Sync?remove=`) may still exist on some firmware versions, but current BluOS grouping uses **`AddSlave`** and **`RemoveSlave`** on the primary player.

## SyncStatus XML

`GET /SyncStatus` describes both standalone players and runtime sync groups.

### Primary (group leader)

```xml
<SyncStatus group="Living Room Speakers+Kitchen Speakers" name="Living Room Speakers">
  <slave id="172.16.10.88" port="11000"/>
</SyncStatus>
```

- `group` — combined group name advertised to clients such as Tidal Connect
- `slave` — one element per attached slave (`id` is the slave IP)

### Slave (group follower)

```xml
<SyncStatus name="Kitchen Speakers">
  <master port="11000">172.16.10.174</master>
</SyncStatus>
```

- `master` — IP of the primary (may appear as a child element or legacy root attribute)

Values may include a port suffix (`172.16.10.174:11000`). Clients should normalize to the host/IP portion.

## Sync Group Behavior

Runtime sync groups are managed through the **primary** device:

- **Create / add slave:** `GET http://<primary-ip>:11000/AddSlave?slave=<slave-ip>&port=11000`
- **Remove slave / ungroup:** `GET http://<primary-ip>:11000/RemoveSlave?slave=<slave-ip>&port=11000`
- Playback commands on the primary propagate to all slaves automatically
- Playback commands on a slave may break the sync group
- Ungrouping must be sent to the **primary**, not broadcast to every player IP

When controlling "all devices", synced devices may receive redundant commands — the API handles this gracefully.

## Implementation Pattern

1. Discover devices (mDNS/LSDP)
2. Filter by name pattern if specified
3. Call endpoint on each matching device's IP via `ThreadPoolExecutor`
4. Report per-device success/failure

Each device call is independent — one failure doesn't affect others.

For sync operations specifically:

1. Query `/SyncStatus` on each player to learn primary/slave relationships
2. Send `AddSlave` / `RemoveSlave` only to the primary IP
3. Use `sync list` to verify group state after changes
