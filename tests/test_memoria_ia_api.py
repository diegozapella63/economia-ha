"""A Memória da IA pelo HTTP (1.52.0), com o servidor de verdade: GET e POST /api/memoria-ia leem e escrevem a lista da casa,
que fica na pasta share (share/familia/memoria_ia.json), fora do app, para todos os apps da família."""
import json
import os
import unittest

from test_api_fluxos import Servidor


class MemoriaIA(Servidor):
    def test_guardar_listar_e_apagar(self):
        self.assertEqual(self.pede("GET", "/api/memoria-ia"), (200, {"lista": [], "max": 60}))
        st, r = self.pede("POST", "/api/memoria-ia", {"acao": "nova", "texto": "  O café é   sempre o da marca azul "}, cab={"X-Remote-User-Display-Name": "Ana"})
        self.assertEqual((st, [(x["texto"], x["app"], x["quem"]) for x in r["lista"]]), (200, [("O café é sempre o da marca azul", "EconomIA", "Ana")]))
        arq = os.path.join(self.pasta, "familia", "memoria_ia.json")
        self.assertTrue(os.path.exists(arq), "na pasta share da casa, ao lado da pasta do app")
        with open(arq, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["lista"][0]["texto"], "O café é sempre o da marca azul")
        self.assertEqual(self.pede("POST", "/api/memoria-ia", {"acao": "nova", "texto": " a "}), (400, {"erro": "Escreva o que é para lembrar."}))
        self.assertEqual(self.pede("POST", "/api/memoria-ia", bruto=b"")[0], 413)
        st, r = self.pede("POST", "/api/memoria-ia", {"acao": "apagar", "id": r["lista"][0]["id"]})
        self.assertEqual((st, r["lista"]), (200, []))


if __name__ == "__main__":
    unittest.main()
