import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TravelPlannerTests(unittest.TestCase):
    def test_import_without_llm_key_does_not_exit(self):
        env = os.environ.copy()
        env.pop("LLM_API_KEY", None)
        env.pop("KAKAO_API_KEY", None)
        env["PYTHONPATH"] = str(ROOT)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import travel_planner; print(travel_planner.get_travel_recommendation('2025-08-01')['recommended_city'])",
                ],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        final_line = result.stdout.strip().splitlines()[-1]
        self.assertIn(final_line, {"제주", "서울", "부산", "경주", "강릉", "속초", "전주"})


if __name__ == "__main__":
    unittest.main()
