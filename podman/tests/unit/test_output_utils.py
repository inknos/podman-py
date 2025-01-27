import unittest

from podman.api import output_utils


class DemuxOutputTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_demux_output_with_empty_bytes(self):
        """Test demux_output with empty bytes."""
        self.assertEqual(output_utils.demux_output(b""), (None, None))

    def test_demux_output_with_stdout_only(self):
        """Test demux_output with stdout only.
        $ echo 'test'
        """
        stream = b'\x01\x00\x00\x00\x00\x00\x00\x05test\n'
        stdout = b'test\n'
        stderr = None
        self.assertEqual(output_utils.demux_output(stream), (stdout, stderr))

    def test_demux_output_with_stderr_only(self):
        """Test demux_output with stderr only.
        $ ls test
        """
        stream = b'\x02\x00\x00\x00\x00\x00\x00$ls: test: No such file or directory\n'
        stdout = None
        stderr = b'ls: test: No such file or directory\n'
        self.assertEqual(output_utils.demux_output(stream), (stdout, stderr))

    def test_demux_output_when_payload_is_bigger_than_data_bytes(self):
        """Test demux_output when payload is bigger than data bytes."""
        stream = b'\x01\x00\x00\x00\x00\x00\x00\x05testwithverybigsize'
        stdout = b'testw'
        stderr = None
        self.assertEqual(output_utils.demux_output(stream), (stdout, stderr))
