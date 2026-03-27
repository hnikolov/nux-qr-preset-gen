import tomllib  # Use 'import tomli as tomllib' if on Python < 3.11

import argparse
import os
from mpp_qr_preset import *


def load_preset(file_path):
    with open(file_path, "rb") as f:
        data = tomllib.load(f)
    return data


def load_preset_from_string(toml_string: str) -> dict:
    import io
    data = tomllib.load(io.BytesIO(toml_string.encode("utf-8")))
    return data


def build_preset_from_dict(preset: dict, output_dir: str = "presets") -> str:
    """Build a QR preset from a preset dict. Returns the PNG file path."""
    raw = decode_link(BASELINE_LINK)

    set_order(raw, preset['signal_chain'])
    set_volume(raw, preset['volume'])

    set_gate(raw, preset['GATE'])
    set_compressor(raw, preset['CMP'])
    set_effect(raw, preset['EFX'])
    set_amplifier(raw, preset['AMP'])
    set_ir_params(raw, preset['IR'])
    set_eq_params(raw, preset['EQ'])
    set_modulation(raw, preset['MOD'])
    set_delay(raw, preset['DLY'])
    set_reverb(raw, preset['RVB'])

    link = encode_link(raw)
    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, preset['title'] + ".png")
    save_qr(link, png_path)
    return png_path


def convert_toml_file(file_path: str, output_dir: str = "presets") -> str:
    """Convert a .toml preset file to a QR .png. Returns the PNG path."""
    preset = load_preset(file_path)
    return build_preset_from_dict(preset, output_dir)


def convert_toml_string(toml_string: str, output_dir: str = "presets") -> str:
    """Convert a TOML string to a QR .png. Returns the PNG path."""
    preset = load_preset_from_string(toml_string)
    return build_preset_from_dict(preset, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio Preset Loader")
    parser.add_argument("filename", nargs="?", default="SCoM-Intro.toml",
                        help="Path to the TOML preset file")

    args = parser.parse_args()
    print(f"Loading: {args.filename}")

    convert_toml_file(args.filename)
  