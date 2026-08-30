#!/usr/bin/env python3
"""
Test script for the Custom Event Processor feature (New Architecture).
"""
import unittest
import tempfile
import os
import zipfile
from pathlib import Path
import yaml
import numpy as np
import json

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript
from funscript.funscript import funscript_cache
from processing.event_processor import process_events, EventProcessorError
from processing.chapter_export import ChapterExportOptions


class TestEventProcessor(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory with dummy funscript and event files, and event definitions."""
        funscript_cache.clear()
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)

        # Create a minimal event_definitions.yml for tests (do not append to the full config file)
        self.event_definitions_path = self.test_path / "event_definitions.yml"
        with open(self.event_definitions_path, 'w') as f:
            f.write("""
normalization:
  volume: {max: 1.0}
  pulse_frequency: {max: 200.0}
  pulse_width: {max: 100.0}
definitions:
  good_slave_test:
    default_params:
      duration_ms: 1000
      volume_shift: 0.2
      pulse_freq_hz: 27
      pulse_width: 0.45
    steps:
      - operation: apply_linear_change
        axis: volume
        params:
          start_value: $volume_shift
          duration_ms: $duration_ms
          mode: additive
      - operation: apply_linear_change
        axis: pulse_frequency
        params:
          start_value: $pulse_freq_hz
          duration_ms: $duration_ms
          mode: overwrite
      - operation: apply_linear_change
        axis: pulse_width
        params:
          start_value: $pulse_width
          duration_ms: $duration_ms
          mode: overwrite

  edge_test:
    default_params:
      duration_ms: 1000
      volume_shift: 0.1
      buzz_freq: 2
      buzz_intensity: 0.5
      ramp_up: 100
    steps:
      - operation: apply_linear_change
        axis: volume
        params:
          start_value: $volume_shift
          duration_ms: $duration_ms
          mode: additive
      - operation: apply_modulation
        axis: volume
        params:
          waveform: sin
          frequency: $buzz_freq
          amplitude: $buzz_intensity
          duration_ms: $duration_ms
          ramp_in_ms: $ramp_up
          mode: additive
""")

        # Create a dummy user event file
        self.event_file_path = self.test_path / "test.events.yml"
        self.user_events_data = {
            "events": [
                {"time": 500, "name": "good_slave_test", "params": {"duration_ms": 1000}},
                {"time": 1500, "name": "edge_test", "params": {"duration_ms": 1000}}
            ]
        }
        with open(self.event_file_path, "w") as f:
            yaml.dump(self.user_events_data, f)

        # Create dummy funscript files
        self.volume_path = self.test_path / "test.volume.funscript"
        self.pulse_freq_path = self.test_path / "test.pulse_frequency.funscript"
        self.pulse_width_path = self.test_path / "test.pulse_width.funscript"
        
        self.actions = [{"at": i * 100, "pos": 50} for i in range(31)]
        self.pulse_freq_actions = [{"at": i * 100, "pos": 25} for i in range(31)]
        
        with open(self.volume_path, "w") as f: json.dump({"actions": self.actions}, f)
        with open(self.pulse_freq_path, "w") as f: json.dump({"actions": self.pulse_freq_actions}, f)
        with open(self.pulse_width_path, "w") as f: json.dump({"actions": self.actions}, f) # Same as volume initially

    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_event_processing(self):
        """Test the full event processing workflow with the new architecture."""
        process_events(str(self.event_file_path), True, self.event_definitions_path)

        mod_volume_fs = Funscript.from_file(self.volume_path)
        mod_pulse_freq_fs = Funscript.from_file(self.pulse_freq_path)
        mod_pulse_width_fs = Funscript.from_file(self.pulse_width_path)

        # Verify 'good_slave_test' (500ms to 1500ms)
        gs_indices = np.where((mod_volume_fs.x >= 0.5) & (mod_volume_fs.x < 1.5))[0]
        self.assertTrue(np.allclose(mod_volume_fs.y[gs_indices], 0.7))
        self.assertTrue(np.allclose(mod_pulse_freq_fs.y[gs_indices], 0.13)) # 27 / 200 = 0.135 -> 0.13
        self.assertTrue(np.allclose(mod_pulse_width_fs.y[gs_indices], 0.45))

        # Verify 'edge_test' (1500ms to 2500ms)
        edge_indices = np.where((mod_volume_fs.x >= 1.5) & (mod_volume_fs.x < 2.5))[0]
        self.assertFalse(np.allclose(mod_volume_fs.y[edge_indices], 0.6))
        self.assertGreater(np.max(mod_volume_fs.y[edge_indices]), 0.6)

        # Verify values outside event ranges are unchanged
        before_indices = np.where(mod_volume_fs.x < 0.5)[0]
        after_indices = np.where(mod_volume_fs.x >= 2.5)[0]
        after_pf_indices = np.where(mod_pulse_freq_fs.x >= 2.5)[0]
        self.assertTrue(np.allclose(mod_volume_fs.y[before_indices], 0.5))
        self.assertTrue(np.allclose(mod_volume_fs.y[after_indices], 0.5))
        self.assertTrue(np.allclose(mod_pulse_freq_fs.y[after_pf_indices], 0.25))


    def test_chapter_export_to_base_funscript(self):
        base_path = self.test_path / "test.funscript"
        with open(base_path, "w") as f:
            json.dump({"actions": self.actions, "creator": "test", "metadata": {"chapters": [{"name": "Old", "startTime": "00:00:00.000", "endTime": "00:00:00.200"}]}}, f)

        options = ChapterExportOptions(write_funscript=True)
        process_events(
            str(self.event_file_path),
            False,
            self.event_definitions_path,
            10,
            None,
            options,
        )

        with open(base_path, "r") as f:
            data = json.load(f)
        chapters = data["metadata"]["chapters"]
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]["name"], "General - Good Slave Test")
        self.assertEqual(chapters[0]["startTime"], "00:00:00.500")
        self.assertEqual(chapters[0]["endTime"], "00:00:01.500")
        self.assertEqual(chapters[1]["name"], "General - Edge Test")


class TestOrgasmCountdownDerive(unittest.TestCase):
    def test_default_duration_unchanged(self):
        from processing.event_processor import _derive_orgasm_countdown_params

        params = {
            'duration_ms': 46867,
            'orgasm_offset_ms': 21000,
            'ramp_ms': 1500,
            'seg_orgasm_ms': 999,  # overwritten
            'goodboy_duration_ms': 999,
        }
        _derive_orgasm_countdown_params(params, 'mcb_orgasm_countdown')
        self.assertEqual(params['seg_orgasm_ms'], 25867)
        self.assertEqual(params['goodboy_duration_ms'], 5000)

    def test_double_climax_doubles_goodboy(self):
        from processing.event_processor import _derive_orgasm_countdown_params

        params = {
            'duration_ms': 46867 + 25867,  # double climax
            'orgasm_offset_ms': 21000,
            'ramp_ms': 1500,
        }
        _derive_orgasm_countdown_params(params, 'mcb_orgasm_countdown_stroke_override')
        self.assertEqual(params['seg_orgasm_ms'], 51734)
        self.assertEqual(params['goodboy_duration_ms'], 10000)

    def test_short_climax_keeps_goodboy_min_5s(self):
        from processing.event_processor import _derive_orgasm_countdown_params

        params = {
            'duration_ms': 36000,  # climax ~15s (< base 25.867s)
            'orgasm_offset_ms': 21000,
            'ramp_ms': 1500,
        }
        _derive_orgasm_countdown_params(params, 'mcb_orgasm_countdown')
        self.assertEqual(params['seg_orgasm_ms'], 15000)
        self.assertEqual(params['goodboy_duration_ms'], 5000)

    def test_too_short_raises(self):
        from processing.event_processor import _derive_orgasm_countdown_params

        params = {
            'duration_ms': 21000,
            'orgasm_offset_ms': 21000,
            'ramp_ms': 1500,
        }
        with self.assertRaises(EventProcessorError):
            _derive_orgasm_countdown_params(params, 'mcb_orgasm_countdown')

    def test_other_events_untouched(self):
        from processing.event_processor import _derive_orgasm_countdown_params

        params = {'duration_ms': 99999, 'seg_orgasm_ms': 1, 'goodboy_duration_ms': 2}
        _derive_orgasm_countdown_params(params, 'mcb_goodboy')
        self.assertEqual(params['seg_orgasm_ms'], 1)
        self.assertEqual(params['goodboy_duration_ms'], 2)


class TestExtractComposite(unittest.TestCase):
    def test_default_pulse_amp_offsets(self):
        from processing.extract_composite import EXTRACT_BASE_MS, derive_extract_params

        params = {'duration_ms': EXTRACT_BASE_MS}
        derive_extract_params(params, 'mcb_extract')
        self.assertEqual(params['offset_pulse_0_ms'], 0)
        self.assertEqual(params['hz_pulse_0'], 60.0)
        self.assertEqual(params['hz_pulse_4'], 120.0)
        self.assertEqual(params['amp_0'], 0.01)
        self.assertEqual(params['amp_9'], 0.04)
        # last amp segment ends at duration
        self.assertEqual(
            params['offset_amp_9_ms'] + params['seg_amp_9_ms'],
            EXTRACT_BASE_MS,
        )

    def test_half_duration_scales(self):
        from processing.extract_composite import EXTRACT_BASE_MS, derive_extract_params

        params = {'duration_ms': EXTRACT_BASE_MS // 2}
        derive_extract_params(params, 'mcb_extract_4p')
        self.assertEqual(params['offset_pulse_1_ms'], int(round((EXTRACT_BASE_MS // 2) * 0.353)))

    def test_too_short_raises(self):
        from processing.extract_composite import derive_extract_params

        with self.assertRaises(ValueError):
            derive_extract_params({'duration_ms': 59999}, 'mcb_extract')

    def test_motion_3p_seeded(self):
        from processing.extract_composite import build_extract_motion_steps
        import random

        params = {'duration_ms': 60000, 'ramp_ms': 500, 'seed': 1}
        steps = build_extract_motion_steps(params, 'mcb_extract', rng=random.Random(1))
        self.assertGreater(len(steps), 10)
        axes = {s['axis'] for s in steps}
        self.assertTrue(any('alpha' in a for a in axes))
        self.assertTrue(any('beta' in a for a in axes))

    def test_motion_4p_seeded(self):
        from processing.extract_composite import build_extract_motion_steps
        import random

        params = {'duration_ms': 60000, 'ramp_ms': 500}
        steps = build_extract_motion_steps(params, 'mcb_extract_4p', rng=random.Random(2))
        axes = {s['axis'] for s in steps}
        self.assertEqual(axes, {'e1', 'e2', 'e3', 'e4'})

    def test_other_events_untouched(self):
        from processing.extract_composite import derive_extract_params, build_extract_motion_steps

        params = {'duration_ms': 1000}
        derive_extract_params(params, 'mcb_goodboy')
        self.assertNotIn('hz_pulse_0', params)
        self.assertEqual(build_extract_motion_steps(params, 'mcb_goodboy'), [])

    def test_l0_beats_every_second(self):
        from processing.extract_composite import detect_l0_beats, every_nth_beat, switch_offsets_to_segments
        import numpy as np

        # Triangle stroke: peaks/valleys every 0.5s → beats at 0.5,1.0,1.5,... within window
        t = np.linspace(0, 10, 201)
        y = np.abs((t % 1.0) - 0.5)  # valleys at n, peaks at n+0.5
        beats = detect_l0_beats(t, y, 0, 10000, min_interval_ms=50)
        self.assertGreater(len(beats), 5)
        switches = every_nth_beat(beats, 2)
        self.assertEqual(switches, beats[::2])
        segs = switch_offsets_to_segments(switches, 10000)
        self.assertEqual(segs[0][0], 0)
        self.assertEqual(segs[-1][0] + segs[-1][1], 10000)

    def test_beat_motion_uses_switch_offsets(self):
        from processing.extract_composite import build_extract_motion_steps
        import random

        params = {
            'duration_ms': 60000,
            'ramp_ms': 500,
            'switch_offsets_ms': [0, 2000, 4000, 8000, 16000, 32000],
        }
        steps = build_extract_motion_steps(
            params, 'mcb_extract_4p_beat', rng=random.Random(3)
        )
        axes = {s['axis'] for s in steps}
        self.assertEqual(axes, {'e1', 'e2', 'e3', 'e4'})
        # First non-ramp segment should start at a switch boundary
        motion = [s for s in steps if s['axis'] == 'e1']
        self.assertTrue(any(s['start_offset'] == 2000 for s in motion))

    def test_beat_derive_params(self):
        from processing.extract_composite import EXTRACT_BASE_MS, derive_extract_params

        params = {'duration_ms': EXTRACT_BASE_MS}
        derive_extract_params(params, 'mcb_extract_beat')
        self.assertEqual(params['hz_pulse_4'], 120.0)


if __name__ == "__main__":
    print("Running Custom Event Processor Tests (New Architecture)...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestEventProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestOrgasmCountdownDerive))
    suite.addTests(loader.loadTestsFromTestCase(TestExtractComposite))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    print("Tests finished.")
    if result.failures or result.errors: sys.exit(1)