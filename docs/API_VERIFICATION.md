# BluOS API Notes

Source of truth: [BluOS Custom Integration API v1.7](https://bluesoundprofessional.com/wp-content/uploads/2025/06/BluOS-Custom-Integration-API_v1.7.pdf) (also published at bluos.io). Verified against LAN players on firmware 4.16.x.

The BluOS API is device-specific. Each device has its own IP and responds independently on port 11000. There are no broadcast or multi-device endpoints — multi-device control is implemented client-side by iterating over discovered devices.

## Endpoints Used

| Category | Endpoints | Notes |
|----------|-----------|-------|
| Playback | `/Play`, `/Pause`, `/Stop`, `/Skip`, `/Back` | Per-device, safe to call concurrently |
| Queue | `/Playlist`, `/Clear`, `/Move?old=&new=` | Play queue (not `/Queue`) |
| Inputs | `/Settings?id=capture&schemaVersion=32`, `/Play?inputTypeIndex=` | Capture list + select (fw ≥ 4.2) |
| Bluetooth | read from capture settings `bluetoothAutoplay`; set `/audiomodes?bluetoothAutoplay=` | No `/AudioModes` GET in v1.7 |
| Presets | `/Presets`, `/Preset?id=` | Per-device presets |
| Sync | `/AddSlave`, `/RemoveSlave`, `/SyncStatus` | Primary controls runtime group |
| Status | `/Status` | Volume, state, track info |
| System | `/Reboot` (POST), `/diagnostics` | Per-device |

### Do not use (legacy / non-spec)

These return **404** on current firmware (verified 4.16.6): `/Queue`, `/AudioInputs`, `/AudioInput`, `/AudioModes`.

Legacy sync query forms (`/Sync?slave=`, `/Sync?remove=`) may still exist on some firmware versions, but current BluOS grouping uses **`AddSlave`** and **`RemoveSlave`** on the primary player.

## Play queue (`/Playlist`)

Song entries use elements `title`, `art` (artist), `alb` (album), `service`, plus attribute `id` (queue position). Prefer `/Playlist?start=0&end=N` for bounded responses.

## Capture inputs

`GET /Settings?id=capture&schemaVersion=32` returns a settings tree. Input sources are `menuGroup` nodes under `capture` (e.g. `capture-input0` = Analog). Bluetooth mode is the `setting` with `id="bluetoothAutoplay"` (`value` 0–3).

Select an input with `GET /Play?inputTypeIndex=<type>-<n>` where type is `analog`, `spdif`, `arc`, etc.

## SyncStatus XML

`GET /SyncStatus` describes both standalone players and runtime sync groups.

### Primary (group leader)

```xml
<SyncStatus group="Living Room Speakers+Kitchen Speakers" name="Living Room Speakers">
  <slave id="172.16.10.88" port="11000"/>
</SyncStatus>
```

### Slave (group follower)

```xml
<SyncStatus name="Kitchen Speakers">
  <master port="11000">172.16.10.174</master>
</SyncStatus>
```

Values may include a port suffix (`172.16.10.174:11000`). Clients should normalize to the host/IP portion.

## Sync Group Behavior

Runtime sync groups are managed through the **primary** device:

- **Create / add slave:** `GET http://<primary-ip>:11000/AddSlave?slave=<slave-ip>&port=11000`
- **Remove slave / ungroup:** `GET http://<primary-ip>:11000/RemoveSlave?slave=<slave-ip>&port=11000`
- Playback commands on the primary propagate to all slaves automatically
- Ungrouping must be sent to the **primary**, not broadcast to every player IP

## Implementation Pattern

1. Discover devices (mDNS/LSDP)
2. Filter by name pattern if specified
3. Call endpoint on each matching device's IP via `ThreadPoolExecutor`
4. Report per-device success/failure

For sync operations specifically:

1. Query `/SyncStatus` on each player to learn primary/slave relationships
2. Send `AddSlave` / `RemoveSlave` only to the primary IP
3. Use `sync list` to verify group state after changes
