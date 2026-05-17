"""
Tests for ServicesMonitor.

Tests process detection using psutil/pgrep by spawning real dummy
processes, checking their detection, killing them, and verifying the
bitmask updates accordingly.
"""

import os
import signal
import subprocess
import time
import unittest

from companion_health.services.monitor import ServicesMonitor


class TestServicesMonitorUnit(unittest.TestCase):
    """Unit tests for ServicesMonitor basic behavior."""

    def test_empty_services_returns_zero(self):
        """No services configured should return 0 bitmask."""
        mon = ServicesMonitor([])
        self.assertEqual(mon.get_status(), 0)

    def test_none_services_returns_zero(self):
        """None passed for services should return 0 bitmask."""
        mon = ServicesMonitor(None)
        self.assertEqual(mon.get_status(), 0)

    def test_max_services_truncation(self):
        """More than 32 services should be truncated."""
        names = [f"svc_{i}" for i in range(40)]
        mon = ServicesMonitor(names)
        self.assertEqual(len(mon.services), 32)

    def test_nonexistent_process_returns_false(self):
        """A process name that definitely does not exist returns False."""
        mon = ServicesMonitor(['__cch_nonexistent_test_process_xyz__'])
        self.assertFalse(mon.check_service('__cch_nonexistent_test_process_xyz__'))

    def test_nonexistent_bitmask_is_zero(self):
        """Bitmask for a single nonexistent service should be 0."""
        mon = ServicesMonitor(['__cch_nonexistent_test_process_xyz__'])
        self.assertEqual(mon.get_status(), 0)

    def test_failed_services_lists_missing(self):
        """get_failed_services should return names that are not running."""
        mon = ServicesMonitor(['__cch_fake_a__', '__cch_fake_b__'])
        failed = mon.get_failed_services()
        self.assertIn('__cch_fake_a__', failed)
        self.assertIn('__cch_fake_b__', failed)

    def test_running_services_empty_for_missing(self):
        """get_running_services should be empty when nothing is running."""
        mon = ServicesMonitor(['__cch_fake_a__'])
        running = mon.get_running_services()
        self.assertEqual(running, [])

    def test_known_running_process_detected(self):
        """A process we know is running (like python3) should be found."""
        # The test itself is running under python3, so this must pass
        mon = ServicesMonitor(['python3'])
        self.assertTrue(mon.check_service('python3'))

    def test_known_process_bitmask(self):
        """Bitmask should have bit 0 set for a known running process."""
        mon = ServicesMonitor(['python3'])
        status = mon.get_status()
        self.assertEqual(status & 1, 1)

    def test_mixed_bitmask(self):
        """Mix of running and nonexistent should set only correct bits."""
        mon = ServicesMonitor([
            'python3',                              # bit 0 - running
            '__cch_nonexistent_test_process_xyz__',  # bit 1 - not running
        ])
        status = mon.get_status()
        self.assertEqual(status & 0b01, 1, "bit 0 should be set (python3)")
        self.assertEqual(status & 0b10, 0, "bit 1 should be clear (nonexistent)")

    def test_status_dict_types(self):
        """get_status_dict should return str->bool mapping."""
        mon = ServicesMonitor(['python3', '__cch_fake__'])
        d = mon.get_status_dict()
        self.assertIsInstance(d, dict)
        self.assertIn('python3', d)
        self.assertIn('__cch_fake__', d)
        self.assertIsInstance(d['python3'], bool)


class TestServicesMonitorLiveProcess(unittest.TestCase):
    """Integration tests that spawn and kill real processes.

    These tests create a dummy long-running process, verify that
    ServicesMonitor detects it via the bitmask, then kill it and
    verify the bitmask updates.
    """

    DUMMY_SCRIPT = "cch_test_dummy_service"

    def setUp(self):
        """Spawn a dummy background process for testing."""
        # Use a unique name so we don't collide with real processes.
        # We launch "sleep 300" with a process name we can grep for
        # by wrapping it in a bash command that sets argv[0].
        self.proc = subprocess.Popen(
            ['bash', '-c', f'exec -a {self.DUMMY_SCRIPT} sleep 300'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Give the OS a moment to register the process
        time.sleep(0.3)

    def tearDown(self):
        """Clean up the dummy process."""
        try:
            self.proc.kill()
            self.proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def test_detect_spawned_process(self):
        """ServicesMonitor should detect our dummy process."""
        mon = ServicesMonitor([self.DUMMY_SCRIPT])
        self.assertTrue(
            mon.check_service(self.DUMMY_SCRIPT),
            f"Should detect running process '{self.DUMMY_SCRIPT}'"
        )

    def test_bitmask_set_for_spawned_process(self):
        """Bitmask bit 0 should be set when dummy is running."""
        mon = ServicesMonitor([self.DUMMY_SCRIPT])
        status = mon.get_status()
        self.assertEqual(
            status & 1, 1,
            "Bit 0 should be set for running dummy service"
        )

    def test_bitmask_clears_after_kill(self):
        """After killing the dummy process, bit 0 should clear."""
        mon = ServicesMonitor([self.DUMMY_SCRIPT])

        # Verify it is detected first
        status_before = mon.get_status()
        self.assertEqual(status_before & 1, 1, "Should be running before kill")

        # Kill it
        self.proc.kill()
        self.proc.wait(timeout=5)
        time.sleep(0.5)  # Let the OS reap the process

        # Verify it is now gone
        status_after = mon.get_status()
        self.assertEqual(
            status_after & 1, 0,
            "Bit 0 should be clear after killing the process"
        )

    def test_failed_services_after_kill(self):
        """get_failed_services should list the dummy after it is killed."""
        mon = ServicesMonitor([self.DUMMY_SCRIPT])

        # Kill it
        self.proc.kill()
        self.proc.wait(timeout=5)
        time.sleep(0.5)

        failed = mon.get_failed_services()
        self.assertIn(self.DUMMY_SCRIPT, failed)

    def test_multi_service_bitmask_partial_kill(self):
        """With two services, killing one should only clear its bit."""
        # Spawn a second dummy
        proc2_name = "cch_test_dummy_svc2"
        proc2 = subprocess.Popen(
            ['bash', '-c', f'exec -a {proc2_name} sleep 300'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.3)

        try:
            mon = ServicesMonitor([self.DUMMY_SCRIPT, proc2_name])

            # Both should be running
            status = mon.get_status()
            self.assertEqual(status & 0b11, 0b11, "Both bits should be set")

            # Kill only the first one
            self.proc.kill()
            self.proc.wait(timeout=5)
            time.sleep(0.5)

            status = mon.get_status()
            self.assertEqual(status & 0b01, 0, "Bit 0 should be clear")
            self.assertEqual(status & 0b10, 0b10, "Bit 1 should still be set")
        finally:
            proc2.kill()
            proc2.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
