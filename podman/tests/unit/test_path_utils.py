import datetime
import os
import unittest
import tempfile
from unittest import mock

from podman import api


class PathUtilsTestCase(unittest.TestCase):
    def setUp(self):
        self.xdg_runtime_dir = os.getenv('XDG_RUNTIME_DIR')

    @mock.patch.dict(os.environ, clear=True)
    def test_get_runtime_dir_env_var_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ['XDG_RUNTIME_DIR'] = str(tmpdir)
            self.assertEqual(str(tmpdir), api.path_utils.get_runtime_dir())

    @mock.patch.dict(os.environ, clear=True)
    def test_get_runtime_dir_env_var_not_set(self):
        if not self.xdg_runtime_dir:
            self.skipTest('XDG_RUNTIME_DIR must be set for this test.')
        if self.xdg_runtime_dir.startswith('/run/user/'):
            self.skipTest("XDG_RUNTIME_DIR in /run/user/, can't check")
        self.assertNotEqual(self.xdg_runtime_dir, api.path_utils.get_runtime_dir())

    @mock.patch('os.path.isdir', lambda d: False)
    @mock.patch.dict(os.environ, clear=True)
    def test_get_runtime_dir_env_var_not_set_and_no_run(self):
        """Fake that XDG_RUNTIME_DIR is not set and /run/user/ does not exist."""
        if not self.xdg_runtime_dir:
            self.skipTest('XDG_RUNTIME_DIR must be set to fetch a working dir.')
        self.assertNotEqual(self.xdg_runtime_dir, api.path_utils.get_runtime_dir())

    @mock.patch.dict(os.environ, clear=True)
    def test_get_xdg_config_home_env_var_not_set(self):
        """Fake taht XDG_RUNTIME_DIR is not set"""
        self.assertEqual(
            os.path.join(os.path.expanduser('~'), '.config'), api.path_utils.get_xdg_config_home()
        )


if __name__ == '__main__':  # pragma: no cover
    unittest.main()  # pragma: no cover
