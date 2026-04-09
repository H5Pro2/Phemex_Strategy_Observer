# ==================================================
# mcm_core_engine.py
# ==================================================

def compute_tension_from_ohlc(
    o_: float,
    h_: float,
    l_: float,
    c_: float,
    v_: float | None = None,
):
    """
    returns:
        energy (float)
        coherence (float) ∈ [-1, +1]
        asymmetry (int) ∈ {-1,0,+1}
        coh_zone: G1, G2, G3, G4, CENTER
    """

    # -------------------------------------------
    # Range
    span = max(h_ - l_, 1e-9)

    # -------------------------------------------
    # Coherence (gerichtete Bewegung)
    coherence = (c_ - o_) / span
    coherence = max(-1.0, min(1.0, coherence))

    # -------------------------------------------
    # Energie als Abweichung vom Kerzenzentrum
    M = (o_ + h_ + l_ + c_) / 4.0

    o = abs(o_ - M)
    h = abs(h_ - M)
    l = abs(l_ - M)
    c = abs(c_ - M)

    energy = (o + h + l + c) / span

    # -------------------------------------------
    # Asymmetrie
    if coherence > 0:
        asymmetry = 1
    elif coherence < 0:
        asymmetry = -1
    else:
        asymmetry = 0

    # -------------------------------------------
    if coherence < -0.6:
        coh_zone = -2.0     # "G1"
    elif coherence < -0.2:
        coh_zone = -1.0     #" G2"
    elif coherence > 0.6:
        coh_zone = 2.0      # "G4"
    elif coherence > 0.2:
        coh_zone = 1.0      # "G3"
    else:
        coh_zone = 0.0      # "CENTER" 

    # ------------------------------------------
    return float(energy), float(coherence), int(asymmetry), float(coh_zone)