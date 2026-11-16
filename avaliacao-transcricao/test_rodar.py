"""Testes das funções puras de rodar.py (sem áudio, sem Whisper, sem internet)."""
from rodar import (calcular_wer, classificar_segmento, filtrar_eco, filtrar_whisper,
                   normalizar)


def seg(ini, fim, texto, **extra):
    return {"ini": ini, "fim": fim, "texto": texto, "no_speech_prob": 0.0, "compressao": 1.0, **extra}


def test_normalizar_tira_pontuacao_e_maiusculas_mas_mantem_acento():
    assert normalizar("Olá, Mundo! Cuide-se.") == "olá mundo cuide se"


def test_wer_zero_para_texto_igual_e_conta_insercao():
    assert calcular_wer("Bom dia, tudo bem?", "bom dia tudo bem")["wer"] == 0
    r = calcular_wer("bom dia tudo bem", "bom dia tudo bem sim")
    assert r["insercoes"] == 1 and r["wer"] == 0.25
    assert calcular_wer("bom dia", "")["wer"] == 1.0  # hipótese vazia: tudo removido


def test_filtro_de_eco_remove_repeticao_que_coincide_no_tempo():
    canal_b = [seg(10.0, 14.0, "Eu fico repassando a lista de pendências.")]
    canal_a = [seg(10.1, 14.1, "eu fico repassando a lista de pendências")]
    mantidos, removidos = filtrar_eco(canal_a, canal_b)
    assert mantidos == [] and len(removidos) == 1


def test_filtro_de_eco_mantem_fala_legitima():
    canal_b = [seg(10.0, 14.0, "Eu fico repassando a lista de pendências.")]
    texto_igual_em_outro_momento = seg(30.0, 34.0, "Eu fico repassando a lista de pendências.")
    texto_diferente_no_mesmo_momento = seg(10.0, 13.0, "Respire fundo e solte o ar bem devagar.")
    frase_curta_parecida = seg(13.0, 14.5, "Duvidar de novo.")
    mantidos, removidos = filtrar_eco(
        [texto_igual_em_outro_momento, texto_diferente_no_mesmo_momento, frase_curta_parecida], canal_b)
    assert len(mantidos) == 3 and removidos == []


def test_classificar_segmento_usa_o_roteiro_como_gabarito():
    linha = {"turnos": [{"falante": "terapeuta", "texto": "Como foi a semana?", "ini": 0, "fim": 3},
                        {"falante": "paciente", "texto": "Foi cansativa, dormi mal.", "ini": 4, "fim": 7}],
             "silencios": [[7, 25]]}
    assert classificar_segmento(seg(0, 3, "como foi a semana"), linha) == "fala"
    assert classificar_segmento(seg(4.1, 7, "foi cansativa dormi mal"), linha) == "eco"
    assert classificar_segmento(seg(10, 14, "Legendas pela comunidade"), linha) == "silencio"
    assert classificar_segmento(seg(4.2, 6.8, "texto qualquer sem relação"), linha) == "outro"
    # a terapeuta repete palavras do paciente ao interromper: a frase existe nos dois turnos, vale o que coincide no tempo
    linha["turnos"].append({"falante": "terapeuta", "texto": "Dormi mal.", "ini": 6.3, "fim": 7.2})
    assert classificar_segmento(seg(6.3, 7.2, "dormi mal"), linha) == "fala"


def test_filtro_do_whisper_corta_nao_fala_e_repeticao():
    segs = [seg(0, 2, "ok"), seg(2, 4, "inventado", no_speech_prob=0.9), seg(4, 6, "la la la", compressao=3.1)]
    mantidos, removidos = filtrar_whisper(segs)
    assert [s["texto"] for s in mantidos] == ["ok"] and len(removidos) == 2
