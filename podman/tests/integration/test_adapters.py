import getpass
import unittest
import subprocess
import pytest

import time

from podman import PodmanClient
from podman.tests.integration import base, utils


class AdapterIntegrationTest(base.IntegrationTest):
    def setUp(self):
        super().setUp()

    def test_00_ssh_connectivity(self):
        """Test SSH connectivity before attempting client connection to fail fast."""
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "ConnectTimeout=2",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "PasswordAuthentication=no",
                    "-o",
                    "BatchMode=yes",
                    f"{getpass.getuser()}@localhost",
                    "exit",
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                pytest.exit(
                    f"SSH connection to localhost failed (return code {result.returncode}). "
                    f"SSH error: {result.stderr.decode() if result.stderr else 'No error output'}. "
                    f"Stopping test suite to prevent hanging."
                )
        except subprocess.TimeoutExpired:
            pytest.exit(
                "SSH connection to localhost timed out. Stopping test suite to prevent hanging."
            )
        except FileNotFoundError:
            self.skipTest("SSH client not found.")

    def test_ssh_ping(self):
        with PodmanClient(
            base_url=f"http+ssh://{getpass.getuser()}@localhost:22{self.socket_file}"
        ) as client:
            self.assertTrue(client.ping())

        with PodmanClient(
            base_url=f"ssh://{getpass.getuser()}@localhost:22{self.socket_file}"
        ) as client:
            self.assertTrue(client.ping())

    def test_unix_ping(self):
        with PodmanClient(base_url=f"unix://{self.socket_file}") as client:
            self.assertTrue(client.ping())

        with PodmanClient(base_url=f"http+unix://{self.socket_file}") as client:
            self.assertTrue(client.ping())

    def test_tcp_ping(self):
        podman = utils.PodmanLauncher(
            "tcp:localhost:8889",
            podman_path=base.IntegrationTest.podman,
            log_level=self.log_level,
        )
        try:
            podman.start(check_socket=False)
            time.sleep(0.5)

            with PodmanClient(base_url="tcp:localhost:8889") as client:
                self.assertTrue(client.ping())

            with PodmanClient(base_url="http://localhost:8889") as client:
                self.assertTrue(client.ping())
        finally:
            podman.stop()


if __name__ == '__main__':
    unittest.main()
