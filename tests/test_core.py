import tempfile
import unittest
import zipfile
import io
import xml.etree.ElementTree as ET

from api.export_template_excel import generate_excel_from_template
from app_server import run_motion_tracking


class ExportTests(unittest.TestCase):
    def test_generated_workbook_is_valid_zip(self):
        payload = {
            "date": "2026-11-23",
            "process": "Test",
            "employee": "Operator",
            "steps": [
                {"name": "A", "runs": [10.0, 12.0]},
                {"name": "B", "runs": [20.0, 22.0]},
            ],
        }
        output = generate_excel_from_template(payload)
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as workbook:
            workbook.write(output)
            workbook.flush()
            with zipfile.ZipFile(workbook.name) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("xl/worksheets/sheet1.xml", archive.namelist())

    def test_rejects_more_steps_than_template_supports(self):
        payload = {"steps": [{"name": str(i), "runs": [1]} for i in range(18)]}
        with self.assertRaisesRegex(ValueError, "17"):
            generate_excel_from_template(payload)

    def test_best_round_ignores_incomplete_rounds(self):
        payload = {
            "swctPlotMode": "best_round",
            "steps": [
                {"name": "A", "runs": [10.0, 1.0]},
                {"name": "B", "runs": [20.0, None]},
            ],
        }
        output = generate_excel_from_template(payload)
        with zipfile.ZipFile(io.BytesIO(output)) as archive:
            root = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
        ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        values = {
            cell.attrib["r"]: cell.findtext("x:v", namespaces=ns)
            for cell in root.findall(".//x:c", ns)
            if cell.attrib.get("r") in {"G7", "G9"}
        }
        self.assertEqual(values, {"G7": "10.00", "G9": "20.00"})


class MotionTrackingTests(unittest.TestCase):
    def test_unreadable_video_has_clear_error(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as video:
            video.write(b"not a video")
            video.flush()
            with self.assertRaisesRegex(ValueError, "ไม่สามารถเปิดวิดีโอ"):
                run_motion_tracking(video.name, [])


if __name__ == "__main__":
    unittest.main()
