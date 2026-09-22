"""State48 tests (P3 Step 3-2)."""

import state.state48 as st


def test_feature_contract():
    assert st.N_FEATURES == 48
    assert st.S46_TS_INJECT_OK == 0


def test_valid_mask_no_fill():
    vec, valid = st.build_state48({})
    assert len(vec) == 48 and len(valid) == 48
    assert vec[0] == 0.0 and valid[0] == 0
    vec2, valid2 = st.build_state48({"cpu_util": 50.0, "cpu_temp_c": 60.0})
    assert valid2[0] == 1 and abs(vec2[0] - 0.5) < 1e-9
    vec3, valid3 = st.build_state48({"cpu_util": float("nan")})
    assert vec3[0] == 0.0 and valid3[0] == 0
    assert vec2[st.S46_IDX] == 0.0 and valid2[st.S46_IDX] == 1
    vec4, valid4 = st.build_state48({})
    assert vec4[0] == 0.0 and valid4[0] == 0


def test_build_1hz_normalize():
    vec, valid = st.build_state48({
        "cpu_util": 100.0, "cpu_temp_c": 105.0, "gpu_util": 0.0,
        "gpu_temp_c": 20.0, "burst_tokens_j": 350.0, "soc_pct": 80.0,
    })
    assert vec[0] == 1.0 and vec[1] == 1.0 and vec[2] == 0.0
    assert abs(vec[st.S33_BURST_TOKENS] - 0.5) < 1e-9
    vec5, _ = st.build_state48({"cpu_util": 999.0, "cpu_temp_c": -50.0})
    assert vec5[0] == 1.0 and vec5[1] == 0.0
    assert 0.0 <= vec[st.S44_VALID_SENSE] <= 1.0
    assert 0.0 <= vec[st.S45_VALID_STATE] <= 1.0
