import logging

import httpx

logger = logging.getLogger(__name__)

_USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# nutrientNumber pode vir como str ou int — normalizado para str no mapeamento
_NUTRIENT_MAP = {
    "208": "kcal",
    "203": "proteina_g",
    "204": "lipideos_g",
    "205": "carboidrato_g",
    "291": "fibra_g",
}


def _extrair_macros(food_nutrients: list) -> dict:
    macros = {k: None for k in _NUTRIENT_MAP.values()}
    for n in food_nutrients:
        num = str(n.get("nutrientNumber", ""))
        campo = _NUTRIENT_MAP.get(num)
        if campo is None:
            continue
        valor = n.get("value") if "value" in n else n.get("amount")
        if valor is not None:
            macros[campo] = float(valor)
    return macros


async def buscar_alimento_usda(termo: str, api_key: str) -> list[dict]:
    if not api_key:
        return []

    params = {
        "api_key": api_key,
        "query": termo,
        "dataType": ["Foundation", "SR Legacy"],
        "pageSize": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(_USDA_URL, params=params)
            r.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("usda_busca_falhou", extra={"termo": termo, "error": str(e)})
        return []

    foods = r.json().get("foods", [])
    resultados = []
    for food in foods[:5]:
        macros = _extrair_macros(food.get("foodNutrients", []))

        if macros["kcal"] is None and all(
            macros[k] is not None for k in ("proteina_g", "carboidrato_g", "lipideos_g")
        ):
            macros["kcal"] = round(
                macros["proteina_g"] * 4 + macros["carboidrato_g"] * 4 + macros["lipideos_g"] * 9,
                1,
            )
            kcal_estimado = True
        else:
            kcal_estimado = False

        resultados.append(
            {
                "nome_en": food.get("description", ""),
                "taco_id": None,
                "fonte": "USDA",
                **macros,
                "kcal_estimado": kcal_estimado,
            }
        )
    return resultados
