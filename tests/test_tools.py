import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.tools import calc_qps, calc_storage


def test_calc_qps_increases_with_concurrency():
    qps_low = calc_qps(dau=1000, peak_concurrency=100, read_write_ratio=4)
    qps_high = calc_qps(dau=1000, peak_concurrency=500, read_write_ratio=4)
    assert qps_high["peak_qps"] > qps_low["peak_qps"]
    assert math.isclose(qps_high["read_qps"] + qps_high["write_qps"], qps_high["peak_qps"], rel_tol=1e-5)


def test_calc_storage_retention_scaling():
    s_short = calc_storage(records_per_user=10, avg_record_size_kb=5, retention_days=10, dau=1000)
    s_long = calc_storage(records_per_user=10, avg_record_size_kb=5, retention_days=20, dau=1000)
    assert s_long["total_gb_retention"] > s_short["total_gb_retention"]
