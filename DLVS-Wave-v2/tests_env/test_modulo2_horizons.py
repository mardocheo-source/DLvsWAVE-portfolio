"""Test Modulo 2: Parallel Horizons fetch, topocentric observer, and fault tolerance."""
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from horizons import BodyTarget, HorizonsFetcher, HorizonsObserverConfig
from naming import validate_column_names


def test_horizons_parallel_and_fault_tolerance():
    test_dir = Path(__file__).resolve().parent
    report_json_path = test_dir / "test_horizons_report.json"
    output_csv = test_dir / "test_horizons_ephemerides.csv"

    # Define targets: Sun, Moon, Asteroid Ceres, and an INVALID body to test fault tolerance
    bodies = [
        BodyTarget(name="sun", command="10", body_type="star"),
        BodyTarget(name="moon", command="301", body_type="moon"),
        BodyTarget(name="ceres", command="1", body_type="asteroid", id_type="smallbody"),
        BodyTarget(name="faulty_target_mock", command="INVALID_999999", body_type="mock", is_optional=True),
    ]

    config = HorizonsObserverConfig(
        start_time="2024-01-01",
        stop_time="2024-01-07",
        step_size="1d",
        observer_type="topocentric",
        lat=38.0,
        lon=140.0,
        elevation_km=0.1,
        max_workers=3,
        timeout_seconds=30,
        max_retries=3,
        retry_delay_seconds=1.0,
    )

    fetcher = HorizonsFetcher(config)
    print(f"[TEST 2] Launching parallel fetch for {len(bodies)} targets over 7-day span...")
    df_astro, report = fetcher.fetch_all(bodies=bodies)

    fetcher.save_report(report, report_json_path)
    df_astro.to_csv(output_csv, index=False)

    print(f"[TEST 2] Fetched {len(df_astro)} days, {len(df_astro.columns)} columns.")
    print(f"[TEST 2] Successful bodies: {report.successful_bodies}")
    print(f"[TEST 2] Failed bodies (fault tolerance check): {report.failed_bodies}")

    # Assertions
    assert "sun" in report.successful_bodies, "Sun ephemerides should have succeeded!"
    assert "moon" in report.successful_bodies, "Moon ephemerides should have succeeded!"
    assert "ceres" in report.successful_bodies, "Ceres ephemerides should have succeeded!"
    assert "faulty_target_mock" in report.failed_bodies, "Faulty target should be marked as failed in report!"

    assert report_json_path.exists(), "Error report JSON was not saved!"
    with report_json_path.open("r", encoding="utf-8") as f:
        rep_data = json.load(f)
        assert "faulty_target_mock" in rep_data["failed_bodies"]
        assert rep_data["body_results"]["faulty_target_mock"]["error_message"] is not None

    # Verify column naming on successful columns
    is_valid, invalid_cols = validate_column_names(df_astro.columns)
    assert is_valid, f"Invalid column names found in Horizons dataframe: {invalid_cols}"

    print("[TEST 2] SUCCESS: Parallel Horizons fetch and Fault Tolerance test passed!")


if __name__ == "__main__":
    test_horizons_parallel_and_fault_tolerance()
