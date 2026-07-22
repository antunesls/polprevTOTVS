import json
import tempfile
import unittest
from pathlib import Path

from src.telemetry_analyzer import (
    analyze_telemetry,
    filter_reports_by_telemetry,
    load_prometheus_metrics,
    normalize_routine_code,
)


class TelemetryAnalyzerTest(unittest.TestCase):
    def test_normalizes_routine_code_removing_parentheses_and_spaces(self):
        self.assertEqual(normalize_routine_code(" MATA103() "), "MATA103")

    def test_loads_prometheus_routine_and_user_metrics(self):
        content = """
# HELP protheus_routine_calls_total Total
protheus_routine_calls_total{branch="01",company="01",environment="OFICIAL",module="COM",routine="MATA103()"} 12.0
protheus_routine_user_calls_total{branch="01",company="01",environment="OFICIAL",module="COM",routine="MATA103()",user="JOAO",user_name="Joao Silva"} 5.0
protheus_routine_user_calls_total{branch="01",company="01",environment="OFICIAL",module="COM",routine="MATA103()",user="MARIA",user_name="Maria Souza"} 7.0
""".strip()

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir) / "metrics.txt"
            metrics_path.write_text(content, encoding="utf-8")

            metrics = load_prometheus_metrics(str(metrics_path))

        self.assertEqual(metrics["routine_totals"]["MATA103"]["calls"], 12)
        self.assertEqual(metrics["routine_users"]["MATA103"]["JOAO"]["calls"], 5)
        self.assertEqual(metrics["routine_users"]["MATA103"]["MARIA"]["user_name"], "Maria Souza")

    def test_analyzes_usage_against_effective_user_access(self):
        content = """
protheus_routine_calls_total{module="COM",routine="MATA103()"} 12.0
protheus_routine_calls_total{module="COM",routine="MATA999()"} 3.0
protheus_routine_user_calls_total{module="COM",routine="MATA103()",user="JOAO",user_name="Joao Silva"} 12.0
protheus_routine_user_calls_total{module="COM",routine="MATA999()",user="MARIA",user_name="Maria Souza"} 3.0
""".strip()
        reports = [
            {
                "user": "JOAO",
                "user_name": "Joao Silva",
                "user_depto": "COMERCIAL",
                "routines_summary": [
                    {"routine": "MATA103", "description": "Documento Entrada", "effective_access": "PERMITIDO"},
                    {"routine": "MATA010", "description": "Produtos", "effective_access": "PERMITIDO"},
                ],
            },
            {
                "user": "MARIA",
                "user_name": "Maria Souza",
                "user_depto": "FINANCEIRO",
                "routines_summary": [
                    {"routine": "MATA103", "description": "Documento Entrada", "effective_access": "NAO_PERMITIDO"},
                ],
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir) / "metrics.txt"
            output_path = Path(tmpdir) / "analysis.json"
            metrics_path.write_text(content, encoding="utf-8")

            result = analyze_telemetry(str(metrics_path), reports=reports, output_json_path=str(output_path))

            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result["summary"]["routines_used"], 2)
        self.assertEqual(result["top_routines"][0]["routine"], "MATA103")
        self.assertEqual(result["top_users_by_routine"]["MATA103"][0]["user"], "JOAO")
        self.assertEqual(result["unused_allowed_routines"][0]["routine"], "MATA010")
        self.assertEqual(result["used_without_effective_access"][0]["routine"], "MATA999")
        self.assertEqual(result["used_without_effective_access"][0]["user"], "MARIA")
        self.assertEqual(saved["summary"], result["summary"])

    def test_filters_reports_by_telemetry_before_rule_generation(self):
        reports = [
            {
                "user": "JOAO",
                "routines_summary": [
                    {"routine": "MATA103", "description": "Usada"},
                    {"routine": "MATA010", "description": "Sem uso"},
                ],
            }
        ]
        metrics = {
            "routine_totals": {
                "MATA103": {"routine": "MATA103", "calls": 3},
                "MATA010": {"routine": "MATA010", "calls": 0},
            },
            "routine_users": {},
        }

        filtered, summary = filter_reports_by_telemetry(reports, metrics=metrics, min_calls=1)

        self.assertEqual([r["routine"] for r in filtered[0]["routines_summary"]], ["MATA103"])
        self.assertEqual(summary["removed_routines"], 1)
        self.assertEqual(filtered[0]["_telemetry_filter"]["removed_routines"], ["MATA010"])
        self.assertEqual(reports[0]["routines_summary"][1]["routine"], "MATA010")

    def test_filter_keeps_routine_when_user_metric_exists_even_without_aggregate_metric(self):
        reports = [{"user": "MARIA", "routines_summary": [{"routine": "FINA050"}]}]
        metrics = {
            "routine_totals": {},
            "routine_users": {"FINA050": {"MARIA": {"calls": 2}}},
        }

        filtered, summary = filter_reports_by_telemetry(reports, metrics=metrics, min_calls=1)

        self.assertEqual(filtered[0]["routines_summary"][0]["routine"], "FINA050")
        self.assertEqual(summary["removed_routines"], 0)


if __name__ == "__main__":
    unittest.main()
