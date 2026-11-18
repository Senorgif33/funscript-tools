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
        derive_extract_params(params, 'mcb_extract_dual')
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
        derive_extract_params(params, 'mcb_extract_dual')
        self.assertEqual(params['offset_pulse_1_ms'], int(round((EXTRACT_BASE_MS // 2) * 0.353)))

    def test_too_short_raises(self):
        from processing.extract_composite import derive_extract_params

        with self.assertRaises(ValueError):
            derive_extract_params({'duration_ms': 59999}, 'mcb_extract_dual')

    def test_motion_dual_both_geometries(self):
        from processing.extract_composite import (
            _build_3p_motion,
            _build_4p_motion,
            build_extract_motion_steps,
            resolve_extract_segments,
        )
        import random

        params = {'duration_ms': 60000, 'ramp_ms': 500, 'seed': 1}
        steps = build_extract_motion_steps(params, 'mcb_extract_dual')
        axes = {s['axis'] for s in steps}
        self.assertTrue(any('alpha' in a for a in axes))
        self.assertTrue(any('beta' in a for a in axes))
        self.assertTrue({'e1', 'e2', 'e3', 'e4'} <= axes)

        segments = resolve_extract_segments(dict(params), 'mcb_extract_dual')
        solo3 = _build_3p_motion(60000, random.Random(1), params, segments)
        solo4 = _build_4p_motion(60000, random.Random(1), params, segments)
        self.assertEqual(
            [s for s in steps if s['axis'] not in ('e1', 'e2', 'e3', 'e4')],
            solo3,
        )
        self.assertEqual(
            [s for s in steps if s['axis'] in ('e1', 'e2', 'e3', 'e4')],
            solo4,
        )

    def test_other_events_untouched(self):
        from processing.extract_composite import derive_extract_params, build_extract_motion_steps

        params = {'duration_ms': 1000}
        derive_extract_params(params, 'mcb_goodboy')
        self.assertNotIn('hz_pulse_0', params)
        self.assertEqual(build_extract_motion_steps(params, 'mcb_goodboy'), [])

    def test_yaml_shell_written_once(self):
        import yaml
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        data = yaml.safe_load((root / 'config.event_definitions.yml').read_text(encoding='utf-8'))
        defs = data['definitions']
        for old in ('mcb_extract', 'mcb_extract_4p', 'mcb_extract_beat', 'mcb_extract_4p_beat'):
            self.assertNotIn(old, defs)
        self.assertIn('corrupt_4p', defs)
        for name in ('mcb_extract_dual', 'mcb_extract_beat_dual'):
            axes = [step['axis'] for step in defs[name]['steps']]
            self.assertEqual(axes.count('pulse_width'), 1)
            self.assertEqual(sum(a == 'pulse_frequency' for a in axes), 5)
            self.assertEqual(sum(a.startswith('volume') for a in axes), 10)
            self.assertFalse(any('alpha' in a or 'beta' in a or a.startswith('e') for a in axes))

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
            params, 'mcb_extract_beat_dual', rng=random.Random(3)
        )
        axes = {s['axis'] for s in steps}
        self.assertTrue(any('alpha' in a for a in axes))
        self.assertTrue({'e1', 'e2', 'e3', 'e4'} <= axes)
        alpha_offs = {s['start_offset'] for s in steps if 'alpha' in s['axis']}
        e1_offs = {s['start_offset'] for s in steps if s['axis'] == 'e1'}
        self.assertIn(2000, alpha_offs)
        self.assertIn(2000, e1_offs)

    def test_beat_derive_params(self):
        from processing.extract_composite import EXTRACT_BASE_MS, derive_extract_params

        params = {'duration_ms': EXTRACT_BASE_MS}
        derive_extract_params(params, 'mcb_extract_beat_dual')
        self.assertEqual(params['hz_pulse_4'], 120.0)

    def test_beat_min_duration_25s(self):
        from processing.extract_composite import derive_extract_params

        ok = {'duration_ms': 25000}
        derive_extract_params(ok, 'mcb_extract_beat_dual')
        self.assertIn('hz_pulse_0', ok)

        with self.assertRaises(ValueError):
            derive_extract_params({'duration_ms': 24999}, 'mcb_extract_beat_dual')

        # SCD extract still requires 60s
        with self.assertRaises(ValueError):
            derive_extract_params({'duration_ms': 25000}, 'mcb_extract_dual')


class TestCollectTimelineApplyIssues(unittest.TestCase):
    def test_extract_too_short_is_reported(self):
        from processing.event_processor import collect_timeline_apply_issues

        defs = {
            'mcb_extract_beat_dual': {
                'default_params': {'duration_ms': 265367, 'pulse_width': 65, 'ramp_ms': 500},
                'steps': [],
            }
        }
        events = [{
            'time': 1000,
            'name': 'mcb_extract_beat_dual',
            'params': {'duration_ms': 10000},
        }]
        issues = collect_timeline_apply_issues(events, defs)
        self.assertEqual(len(issues), 1)
        self.assertIn('25000', issues[0])
        self.assertIn('t=1000', issues[0])

    def test_valid_extract_has_no_issues(self):
        from processing.event_processor import collect_timeline_apply_issues

        defs = {
            'mcb_extract_beat_dual': {
                'default_params': {'duration_ms': 265367, 'pulse_width': 65, 'ramp_ms': 500},
                'steps': [],
            }
        }
        events = [{
            'time': 0,
            'name': 'mcb_extract_beat_dual',
            'params': {'duration_ms': 25000},
        }]
        self.assertEqual(collect_timeline_apply_issues(events, defs), [])

    def test_unknown_event_is_reported(self):
        from processing.event_processor import collect_timeline_apply_issues

        issues = collect_timeline_apply_issues(
            [{'time': 5, 'name': 'nope', 'params': {}}],
            {},
        )
        self.assertTrue(any('not defined' in m for m in issues))


class TestEmptyEventsFile(unittest.TestCase):
    def test_writes_empty_template_beside_funscript(self):
        from processing.event_processor import events_path_for_funscript, write_empty_events_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            funscript_path = root / "clip.funscript"
            funscript_path.write_text("{}", encoding="utf-8")
            events_path = events_path_for_funscript(funscript_path)
            self.assertEqual(events_path, root / "clip.events.yml")
            write_empty_events_file(events_path)
            text = events_path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) or {}
            self.assertEqual(data.get("events") or [], [])
            self.assertIn("Custom Events File", text)
            self.assertIn("events:", text)


if __name__ == "__main__":
    print("Running Custom Event Processor Tests (New Architecture)...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestEventProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestOrgasmCountdownDerive))
    suite.addTests(loader.loadTestsFromTestCase(TestExtractComposite))
    suite.addTests(loader.loadTestsFromTestCase(TestCollectTimelineApplyIssues))
    suite.addTests(loader.loadTestsFromTestCase(TestEmptyEventsFile))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    print("Tests finished.")
    if result.failures or result.errors: sys.exit(1)