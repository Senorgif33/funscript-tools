#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from ui.custom_events_builder import (
    apply_params_keeping_time,
    defaults_keeping_event_duration,
    params_for_saved_defaults,
)


class TestEventDefaultPlacement(unittest.TestCase):
    def test_save_as_default_keeps_duration_field_but_does_not_overwrite_it(self):
        saved = params_for_saved_defaults({
            'duration_ms': 120000,
            'time': 45000,
            'pulse_width': 40,
            'ramp_ms': 250,
        })
        self.assertEqual(saved, {'pulse_width': 40, 'ramp_ms': 250})

        defaults = {'duration_ms': 265367, 'pulse_width': 65, 'ramp_ms': 500}
        defaults.update(saved)
        self.assertEqual(defaults['duration_ms'], 265367)
        self.assertEqual(defaults['pulse_width'], 40)

    def test_reset_keeps_this_events_duration(self):
        merged = defaults_keeping_event_duration(
            {'duration_ms': 265367, 'pulse_width': 65, 'ramp_ms': 500},
            {'duration_ms': 80000, 'pulse_width': 10, 'ramp_ms': 100},
        )
        self.assertEqual(merged['duration_ms'], 80000)
        self.assertEqual(merged['pulse_width'], 65)
        self.assertEqual(merged['ramp_ms'], 500)

    def test_apply_to_all_updates_params_and_leaves_start_times(self):
        events = [
            {'time': 1000, 'name': 'edge', 'params': {'duration_ms': 2000, 'intensity': 0.2}},
            {'time': 9000, 'name': 'edge', 'params': {'duration_ms': 3000, 'intensity': 0.2}},
            {'time': 5000, 'name': 'buzz', 'params': {'duration_ms': 1000, 'intensity': 0.9}},
        ]
        n = apply_params_keeping_time(
            events,
            'edge',
            {'duration_ms': 4000, 'intensity': 0.5},
        )
        self.assertEqual(n, 2)
        self.assertEqual(events[0]['time'], 1000)
        self.assertEqual(events[1]['time'], 9000)
        self.assertEqual(events[0]['params']['duration_ms'], 2000)
        self.assertEqual(events[1]['params']['duration_ms'], 3000)
        self.assertEqual(events[1]['params']['intensity'], 0.5)
        self.assertEqual(events[2]['params']['intensity'], 0.9)
        self.assertEqual(events[2]['time'], 5000)


if __name__ == "__main__":
    unittest.main()
