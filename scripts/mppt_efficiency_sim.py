"""
Simple simulation comparing 4 Independent MPPT Channels vs. 1 Shared MPPT Channel
for a 4-sided body (CubeSat / Rover) where only 1-2 sides face the sun at a time.
"""

import math

def calculate_panel_output(angle_offset_deg, sun_angle_deg):
    """
    Calculates the power, Vmp, and Imp for a single solar panel face.
    - Sun illumination follows cosine law (cos(theta)).
    - Dark/shaded sides produce 0 current.
    - Lit panels warm up, which shifts their Vmp (temperature coefficient).
    """
    rel_angle = math.radians((sun_angle_deg - angle_offset_deg) % 360)
    cos_theta = math.cos(rel_angle)
    
    # If the face is facing away from the sun (> 90 deg incidence), it is shaded
    if cos_theta <= 0:
        return {"power": 0.0, "vmp": 0.0, "imp": 0.0, "sun_pct": 0.0}

    sun_pct = cos_theta * 100.0
    irradiance = 1000.0 * cos_theta  # W/m^2

    # Baseline module specs at 25°C
    Voc_25C = 6.0    # Volts
    Isc_1000 = 1.0   # Amps

    # Lit panels heat up (~25°C ambient + 30°C rise at 1000 W/m^2)
    temp_cell = 25.0 + 30.0 * (irradiance / 1000.0)
    
    # Voltage drops by ~22mV/°C as cell heats up; current is proportional to irradiance
    Voc = Voc_25C - 0.022 * (temp_cell - 25.0) + 0.15 * math.log(max(irradiance / 1000.0, 1e-4))
    Vmp = Voc * 0.82
    Imp = (Isc_1000 * (irradiance / 1000.0)) * 0.90
    Power = Vmp * Imp

    return {"power": Power, "vmp": Vmp, "imp": Imp, "sun_pct": sun_pct}


def run_comparison():
    # 4 faces positioned orthogonally around the body (0°, 90°, 180°, 270°)
    faces = [0, 90, 180, 270]
    
    print("=" * 68)
    print("      4 INDEPENDENT MPPTs vs. 1 CENTRAL SHARED MPPT")
    print("=" * 68)

    # -------------------------------------------------------------
    # Case 1: Specific Snapshot (Sun at 30° -> 2 faces lit obliquely)
    # -------------------------------------------------------------
    sun_angle = 30  # Face 0 at 30° (87% sun), Face 1 at 60° (50% sun), Faces 2 & 3 shaded
    
    panel_data = [calculate_panel_output(f, sun_angle) for f in faces]
    lit_panels = [p for p in panel_data if p["power"] > 0]

    # --- 4 Independent MPPTs ---
    # Each channel tracks its panel at its own true Vmp (no blocking diode drop)
    p_4mppt = sum(p["power"] for p in panel_data)

    # --- 1 Shared MPPT ---
    # 1. Panels must be isolated with Schottky blocking diodes (Vf ~ 0.35V loss)
    # 2. All lit panels are forced to operate at the SAME compromise bus voltage
    avg_vmp = sum(p["vmp"] * p["imp"] for p in lit_panels) / sum(p["imp"] for p in lit_panels)
    p_1mppt = 0.0
    for p in lit_panels:
        # Power lost to voltage mismatch + 0.35V diode forward drop
        v_mismatch_loss = 1.0 - 0.5 * ((p["vmp"] - avg_vmp) / p["vmp"]) ** 2
        effective_v = max(0.0, avg_vmp - 0.35)
        p_1mppt += effective_v * p["imp"] * v_mismatch_loss

    instant_gain = ((p_4mppt - p_1mppt) / p_1mppt) * 100.0

    print(f"\n[Scenario: Sun at {sun_angle}° (2 sides lit, 2 sides in shadow)]")
    for i, p in enumerate(panel_data):
        status = f"{p['sun_pct']:.0f}% Sun | Vmp={p['vmp']:.2f}V | {p['power']:.2f}W" if p['power'] > 0 else "In Shadow (0W)"
        print(f"  Face {i+1} ({faces[i]}°): {status}")

    print(f"\n  -> 4 Independent MPPTs Harvested : {p_4mppt:.2f} W")
    print(f"  -> 1 Shared MPPT Harvested       : {p_1mppt:.2f} W")
    print(f"  -> Efficiency Advantage          : +{instant_gain:.1f}%\n")

    # -------------------------------------------------------------
    # Case 2: Full 360° Rotation / Orbit Average
    # -------------------------------------------------------------
    angles = range(0, 360, 5)
    total_4mppt_energy = 0.0
    total_1mppt_energy = 0.0

    for deg in angles:
        current_data = [calculate_panel_output(f, deg) for f in faces]
        active = [p for p in current_data if p["power"] > 0]
        
        # 4 MPPT sum
        total_4mppt_energy += sum(p["power"] for p in current_data)
        
        # 1 MPPT sum with diode drop & voltage mismatch
        if active:
            v_shared = sum(p["vmp"] * p["imp"] for p in active) / sum(p["imp"] for p in active)
            for p in active:
                mismatch = 1.0 - 0.5 * ((p["vmp"] - v_shared) / p["vmp"]) ** 2
                total_1mppt_energy += max(0.0, v_shared - 0.35) * p["imp"] * mismatch

    avg_4mppt = total_4mppt_energy / len(angles)
    avg_1mppt = total_1mppt_energy / len(angles)
    orbit_gain = ((avg_4mppt - avg_1mppt) / avg_1mppt) * 100.0

    print("-" * 68)
    print(f"[Full 360° Rotation / Orbit Average]")
    print(f"  -> 4 MPPT Average Power Harvested : {avg_4mppt:.2f} W")
    print(f"  -> 1 MPPT Average Power Harvested : {avg_1mppt:.2f} W")
    print(f"  -> Total Orbit Energy Gain         : +{orbit_gain:.1f}%")
    print("=" * 68)


if __name__ == "__main__":
    run_comparison()
