import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from app.model_hub.validator import (
    validate_schema,
    validate_schema_vs_columns,
    validate_bundle_files,
    parse_schema_json,
)


class TestValidateSchema(unittest.TestCase):

    def _valid_schema(self):
        return {
            "fields": [
                {"name": "age", "type": "int", "ui": "slider", "min": 18, "max": 70, "default": 30},
                {"name": "title", "type": "category", "ui": "selectbox", "values": ["A", "B"]},
            ]
        }

    def test_valid_schema_no_issues(self):
        issues = validate_schema(self._valid_schema())
        self.assertEqual(issues, [])

    def test_missing_fields_key(self):
        issues = validate_schema({})
        self.assertTrue(len(issues) > 0)
        self.assertTrue(any("fields" in i for i in issues))

    def test_empty_fields_list(self):
        issues = validate_schema({"fields": []})
        self.assertTrue(len(issues) > 0)

    def test_duplicate_field_names(self):
        schema = {
            "fields": [
                {"name": "age", "type": "int", "ui": "slider", "min": 0, "max": 100},
                {"name": "age", "type": "float", "ui": "number_input"},
            ]
        }
        issues = validate_schema(schema)
        self.assertTrue(any("Duplicate" in i or "duplicate" in i for i in issues))

    def test_invalid_ui_type(self):
        schema = {"fields": [{"name": "x", "type": "int", "ui": "radio_button"}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_invalid_type_value(self):
        schema = {"fields": [{"name": "x", "type": "vector", "ui": "slider", "min": 0, "max": 10}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_slider_min_greater_than_max(self):
        schema = {"fields": [{"name": "x", "type": "int", "ui": "slider", "min": 100, "max": 10}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_slider_default_out_of_range(self):
        schema = {"fields": [{"name": "x", "type": "int", "ui": "slider", "min": 0, "max": 10, "default": 50}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_selectbox_missing_values(self):
        schema = {"fields": [{"name": "x", "type": "category", "ui": "selectbox"}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_selectbox_empty_values(self):
        schema = {"fields": [{"name": "x", "type": "category", "ui": "selectbox", "values": []}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_non_dict_input(self):
        issues = validate_schema("not a dict")
        self.assertTrue(len(issues) > 0)

    def test_layout_columns_valid(self):
        schema = {"layout": {"columns": 2}, "fields": [
            {"name": "x", "type": "int", "ui": "slider", "min": 0, "max": 10, "row": 1, "col_span": 2}
        ]}
        issues = validate_schema(schema)
        self.assertEqual(issues, [])

    def test_layout_columns_invalid_value(self):
        schema = {"layout": {"columns": 5}, "fields": [
            {"name": "x", "type": "int", "ui": "slider", "min": 0, "max": 10}
        ]}
        issues = validate_schema(schema)
        self.assertTrue(any("columns" in i for i in issues))

    def test_result_label_valid(self):
        schema = {"result_label": "Predicted Annual Salary (USD)", "fields": [
            {"name": "x", "type": "int", "ui": "slider", "min": 0, "max": 10}
        ]}
        issues = validate_schema(schema)
        self.assertEqual(issues, [])

    def test_result_label_empty_flagged(self):
        schema = {"result_label": "   ", "fields": [
            {"name": "x", "type": "int", "ui": "slider", "min": 0, "max": 10}
        ]}
        issues = validate_schema(schema)
        self.assertTrue(any("result_label" in i for i in issues))

    def test_old_schema_no_layout_still_valid(self):
        """Schemas without layout keys must remain valid (backward compat)."""
        schema = {"fields": [
            {"name": "age", "type": "int", "ui": "slider", "min": 18, "max": 70},
            {"name": "title", "type": "category", "ui": "selectbox", "values": ["A", "B"]},
        ]}
        self.assertEqual(validate_schema(schema), [])


class TestValidateSchemaVsColumns(unittest.TestCase):

    def test_direct_match_no_issues(self):
        schema = {"fields": [{"name": "age", "type": "int", "ui": "slider", "min": 0, "max": 100}]}
        columns = ["age"]
        issues = validate_schema_vs_columns(schema, columns)
        self.assertEqual(issues, [])

    def test_ohe_match_no_hard_errors(self):
        schema = {"fields": [
            {"name": "job_title", "type": "category", "ui": "selectbox",
             "values": ["Data Scientist", "ML Engineer"]}
        ]}
        columns = ["job_title_Data Scientist", "job_title_ML Engineer"]
        issues = validate_schema_vs_columns(schema, columns)
        hard_errors = [i for i in issues if "no matching column" in i.lower() or "missing" in i.lower()]
        self.assertEqual(hard_errors, [])

    def test_missing_field_is_flagged(self):
        schema = {"fields": [{"name": "salary", "type": "float", "ui": "number_input"}]}
        columns = ["age", "experience"]
        issues = validate_schema_vs_columns(schema, columns)
        self.assertTrue(len(issues) > 0)

    def test_extra_columns_noted(self):
        schema = {"fields": [{"name": "age", "type": "int", "ui": "slider", "min": 0, "max": 100}]}
        columns = ["age", "extra_engineered_feature"]
        issues = validate_schema_vs_columns(schema, columns)
        self.assertTrue(any("0.0" in i or "extra" in i.lower() or "not covered" in i.lower() for i in issues))


class TestValidateBundleFiles(unittest.TestCase):

    # Pickle format
    def test_pickle_all_files_present(self):
        missing = validate_bundle_files(["model.pkl", "columns.pkl", "schema.json"])
        self.assertEqual(missing, [])

    def test_pickle_missing_columns(self):
        missing = validate_bundle_files(["model.pkl", "schema.json"])
        self.assertTrue(len(missing) > 0)

    def test_pickle_missing_schema(self):
        missing = validate_bundle_files(["model.pkl", "columns.pkl"])
        self.assertIn("schema.json", missing)

    def test_pickle_extra_files_ignored(self):
        missing = validate_bundle_files(["model.pkl", "columns.pkl", "schema.json", "readme.txt"])
        self.assertEqual(missing, [])

    # ONNX format
    def test_onnx_all_files_present(self):
        missing = validate_bundle_files(["model.onnx", "columns.json", "schema.json"])
        self.assertEqual(missing, [])

    def test_onnx_missing_columns_json(self):
        missing = validate_bundle_files(["model.onnx", "schema.json"])
        self.assertTrue(len(missing) > 0)

    def test_onnx_with_aliases_valid(self):
        missing = validate_bundle_files(["model.onnx", "columns.json", "schema.json", "aliases.json"])
        self.assertEqual(missing, [])

    # detect_bundle_format
    def test_detect_onnx(self):
        from app.model_hub.validator import detect_bundle_format
        self.assertEqual(detect_bundle_format(["model.onnx", "columns.json", "schema.json"]), "onnx")

    def test_detect_pickle(self):
        from app.model_hub.validator import detect_bundle_format
        self.assertEqual(detect_bundle_format(["model.pkl", "columns.pkl", "schema.json"]), "pickle")

    def test_detect_unknown(self):
        from app.model_hub.validator import detect_bundle_format
        self.assertEqual(detect_bundle_format(["schema.json"]), "unknown")


class TestParseSchemaJson(unittest.TestCase):

    def test_valid_json_parses_correctly(self):
        import json
        schema = {"fields": [{"name": "x", "type": "int", "ui": "slider", "min": 0, "max": 10}]}
        raw = json.dumps(schema).encode("utf-8")
        parsed, issues = parse_schema_json(raw)
        self.assertEqual(issues, [])
        self.assertEqual(parsed["fields"][0]["name"], "x")

    def test_invalid_json_returns_empty_dict(self):
        parsed, issues = parse_schema_json(b"not valid json {{{")
        self.assertEqual(parsed, {})
        self.assertTrue(len(issues) > 0)

    def test_accepts_string_input(self):
        import json
        schema = {"fields": [{"name": "y", "type": "float", "ui": "number_input"}]}
        raw = json.dumps(schema)
        parsed, issues = parse_schema_json(raw)
        self.assertIsInstance(parsed, dict)




class TestValidateAliases(unittest.TestCase):

    def _schema_with_selectbox(self):
        return {
            "fields": [
                {"name": "role", "type": "category", "ui": "selectbox",
                 "values": ["CRA", "PV", "RA"]},
                {"name": "years", "type": "int", "ui": "slider", "min": 0, "max": 30},
            ]
        }

    def test_valid_aliases_no_issues(self):
        from app.model_hub.validator import validate_aliases
        aliases = {"role": {"CRA": "Clinical Research Associate", "PV": "Pharmacovigilance"}}
        issues = validate_aliases(aliases, self._schema_with_selectbox())
        self.assertEqual(issues, [])

    def test_unknown_field_name_flagged(self):
        from app.model_hub.validator import validate_aliases
        aliases = {"nonexistent_field": {"X": "Y"}}
        issues = validate_aliases(aliases, self._schema_with_selectbox())
        self.assertTrue(any("nonexistent_field" in i for i in issues))

    def test_unknown_model_value_flagged(self):
        from app.model_hub.validator import validate_aliases
        aliases = {"role": {"UNKNOWN_CODE": "Some Label"}}
        issues = validate_aliases(aliases, self._schema_with_selectbox())
        self.assertTrue(any("UNKNOWN_CODE" in i for i in issues))

    def test_duplicate_display_label_flagged(self):
        from app.model_hub.validator import validate_aliases
        aliases = {"role": {"CRA": "Same Label", "PV": "Same Label"}}
        issues = validate_aliases(aliases, self._schema_with_selectbox())
        self.assertTrue(any("duplicate" in i.lower() for i in issues))

    def test_empty_label_flagged(self):
        from app.model_hub.validator import validate_aliases
        aliases = {"role": {"CRA": ""}}
        issues = validate_aliases(aliases, self._schema_with_selectbox())
        self.assertTrue(len(issues) > 0)

    def test_non_dict_aliases_flagged(self):
        from app.model_hub.validator import validate_aliases
        issues = validate_aliases("not a dict", self._schema_with_selectbox())
        self.assertTrue(len(issues) > 0)

    def test_partial_aliases_valid(self):
        from app.model_hub.validator import validate_aliases
        # Only aliasing some values is allowed
        aliases = {"role": {"CRA": "Clinical Research Associate"}}
        issues = validate_aliases(aliases, self._schema_with_selectbox())
        self.assertEqual(issues, [])


if __name__ == '__main__':
    unittest.main()
