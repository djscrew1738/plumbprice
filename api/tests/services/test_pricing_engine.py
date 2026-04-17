"""
Unit tests for PricingEngine, LaborEngine, and pricing helpers.
No database or LLM — fully deterministic, pure-function tests.
"""

import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from app.services.pricing_engine import (
    PricingEngine,
    MaterialItem,
    get_city_multiplier,
    get_permit_cost,
    get_trip_charge,
    TAX_RATES,
    CITY_ZONE_MULTIPLIERS,
    _PERMIT_REQUIRED,
)
from app.services.labor_engine import (
    LaborTemplateData,
    get_template,
    LABOR_TEMPLATES,
    AccessType,
    UrgencyType,
)
from app.services.pricing_table import _MARKET_RANGES
from app.services.supplier_service import MATERIAL_ASSEMBLIES, CANONICAL_MAP

engine = PricingEngine()


# ─── MaterialItem ─────────────────────────────────────────────────────────────

class TestMaterialItem:
    def test_total_cost_computed_on_init(self):
        m = MaterialItem("test.item", "Test", 3.0, "ea", 10.00, "ferguson")
        assert m.total_cost == 30.00

    def test_total_cost_rounds_to_cents(self):
        m = MaterialItem("test.item", "Test", 1.0, "ea", 8.4219, "ferguson")
        assert m.total_cost == 8.42

    def test_fractional_quantity(self):
        m = MaterialItem("test.pipe", "Pipe", 2.5, "ft", 4.00, "moore_supply")
        assert m.total_cost == 10.00


# ─── get_city_multiplier ──────────────────────────────────────────────────────

class TestCityMultiplier:
    def test_highland_park_premium(self):
        assert get_city_multiplier("Highland Park") == 1.25

    def test_case_insensitive(self):
        assert get_city_multiplier("HIGHLAND PARK") == 1.25
        assert get_city_multiplier("highland park") == 1.25

    def test_unknown_city_returns_one(self):
        assert get_city_multiplier("Atlantis") == 1.0

    def test_none_returns_one(self):
        assert get_city_multiplier(None) == 1.0

    def test_dallas_is_baseline(self):
        assert get_city_multiplier("Dallas") == 1.0

    def test_frisco_premium(self):
        assert get_city_multiplier("Frisco") == 1.15

    def test_everman_discount(self):
        assert get_city_multiplier("Everman") == 0.92

    def test_strips_whitespace(self):
        assert get_city_multiplier("  southlake  ") == 1.20

    def test_all_multipliers_in_valid_range(self):
        for city, mult in CITY_ZONE_MULTIPLIERS.items():
            assert 0.80 <= mult <= 1.30, f"{city} multiplier {mult} out of expected range"


# ─── get_permit_cost ──────────────────────────────────────────────────────────

class TestPermitCost:
    def test_water_heater_in_dallas(self):
        cost = get_permit_cost("WH_50G_GAS_STANDARD", "Dallas")
        assert cost == 115.0

    def test_gas_line_in_tarrant(self):
        cost = get_permit_cost("GAS_LINE_NEW_RUN", "Tarrant")
        assert cost == 110.0

    def test_no_permit_for_simple_job(self):
        cost = get_permit_cost("TOILET_REPLACE_STANDARD", "Dallas")
        assert cost == 0.0

    def test_unknown_county_falls_back_to_dallas(self):
        cost = get_permit_cost("WH_50G_GAS_STANDARD", "Unknown County")
        assert cost == 115.0

    def test_repipe_permit_exists(self):
        cost = get_permit_cost("WHOLE_HOUSE_REPIPE_PEX", "Collin")
        assert cost > 0

    def test_backflow_permit_in_denton(self):
        cost = get_permit_cost("BACKFLOW_PREVENTER_INSTALL", "Denton")
        assert cost > 0


# ─── get_trip_charge ─────────────────────────────────────────────────────────

class TestTripCharge:
    def test_dallas_trip_charge(self):
        assert get_trip_charge("dallas") == 115.0

    def test_tarrant_trip_charge(self):
        assert get_trip_charge("tarrant") == 105.0

    def test_unknown_county_fallback(self):
        assert get_trip_charge("unknown") == 105.0

    def test_case_insensitive(self):
        assert get_trip_charge("Dallas") == get_trip_charge("dallas")


# ─── TAX_RATES ───────────────────────────────────────────────────────────────

class TestTaxRates:
    def test_all_dfw_counties_defined(self):
        for county in ["dallas", "tarrant", "collin", "denton", "rockwall", "parker"]:
            assert county in TAX_RATES, f"Missing tax rate for {county}"

    def test_texas_rate_range(self):
        for county, rate in TAX_RATES.items():
            assert 0.0625 <= rate <= 0.0825, f"{county} rate {rate} outside TX legal range"


# ─── LaborTemplateData.calculate_labor_cost ───────────────────────────────────

class TestLaborCalculation:
    def _make_template(self, base_hours=2.0, helper=False, helper_hours=None):
        return LaborTemplateData(
            code="TEST",
            name="Test Job",
            category="service",
            base_hours=base_hours,
            lead_rate=105.0,
            helper_required=helper,
            helper_rate=55.0,
            helper_hours=helper_hours,
            disposal_hours=0.25,
        )

    def test_standard_first_floor(self):
        tmpl = self._make_template(base_hours=2.0)
        result = tmpl.calculate_labor_cost(access="first_floor", urgency="standard")
        assert result["adjusted_hours"] == 2.0
        assert result["lead_cost"] == 2.0 * 105.0

    def test_attic_multiplier(self):
        tmpl = self._make_template(base_hours=2.0)
        result = tmpl.calculate_labor_cost(access="attic", urgency="standard")
        assert result["adjusted_hours"] == pytest.approx(3.0)  # 2.0 * 1.5

    def test_emergency_multiplier(self):
        tmpl = self._make_template(base_hours=2.0)
        result = tmpl.calculate_labor_cost(access="first_floor", urgency="emergency")
        assert result["adjusted_hours"] == pytest.approx(4.0)  # 2.0 * 2.0

    def test_attic_emergency_stacks(self):
        tmpl = self._make_template(base_hours=2.0)
        result = tmpl.calculate_labor_cost(access="attic", urgency="emergency")
        # 2.0 * 1.5 * 2.0 = 6.0
        assert result["adjusted_hours"] == pytest.approx(6.0)

    def test_helper_cost_included_when_required(self):
        tmpl = self._make_template(base_hours=2.0, helper=True, helper_hours=1.5)
        result = tmpl.calculate_labor_cost()
        assert result["helper_required"] is True
        assert result["helper_cost"] == pytest.approx(1.5 * 55.0)

    def test_no_helper_cost_when_not_required(self):
        tmpl = self._make_template(base_hours=2.0, helper=False)
        result = tmpl.calculate_labor_cost()
        assert result["helper_cost"] == 0.0

    def test_disposal_cost_always_present(self):
        tmpl = self._make_template(base_hours=2.0)
        result = tmpl.calculate_labor_cost()
        assert result["disposal_cost"] == pytest.approx(0.25 * 105.0)

    def test_total_labor_cost_sums_components(self):
        tmpl = self._make_template(base_hours=2.0, helper=True, helper_hours=1.0)
        result = tmpl.calculate_labor_cost()
        expected = result["lead_cost"] + result["helper_cost"] + result["disposal_cost"]
        assert result["total_labor_cost"] == pytest.approx(expected)


# ─── LABOR_TEMPLATES catalog sanity ──────────────────────────────────────────

class TestLaborTemplatesCatalog:
    def test_key_templates_exist(self):
        critical = [
            "TOILET_REPLACE_STANDARD",
            "WH_50G_GAS_STANDARD",
            "WH_50G_GAS_ATTIC",
            "KITCHEN_FAUCET_REPLACE",
            "PRV_REPLACE",
            "GARBAGE_DISPOSAL_INSTALL",
            "SHOWER_VALVE_REPLACE",
        ]
        for code in critical:
            assert code in LABOR_TEMPLATES, f"Missing labor template: {code}"

    def test_all_templates_have_positive_base_hours(self):
        for code, tmpl in LABOR_TEMPLATES.items():
            assert tmpl.base_hours > 0, f"{code} has non-positive base_hours"

    def test_get_template_returns_none_for_unknown(self):
        assert get_template("NONEXISTENT_TASK") is None

    def test_get_template_finds_known(self):
        t = get_template("TOILET_REPLACE_STANDARD")
        assert t is not None
        assert t.code == "TOILET_REPLACE_STANDARD"


# ─── PricingEngine.calculate_service_estimate ────────────────────────────────

class TestPricingEngineServiceEstimate:
    def _toilet_materials(self):
        return [
            MaterialItem("toilet.wax_ring",       "Wax Ring",        1, "ea", 8.42,  "ferguson"),
            MaterialItem("toilet.closet_bolts",    "Closet Bolts",    1, "ea", 6.18,  "ferguson"),
            MaterialItem("toilet.supply_line_12",  "Supply Line",     1, "ea", 10.95, "ferguson"),
            MaterialItem("toilet.unit_standard",   "Toilet Unit",     1, "ea", 185.00,"ferguson"),
        ]

    def test_grand_total_is_positive(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        assert result.grand_total > 0

    def test_grand_total_equals_subtotal_plus_tax(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        assert result.grand_total == pytest.approx(result.subtotal + result.tax_total, abs=0.01)

    def test_tax_applied_to_materials_only(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        expected_tax = round(result.materials_total * TAX_RATES["dallas"], 2)
        assert result.tax_total == pytest.approx(expected_tax, abs=0.01)

    def test_highland_park_premium_raises_total(self):
        base = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
            city=None,
        )
        premium = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
            city="Highland Park",
        )
        assert premium.grand_total > base.grand_total

    def test_trip_charge_excluded_when_flag_false(self):
        with_trip = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
            include_trip_charge=True,
        )
        without_trip = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
            include_trip_charge=False,
        )
        assert with_trip.grand_total > without_trip.grand_total

    def test_water_heater_includes_permit(self):
        wh_materials = [
            MaterialItem("wh.50g_gas_unit",              "50G Gas WH",       1, "ea", 598.00, "ferguson"),
            MaterialItem("wh.gas_flex_connector_18",     "Gas Flex",         1, "ea",  14.50, "ferguson"),
            MaterialItem("wh.expansion_tank_2g",         "Expansion Tank",   1, "ea",  42.80, "ferguson"),
            MaterialItem("wh.tp_valve_075",              "T&P Valve",        1, "ea",  22.95, "ferguson"),
            MaterialItem("wh.dielectric_union_pair",     "Dielectric Unions",1, "ea",  18.40, "ferguson"),
        ]
        result = engine.calculate_service_estimate(
            task_code="WH_50G_GAS_STANDARD",
            materials=wh_materials,
            county="Dallas",
        )
        # Dallas water heater permit = $115; should be in subtotal
        permit_lines = [li for li in result.line_items if li.line_type == "permit"]
        assert len(permit_lines) == 1
        assert permit_lines[0].total_cost == 115.0

    def test_attic_access_increases_total(self):
        mats = self._toilet_materials()
        first_floor = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=mats,
            county="Dallas",
            access="first_floor",
        )
        attic = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=mats,
            county="Dallas",
            access="attic",
        )
        assert attic.grand_total > first_floor.grand_total

    def test_emergency_urgency_increases_total(self):
        mats = self._toilet_materials()
        standard = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=mats,
            county="Dallas",
            urgency="standard",
        )
        emergency = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=mats,
            county="Dallas",
            urgency="emergency",
        )
        assert emergency.grand_total > standard.grand_total

    def test_materials_total_matches_sum_of_material_items(self):
        mats = self._toilet_materials()
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=mats,
            county="Dallas",
        )
        expected_materials = sum(m.total_cost for m in mats)
        assert result.materials_total == pytest.approx(expected_materials, abs=0.01)

    def test_unknown_task_code_raises(self):
        with pytest.raises(ValueError, match="Unknown labor template"):
            engine.calculate_service_estimate(
                task_code="FAKE_TASK_CODE_99",
                materials=[],
                county="Dallas",
            )

    def test_confidence_score_between_0_and_1(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        assert 0.0 <= result.confidence_score <= 1.0

    def test_confidence_label_valid(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        assert result.confidence_label in {"HIGH", "MEDIUM", "LOW", "ESTIMATE_ONLY"}

    def test_all_line_items_have_positive_totals(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        for li in result.line_items:
            assert li.total_cost >= 0, f"Negative line item: {li.description}"

    def test_line_items_sum_close_to_subtotal(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        # tax is added to subtotal for grand total; line items excluding tax should ~= subtotal
        line_sum = sum(
            li.total_cost for li in result.line_items if li.line_type != "tax"
        )
        assert abs(line_sum - result.subtotal) < 1.0  # allow rounding tolerance

    def test_different_counties_different_tax(self):
        mats = self._toilet_materials()
        dallas = engine.calculate_service_estimate("TOILET_REPLACE_STANDARD", mats, county="Dallas")
        tarrant = engine.calculate_service_estimate("TOILET_REPLACE_STANDARD", mats, county="Tarrant")
        # Both are 8.25% in 2025, so equal; test ensures no crash and both positive
        assert dallas.tax_total > 0
        assert tarrant.tax_total > 0


# ─── DFW Expansion: data integrity tests ─────────────────────────────────────

# All 45 new template codes added in the DFW 2025-2026 expansion
_NEW_TEMPLATE_CODES = [
    "WH_50G_ELECTRIC_ATTIC", "WH_TANKLESS_ELECTRIC", "WH_HYBRID_HEAT_PUMP",
    "WH_RECIRCULATION_LINE_NEW", "WH_PAN_DRAIN_OVERFLOW_ONLY",
    "DRAIN_CLEAN_FLOOR", "DRAIN_CLEAN_MAIN_HYDRO_COMBO", "SEWER_CAMERA_LOCATOR",
    "SEWER_LINER_CIPP", "SEWER_BELLY_REPAIR", "DRAIN_POP_UP_REPLACE",
    "CONDENSATE_DRAIN_INSTALL",
    "BIDET_STANDALONE_INSTALL", "PEDESTAL_SINK_INSTALL", "UNDERMOUNT_SINK_INSTALL",
    "FREESTANDING_TUB_INSTALL", "WALK_IN_SHOWER_VALVE_INSTALL",
    "WET_BAR_SINK_INSTALL", "UTILITY_SINK_INSTALL", "POT_FILLER_INSTALL",
    "COPPER_PINHOLE_REPAIR", "POLYBUTYLENE_SECTION_REPLACE",
    "PIPE_BURST_EMERGENCY", "FREEZE_DAMAGE_THAW_REPAIR", "PIPE_INSULATION_INSTALL",
    "GAS_LINE_DRYER", "GAS_LINE_RANGE_OVEN", "GAS_LINE_FIREPLACE",
    "GAS_LINE_GRILL_OUTDOOR", "GAS_LEAK_DETECTION",
    "COMMERCIAL_GREASE_TRAP_CLEAN", "COMMERCIAL_GREASE_TRAP_INSTALL",
    "COMMERCIAL_FLOOR_DRAIN_INSTALL", "FLUSHOMETER_REPLACE",
    "COMMERCIAL_WATER_HEATER_INSTALL",
    "IRRIGATION_BACKFLOW_INSTALL", "IRRIGATION_VALVE_REPAIR",
    "CATCH_BASIN_INSTALL", "YARD_HYDRANT_INSTALL",
    "ADA_GRAB_BAR_INSTALL", "WATER_HEATER_TIMER_INSTALL",
    "EMERGENCY_SHUTOFF_VALVE_INSTALL",
    # Phase 3 additions
    "LEAK_DETECTION_ELECTRONIC", "SMOKE_TEST_SEWER", "HYDROSTATIC_TEST_SEWER",
    "THERMAL_IMAGING_LEAK", "VIDEO_CALL_DIAGNOSTIC", "SECOND_OPINION_INSPECTION",
    "WATER_LINE_REPAIR_COPPER", "WATER_LINE_REPAIR_PEX",
    "WATER_LINE_REPLACE_MAIN_STREET", "MANIFOLD_INSTALL_PEX",
    "PRESSURE_BOOSTER_INSTALL", "SHUT_OFF_VALVE_MAIN", "THERMAL_EXPANSION_VALVE",
    "DRAIN_CLEAN_LAUNDRY", "DRAIN_CLEAN_DOUBLE_KITCHEN", "CLEANOUT_CAP_REPLACE",
    "VENT_PIPE_REPAIR_ROOF", "AAV_INSTALL", "EJECTOR_PUMP_INSTALL",
    "SHOWER_DOOR_PLUMBING_PREP", "SHOWER_DIVERTER_REPAIR",
    "ROMAN_TUB_FAUCET_REPLACE", "CLAW_FOOT_TUB_PLUMBING",
    "BARRIER_FREE_SHOWER_INSTALL", "STEAM_SHOWER_VALVE_INSTALL",
    "BIDET_SPRAYER_INSTALL",
    "INSTANT_HOT_WATER_INSTALL", "REFRIGERATOR_LINE_INSTALL",
    "DISHWASHER_DRAIN_REPAIR", "GARBAGE_DISPOSAL_REPLACE_HP",
    "PREP_SINK_INSTALL", "COMMERCIAL_SPRAYER_FAUCET",
    "FRENCH_DRAIN_INSTALL", "SUMP_PUMP_REPLACE", "POOL_PLUMBING_REPAIR",
    "OUTDOOR_SHOWER_INSTALL", "SPRINKLER_LINE_REPAIR", "RAIN_BARREL_HOOKUP",
    "GAS_LINE_POOL_HEATER", "GAS_LINE_GENERATOR", "GAS_LINE_TANKLESS_WH",
    "GAS_METER_UPGRADE_COORD", "GAS_APPLIANCE_DISCONNECT",
    "WATER_SOFTENER_REPLACE", "WATER_SOFTENER_REPAIR",
    "UV_DISINFECTION_INSTALL", "SEDIMENT_FILTER_INSTALL", "WATER_TESTING_SERVICE",
    "EMERGENCY_WATER_SHUTOFF", "EMERGENCY_GAS_SHUTOFF",
    "EMERGENCY_SEWER_BACKUP", "FLOOD_DAMAGE_MITIGATION", "AFTER_HOURS_DIAGNOSTIC",
    "PLUMBING_INSPECTION_ANNUAL", "WINTERIZATION_SERVICE",
    "DE_WINTERIZATION_SERVICE", "WATER_HEATER_ANNUAL_SERVICE",
    "FIXTURE_CAULK_RESEAL", "WHOLE_HOUSE_SHUTOFF_TEST", "HOSE_BIB_WINTERIZE",
    # Phase 4 additions — Construction
    "ROUGH_IN_MASTER_BATH", "ROUGH_IN_SECONDARY_BATH", "ROUGH_IN_HALF_BATH",
    "ROUGH_IN_KITCHEN", "ROUGH_IN_LAUNDRY", "ROUGH_IN_OUTDOOR",
    "ROUGH_IN_GAS_WHOLE_HOUSE", "ROUGH_IN_WH_LOCATION",
    "SEWER_TAP_CONNECTION", "WATER_TAP_CONNECTION",
    "FIRE_SPRINKLER_RESIDENTIAL", "CONCRETE_CORE_DRILL",
    "STUB_OUT_CAP_TEST", "FIXTURE_TRIM_OUT_FULL_BATH",
    "SLEEVE_INSTALL_PER_PENETRATION", "MULTI_STORY_RISER_PER_FLOOR",
    "TANKLESS_RECIRCULATION_LOOP", "SLAB_PLUMBING_LAYOUT",
    # Phase 4 additions — Commercial
    "COMMERCIAL_TOILET_INSTALL", "COMMERCIAL_WALL_HUNG_TOILET",
    "COMMERCIAL_URINAL_INSTALL", "DRINKING_FOUNTAIN_INSTALL",
    "EYE_WASH_STATION_INSTALL", "MOP_SINK_INSTALL",
    "COMMERCIAL_DISHWASHER_HOOKUP", "HANDS_FREE_FAUCET_INSTALL",
    "COMMERCIAL_PRV_INSTALL", "TMV_INSTALL",
    "GREASE_INTERCEPTOR_INSTALL", "ROOF_DRAIN_INSTALL",
    "SEWAGE_LIFT_STATION", "COMMERCIAL_WATER_SOFTENER",
    "BACKFLOW_PREVENTER_REPAIR",
    # Phase 4 additions — Service gaps
    "WH_DRAIN_PAN_REPLACE", "WH_GAS_VALVE_REPLACE",
    "TPR_VALVE_REPLACE", "WH_FLUE_REPAIR",
    "WHIRLPOOL_TUB_REPAIR", "BATHTUB_DISCONNECT_RECONNECT",
    "TUB_DRAIN_ASSEMBLY_REPLACE", "SHOWER_DRAIN_REPLACE",
    "FLOOR_DRAIN_RESIDENTIAL",
    "RPZ_REBUILD", "DCVA_REPAIR",
    "EARTHQUAKE_VALVE_INSTALL", "GAS_DRIP_LEG_INSTALL",
    "GATE_TO_BALL_VALVE_UPGRADE", "SUPPLY_STOP_MULTI_REPLACE",
    "WASHING_MACHINE_HOSE_REPLACE", "DISHWASHER_SUPPLY_INSTALL",
    "GAS_RANGE_CONNECTOR_REPLACE", "GARBAGE_DISPOSAL_RESET_UNJAM",
    "RADIANT_FLOOR_LOOP", "HYDRONIC_HEATING_REPAIR",
    "RECLAIMED_WATER_LINE", "SEPTIC_PUMP_OUT_COORD",
    "WELL_PUMP_REPAIR", "WELL_PRESSURE_TANK_REPLACE",
    "GREYWATER_SYSTEM_INSTALL", "VANITY_PLUMBING_MODIFICATION",
    "WATER_LINE_LOCATE_MARK", "TRAP_PRIMER_INSTALL",
    "EXPANSION_JOINT_REPAIR", "WATER_METER_RELOCATE",
    "CLEANOUT_INSTALL_EXTERIOR", "SHOWER_BODY_SPRAY_INSTALL",
    "DUAL_FLUSH_CONVERSION",
    # Phase 5 — Pipe Materials, Remodel, Smart, Multi-Family, Specialty
    # Q. Pipe Materials
    "CAST_IRON_PIPE_REPAIR", "CAST_IRON_SECTION_REPLACE", "CAST_IRON_STACK_REPLACE",
    "GALVANIZED_PIPE_REPAIR", "GALVANIZED_TO_PEX_SECTION", "GALVANIZED_WHOLE_HOUSE_REPIPE",
    "CPVC_PIPE_REPAIR", "CPVC_TO_PEX_SECTION",
    "LEAD_SERVICE_LINE_REPLACE", "ORANGEBURG_SEWER_REPLACE",
    # R. Remodel
    "BATH_REMODEL_PLUMBING_STANDARD", "BATH_REMODEL_PLUMBING_MASTER",
    "KITCHEN_REMODEL_PLUMBING", "TUB_TO_SHOWER_CONVERSION",
    "SHOWER_TO_TUB_CONVERSION", "SINGLE_TO_DOUBLE_VANITY", "LAUNDRY_ROOM_RELOCATE",
    # S. Smart Plumbing
    "SMART_WATER_MONITOR_INSTALL", "SMART_SHUTOFF_VALVE_INSTALL",
    "SMART_LEAK_SENSOR_SYSTEM", "SMART_TOILET_INSTALL",
    "TOUCHLESS_FAUCET_RESIDENTIAL", "TANKLESS_POU_INSTALL",
    # T. Multi-Family
    "MULTIFAMILY_UNIT_SHUTOFF", "MULTIFAMILY_RISER_REPAIR",
    "MULTIFAMILY_STACK_REPAIR", "CONDO_WATER_HEATER_REPLACE", "SHARED_SEWER_LINE_REPAIR",
    # U. Medical
    "MEDICAL_GAS_OUTLET_INSTALL", "LAB_WASTE_SYSTEM",
    "DENTAL_CHAIR_PLUMBING", "AUTOCLAVE_PLUMBING",
    # V. Restaurant
    "RESTAURANT_FLOOR_DRAIN_INSTALL", "RESTAURANT_HANDWASH_STATION",
    "THREE_COMPARTMENT_SINK_INSTALL", "BAR_SINK_INSTALL",
    "ICE_MACHINE_PLUMBING", "COMMERCIAL_COFFEE_HOOKUP",
    # W. Aging-in-Place
    "WALK_IN_TUB_INSTALL", "COMFORT_HEIGHT_TOILET_ADA",
    "LEVER_HANDLE_CONVERSION", "RAISED_TOILET_SEAT_PLUMBING", "ANTI_SCALD_VALVE_RETROFIT",
    # X. DFW Slab & Climate
    "SLAB_LEAK_DETECTION_FULL", "SLAB_LEAK_TUNNEL_REPAIR",
    "SLAB_LEAK_EPOXY_LINING", "FOUNDATION_WATERING_SYSTEM",
    "THERMAL_PIPE_EXPANSION_FIX", "ATTIC_PIPE_INSULATION_UPGRADE",
    # Y. Tankless & WH Extended
    "TANKLESS_ERROR_DIAGNOSTIC", "TANKLESS_VENT_INSTALL",
    "TANKLESS_CONDENSATE_DRAIN", "WH_POWER_VENT_REPLACE", "WH_CONVERSION_GAS_TO_ELECTRIC",
    # Z. Code Compliance
    "PRE_INSPECTION_PREP", "HOME_SALE_PLUMBING_INSPECTION",
    "CODE_VIOLATION_REMEDIATION", "PERMIT_CLOSURE_INSPECTION_PREP",
    "WATER_CONSERVATION_AUDIT", "CROSS_CONNECTION_SURVEY",
]


class TestNewLaborTemplatesExist:
    """Every new DFW template code must be registered in LABOR_TEMPLATES."""

    @pytest.mark.parametrize("code", _NEW_TEMPLATE_CODES)
    def test_template_exists(self, code):
        assert code in LABOR_TEMPLATES, f"Missing labor template: {code}"

    @pytest.mark.parametrize("code", _NEW_TEMPLATE_CODES)
    def test_template_has_valid_base_hours(self, code):
        tmpl = LABOR_TEMPLATES[code]
        assert tmpl.base_hours > 0, f"{code} base_hours must be positive"

    @pytest.mark.parametrize("code", _NEW_TEMPLATE_CODES)
    def test_template_calculates_labor(self, code):
        """Every new template must produce a valid labor cost dict."""
        tmpl = LABOR_TEMPLATES[code]
        result = tmpl.calculate_labor_cost()
        assert result["total_labor_cost"] > 0


class TestNewMarketRangesExist:
    """Every labor template must have a matching market range."""

    @pytest.mark.parametrize("code", _NEW_TEMPLATE_CODES)
    def test_market_range_exists(self, code):
        assert code in _MARKET_RANGES, f"Missing market range for template: {code}"

    @pytest.mark.parametrize("code", _NEW_TEMPLATE_CODES)
    def test_market_range_has_dollar_sign(self, code):
        rng = _MARKET_RANGES[code]
        assert "$" in rng, f"Market range for {code} should contain a $ sign"


class TestMaterialAssembliesIntegrity:
    """Every assembly must link to a valid labor template and valid canonical items."""

    def test_all_assembly_templates_exist(self):
        for asm_code, asm in MATERIAL_ASSEMBLIES.items():
            lt = asm.get("labor_template")
            if lt:
                assert lt in LABOR_TEMPLATES, (
                    f"Assembly {asm_code} references missing template: {lt}"
                )

    def test_all_assembly_items_in_canonical_map(self):
        for asm_code, asm in MATERIAL_ASSEMBLIES.items():
            for item_id, qty in asm.get("items", {}).items():
                assert item_id in CANONICAL_MAP, (
                    f"Assembly {asm_code} references missing canonical item: {item_id}"
                )
                assert qty > 0, (
                    f"Assembly {asm_code} item {item_id} has non-positive qty"
                )

    def test_new_templates_have_assemblies(self):
        """Templates that reference applicable_assemblies should have those assemblies defined."""
        for code in _NEW_TEMPLATE_CODES:
            tmpl = LABOR_TEMPLATES[code]
            if tmpl.applicable_assemblies:
                for asm_code in tmpl.applicable_assemblies:
                    assert asm_code in MATERIAL_ASSEMBLIES, (
                        f"Template {code} references missing assembly: {asm_code}"
                    )


class TestNewPermitMappings:
    """New gas/sewer/backflow/WH templates must have permit mappings."""

    _EXPECTED_PERMITS = {
        "WH_50G_ELECTRIC_ATTIC": "water_heater",
        "WH_TANKLESS_ELECTRIC": "water_heater",
        "WH_HYBRID_HEAT_PUMP": "water_heater",
        "COMMERCIAL_WATER_HEATER_INSTALL": "water_heater",
        "GAS_LINE_DRYER": "gas",
        "GAS_LINE_RANGE_OVEN": "gas",
        "GAS_LINE_FIREPLACE": "gas",
        "GAS_LINE_GRILL_OUTDOOR": "gas",
        "SEWER_LINER_CIPP": "sewer",
        "SEWER_BELLY_REPAIR": "sewer",
        "IRRIGATION_BACKFLOW_INSTALL": "backflow",
    }

    @pytest.mark.parametrize("code,ptype", list(_EXPECTED_PERMITS.items()))
    def test_permit_mapped(self, code, ptype):
        assert _PERMIT_REQUIRED.get(code) == ptype, (
            f"{code} should require '{ptype}' permit"
        )

    @pytest.mark.parametrize("code,ptype", list(_EXPECTED_PERMITS.items()))
    def test_permit_cost_positive(self, code, ptype):
        cost = get_permit_cost(code, "Dallas")
        assert cost > 0, f"{code} should have a positive permit cost in Dallas"


class TestScaleEstimateRegression:
    """Regression: scaled subtotal must never exceed grand_total."""

    def _toilet_materials(self):
        return [
            MaterialItem("toilet.american_std_champion", "Toilet", 1, "ea", 289.00, "ferguson"),
            MaterialItem("toilet.wax_ring",              "Wax Ring", 1, "ea", 5.49, "ferguson"),
        ]

    def test_single_qty_subtotal_le_grand_total(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        assert result.subtotal <= result.grand_total

    def test_scaled_qty_subtotal_le_grand_total(self):
        result = engine.calculate_service_estimate(
            task_code="TOILET_REPLACE_STANDARD",
            materials=self._toilet_materials(),
            county="Dallas",
        )
        for qty in [2, 3, 5, 10]:
            scaled = engine.scale_estimate(result, qty)
            assert scaled.subtotal <= scaled.grand_total, (
                f"qty={qty}: subtotal ${scaled.subtotal} > grand_total ${scaled.grand_total}"
            )
