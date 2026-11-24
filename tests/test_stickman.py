import shutil
import tempfile
import unittest
from pathlib import Path
from stickman import validate, timeline, subtitles, frame, render, load_scene

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.scenes=validate({"scenes":[{"seconds":.5,"caption":"Hello","actors":[{"action":"wave","x":.3},{"action":"jump","x":.7}]},{"seconds":1,"caption":"Next","action":"run"}]})

    def test_defaults(self):
        self.assertEqual(self.scenes[1]["actors"][0]["scale"],1)

    def test_invalid(self):
        for bad in ({"scenes":[]},{"scenes":[{"seconds":True}]},{"scenes":[{"seconds":1,"action":"fly"}]},{"scenes":[{"seconds":1,"actors":[{"x":2}]}]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(bad)

    def test_timeline(self):
        self.assertEqual(timeline(self.scenes,24),[(0,0,12),(1,12,36)])

    def test_subtitles(self):
        self.assertIn("00:00:00,500 --> 00:00:01,500",subtitles(self.scenes,24))

    def test_frame(self):
        a=frame(self.scenes[0],0,360,640)
        b=frame(self.scenes[0],.16,360,640)
        self.assertEqual(a.size,(360,640))
        self.assertNotEqual(a.tobytes(),b.tobytes())
        self.assertEqual(a.tobytes(),frame(self.scenes[0],0,360,640).tobytes())

    def test_example(self):
        self.assertEqual(len(load_scene(Path(__file__).resolve().parents[1]/"examples"/"demo.json")),3)

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg is not installed")
    def test_render(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/"test.mp4"
            render(self.scenes,output,180,320,12)
            self.assertGreater(output.stat().st_size,1000)

if __name__=="__main__":
    unittest.main()
