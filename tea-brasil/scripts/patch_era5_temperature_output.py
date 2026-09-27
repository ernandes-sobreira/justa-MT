#!/usr/bin/env python3
from pathlib import Path

p=Path('tea-brasil/scripts/build_era5land_temperatura_2022.py')
s=p.read_text(encoding='utf-8')

repls={
'''    needed = {"codigo_ibge", "municipio", "uf"}\n''':'''    needed = {"codigo_ibge", "municipio", "uf", "percentual_tea_2022"}\n''',
'''    return df[["codigo_ibge", "municipio", "uf"]].copy()\n''':'''    return df[["codigo_ibge", "municipio", "uf", "percentual_tea_2022"]].copy()\n''',
'''        "codigo_ibge", "municipio", "uf",\n        "temperatura_media_ar_c_2022"''':'''        "codigo_ibge", "municipio", "uf", "percentual_tea_2022",\n        "temperatura_media_ar_c_2022"''',
'''    records = df.where(pd.notna(df), None).to_dict(orient="records")\n    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")\n''':'''    records = df.astype(object).where(pd.notna(df), None).to_dict(orient="records")\n    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")\n''',
'''        "unique_codes": EXPECTED,\n        "cobertura": coverage,\n''':'''        "unique_codes": EXPECTED,\n        "tea_join": {\n            "campo": "percentual_tea_2022",\n            "fonte": "Censo 2022 / base TEA-Brasil previamente validada",\n            "chave": "codigo_ibge (7 digitos)",\n            "linhas": EXPECTED,\n            "codigos_unicos": EXPECTED,\n            "regra": "join one-to-one no universo mestre; ausencias TEA permanecem NA",\n        },\n        "cobertura": coverage,\n''',
'''    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")\n''':'''    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")\n'''
}

for old,new in repls.items():
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'Expected exactly one match, got {n}: {old[:120]!r}')
    s=s.replace(old,new)

# Guard the final builder contract.
for required in ['percentual_tea_2022','allow_nan=False','tea_join']:
    if required not in s:
        raise RuntimeError(f'Missing required final-builder marker: {required}')

p.write_text(s,encoding='utf-8')
print('PATCH_BUILDER_OK',len(s))
