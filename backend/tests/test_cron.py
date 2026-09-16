"""Pruebas unitarias del keepalive diario de Supabase."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException  # noqa: E402

from app.config import settings  # noqa: E402
from app.routers.cron import mantener_bd_activa  # noqa: E402


class CronKeepaliveTest(unittest.TestCase):
    def setUp(self):
        self.secret_original = settings.cron_secret
        settings.cron_secret = "secreto-de-prueba"

    def tearDown(self):
        settings.cron_secret = self.secret_original

    def test_rechaza_una_llamada_sin_secreto(self):
        with self.assertRaises(HTTPException) as error:
            mantener_bd_activa(authorization="")

        self.assertEqual(error.exception.status_code, 401)

    @patch("app.routers.cron.db.fetch_one", return_value={"ok": 1})
    def test_secret_valido_ejecuta_una_consulta_real(self, fetch_one):
        respuesta = mantener_bd_activa(
            authorization="Bearer secreto-de-prueba",
        )

        self.assertEqual(respuesta, {"status": "ok", "database": "reachable"})
        fetch_one.assert_called_once_with("SELECT 1 AS ok")


if __name__ == "__main__":
    unittest.main()
