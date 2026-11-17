"""Gera os dados da demonstração (Hugging Face Space estático) a partir das transcrições salvas.

Não roda o Whisper: só reaplica o filtro de eco de rodar.py e guarda, para cada segmento,
a similaridade com o canal do paciente. A página usa esse número para ligar e desligar o filtro.

    python space/gerar_dados.py          (dentro de avaliacao-transcricao, com o .venv)
"""
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

import rodar  # noqa: E402

LIMIARES = list(range(30, 101, 5))  # abaixo de 55 o filtro começa a apagar fala legítima: a página mostra isso
TRECHO_S = (3.5, 25.5)  # trecho de áudio da página: dois turnos de cada falante


def segmentos_com_similaridade(segs_a, segs_b, linha, folga_s=0.3):
    saida = []
    for sa in segs_a:
        vizinhos = [sb["texto"] for sb in segs_b
                    if rodar.sobreposicao(sa["ini"] - folga_s, sa["fim"] + folga_s, sb["ini"], sb["fim"]) > 0]
        sim = rodar.similaridade(sa["texto"], " ".join(vizinhos)) if vizinhos else 0.0
        saida.append({"ini": sa["ini"], "fim": sa["fim"], "texto": sa["texto"], "sim": sim,
                      "tipo": rodar.classificar_segmento(sa, linha, "terapeuta")})
    return saida


def medida(segs, linha, removidos=None):
    m = rodar.medir(segs, linha, "terapeuta", removidos)
    return {"wer": round(100 * m["wer"], 1), "eco": m["eco"], "fala": m["fala"],
            "fala_removida": m["removidos"]["fala"] if removidos is not None else 0}


def main():
    linha = json.loads((AQUI.parent / "dados" / "linha_do_tempo.json").read_text(encoding="utf-8"))
    tr = rodar.carregar_transcricoes()
    b_t1, _ = rodar.filtrar_whisper(tr["B_tratado"])
    dados = {"limiares": LIMIARES, "limiar_padrao": rodar.LIMIAR_ECO, "condicoes": {}}
    for cond in ("eco_baixo", "eco_alto"):
        a_pad = tr[f"A_{cond}_padrao"]
        a_t1, _ = rodar.filtrar_whisper(tr[f"A_{cond}_tratado"])
        por_limiar = {}
        for limiar in LIMIARES:
            mantidos, removidos = rodar.filtrar_eco(a_t1, b_t1, limiar)
            por_limiar[limiar] = medida(mantidos, linha, removidos)
        dados["condicoes"][cond] = {
            "antes": {"medida": medida(a_pad, linha),
                      "segmentos": segmentos_com_similaridade(a_pad, tr["B_padrao"], linha)},
            "depois": {"por_limiar": por_limiar,
                       "segmentos": segmentos_com_similaridade(a_t1, b_t1, linha)},
        }

    # os números da página têm de ser os do README
    c = dados["condicoes"]
    assert c["eco_baixo"]["antes"]["medida"]["wer"] == 125.4, c["eco_baixo"]["antes"]["medida"]
    assert c["eco_baixo"]["depois"]["por_limiar"][80]["wer"] == 1.6
    assert c["eco_alto"]["antes"]["medida"]["wer"] == 123.5
    assert c["eco_alto"]["depois"]["por_limiar"][80]["wer"] == 1.9
    # a página decide o que cai com "sim >= limiar": tem de dar o mesmo que o filtro de rodar.py
    for cond, d in c.items():
        for limiar in LIMIARES:
            sobram = [s for s in d["depois"]["segmentos"] if s["sim"] < limiar]
            assert sum(s["tipo"] == "eco" for s in sobram) == d["depois"]["por_limiar"][limiar]["eco"], (cond, limiar)

    (AQUI / "dados.js").write_text("window.DADOS = " + json.dumps(dados, ensure_ascii=False) + ";\n", encoding="utf-8")

    ini, fim = (int(t * rodar.SR) for t in TRECHO_S)
    for nome in ("A_limpo", "A_eco_baixo", "A_eco_alto"):
        x = rodar.ler_wav(AQUI.parent / "audio" / f"{nome}.wav")
        rodar.salvar_wav(AQUI / f"{nome}.wav", x[ini:fim])
    print("ok:", {k: (v["antes"]["medida"]["wer"], v["depois"]["por_limiar"][80]) for k, v in c.items()})


if __name__ == "__main__":
    main()
