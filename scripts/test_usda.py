"""Teste standalone da camada USDA. Execute a partir da raiz do projeto:
   python scripts/test_usda.py
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from app.config import settings
from app.services.usda_service import buscar_alimento_usda

API_KEY = settings.USDA_API_KEY
_USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"


async def main():
    # ------------------------------------------------------------------
    # (a) Dict CRU do primeiro foodNutrient do primeiro resultado de "tilapia"
    # ------------------------------------------------------------------
    print("=" * 60)
    print("(a) DICT CRU — primeiro foodNutrient de 'tilapia'")
    print("=" * 60)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            _USDA_URL,
            params={
                "api_key": API_KEY,
                "query": "tilapia",
                "dataType": ["Foundation", "SR Legacy"],
                "pageSize": 1,
            },
        )
        r.raise_for_status()
        data = r.json()
    foods = data.get("foods", [])
    if foods:
        primeiro_nutriente = foods[0].get("foodNutrients", [None])[0]
        print(json.dumps(primeiro_nutriente, indent=2, ensure_ascii=False))
    else:
        print("Nenhum resultado retornado pela API.")

    # ------------------------------------------------------------------
    # (b) tilapia — nº de resultados + macros do 1º
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("(b) buscar_alimento_usda('tilapia', chave)")
    print("=" * 60)
    res = await buscar_alimento_usda("tilapia", API_KEY)
    print(f"Nº de resultados: {len(res)}")
    if res:
        print("Macros do 1º resultado:")
        print(json.dumps(res[0], indent=2, ensure_ascii=False))

    # ------------------------------------------------------------------
    # (c) rice — nº de resultados + macros do 1º
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("(c) buscar_alimento_usda('rice', chave)")
    print("=" * 60)
    res = await buscar_alimento_usda("rice", API_KEY)
    print(f"Nº de resultados: {len(res)}")
    if res:
        print("Macros do 1º resultado:")
        print(json.dumps(res[0], indent=2, ensure_ascii=False))

    # ------------------------------------------------------------------
    # (d) xyzabc — deve retornar lista vazia
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("(d) buscar_alimento_usda('xyzabc', chave)")
    print("=" * 60)
    res = await buscar_alimento_usda("xyzabc", API_KEY)
    print(f"Resultado: {res}  (esperado: [])")

    # ------------------------------------------------------------------
    # (e) api_key vazia — deve retornar [] sem chamar a API
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("(e) buscar_alimento_usda('tilapia', '') — chave vazia")
    print("=" * 60)
    res = await buscar_alimento_usda("tilapia", "")
    print(f"Resultado: {res}  (esperado: [])")


if __name__ == "__main__":
    asyncio.run(main())
