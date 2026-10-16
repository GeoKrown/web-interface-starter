r"""Run after setup: .venv\Scripts\python.exe -m unittest -v"""
import argparse
import hashlib
import json
import socket
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

import bootstrap
import run


class StarterTests(unittest.TestCase):
    def test_archive_verification(self):
        data = b"example archive"
        line = hashlib.sha512(data).hexdigest() + "  caddy.zip"
        bootstrap.verify_archive(data, line, "caddy.zip")
        for checksums in ("", line + "\n" + line, line.replace("caddy.zip", "other.zip")):
            with self.assertRaises(ValueError):
                bootstrap.verify_archive(data, checksums, "caddy.zip")
        with self.assertRaises(ValueError):
            bootstrap.verify_archive(b"changed", line, "caddy.zip")

    def test_domain_and_ports(self):
        self.assertEqual(run.domain_name("App.Example.com"), "app.example.com")
        for value in ("https://example.com", "example.com/path", "example.com:443", "example.com\n}"):
            with self.assertRaises(argparse.ArgumentTypeError):
                run.domain_name(value)
        for value in ("80", "65536"):
            with self.assertRaises(argparse.ArgumentTypeError):
                run.port_number(value)

    def test_occupied_port(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen()
            with self.assertRaisesRegex(RuntimeError, "already in use"):
                run.ensure_free(sock.getsockname()[1])

    @unittest.skipUnless((run.ROOT / "bin" / "caddy.exe").exists(), "Run setup first")
    def test_real_proxy_api_static_and_cleanup(self):
        def free_port():
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                return sock.getsockname()[1]

        web_port, api_port = free_port(), free_port()
        while api_port == web_port:
            api_port = free_port()
        original_wait = run.wait_ready
        children_seen = []

        def ready(url, instance, children, timeout=20):
            original_wait(url, instance, children, timeout)
            children_seen[:] = children
            if len(children) != 2:
                return
            base = f"http://127.0.0.1:{web_port}"
            with run.HTTP.open(base) as response:
                self.assertIn(b"Launchpad", response.read())
            with run.HTTP.open(base + "/api/projects") as response:
                self.assertEqual(len(json.load(response)["items"]), 3)
            for path in ("/app.py", "/setup.ps1", "/.env", "/.runtime/data", "/api/missing"):
                with self.assertRaises(HTTPError) as error:
                    run.HTTP.open(base + path)
                self.assertEqual(error.exception.code, 404)
                error.exception.close()
            for title, status in (("  My app  ", 200), ("   ", 422), ("x" * 81, 422), ("x" * 20000, 413)):
                request = Request(base + "/api/preview", json.dumps({"title": title}).encode(),
                                  {"Content-Type": "application/json"})
                try:
                    with run.HTTP.open(request) as response:
                        self.assertEqual(response.status, status)
                        result = json.load(response)
                        self.assertEqual(result["title"], "My app")
                        self.assertFalse(result["saved"])
                except HTTPError as error:
                    self.assertEqual(error.code, status)
                    error.close()

        with patch.object(sys, "argv", ["run.py", "--smoke", "--port", str(web_port), "--api-port", str(api_port)]), \
                patch.object(run, "wait_ready", side_effect=ready):
            run.main()
        self.assertEqual(len(children_seen), 2)
        self.assertTrue(all(child.poll() is not None for child in children_seen))
        run.ensure_free(web_port)
        run.ensure_free(api_port)


if __name__ == "__main__":
    unittest.main()
