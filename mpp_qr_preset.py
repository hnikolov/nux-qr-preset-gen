#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NUX Mighty Plug Pro (MP-3) QR Preset Builder
--------------------------------------------

How to use
----------
1) Paste your baseline `nux://MightyAmp:...` link into BASELINE_LINK below, or
   set it at runtime (e.g., from a file).
2) Edit the example under `if __name__ == "__main__":` to set modules/params.
3) Run:
      python mpp_qr_preset.py
   It will print the new link, and if 'qrcode' is installed, also write a PNG.

Notes
-----
- The builder always preserves all unmapped bytes from the baseline.
- All values are clipped to [0, 100] where appropriate.
"""

from __future__ import annotations
import base64
import math
from typing import Optional, Tuple
import qrcode  # pip install qrcode[pil]

# =========================
# Constants & Byte Mapping
# =========================

PAYLOAD_LEN = 115

# EQ flags (byte 6)
FLAG_EQ_MODEL_10B = 0x02 # 1=10-band, 0=6-band

# Headers (bypass bits + model id in low bits)
HDR_CMP  = 3
HDR_EFX  = 4
HDR_AMP  = 5
HDR_EQ   = 6
HDR_GATE = 7
HDR_MOD  = 8
HDR_DLY  = 9
HDR_RVB  = 10
HDR_IR   = 11
HDR_BYPASS = 0x40

VOL = 86

# ===========================================
# Models (1-based indices unless noted)
# ===========================================
CMP_MODEL = {
    "rose": 1,
    "k-comp": 2,
    "studio": 3,
}

EFX_MODEL = {
    "distortion+": 1,
    "rc boost": 2,
    "ac boost": 3,
    "dist one": 4,
    "t screamer": 5,
    "blues drive": 6,
    "morning drive": 7,
    "eat dist": 8,
    "red dist": 9,
    "crunch": 10,
    "muff fuzz": 11,
    "katana": 12,
    "st singer": 13,
    "touch wah": 14,
}

AMP_MODEL = {
    "jazz clean": 1,
    "deluxe rvb": 2,
    "bass mate": 3,
    "tweedy": 4,
    "tween reverb": 5,
    "hiwire": 6,
    "cali crunch": 7,
    "class a15": 8,
    "class a30": 9,
    "plexi 100": 10,
    "plexi 45": 11,
    "brit 800": 12,
    "1987x50": 13,
    "slo 100": 14,
    "fireman hbe": 15,
    "dual rect": 16,
    "die vh4": 17,
    "vibro king": 18,
    "budda": 19,
    "mr z38": 20,
    "super rvb": 21,
    "brit blues": 22,
    "match d30": 23,
    "brit 2000": 24,
    "uber higain": 25,
    "agl": 26,
    "mld": 27,
    "optima air": 28,
    "stageman": 29,
}

GATE_MODEL = {
    "default": 1,
}

MOD_MODEL = {
    "ce-1": 1,
    "ce-2": 2,
    "st chorus": 3,
    "vibrato": 4,
    "detune": 5,
    "flanger": 6,
    "phase 90": 7,
    "phase 100": 8,
    "s.c.f.": 9,
    "u-vibe": 10,
    "tremolo": 11,
    "rotary": 12,
    "sch-1": 13,
    "mono octave": 14,
}

DLY_MODEL = {
    "analog": 1,
    "digital": 2,
    "modulation": 3,
    "tape": 4,
    "pan": 5,
    "phi": 6,
}

RVB_MODEL = {
    "room": 1,
    "hall": 2,
    "plate": 3,
    "spring": 4,
    "shimmer": 5,
    "damp": 6,
}

IR_MODEL = {
    "JZ120": 1, 
    "DR112": 2, 
    "TR212": 3, 
    "HIWIRE412": 4, 
    "CALI 112": 5, 
    "A112": 6, 
    "GB412": 7, 
    "M1960AX": 8, 
    "M1960AV": 9, 
    "M1960TV": 10, 
    "SLO412": 11, 
    "FIREMAN 412": 12, 
    "RECT 412": 13, 
    "DIE412": 14, 
    "MATCH212": 15, 
    "UBER412": 16, 
    "BS410": 17, 
    "A212": 18, 
    "M1960AHW": 19, 
    "M1936": 20, 
    "BUDDA112": 21, 
    "Z212": 22, 
    "SUPERVERB410": 23, 
    "VIBROKING310": 24, 
    "AGL_DB810": 25, 
    "AMP_SV212": 26, 
    "AMP_SV410": 27, 
    "AMP_SV810": 28, 
    "BASSGUY410": 29, 
    "EDEN410": 30, 
    "MKB410": 31, 
    "G-HBIRD": 32, 
    "G-J15": 33, 
    "M-D45": 34,
}

EQ_MODEL = {
    "6-band": 0, # important
    "10-band": 1,
}

# ============================
# Effect Parameters & indexes
# ============================
GATE_PARAM = {
    "default": {"sensitivity": 51, "decay": 52},
}

CMP_PARAM = {
    "rose": {"sustain": 17, "level": 18},
    "k-comp": {"sustain": 17, "level": 18, "clipping": 19},
    "studio": {"threshold": 17, "ratio": 18, "gain": 19, "release": 20}, 
}

EFX_PARAM = {
    "distortion+": {"output": 22, "sensitivity": 23},
    "rc boost": {"gain": 22, "volume": 23, "bass": 24, "treble": 25},
    "ac boost": {"gain": 22, "volume": 23, "bass": 24, "treble": 25},
    "dist one": {"level": 22, "tone": 23, "drive": 24}, 
    "t screamer": {"drive": 22, "tone": 23, "level": 24}, 
    "blues drive": {"level": 22, "tone": 23, "gain": 24}, 
    "morning drive": {"volume": 22, "drive": 23, "tone": 24}, 
    "eat dist": {"distortion": 22, "filter": 23, "volume": 24}, 
    "red dist": {"drive": 22, "tone": 23, "level": 24}, 
    "crunch": {"volume": 22, "tone": 23, "gain": 24}, 
    "muff fuzz": {"volume": 22, "tone": 23, "sustain": 24}, 
    "katana": {"boost": 22, "volume": 23}, # Boost is on/off switch 0:Off, >0:On
    "st singer": {"gain": 23, "filter": 24, "volume": 22}, 
    "touch wah": {"wah": 23, "sense": 24, "level": 26, "ud_switch": 25, "type":22},
    # ud_switch is on/off switch 0:Off, >0:On, type is 0:Cry, 1:VX, 2:Full, 3:Talk
}

AMP_PARAM = {
    "jazz clean": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "bright_sw": 34},
    "deluxe rvb": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33},
    "bass mate": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "tweedy": {"gain": 29, "master": 30, "tone": 34},
    "tween reverb": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "bright_sw": 34},
    "hiwire": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "cali crunch": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "class a15": {"gain": 29, "master": 30, "bass": 31, "treble": 33, "cut": 34},
    "class a30": {"gain": 29, "master": 30, "bass": 31, "treble": 33, "cut": 34},
    "plexi 100": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "plexi 45": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "brit 800": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "1987x50": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "slo 100": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "fireman hbe": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "dual rect": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "die vh4": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "vibro king": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "bright_sw": 34},
    "budda": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "cut": 34},
    "mr z38": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "cut": 34},
    "super rvb": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "bright_sw": 34},
    "brit blues": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "match d30": {"gain": 29, "master": 30, "bass": 31, "treble": 33, "cut": 34},
    "brit 2000": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "uber higain": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "presence": 34},
    "agl": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "mid_freq": 34},
    "mld": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33, "mid_freq": 34},
    "optima air": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33},
    "stageman": {"gain": 29, "master": 30, "bass": 31, "middle": 32, "treble": 33},
}

MOD_PARAM = {
    "ce-1": {"intensity": 56, "depth": 57, "rate": 58},
    "ce-2": {"rate": 56, "depth": 57},
    "st chorus": {"intensity": 56, "width": 57, "rate": 58},
    "vibrato": {"rate": 56, "depth": 57},
    "detune": {"shift_l": 56, "mix": 57, "shift_r": 58},
    "flanger": {"level": 56, "rate": 57, "width": 58, "feedback": 59},
    "phase 90": {"speed": 56},
    "phase 100": {"intensity": 56, "speed": 57},
    "s.c.f.": {"speed": 56, "width": 57, "mode": 58, "intensity": 59}, #0-Chorus, 1-P.M., 2-Flanger
    "u-vibe": {"speed": 56, "volume": 57, "intensity": 58, "mode": 59}, #0-Chorus, 1-Vibrato
    "tremolo": {"rate": 56, "depth": 57},
    "rotary": {"balance": 56, "speed": 57},
    "sch-1": {"rate": 56, "depth": 57, "tone": 58},
    "mono octave": {"sub": 56, "dry": 57, "up": 58},
}

DLY_PARAM = {
    "analog": {"rate": 63, "echo": 64, "intensity": 65},  # rate ≈ 0..400 ms
    "digital": {"elevel": 63, "feedback": 64, "time": 65},  # time is non-linear, ≈ 0..1000 ms
    "modulation": {"time": 63, "level": 64, "mod": 65, "repeat": 66},  # time is non-linear, ≈ 0..1200 ms
    "tape": {"time": 63, "level": 64, "repeat": 65},  # time is non-linear, ≈ 0..550 ms
    "pan": {"time": 63, "repeat": 64, "level": 65},  # time is linear, ≈ 0..1000 ms
    "phi": {"time": 63, "repeat": 64, "mix": 65},  # time is linear, ≈ 0..1000 ms
}
    
RVB_PARAM = {
    "room":    {"decay": 72, "tone": 73, "level": 74},
    "hall":    {"decay": 72, "predelay": 73, "liveliness": 74, "level": 75},
    "plate":   {"decay": 72, "level": 73},
    "spring":  {"decay": 72, "level": 73},
    "shimmer": {"mix": 72, "decay": 73, "shimmer": 74},
    "damp":    {"mix": 72, "depth": 73},
}
  
EQ_PARAM = {
    "6-band":  {'100Hz': 38, '220Hz': 39, '500Hz': 40, '1.2kHz': 41, '2.6kHz': 42, '6.4kHz': 43},
    "10-band": {'Vol': 38, '31Hz': 39, '62Hz': 40, '125Hz': 41, '250Hz': 42, '500Hz': 43, '1kHz': 44, '2kHz': 45, '4kHz': 46, '8kHz': 47, '16kHz': 48},
}

IR_PARAM = {"volume": 80, "lowcut": 81, "highcut": 82}

# ========================
# Time Parameters & ranges
# ========================
DLY_TIME_PARAM = {
    "analog": {"name": "rate", "vmin": 0.04, "vmax": 0.4},  # rate ≈ 0..400 ms
    "digital": {"name": "time", "vmin": 0.08, "vmax": 0.99},  # time is non-linear, ≈ 0..1000 ms
    "modulation": {"name": "time", "vmin": 0.02, "vmax": 1.19},  # time is non-linear, ≈ 0..1200 ms
    "tape":{"name": "time", "vmin": 0.05, "vmax": 0.55},  # time is non-linear, ≈ 0..550 ms
    "pan": {"name": "time", "vmin": 0.08, "vmax": 0.99},  # time is linear, ≈ 0..1000 ms
    "phi": {"name": "time", "vmin": 0.08, "vmax": 0.99},  # time is linear, ≈ 0..1000 ms
}

# NOTE: Ranges must be verified!
RVB_TIME_PARAM = {
    "room":    {"name": "decay", "vmin": 0.2, "vmax": 1.2},
    "hall":    {"name": "decay", "vmin": 1.5, "vmax": 5.5}, # pre_delay: 0-100ms, so 1:1 0-100%
    "plate":   {"name": "decay", "vmin": 1.0, "vmax": 4.0},
    "spring":  {"name": "decay", "vmin": 0.2, "vmax": 2.8},
    "shimmer": {"name": "decay", "vmin": 3.0, "vmax": 10.0},
    "damp":    {"name": "depth", "vmin": 0.5, "vmax": 3.5},
}

# ====================================
# Signal chain modules order / indexes
# ====================================
SLOT_1 = 91 
SLOT_2 = 92 
SLOT_3 = 93 
SLOT_4 = 94 
SLOT_5 = 95 
SLOT_6 = 96 
SLOT_7 = 97 
SLOT_8 = 98 
SLOT_9 = 99 

ORDER = {
    "CMP": 1,
    "EFX": 2,
    "AMP": 3,
    "EQ": 4,
    "GATE": 5,
    "MOD": 6,
    "DLY": 7,
    "RVB": 8,
    "IR": 9,
}

# =========================
# Encoding / Decoding
# =========================
def decode_link(link: str) -> bytearray:
    """Decode a nux://MightyAmp:... link into a 115-byte array."""
    assert link.startswith("nux://MightyAmp:"), "Unexpected link scheme"
    b64 = link.split("MightyAmp:", 1)[1]
    print(b64)
    raw = base64.b64decode(b64 + ("=" * ((4 - len(b64) % 4) % 4)))
    assert len(raw) == PAYLOAD_LEN, f"Unexpected payload length {len(raw)}"
    return bytearray(raw)

def encode_link(raw: bytearray) -> str:
    """Encode a 115-byte payload back into a link."""
    assert len(raw) == PAYLOAD_LEN
    return "nux://MightyAmp:" + base64.b64encode(bytes(raw)).decode("ascii")

def save_qr(link: str, png_path: str) -> None:
    """Save QR (requires 'qrcode')."""
    img = qrcode.make(link)
    img.save(png_path)
    print("QR saved to:", png_path)

# =========================
# Helpers: Enable / Disable
# =========================
def set_eq_enabled(raw: bytearray, enabled: bool) -> None:
    # EQ ON/OFF by header @ 6
    if enabled:   raw[HDR_EQ] &= ~HDR_BYPASS
    else:         raw[HDR_EQ] |= HDR_BYPASS

# =========================
# Helpers: Set Models
# =========================
def set_header_model(raw: bytearray, hdr_offset: int, model_id: int, bypass: Optional[bool]=None) -> None:
    # Keep only high bits (0xC0), write model id into low bits, then set/clear bypass if provided
    raw[hdr_offset] = (raw[hdr_offset] & 0xC0) | (model_id & 0x3F)
    if bypass is not None:
        if bypass: raw[hdr_offset] |= HDR_BYPASS
        else:      raw[hdr_offset] &= ~HDR_BYPASS
    
def set_eq_model(raw: bytearray, ten_band: bool) -> None:
    # 10-band vs 6-band via flags bit 0x02
    if ten_band:  raw[HDR_EQ] |= FLAG_EQ_MODEL_10B
    else:         raw[HDR_EQ] &= ~FLAG_EQ_MODEL_10B
    
    
# =========================
# Scaling Utilities
# =========================
def clip01(v: int) -> int:
    return max(0, min(100, int(round(v))))

def percentage_from_range(value, vmin, vmax) -> int:
    return clip01(((value - vmin) / (vmax - vmin)) * 100)
    
# IR scaling
def ir_vol_value_from_db(db: float) -> int:
    # dB in [-12, +12] → 0..100
    return clip01((db + 12.0) / 0.24)

def ir_vol_db_from_value(val: int) -> float:
    return 0.24 * val - 12.0

def ir_lowcut_value_from_hz(hz: float) -> int:
    # linear 20..300 Hz
    return clip01((hz - 20.0) / 2.8)

def ir_lowcut_hz_from_value(val: int) -> float:
    return 20.0 + 2.8 * val

def ir_highcut_value_from_hz(hz: float) -> int:
    # logarithmic 5k..20k: value = 100 * log_{4}(hz/5000)
    return clip01(100.0 * math.log(hz / 5000.0, 4))

def ir_highcut_hz_from_value(val: int) -> float:
    return 5000.0 * (4.0 ** (val / 100.0))

# EQ scaling
def eq_value_from_db(db: float) -> int:
    # dB in [-15, +15] → 0..100
    return clip01((db + 15.0) / 0.3)

def eq_db_from_value(val: int) -> float:
    return 0.3 * val - 15.0


# =================
# Parameter Writers
# =================
def write_uint8(raw: bytearray, offset: int, value: int) -> None:
    raw[offset] = clip01(value)

def set_gate(raw: bytearray, pdict):
    set_header_model(raw, HDR_GATE, GATE_MODEL["default"], bypass = not pdict['enabled'])
    # Write parameter values if present
    mapping = GATE_PARAM["default"]
    for pname, offset in mapping.items():
        if pname in pdict.keys() and pdict[pname] is not None:
            write_uint8(raw, offset, pdict[pname])
        else:
            print("WARNING (", model, "): Value not provided for parameter - ", pname)

# TODO: 'ratio': '2.5:1', release:120, threshold: -24 (Studio Cmp generated)
def set_compressor(raw: bytearray, pdict):
    model = pdict["name"].lower()
    assert model in CMP_MODEL, f"Unknown Compressor model: {model}"
    set_header_model(raw, HDR_CMP, CMP_MODEL[model], bypass = not pdict['enabled'])
    # Write parameter values if present
    mapping = CMP_PARAM[model]
    for pname, offset in mapping.items():
        if pname in pdict.keys() and pdict[pname] is not None:
            write_uint8(raw, offset, pdict[pname])
        else:
            print("WARNING (", model, "): Value not provided for parameter - ", pname)
       
def set_effect(raw: bytearray, pdict):
    model = pdict["name"].lower()
    assert model in EFX_MODEL, f"Unknown Effect model: {model}"
    set_header_model(raw, HDR_EFX, EFX_MODEL[model], bypass = not pdict['enabled'])
    # Write parameter values if present
    mapping = EFX_PARAM[model]
    for pname, offset in mapping.items():
        if pname in pdict.keys() and pdict[pname] is not None:
            write_uint8(raw, offset, pdict[pname])
        else:
            print("WARNING (", model, "): Value not provided for parameter - ", pname)

def set_amplifier(raw: bytearray, pdict):
    model = pdict["name"].lower()
    assert model in AMP_MODEL, f"Unknown Amplifier model: {model}"
    set_header_model(raw, HDR_AMP, AMP_MODEL[model], bypass = not pdict['enabled'])
    # Write parameter values if present
    mapping = AMP_PARAM[model]
    for pname, offset in mapping.items():
        if pname in pdict.keys() and pdict[pname] is not None:
            write_uint8(raw, offset, pdict[pname])
        else:
            print("WARNING (", model, "): Value not provided for parameter - ", pname)

def set_modulation(raw: bytearray, pdict):
    model = pdict["name"].lower()
    bypass = not pdict['enabled']
    assert model in MOD_MODEL, f"Unknown MODULATION model: {model}"
    set_header_model(raw, HDR_MOD, MOD_MODEL[model], bypass = not pdict['enabled'])
    # Write parameter values if present
    mapping = MOD_PARAM[model]
    for pname, offset in mapping.items():
        if pname in pdict.keys() and pdict[pname] is not None:
            write_uint8(raw, offset, pdict[pname])
        else:
            print("WARNING (", model, "): Value not provided for parameter - ", pname)

# TODO: Non-linear scaling of parameters time and rate
def set_delay(raw: bytearray, pdict):
    model = pdict["name"].lower()
    assert model in DLY_MODEL, f"Unknown Delay model: {model}"
    set_header_model(raw, HDR_DLY, DLY_MODEL[model], bypass = not pdict['enabled'])
    # Write parameter values if present
    mapping = DLY_PARAM[model]
    for pname, offset in mapping.items():
        if pname in pdict.keys() and pdict[pname] is not None:
            write_uint8(raw, offset, pdict[pname])
        else:
            print("WARNING (", model, "): Value not provided for parameter - ", pname)

    # Linear translating time-to-percentage values
    name = DLY_TIME_PARAM[model]["name"]
    value = percentage_from_range(pdict[name], DLY_TIME_PARAM[model]["vmin"], DLY_TIME_PARAM[model]["vmax"])
    offset = mapping[name]
    write_uint8(raw, offset, value)
    # print(model, DLY_TIME_PARAM[model]["name"], DLY_TIME_PARAM[model]["vmin"], DLY_TIME_PARAM[model]["vmax"], offset, pdict[name], value)
        
def set_reverb(raw: bytearray, pdict):
    model = pdict["name"].lower()
    assert model in RVB_MODEL, f"Unknown Reverb model: {model}"
    set_header_model(raw, HDR_RVB, RVB_MODEL[model], bypass = not pdict['enabled'])
    # Write parameter values if present
    mapping = RVB_PARAM[model]
    for pname, offset in mapping.items():
        if pname in pdict.keys() and pdict[pname] is not None:
            write_uint8(raw, offset, pdict[pname])
        else:
            print("WARNING: Value not provided for parameter - ", pname)

    # Linear translating time-to-percentage values (decay)
    name = RVB_TIME_PARAM[model]["name"]
    value = percentage_from_range(pdict[name], RVB_TIME_PARAM[model]["vmin"], RVB_TIME_PARAM[model]["vmax"])
    offset = mapping[name]
    write_uint8(raw, offset, value)
    # print(model, RVB_TIME_PARAM[model]["name"], RVB_TIME_PARAM[model]["vmin"], RVB_TIME_PARAM[model]["vmax"], offset, pdict[name], value)

def set_ir_params(raw: bytearray, pdict):
    model = pdict["name"].upper()
    assert model in IR_MODEL, f"Unknown IR Cabinet model: {model}"
    set_header_model(raw, HDR_IR, IR_MODEL[model], bypass = not pdict['enabled'])

    if pdict["level"] is not None:       write_uint8(raw, IR_PARAM["volume"],  ir_vol_value_from_db(pdict["level"]))
    if pdict["low_cut"] is not None:  write_uint8(raw, IR_PARAM["lowcut"],  ir_lowcut_value_from_hz(pdict["low_cut"]))
    if pdict["high_cut"] is not None: write_uint8(raw, IR_PARAM["highcut"], ir_highcut_value_from_hz(pdict["high_cut"]))

def set_eq_params(raw: bytearray, pdict):
    model = pdict["name"].lower()
    assert model in EQ_MODEL, f"Unknown Equaliser model: {model}"
    set_eq_model(raw, pdict["name"]=="10-Band")
    set_eq_enabled(raw, pdict['enabled'])

    # Write parameter values if present
    mapping = EQ_PARAM[model]
    for pname, offset in mapping.items():
        if pname in pdict.keys() and pdict[pname] is not None:
            write_uint8(raw, offset, eq_value_from_db(pdict[pname]))
        else:
            print("WARNING (", model, "): Value not provided for parameter - ", pname)    

# =======================
def set_order(raw: bytearray, modules):
    assert len(modules) == len(set(modules)), "Order expect only one instance of each module. Duplicates detected."
    if modules is not None:
        assert len(modules) == 9, "9 modules are expected"
        for idx, m in enumerate(modules):
            write_uint8(raw, 91+idx, ORDER[m])


def set_volume(raw: bytearray, value: int):
    write_uint8(raw, VOL, value)

# =========================
# Example Usage
# =========================

# Paste your baseline link here (or set it at runtime)
BASELINE_LINK = "nux://MightyAmp:DwEAAgUKAwFBAgMHAAAAAAAjMgoAAA8jRgAAAAA3SyNGLSgAAAAyKysvLzU8NSsrKAAANyMAAAAgPCcAAAAAEhIpAAAAAAAAGA4AAAAAAAAyFSAAAAAyAAAAAAUBAgMJBAYHCAAAAAAAAAAAAAAAAAAAAA=="

def example_build_preset() -> Tuple[str, Optional[str]]:
    """
    Example preset:
    {'title': 'SCoM Intro – Phones (AKG K371)', 
     'signal_chain': ['GATE', 'CMP', 'EFX', 'AMP', 'IR', 'EQ', 'MOD', 'DLY', 'RVB'],
     'volume': 68,
     'GATE': {'enabled': True, 'sensitivity': 35, 'decay': 30},
     'CMP': {'name': 'Studio', 'enabled': True, 'gain': 3, 'threshold': 24, 'ratio': 32, 'release': 76},
     'EFX': {'name': 'T Screamer', 'enabled': True, 'level': 68, 'drive': 12, 'tone': 45},
     'AMP': {'name': 'Plexi 100', 'enabled': True, 'gain': 48, 'master': 72, 'bass': 42, 'middle': 58, 'treble': 62, 'presence': 48},
     'IR': {'name': 'GB412', 'enabled': True, 'description': 'Greenback 4x12', 'level': -1.5, 'low_cut': 85, 'high_cut': 7800},
     'EQ': {'name': '6-Band', 'enabled': True, '100Hz': -1.5, '220Hz': -0.5, '500Hz': 0.5, '1.2kHz': 1.0, '2.6kHz': 1.5, '6.4kHz': -1.0},
     'MOD': {'name': 'ce-1', 'enabled': False},
     'DLY': {'name': 'digital', 'enabled': False, 'elevel': 25, 'feedback': 33, 'time': 0.6},
     'RVB': {'name': 'Room', 'enabled': True, 'level': 18, 'decay': 0.4, 'tone': 52}
    }
    """
    raw = decode_link(BASELINE_LINK)

    set_order(raw, ['GATE', 'CMP', 'EFX', 'AMP', 'IR', 'EQ', 'MOD', 'DLY', 'RVB'])
    set_volume(raw, 68)
    
    set_gate(raw, {'enabled': True, 'sensitivity': 35, 'decay': 30})
    set_compressor(raw, {'name': 'Studio', 'enabled': True, 'gain': 3, 'threshold': 24, 'ratio': 32, 'release': 76})
    set_effect(raw, {'name': 'T Screamer', 'enabled': True, 'level': 68, 'drive': 12, 'tone': 45})
    set_amplifier(raw, {'name': 'Plexi_100', 'enabled': True, 'gain': 48, 'master': 72, 'bass': 42, 'middle': 58, 'treble': 62, 'presence': 48})
    set_ir_params(raw, {'name': 'GB412', 'enabled': True, 'description': 'Greenback 4x12', 'level': -1.5, 'low_cut': 85, 'high_cut': 7800})
    set_eq_params(raw, {'name': '6-Band', 'enabled': True, '100Hz': -1.5, '220Hz': -0.5, '500Hz': 0.5, '1.2kHz': 1.0, '2.6kHz': 1.5, '6.4kHz': -1.0})
    set_modulation(raw, {'name': 'ce-1', 'enabled': False})
    set_delay(raw, {'name': 'digital', 'enabled': False, 'elevel': 25, 'feedback': 33, 'time': 0.6})
    set_reverb(raw, {'name': 'Room', 'enabled': True, 'level': 18, 'decay': 0.4, 'tone': 52})
    
    # ============
    # Build output
    # ============
    link = encode_link(raw)
    png_path = "Preset_Example.png"
    save_qr(link, png_path)
    return link, png_path

# =========================
# Main
# =========================

if __name__ == "__main__":
    link, png = example_build_preset()
    print("\nNew preset link:\n", link)
