# Feature Proposals Based on BluOS API v1.7

After reviewing the [BluOS Custom Integration API v1.7](https://content-bluesound-com.s3.amazonaws.com/uploads/BluOS-Custom-Integration-API_v1.7.pdf), here are recommended features to add to the project:

## High Priority Features

### 1. **LSDP (Lenbrook Service Discovery Protocol) Support** ⭐⭐⭐ ✅ IMPLEMENTED
**Why**: The API documentation notes that mDNS is unreliable on many home networks, leading to product returns. LSDP uses UDP broadcast on port 11430 and is more reliable.

**Implementation Status**: ✅ **COMPLETE**
- ✅ LSDP discovery implemented as alternative/fallback to mDNS
- ✅ UDP broadcast on port 11430
- ✅ LSDP packet format parsing (Query, Announce, Delete messages)
- ✅ Support for Class IDs: 0x0001 (BluOS Player), 0x0002 (BluOS Server), 0x0008 (BluOS Hub)
- ✅ Configurable discovery method (mdns, lsdp, or both)
- ✅ Automatic fallback (mDNS → LSDP if no devices found)

**Benefits Achieved**:
- ✅ More reliable device discovery
- ✅ Better for networks with multicast issues
- ✅ Reduces "no devices found" errors

**Files**: `lsdp.py`, `controller.py`

### 2. **Playback Control Commands** ⭐⭐⭐ ✅ IMPLEMENTED
**Previous State**: Only had `pause` command

**Current State**: ✅ **COMPLETE** - All playback controls implemented

**Implemented Commands**:
- ✅ `play` - Resume playback
- ✅ `skip` - Skip to next track
- ✅ `previous` - Go to previous track
- ✅ `stop` - Stop playback
- ✅ `toggle` - Toggle play/pause state

**API Endpoints Used**:
- ✅ `/Play` - Start/resume playback
- ✅ `/Skip` - Skip to next track
- ✅ `/Back` - Go to previous track
- ✅ `/Stop` - Stop playback

**Usage** (as implemented):
```bash
bluesound-controller play [name]
bluesound-controller skip [name]
bluesound-controller previous [name]
bluesound-controller stop [name]
bluesound-controller toggle [name]
```

**Files**: `controller.py`, `cli.py`, `main.py`

### 3. **Queue Management** ⭐⭐ ✅ IMPLEMENTED
**Status**: ✅ **COMPLETE** - Queue management fully implemented

**Implemented Features**:
- ✅ View current queue (with track details)
- ✅ Clear queue
- ✅ Move track in queue (reorder)
- ⚠️ Remove specific track: Not implemented (can be added if needed)

**API Endpoints Used**:
- ✅ `/Queue` - Get queue information
- ✅ `/Queue?clear=1` - Clear queue
- ✅ `/Queue?move=<index>&to=<index>` - Move track

**Usage** (as implemented):
```bash
bluesound-controller queue [name]          # Show queue
bluesound-controller queue clear [name]    # Clear queue
bluesound-controller queue move 3 1 [name] # Move track 3 to position 1
```

**Files**: `controller.py`, `cli.py`

### 4. **Input Source Selection** ⭐⭐ ✅ IMPLEMENTED
**Status**: ✅ **COMPLETE** - Input selection fully implemented

**Implemented Features**:
- ✅ List available inputs (with current selection indicator)
- ✅ Switch to specific input (Bluetooth, Optical, USB, etc.)
- ✅ Show current input (highlighted in list)

**API Endpoints Used**:
- ✅ `/AudioInputs` - List available inputs
- ✅ `/AudioInput?input=<name>` - Switch input

**Usage** (as implemented):
```bash
bluesound-controller inputs [name]              # List inputs
bluesound-controller inputs "Bluetooth" [name]   # Switch to Bluetooth
bluesound-controller inputs "Optical 1" [name]  # Switch to Optical
```

**Files**: `controller.py`, `cli.py`

### 5. **Bluetooth Mode Control** ⭐⭐ ✅ IMPLEMENTED
**Status**: ✅ **COMPLETE** - Bluetooth mode control fully implemented

**Implemented Features**:
- ✅ Set Bluetooth mode (Manual, Automatic, Guest, Disabled)
- ✅ Show current Bluetooth mode

**API Endpoint Used**:
- ✅ `/AudioModes` - Get current mode
- ✅ `/audiomodes?bluetoothAutoplay=<value>` (0=Manual, 1=Automatic, 2=Guest, 3=Disabled)

**Usage** (as implemented):
```bash
bluesound-controller bluetooth [name]            # Show current mode
bluesound-controller bluetooth manual [name]     # Set to manual
bluesound-controller bluetooth auto [name]       # Set to automatic
bluesound-controller bluetooth guest [name]      # Set to guest mode
bluesound-controller bluetooth disable [name]     # Disable Bluetooth
```

**Files**: `controller.py`, `cli.py`

## Medium Priority Features

### 6. **Soft Reboot Option** ⭐ ✅ IMPLEMENTED
**Previous State**: Only had hard reboot

**Current State**: ✅ **COMPLETE** - Soft reboot option implemented

**Implementation**:
- ✅ Soft reboot option via `--soft` flag
- ✅ Hard reboot remains default

**API Endpoint Used**:
- ✅ `/Reboot` (POST) - Hard reboot
- ✅ `/Reboot?soft=1` (POST) - Soft reboot

**Usage** (as implemented):
```bash
bluesound-controller reboot --soft [name]    # Soft reboot (preferred)
bluesound-controller reboot [name]           # Hard reboot
```

**Files**: `controller.py`, `cli.py`, `main.py`

### 7. **Volume Up/Down Commands** ⭐
**Current**: Has `volume +5` and `volume -5`, but could add dedicated commands

**Add**:
```bash
bluesound-controller volup [amount] [name]    # Volume up (default +5)
bluesound-controller voldown [amount] [name]  # Volume down (default -5)
```

### 8. **Preset Management** ⭐ ✅ IMPLEMENTED
**Status**: ✅ **COMPLETE** - Preset management implemented

**Implemented Features**:
- ✅ List presets (with names and IDs)
- ✅ Play preset
- ⚠️ Save current state as preset: Not implemented (not in BluOS API)

**API Endpoints Used**:
- ✅ `/Presets` - List presets
- ✅ `/Preset?id=<id>` - Play preset

**Usage** (as implemented):
```bash
bluesound-controller presets [name]        # List presets
bluesound-controller presets 1 [name]      # Play preset 1
```

**Files**: `controller.py`, `cli.py`

### 9. **Sync Group Management** ⭐ ✅ IMPLEMENTED
**Status**: ✅ **COMPLETE** - Sync group management fully implemented

**Implemented Features**:
- ✅ Create sync groups (master + slaves)
- ✅ Remove devices from groups (break sync)
- ✅ List sync groups (shows master/slave relationships)
- ✅ Multi-slave support (comma-separated)

**API Endpoints Used**:
- ✅ `/SyncStatus` - Get sync status (already used in status)
- ✅ `/Sync?slave=<ip>` - Add slave to group
- ✅ `/Sync?remove=<ip>` - Remove from group

**Usage** (as implemented):
```bash
bluesound-controller sync create "Living Room" "Kitchen,Bedroom"  # Create group
bluesound-controller sync break "Living Room"                     # Break group
bluesound-controller sync list                                     # List all groups
```

**Files**: `controller.py`, `cli.py`

### 10. **Enhanced Status Information** ⭐
**Add to status output**:
- Current input source
- Bluetooth mode
- Queue length
- Preset information
- Sync group details

## Low Priority / Nice to Have

### 11. **Doorbell Chime** (if supported)
**API Endpoint**: `/DoorbellChime`

**Usage**:
```bash
bluesound-controller chime [name]
```

### 12. **Stream URL Playback**
**Features**:
- Play custom stream URL
- Play from file path

**API Endpoint**:
- `/Play?url=<url>` - Play stream URL

**Usage**:
```bash
bluesound-controller play-url "http://stream.example.com/audio.mp3" [name]
```

### 13. **Repeat and Shuffle Controls**
**API Endpoints**:
- `/Repeat?state=<value>` (0=off, 1=all, 2=one)
- `/Shuffle?state=<value>` (0=off, 1=on)

**Usage**:
```bash
bluesound-controller repeat off|all|one [name]
bluesound-controller shuffle on|off [name]
```

## Implementation Status (v1.0.0)

### ✅ Phase 1 (Core Playback) - COMPLETE
1. ✅ LSDP discovery support - **DONE**
2. ✅ Playback controls (play, skip, previous, stop, toggle) - **DONE**
3. ✅ Enhanced status with input/source info - **DONE**

### ✅ Phase 2 (Advanced Control) - COMPLETE
4. ✅ Queue management - **DONE**
5. ✅ Input source selection - **DONE**
6. ✅ Bluetooth mode control - **DONE**
7. ✅ Soft reboot option - **DONE**

### ✅ Phase 3 (Nice to Have) - MOSTLY COMPLETE
8. ✅ Preset management - **DONE**
9. ✅ Sync group management - **DONE**
10. ⚠️ Repeat/shuffle controls - **NOT IMPLEMENTED** (low priority, can be added if needed)

### Summary
- **Implemented**: 9 out of 10 high/medium priority features
- **Status**: All critical features complete, ready for production use
- **Remaining**: Optional enhancements (repeat/shuffle, stream URL playback, doorbell chime)

## Technical Considerations

### LSDP Implementation
- Use Python's `socket` module for UDP broadcast
- Parse binary packet format (big-endian)
- Handle Announce, Query, Delete messages
- Cache discovered devices with Node ID as key
- Implement timing as per spec (7 startup packets, 57s+random for announces)

### API Endpoint Pattern
All commands follow pattern: `http://<ip>:11000/<Endpoint>?<params>`

### Error Handling
- Handle network timeouts gracefully
- Validate responses
- Provide clear error messages

### Testing
- Mock LSDP packet generation
- Test all new playback commands
- Integration tests for queue/input management

## Benefits Summary

- **Better Discovery**: LSDP more reliable than mDNS
- **Full Playback Control**: Complete control over playback
- **Better User Experience**: More intuitive commands
- **Advanced Features**: Queue, inputs, Bluetooth control
- **Professional Tool**: Matches capabilities of official apps

