import unittest

from common.complexDict import ComplexDict


class ComplexDictPathKeyTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "A": {
                "AirPosZExt/Ext": "1.5mm",
                "Slash\\Key": "x",
                "B": {"C": 3},
            }
        }
        self.ops = ComplexDict(self.data)

    def test_get_prefers_existing_key_with_separator(self):
        self.assertEqual(self.ops["A/AirPosZExt/Ext"], "1.5mm")
        self.assertEqual(self.ops["A/Slash/Key"], "x")

    def test_set_updates_existing_key_with_separator(self):
        self.ops["A/AirPosZExt/Ext"] = "2mm"
        self.assertEqual(self.data["A"]["AirPosZExt/Ext"], "2mm")
        self.assertNotIn("AirPosZExt", self.data["A"])

    def test_delete_removes_existing_key_with_separator(self):
        del self.ops["A/AirPosZExt/Ext"]
        self.assertNotIn("AirPosZExt/Ext", self.data["A"])

    def test_normal_nested_path_still_works(self):
        self.assertEqual(self.ops["A/B/C"], 3)


if __name__ == "__main__":
    unittest.main()