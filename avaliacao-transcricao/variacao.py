"""Quanto o resultado muda de uma execução para outra com o MESMO áudio?

O Whisper sorteia na decodificação quando cai no fallback de temperatura, então rodar duas vezes pode dar texto
diferente. Aqui o canal A de cada condição é transcrito várias vezes (antes e com o tratamento 1) e o script
registra o mínimo, a mediana e o máximo do WER e da contagem de alucinações em silêncio.
Uso: python rodar.py (gera o áudio)  ->  python variacao.py [repeticoes]
"""
import json
import statistics
import sys

import rodar
from rodar import CONDICOES, CONFIGS, RAIZ, ler_wav, referencia


# Os dois primeiros são os braços de rodar.py; os dois últimos separam o que o tratamento 1 mexe (ablação).
BRACOS = {"antes": CONFIGS["padrao"], "t1": CONFIGS["tratado"],
          "so_vad": {"vad_filter": True, "condition_on_previous_text": True},
          "so_cond": {"vad_filter": False, "condition_on_previous_text": False}}
NOMES = {"antes": "antes", "t1": "T1 completo", "so_vad": "só VAD", "so_cond": "só condition_on_previous_text=False"}


def resumo(valores, formato):
    return f"{formato(min(valores))} / {formato(statistics.median(valores))} / {formato(max(valores))}"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    linha = json.loads((RAIZ / "dados" / "linha_do_tempo.json").read_text(encoding="utf-8"))
    modelo, ambiente = rodar.carregar_modelo()
    print(ambiente)
    saida = {"repeticoes": n, "ambiente": ambiente, "condicoes": {}}
    for cond in CONDICOES:
        audio = ler_wav(RAIZ / "audio" / f"A_{cond}.wav")
        saida["condicoes"][cond] = {}
        for braco, cfg in BRACOS.items():
            wers, alucinacoes = [], []
            for _ in range(n):
                segs = rodar.transcrever(modelo, audio, cfg)
                if braco == "t1":
                    segs, _ = rodar.filtrar_whisper(segs)
                texto = " ".join(s["texto"] for s in segs)
                wers.append(rodar.calcular_wer(referencia(linha, "terapeuta"), texto)["wer"])
                alucinacoes.append(rodar.contar_classes(segs, linha, "terapeuta")["silencio"])
            saida["condicoes"][cond][braco] = {"wer": wers, "alucinacoes_em_silencio": alucinacoes}
            print(cond, braco, "WER", resumo(wers, rodar.pct), "| alucinações", resumo(alucinacoes, str), flush=True)

    md = [f"## Variação entre {n} execuções com o mesmo áudio (mínimo / mediana / máximo)", "",
          "| condição | tratamento | WER % | alucinações em silêncio |", "|---|---|---|---|"]
    for cond, bracos in saida["condicoes"].items():
        for braco, v in bracos.items():
            md.append(f"| {cond} | {NOMES[braco]} | {resumo(v['wer'], rodar.pct)} "
                      f"| {resumo(v['alucinacoes_em_silencio'], str)} |")
    (RAIZ / "resultados" / "variacao.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    (RAIZ / "resultados" / "variacao.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
