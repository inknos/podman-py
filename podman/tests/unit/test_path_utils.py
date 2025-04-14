import os
import unittest
import tempfile
import stat
import errno
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

    @mock.patch('os.path.isdir', lambda d: True)
    @mock.patch('os.getuid', lambda: 1000)
    @mock.patch.dict(os.environ, clear=True)
    def test_get_runtime_dir_use_run_user(self):
        """Test when XDG_RUNTIME_DIR is not set but /run/user/UID exists."""
        runtime_dir = api.path_utils.get_runtime_dir()
        self.assertEqual(runtime_dir, '/run/user/1000')

    @mock.patch('os.path.isdir', lambda d: False)
    @mock.patch('os.mkdir')
    @mock.patch('os.lstat')
    @mock.patch.dict(os.environ, clear=True)
    def test_get_runtime_dir_fallback_dir_not_exist(self, mock_lstat, mock_mkdir):
        """Test fallback directory creation when it doesn't exist."""
        # Simulate ENOENT for os.lstat (file not found)
        mock_lstat.side_effect = OSError(errno.ENOENT, "No such file or directory")

        api.path_utils.get_runtime_dir()
        # Check if mkdir was called with correct arguments
        mock_mkdir.assert_called_once()
        # args should include the fallback path and 0o700 permissions
        self.assertEqual(mock_mkdir.call_args[0][1], 0o700)

    @mock.patch('os.path.isdir', lambda d: False)
    @mock.patch('os.lstat')
    @mock.patch('os.unlink')
    @mock.patch('os.mkdir')
    @mock.patch.dict(os.environ, clear=True)
    def test_get_runtime_dir_fallback_not_dir(self, mock_mkdir, mock_unlink, mock_lstat):
        """Test fallback when it exists but is not a directory."""
        # Create a fake stat result that represents a file, not a directory
        stat_result = mock.Mock()
        stat_result.st_mode = 0o644  # regular file
        mock_lstat.return_value = stat_result

        api.path_utils.get_runtime_dir()

        # Should unlink the file and create a directory
        mock_unlink.assert_called_once()
        mock_mkdir.assert_called_once()

    @mock.patch('os.path.isdir', lambda d: False)
    @mock.patch('os.lstat')
    @mock.patch('os.rmdir')
    @mock.patch('os.mkdir')
    @mock.patch.dict(os.environ, clear=True)
    def test_get_runtime_dir_fallback_wrong_permissions(self, mock_mkdir, mock_rmdir, mock_lstat):
        """Test fallback when it exists but has wrong permissions."""
        # Create a fake stat result with wrong owner or permissions
        stat_result = mock.Mock()
        stat_result.st_mode = stat.S_IFDIR | 0o777  # directory with wrong permissions
        stat_result.st_uid = os.getuid() + 1  # wrong owner
        mock_lstat.return_value = stat_result

        api.path_utils.get_runtime_dir()

        # Should remove the directory and create a new one
        mock_rmdir.assert_called_once()
        mock_mkdir.assert_called_once()

    @mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': '/custom/config/path'})
    def test_get_xdg_config_home_from_env(self):
        """Test get_xdg_config_home when XDG_CONFIG_HOME is set."""
        self.assertEqual(api.path_utils.get_xdg_config_home(), '/custom/config/path')

    @mock.patch.dict(os.environ, clear=True)
    @mock.patch('os.path.expanduser', return_value='/home/user')
    def test_get_xdg_config_home_default(self, mock_expanduser):
        """Test get_xdg_config_home when XDG_CONFIG_HOME is not set."""
        self.assertEqual(api.path_utils.get_xdg_config_home(), '/home/user/.config')


if __name__ == '__main__':
    unittest.main()
