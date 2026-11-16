"""Avaliação de transcrição com eco e silêncio (Whisper aberto, faster-whisper).

Refaz tudo: voz sintética -> dois canais -> condições de áudio -> transcrição
-> tratamentos -> medidas. Uso:

    python rodar.py                 # tudo (reaproveita a voz sintética já gerada)
    python rodar.py --refazer-audio # gera a voz sintética de novo (precisa de internet)
    python rodar.py --so-medir      # reusa as transcrições salvas e só recalcula as medidas
"""
import argparse
import asyncio
import json
import os
import platform
import random
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
# O cache do modelo fica dentro do projeto (nada no disco C:). Tem de ser definido antes de importar a Hugging Face.
os.environ.setdefault("HF_HOME", str(RAIZ / ".cache"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import jiwer  # noqa: E402
import numpy as np  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402
from scipy.io import wavfile  # noqa: E402
from scipy.signal import fftconvolve, lfilter  # noqa: E402

SR = 16000
INICIO_S = 0.5
VOZES = {"terapeuta": "pt-BR-FranciscaNeural", "paciente": "pt-BR-AntonioNeural"}
PISO_DE_RUIDO_DB = -55  # ruído de fundo de um microfone em sala quieta, presente em todas as condições do canal A

# Cada condição é uma receita do canal A (terapeuta). Os níveis são relativos ao canal B já nivelado.
CONDICOES = {
    "limpo": {},
    "eco_baixo": {"eco_db": -24, "atraso_ms": 120},
    "eco_alto": {"eco_db": -12, "atraso_ms": 180},
    "ruido": {"snr_db": 15},
}

# Duas configurações de decodificação: a padrão do Whisper e a do tratamento 1.
CONFIGS = {
    "padrao": {"vad_filter": False, "condition_on_previous_text": True},
    "tratado": {"vad_filter": True, "condition_on_previous_text": False},
}

LIMIAR_ECO = 80          # similaridade mínima (0 a 100) para chamar de eco; definido antes de ver os resultados
LIMIAR_ECO_VERDADE = 60  # limiar mais frouxo, só para a classificação de referência (gabarito)
MAX_NO_SPEECH = 0.6      # valores padrão do próprio Whisper
MAX_COMPRESSAO = 2.4


# ---------------------------------------------------------------- funções puras

def normalizar(texto):
    """Minúsculas e sem pontuação. Mantém os acentos: o Whisper acerta acento, então ele conta."""
    texto = texto.lower()
    texto = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in texto)
    return " ".join(texto.split())


def calcular_wer(referencia, hipotese):
    """WER com jiwer sobre texto normalizado. Devolve também substituições, remoções e inserções."""
    ref, hip = normalizar(referencia), normalizar(hipotese)
    if not hip:  # jiwer não aceita hipótese vazia: tudo foi removido
        n = len(ref.split())
        return {"wer": 1.0, "substituicoes": 0, "remocoes": n, "insercoes": 0, "palavras_ref": n}
    r = jiwer.process_words(ref, hip)
    return {"wer": r.wer, "substituicoes": r.substitutions, "remocoes": r.deletions,
            "insercoes": r.insertions, "palavras_ref": len(ref.split())}


def sobreposicao(ini_a, fim_a, ini_b, fim_b):
    """Segundos em que dois intervalos coincidem (0 se não coincidem)."""
    return max(0.0, min(fim_a, fim_b) - max(ini_a, ini_b))


def similaridade(a, b, min_palavras_parcial=4):
    """0 a 100. Em frase longa usa trecho parcial (o eco pode ser só um pedaço do que o paciente disse).
    Frase curta usa o texto inteiro: 'sim' estaria 'contido' em quase qualquer fala e seria apagada por acaso."""
    a, b = normalizar(a), normalizar(b)
    if not a or not b:
        return 0.0
    if len(a.split()) < min_palavras_parcial:
        return fuzz.ratio(a, b)
    return fuzz.partial_ratio(a, b)


def filtrar_whisper(segs, max_no_speech=MAX_NO_SPEECH, max_compressao=MAX_COMPRESSAO):
    """Parte do tratamento 1: descarta o que o próprio Whisper marca como provável não-fala ou texto repetitivo."""
    mantidos, removidos = [], []
    for s in segs:
        ruim = s["no_speech_prob"] > max_no_speech or s["compressao"] > max_compressao
        (removidos if ruim else mantidos).append(s)
    return mantidos, removidos


def filtrar_eco(segs_a, segs_b, limiar=LIMIAR_ECO, folga_s=0.3, min_palavras_parcial=4):
    """Tratamento 2: descarta o segmento do canal A que coincide no tempo com o canal B e repete o texto dele.
    A folga cobre o atraso do eco e a imprecisão dos tempos que o Whisper devolve."""
    mantidos, removidos = [], []
    for sa in segs_a:
        vizinhos = [sb["texto"] for sb in segs_b
                    if sobreposicao(sa["ini"] - folga_s, sa["fim"] + folga_s, sb["ini"], sb["fim"]) > 0]
        eco = bool(vizinhos) and similaridade(sa["texto"], " ".join(vizinhos), min_palavras_parcial) >= limiar
        (removidos if eco else mantidos).append(sa)
    return mantidos, removidos


def casar_turno(seg, turnos, janela_s=10):
    """Acha o turno do roteiro de que o texto do segmento é cópia (parcial). Só olha turnos a até janela_s segundos
    do segmento e, entre os que casam, fica com o que mais coincide no tempo (a mesma frase curta pode existir nos dois falantes)."""
    texto = normalizar(seg["texto"])
    curto = len(texto) < 8  # texto curto casaria com qualquer coisa por acaso: aí exige as palavras exatas dentro do turno

    def casa(turno):
        if curto:
            return f" {texto} " in f" {normalizar(turno)} "
        return fuzz.partial_ratio(texto, normalizar(turno)) >= LIMIAR_ECO_VERDADE

    candidatos = []
    for t in turnos:
        distancia = max(0.0, t["ini"] - seg["fim"], seg["ini"] - t["fim"])
        if texto and distancia <= janela_s and casa(t["texto"]):
            # desempate: 1) texto igual ao turno inteiro (e não só a um pedaço dele); 2) o turno que mais coincide
            # no tempo com o segmento; 3) o mais próximo
            inteiro = fuzz.ratio(texto, normalizar(t["texto"])) >= 90
            candidatos.append((not inteiro, -sobreposicao(seg["ini"], seg["fim"], t["ini"], t["fim"]), distancia, t))
    return min(candidatos, key=lambda c: c[:3])[3] if candidatos else None


def classificar_segmento(seg, linha, canal="terapeuta"):
    """Gabarito: o que este segmento é, olhando o roteiro que gerou o áudio. Primeiro pelo TEXTO, porque sem VAD
    os tempos do Whisper ficam esticados sobre o silêncio e uma fala real parece estar dentro dele.
    fala = texto de um turno do dono do canal; eco = texto de um turno do outro falante;
    silencio = texto sem apoio no roteiro e dentro de um silêncio longo (alucinação); outro = sem apoio, fora dele."""
    turno = casar_turno(seg, linha["turnos"])
    if turno:
        return "fala" if turno["falante"] == canal else "eco"
    dur = max(seg["fim"] - seg["ini"], 1e-6)
    em_silencio = sum(sobreposicao(seg["ini"], seg["fim"], i, f) for i, f in linha["silencios"])
    return "silencio" if em_silencio >= 0.5 * dur else "outro"


def contar_classes(segs, linha, canal):
    c = Counter(classificar_segmento(s, linha, canal) for s in segs)
    return {k: c.get(k, 0) for k in ("fala", "eco", "silencio", "outro")}


def montar_linha_do_tempo(turnos, duracoes, semente=42):
    """Põe cada turno no tempo. Pausa curta entre turnos, silêncio longo onde o roteiro pede,
    e sobreposição onde a terapeuta interrompe (isso dá ao filtro de eco a chance de errar)."""
    rng = random.Random(semente)
    linha = {"turnos": [], "silencios": []}
    fim_anterior = INICIO_S
    for turno, dur in zip(turnos, duracoes):
        if turno.get("silencio_antes_s"):
            ini = fim_anterior + turno["silencio_antes_s"]
            linha["silencios"].append([round(fim_anterior, 3), round(ini, 3)])
        elif turno.get("sobrepoe_s"):
            ini = fim_anterior - turno["sobrepoe_s"]
        else:
            ini = fim_anterior + rng.uniform(0.3, 0.9)
        fim = ini + dur
        linha["turnos"].append({"falante": turno["falante"], "texto": turno["texto"],
                                "ini": round(ini, 3), "fim": round(fim, 3)})
        fim_anterior = max(fim_anterior, fim)
    linha["duracao"] = round(fim_anterior + 1.0, 3)
    return linha


def referencia(linha, falante):
    return " ".join(t["texto"] for t in linha["turnos"] if t["falante"] == falante)


# ---------------------------------------------------------------- áudio

def ler_mp3(caminho):
    """Decodifica o mp3 do edge-tts para float32 mono 16 kHz com o PyAV (já vem com o faster-whisper; sem ffmpeg)."""
    import av
    partes = []
    with av.open(str(caminho)) as c:
        reamostrador = av.AudioResampler(format="s16", layout="mono", rate=SR)
        for frame in c.decode(audio=0):
            partes += [f.to_ndarray().reshape(-1) for f in reamostrador.resample(frame)]
        partes += [f.to_ndarray().reshape(-1) for f in reamostrador.resample(None)]
    return np.concatenate(partes).astype(np.float32) / 32768


def aparar(x, limiar=0.01, margem_s=0.05):
    """Tira o silêncio das pontas do mp3, para o início e o fim do turno no roteiro serem os da fala."""
    ativo = np.flatnonzero(np.abs(x) > limiar * np.abs(x).max())
    m = int(margem_s * SR)
    return x[max(ativo[0] - m, 0): ativo[-1] + m]


async def _sintetizar_todos(turnos, pasta):
    import edge_tts
    limite = asyncio.Semaphore(4)

    async def um(i, turno):
        async with limite:
            for tentativa in range(3):
                try:
                    await edge_tts.Communicate(turno["texto"], VOZES[turno["falante"]]).save(str(pasta / f"{i:02d}.mp3"))
                    return
                except Exception as erro:  # serviço online: tenta de novo antes de desistir
                    ultimo = erro
                    await asyncio.sleep(2)
            raise ultimo

    await asyncio.gather(*(um(i, t) for i, t in enumerate(turnos)))


def montar_canais(linha, audios):
    """Soma os turnos em dois canais mono, cada falante com o mesmo volume médio (RMS 0,1)."""
    n = int(linha["duracao"] * SR)
    canais = {f: np.zeros(n, np.float32) for f in VOZES}
    for falante in VOZES:
        propios = [a for t, a in zip(linha["turnos"], audios) if t["falante"] == falante]
        ganho = 0.1 / np.sqrt(np.mean(np.concatenate(propios) ** 2))
        for t, a in zip(linha["turnos"], audios):
            if t["falante"] == falante:
                i = int(t["ini"] * SR)
                canais[falante][i:i + len(a)] += a * ganho
    return canais["terapeuta"], canais["paciente"]


def rms_em_fala(x, linha, falante):
    trechos = [x[int(t["ini"] * SR):int(t["fim"] * SR)] for t in linha["turnos"] if t["falante"] == falante]
    return float(np.sqrt(np.mean(np.concatenate(trechos) ** 2)))


def resposta_impulsiva(atraso_ms, rng, rt60_s=0.3):
    """Caminho direto atrasado + cauda de reverberação (ruído que decai 60 dB em rt60_s)."""
    n_cauda = int(0.6 * SR)
    cauda = rng.standard_normal(n_cauda) * np.exp(-6.9 * np.arange(n_cauda) / SR / rt60_s)
    cauda /= np.linalg.norm(cauda)
    atraso = int(atraso_ms / 1000 * SR)
    h = np.zeros(atraso + n_cauda)
    h[atraso] = 1.0
    h[atraso:] += 0.5 * cauda  # cauda 6 dB abaixo do som direto
    return h


def simular_condicao(a, b, linha, receita, semente):
    """Canal A como o microfone da terapeuta ouviria, sempre por simulação digital (não é caixa de som real)."""
    rng = np.random.default_rng(semente)
    x = a.astype(np.float64)
    x += rng.standard_normal(len(x)) * 10 ** (PISO_DE_RUIDO_DB / 20)
    if "eco_db" in receita:
        h = resposta_impulsiva(receita["atraso_ms"], rng)
        x += fftconvolve(b, h)[:len(x)] * 10 ** (receita["eco_db"] / 20)
    if "snr_db" in receita:
        # ruído grave de ambiente (ventilador): ruído branco passado num filtro que realça os graves
        ruido = lfilter([1.0], [1.0, -0.95], rng.standard_normal(len(x)))
        ruido *= rms_em_fala(a, linha, "terapeuta") / 10 ** (receita["snr_db"] / 20) / np.std(ruido)
        x += ruido
    return np.clip(x, -1, 1).astype(np.float32)


def salvar_wav(caminho, x):
    wavfile.write(caminho, SR, (x * 32767).astype(np.int16))


def ler_wav(caminho):
    sr, x = wavfile.read(caminho)
    assert sr == SR
    return x.astype(np.float32) / 32768


# ---------------------------------------------------------------- Whisper

def tem_gpu_nvidia():
    try:
        saida = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                "--format=csv,noheader"], capture_output=True, text=True, timeout=20)
        return saida.stdout.strip() if saida.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def preparar_cuda():
    """O pip instala cuBLAS e cuDNN dentro do venv; no Windows o ctranslate2 só acha as DLLs se a pasta estiver no PATH."""
    for pasta in (Path(sys.prefix) / "Lib" / "site-packages" / "nvidia").glob("*/bin"):
        os.add_dll_directory(str(pasta))
        os.environ["PATH"] = f"{pasta}{os.pathsep}{os.environ['PATH']}"


def carregar_modelo():
    """Com GPU NVIDIA: large-v3-turbo em float16. Sem GPU (ou se a GPU falhar): small em int8 na CPU."""
    from faster_whisper import WhisperModel
    cache = str(RAIZ / ".cache")
    gpu = tem_gpu_nvidia()
    falha_gpu = None
    if gpu:
        try:
            preparar_cuda()
            modelo = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16", download_root=cache)
            list(modelo.transcribe(np.zeros(SR * 2, np.float32), language="pt")[0])  # força carregar cuBLAS/cuDNN agora
            return modelo, {"modelo": "large-v3-turbo", "dispositivo": "cuda", "compute_type": "float16", "gpu": gpu}
        except Exception as erro:
            falha_gpu = f"{type(erro).__name__}: {erro}"
            print("GPU falhou, caindo para CPU:", falha_gpu)
    modelo = WhisperModel("small", device="cpu", compute_type="int8", download_root=cache)
    return modelo, {"modelo": "small", "dispositivo": "cpu", "compute_type": "int8", "gpu": gpu,
                    "falha_gpu": falha_gpu}


def transcrever(modelo, audio, config):
    segs, _ = modelo.transcribe(audio, language="pt", beam_size=5, **config)
    return [{"ini": round(s.start, 3), "fim": round(s.end, 3), "texto": s.text.strip(),
             "no_speech_prob": round(s.no_speech_prob, 4), "avg_logprob": round(s.avg_logprob, 4),
             "compressao": round(s.compression_ratio, 4)} for s in segs]


# ---------------------------------------------------------------- etapas

def etapa_audio(refazer):
    """Voz sintética -> linha do tempo + canais A e B. Reaproveita o que já existe, salvo --refazer-audio."""
    pasta = RAIZ / "audio"
    pasta.mkdir(exist_ok=True)
    arq_linha = RAIZ / "dados" / "linha_do_tempo.json"
    if not refazer and arq_linha.exists() and (pasta / "canal_terapeuta.wav").exists():
        print("[audio] reaproveitando a voz sintética existente")
        return json.loads(arq_linha.read_text(encoding="utf-8")), ler_wav(pasta / "canal_terapeuta.wav"), ler_wav(pasta / "canal_paciente.wav")
    turnos = json.loads((RAIZ / "dados" / "roteiro.json").read_text(encoding="utf-8"))
    tts = pasta / "tts"
    tts.mkdir(exist_ok=True)
    asyncio.run(_sintetizar_todos(turnos, tts))
    audios = [aparar(ler_mp3(tts / f"{i:02d}.mp3")) for i in range(len(turnos))]
    linha = montar_linha_do_tempo(turnos, [len(a) / SR for a in audios])
    a, b = montar_canais(linha, audios)
    arq_linha.write_text(json.dumps(linha, ensure_ascii=False, indent=1), encoding="utf-8")
    salvar_wav(pasta / "canal_terapeuta.wav", a)
    salvar_wav(pasta / "canal_paciente.wav", b)
    print(f"[audio] {linha['duracao']:.0f} s, {len(turnos)} turnos, {len(linha['silencios'])} silêncios longos")
    return linha, a, b


def etapa_condicoes(linha, a, b):
    """Gera os quatro áudios do canal A. O canal B (som do computador) é o mesmo em todas as condições."""
    saida = {}
    for i, (nome, receita) in enumerate(CONDICOES.items()):
        saida[nome] = simular_condicao(a, b, linha, receita, semente=100 + i)
        salvar_wav(RAIZ / "audio" / f"A_{nome}.wav", saida[nome])
    return saida


def etapa_transcricao(linha, audios_a, b):
    """Transcreve cada áudio nas duas configurações e salva os segmentos (versionáveis, são pequenos)."""
    pasta = RAIZ / "resultados" / "transcricoes"
    pasta.mkdir(parents=True, exist_ok=True)
    modelo, ambiente = carregar_modelo()
    print("[whisper]", ambiente)
    tempos = {}
    trabalhos = [("B", b)] + [(f"A_{n}", x) for n, x in audios_a.items()]
    for nome, audio in trabalhos:
        for cfg, parametros in CONFIGS.items():
            t0 = time.time()
            segs = transcrever(modelo, audio, parametros)
            tempos[f"{nome}_{cfg}"] = round(time.time() - t0, 1)
            (pasta / f"{nome}_{cfg}.json").write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[whisper] {nome} {cfg}: {len(segs)} segmentos em {tempos[f'{nome}_{cfg}']} s")
    return ambiente, tempos


def carregar_transcricoes():
    pasta = RAIZ / "resultados" / "transcricoes"
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in pasta.glob("*.json")}


# ---------------------------------------------------------------- medidas

def medir(segs, linha, canal, removidos=None):
    """WER do canal + contagem por classe do gabarito. 'removidos' = o que o filtro descartou (para medir o custo)."""
    falante = canal
    r = calcular_wer(referencia(linha, falante), " ".join(s["texto"] for s in segs))
    r["segmentos"] = len(segs)
    r.update(contar_classes(segs, linha, falante))
    if removidos is not None:
        r["removidos"] = contar_classes(removidos, linha, falante)
    return r


def aplicar_tratamentos(tr, cond, linha):
    """Quatro braços para o canal A de uma condição: antes, T1 (silêncio), T2 (eco) e T1+T2."""
    a_pad, b_pad = tr[f"A_{cond}_padrao"], tr["B_padrao"]
    a_tra, b_tra = tr[f"A_{cond}_tratado"], tr["B_tratado"]
    a_t1, rem_t1 = filtrar_whisper(a_tra)
    b_t1, _ = filtrar_whisper(b_tra)
    a_t2, rem_t2 = filtrar_eco(a_pad, b_pad)
    a_t12, rem_t12 = filtrar_eco(a_t1, b_t1)
    return {"antes": medir(a_pad, linha, "terapeuta"),
            "t1": medir(a_t1, linha, "terapeuta", rem_t1),
            "t2": medir(a_t2, linha, "terapeuta", rem_t2),
            "t1+t2": medir(a_t12, linha, "terapeuta", rem_t1 + rem_t12)}


def varrer_limiar(tr, linha):
    """Sensibilidade do filtro de eco (só T2, sobre a transcrição padrão): quanto eco sobra e quanta fala legítima cai."""
    linhas = []
    variantes = [(lim, 4) for lim in (50, 60, 70, 80, 90, 95, 100)] + [(LIMIAR_ECO, 0)]
    for limiar, min_pal in variantes:
        item = {"limiar": limiar, "min_palavras_parcial": min_pal, "eco_restante": {}, "fala_removida": 0}
        for cond in CONDICOES:
            mant, rem = filtrar_eco(tr[f"A_{cond}_padrao"], tr["B_padrao"], limiar, min_palavras_parcial=min_pal)
            item["eco_restante"][cond] = contar_classes(mant, linha, "terapeuta")["eco"]
            item["fala_removida"] += contar_classes(rem, linha, "terapeuta")["fala"]
        linhas.append(item)
    return linhas


def medir_canal_b(tr, linha):
    b_pad = tr["B_padrao"]
    b_t1, rem = filtrar_whisper(tr["B_tratado"])
    return {"antes": medir(b_pad, linha, "paciente"), "t1": medir(b_t1, linha, "paciente", rem)}


def pct(x):
    return f"{100 * x:.1f}".replace(".", ",")


def gerar_tabela(res):
    nomes = {"antes": "antes", "t1": "T1 silêncio", "t2": "T2 eco", "t1+t2": "T1+T2"}
    md = ["## WER do canal A (terapeuta), em %", "",
          "| condição | " + " | ".join(nomes.values()) + " |", "|---|" + "---|" * len(nomes)]
    for cond, bracos in res["canal_a"].items():
        md.append(f"| {cond} | " + " | ".join(pct(bracos[k]["wer"]) for k in nomes) + " |")
    md += ["", "## Segmentos do canal A por tipo (gabarito do roteiro)", "",
           "`fala` = fala legítima da terapeuta; `eco` = fala do paciente no canal da terapeuta; `silêncio` = texto inventado "
           "dentro de um silêncio longo; `outro` = texto sem apoio no roteiro, fora dele.`removidos` = o que o filtro descartou; "
           "`fala removida` = fala legítima apagada por engano.", "",
           "| condição | tratamento | segmentos | fala | eco | silêncio | outro | fala removida |", "|---|---|---|---|---|---|---|---|"]
    for cond, bracos in res["canal_a"].items():
        for k, nome in nomes.items():
            m = bracos[k]
            perdida = m["removidos"]["fala"] if "removidos" in m else "-"
            md.append(f"| {cond} | {nome} | {m['segmentos']} | {m['fala']} | {m['eco']} | {m['silencio']} | {m['outro']} | {perdida} |")
    md += ["", "## Canal B (paciente, som do computador)", "",
           "| tratamento | WER % | segmentos | fala | silêncio | outro |", "|---|---|---|---|---|---|"]
    for k in ("antes", "t1"):
        m = res["canal_b"][k]
        md.append(f"| {nomes[k]} | {pct(m['wer'])} | {m['segmentos']} | {m['fala']} | {m['silencio']} | {m['outro']} |")
    md += ["", "## Sensibilidade do filtro de eco (T2 sozinho)", "",
           "Eco que sobra no canal A por condição, e fala legítima da terapeuta apagada (soma das quatro condições).", "",
           "| limiar | frase curta protegida | eco restante (limpo / baixo / alto / ruído) | fala removida |", "|---|---|---|---|"]
    for v in res["varredura_limiar"]:
        er = v["eco_restante"]
        protegida = "sim" if v["min_palavras_parcial"] else "não"
        md.append(f"| {v['limiar']} | {protegida} | {er['limpo']} / {er['eco_baixo']} / {er['eco_alto']} / {er['ruido']} | {v['fala_removida']} |")
    return "\n".join(md) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--refazer-audio", action="store_true")
    p.add_argument("--so-medir", action="store_true")
    args = p.parse_args()

    # temporários também ficam dentro do projeto, nunca no C:
    (RAIZ / ".tmp").mkdir(exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(RAIZ / ".tmp")
    (RAIZ / "resultados").mkdir(exist_ok=True)
    inicio = time.time()
    tempos = {}

    t0 = time.time()
    linha, a, b = etapa_audio(args.refazer_audio)
    audios_a = etapa_condicoes(linha, a, b)
    tempos["audio_s"] = round(time.time() - t0, 1)

    if args.so_medir:
        ambiente = json.loads((RAIZ / "resultados" / "resultados.json").read_text(encoding="utf-8"))["ambiente"]
        tempos_whisper = {}
    else:
        t0 = time.time()
        ambiente, tempos_whisper = etapa_transcricao(linha, audios_a, b)
        tempos["transcricao_s"] = round(time.time() - t0, 1)

    tr = carregar_transcricoes()
    res = {"canal_a": {c: aplicar_tratamentos(tr, c, linha) for c in CONDICOES},
           "canal_b": medir_canal_b(tr, linha),
           "varredura_limiar": varrer_limiar(tr, linha)}
    from importlib.metadata import version
    res["ambiente"] = {**ambiente, "cpu": platform.processor(), "nucleos": os.cpu_count(),
                       "so": platform.platform(), "python": platform.python_version(),
                       "faster_whisper": version("faster-whisper"), "ctranslate2": version("ctranslate2")}
    res["parametros"] = {"limiar_eco": LIMIAR_ECO, "max_no_speech": MAX_NO_SPEECH, "max_compressao": MAX_COMPRESSAO,
                         "condicoes": CONDICOES, "configs": CONFIGS, "vozes": VOZES}
    res["duracao_audio_s"] = linha["duracao"]
    tempos["total_s"] = round(time.time() - inicio, 1)
    res["tempos"] = {**tempos, "por_transcricao_s": tempos_whisper}
    (RAIZ / "resultados" / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (RAIZ / "resultados" / "tabela.md").write_text(gerar_tabela(res), encoding="utf-8")
    print(gerar_tabela(res))
    print(f"Tempo total: {tempos['total_s']} s")


if __name__ == "__main__":
    main()
