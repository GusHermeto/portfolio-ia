# Avaliação de transcrição com eco e silêncio

Projeto pequeno e reproduzível que mede dois problemas de transcrição de fala em português com Whisper aberto (`faster-whisper`), num cenário de consulta online em dois canais:

- canal A (microfone) = terapeuta; canal B (som do computador) = paciente;
- **eco**: a voz do paciente sai da caixa de som, volta pelo microfone e aparece repetida no canal da terapeuta;
- **silêncio**: o Whisper inventa frases onde ninguém fala (alucinação).

Comparo o antes e o depois de dois tratamentos simples, sem treinar nada. O texto completo está em [ARTIGO.md](ARTIGO.md).

**Tudo aqui é sintético.** O roteiro é fictício, a voz é de síntese (edge-tts) e o eco é **simulado por soma digital de sinais**, não gravado com caixa de som e microfone reais. Leia as [limitações](#limitações) antes de tirar conclusões.

## Como rodar (3 comandos, PowerShell, Windows)

```powershell
py -3.12 -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python rodar.py
.\.venv\Scripts\python -m pytest -q
```

- `rodar.py` refaz tudo (voz, canais, condições, transcrição, medidas) e grava `resultados/resultados.json` e `resultados/tabela.md`. Precisa de internet só para gerar a voz (edge-tts) e baixar o modelo na primeira vez. Opções: `--refazer-audio` (gera a voz de novo) e `--so-medir` (reaproveita as transcrições salvas).
- Sem GPU NVIDIA, apague as duas últimas linhas de `requirements.txt`: o script cai sozinho para o modelo `small` em int8 na CPU.
- `variacao.py` (opcional, uns 13 minutos) repete a transcrição cinco vezes por condição para mostrar quanto o resultado oscila e separa o efeito de cada parte do tratamento 1.
- Modelo e cache ficam em `.cache/` e o ambiente em `.venv/`, dentro da pasta do projeto.

## Onde rodei

| item | valor |
|---|---|
| modelo | `large-v3-turbo`, float16 (GPU encontrada via `nvidia-smi`) |
| GPU | NVIDIA GeForce RTX 2060, 6144 MiB, driver 610.88 |
| CPU | AMD, 12 núcleos lógicos |
| sistema | Windows 11, Python 3.12.10 |
| bibliotecas | faster-whisper 1.2.1, ctranslate2 4.9.0 |
| `rodar.py` do zero (voz sintética incluída, modelo já em cache) | 2 min 16 s (26,1 s de áudio, 107,0 s de transcrição) |
| primeira execução (inclui baixar o modelo, cerca de 1,6 GB de cache) | 194,2 s |
| `variacao.py 5` | 12 min 50 s |

## O que foi feito

1. **Roteiro** fictício (`dados/roteiro.json`): 54 turnos, 27 de cada falante, 716 palavras contadas por espaço, tema ansiedade com o trabalho. Três interrupções curtas da terapeuta sobrepostas à fala do paciente ("Uhum, entendo.", "Duvidar de novo.", "Tudo sozinho."); as duas últimas repetem palavras do paciente de propósito, para testar se o filtro de eco apaga fala legítima.
2. **Voz**: edge-tts, `pt-BR-FranciscaNeural` (terapeuta) e `pt-BR-AntonioNeural` (paciente). O edge-tts funcionou; o plano B (pyttsx3) não foi necessário nem está no código. Dois WAV mono 16 kHz alinhados, 342,5 s, com três silêncios longos de 17, 23 e 29 s.
3. **Condições do canal A**, todas por simulação digital. Todas têm um piso de ruído de microfone de -55 dBFS.

   | condição | o que se soma ao canal A |
   |---|---|
   | `limpo` | só o piso de ruído |
   | `eco_baixo` | canal B a -24 dB, atraso de 120 ms, reverberação (RT60 de 0,3 s) |
   | `eco_alto` | canal B a -12 dB, atraso de 180 ms, mesma reverberação |
   | `ruido` | ruído grave de ambiente (tipo ventilador), 15 dB abaixo da fala |

4. **Tratamento 1 (silêncio)**: `vad_filter=True`, `condition_on_previous_text=False` e filtro que descarta segmento com `no_speech_prob > 0,6` ou `compression_ratio > 2,4` (valores padrão do próprio Whisper).
5. **Tratamento 2 (eco)**: descarta o segmento do canal A que coincide no tempo (folga de 0,3 s) com segmento do canal B e tem similaridade de texto de pelo menos 80 em 100 (`rapidfuzz`). Em frase de menos de quatro palavras a comparação usa o texto inteiro, não o trecho parcial. O limiar 80 foi fixado antes de ver os resultados.
6. **Medidas**: WER por canal e condição (`jiwer`, minúsculas e sem pontuação, acentos mantidos) e contagem de segmentos por tipo, com o roteiro como gabarito: `fala` (fala legítima), `eco` (texto do paciente no canal A), `silêncio` (texto inventado dentro de um silêncio longo) e `outro` (texto sem apoio no roteiro, fora dele).

## Resultados (execução oficial, `resultados/tabela.md`)

WER do canal A (terapeuta), em %. 319 palavras de referência.

| condição | antes | T1 silêncio | T2 eco | T1+T2 |
|---|---|---|---|---|
| limpo | 4,4 | 0,3 | 4,4 | 0,3 |
| eco_baixo | 125,4 | 123,8 | 2,8 | 1,6 |
| eco_alto | 123,5 | 123,5 | 1,9 | 1,9 |
| ruido | 12,5 | 0,3 | 12,5 | 0,3 |

Segmentos do canal A por tipo. `fala removida` = fala legítima da terapeuta apagada pelo filtro (o custo).

| condição | tratamento | segmentos | fala | eco | silêncio | outro | fala removida |
|---|---|---|---|---|---|---|---|
| limpo | antes | 29 | 29 | 0 | 0 | 0 | - |
| limpo | T1 silêncio | 39 | 39 | 0 | 0 | 0 | 0 |
| limpo | T2 eco | 29 | 29 | 0 | 0 | 0 | 0 |
| limpo | T1+T2 | 39 | 39 | 0 | 0 | 0 | 0 |
| eco_baixo | antes | 56 | 28 | 28 | 0 | 0 | - |
| eco_baixo | T1 silêncio | 76 | 35 | 41 | 0 | 0 | 0 |
| eco_baixo | T2 eco | 28 | 28 | 0 | 0 | 0 | 0 |
| eco_baixo | T1+T2 | 36 | 35 | 1 | 0 | 0 | 0 |
| eco_alto | antes | 54 | 26 | 28 | 0 | 0 | - |
| eco_alto | T1 silêncio | 71 | 32 | 39 | 0 | 0 | 0 |
| eco_alto | T2 eco | 26 | 26 | 0 | 0 | 0 | 0 |
| eco_alto | T1+T2 | 32 | 32 | 0 | 0 | 0 | 0 |
| ruido | antes | 46 | 32 | 0 | 14 | 0 | - |
| ruido | T1 silêncio | 43 | 43 | 0 | 0 | 0 | 0 |
| ruido | T2 eco | 46 | 32 | 0 | 14 | 0 | 0 |
| ruido | T1+T2 | 43 | 43 | 0 | 0 | 0 | 0 |

Canal B (paciente, som do computador), 398 palavras de referência:

| tratamento | WER % | segmentos | fala | silêncio | outro |
|---|---|---|---|---|---|
| antes | 0,3 | 37 | 37 | 0 | 0 |
| T1 silêncio | 0,0 | 49 | 49 | 0 | 0 |

Sensibilidade do filtro de eco (T2 sozinho). Eco que sobra no canal A por condição (limpo / baixo / alto / ruído) e fala legítima apagada (soma das quatro condições):

| limiar | frase curta protegida | eco restante (limpo / baixo / alto / ruído) | fala removida |
|---|---|---|---|
| 50 | sim | 0 / 0 / 0 / 0 | 11 |
| 60 | sim | 0 / 0 / 0 / 0 | 0 |
| 70 | sim | 0 / 0 / 0 / 0 | 0 |
| 80 | sim | 0 / 0 / 0 / 0 | 0 |
| 90 | sim | 0 / 0 / 0 / 0 | 0 |
| 95 | sim | 0 / 0 / 0 / 0 | 0 |
| 100 | sim | 0 / 1 / 0 / 0 | 0 |
| 80 | não | 0 / 0 / 0 / 0 | 3 |

### Variação entre execuções (`variacao.py`, 5 repetições com o mesmo áudio)

O Whisper sorteia na decodificação quando cai no fallback de temperatura, então a coluna "antes" não é estável nas condições sem eco. Mínimo / mediana / máximo:

| condição | tratamento | WER % | alucinações em silêncio |
|---|---|---|---|
| limpo | antes | 2,5 / 3,8 / 12,2 | 0 / 1 / 7 |
| limpo | T1 completo | 0,3 / 0,3 / 0,3 | 0 / 0 / 0 |
| limpo | só VAD | 0,3 / 0,3 / 0,3 | 0 / 0 / 0 |
| limpo | só condition_on_previous_text=False | 0,3 / 0,3 / 0,3 | 0 / 0 / 0 |
| eco_baixo | antes | 125,4 / 125,4 / 125,4 | 0 / 0 / 0 |
| eco_baixo | T1 completo | 123,8 / 123,8 / 123,8 | 0 / 0 / 0 |
| eco_baixo | só VAD | 123,8 / 123,8 / 123,8 | 0 / 0 / 0 |
| eco_baixo | só condition_on_previous_text=False | 123,8 / 123,8 / 123,8 | 0 / 0 / 0 |
| eco_alto | antes | 123,5 / 123,5 / 123,5 | 0 / 0 / 0 |
| eco_alto | T1 completo | 123,5 / 123,5 / 123,5 | 0 / 0 / 0 |
| eco_alto | só VAD | 124,1 / 124,1 / 124,1 | 0 / 0 / 0 |
| eco_alto | só condition_on_previous_text=False | 123,5 / 123,5 / 123,5 | 0 / 0 / 0 |
| ruido | antes | 3,1 / 6,3 / 6,6 | 1 / 3 / 5 |
| ruido | T1 completo | 0,3 / 0,3 / 0,3 | 0 / 0 / 0 |
| ruido | só VAD | 1,9 / 1,9 / 1,9 | 0 / 0 / 0 |
| ruido | só condition_on_previous_text=False | 0,6 / 0,6 / 0,6 | 0 / 0 / 0 |

Na execução oficial acima, a condição `ruido` sem tratamento deu 12,5% e 14 segmentos alucinados, fora da faixa das cinco repetições (3,1 a 6,6%); na minha primeira execução, com a mesma linha do tempo, tinha dado 4,7%. Por isso, no "antes" das condições sem eco, olhe a faixa, não o valor único.

### O que os números dizem (e o que não)

- **Eco**: sem tratamento, o canal da terapeuta ganha 399 palavras inseridas na condição `eco_baixo` (o paciente diz 398 no roteiro): o Whisper transcreveu o vazamento quase inteiro. O filtro entre canais leva o WER de 125,4% e 123,5% para 2,8% e 1,9%. O tratamento 1 sozinho não resolve eco (123,8% e 123,5%), porque eco é fala e o VAD a mantém.
- **Custo do filtro**: com o limiar 80 e a proteção de frase curta, nenhum segmento legítimo da terapeuta foi apagado nas quatro condições. Sem a proteção, ele apaga a interjeição "Duvidar de novo." em 3 das 4 condições. Com limiar 50, apagou 11 segmentos legítimos.
- **Silêncio**: o tratamento 1 deixou o WER em 0,3% e zero alucinações nas condições `limpo` e `ruido`, igual nas cinco repetições. VAD e `condition_on_previous_text=False` sozinhos já resolvem o `limpo`; no `ruido`, só VAD dá 1,9%, só `condition_on_previous_text=False` dá 0,6% e os dois juntos 0,3%.
- **O filtro por `no_speech_prob` e `compression_ratio` nunca disparou**: `no_speech_prob` foi 0,000 em todos os segmentos das 10 transcrições da execução oficial e o maior `compression_ratio` foi 2,29 (corte em 2,4). Quem fez o trabalho foram o VAD e o `condition_on_previous_text`.
- **Perdas que o filtro não causa**: em `eco_alto`, as interrupções "Duvidar de novo." e "Tudo sozinho." nunca foram transcritas à parte (ficaram dentro do segmento do eco do paciente). São 5 palavras removidas no WER de T2 que nenhum filtro de texto recupera.
- **Sobra de eco com T1+T2**: em `eco_baixo`, o fragmento "Eu confiro." passou, porque o VAD o separou em frase curta e a proteção de frase curta não o compara por trecho. É o preço de proteger interjeições legítimas.

## Limitações

- **Voz sintética**: sem hesitação, sem sobreposição natural, sem sotaque nem ruído de fala real. O Whisper tende a ir melhor em voz limpa de TTS do que em consulta real.
- **Eco simulado**: é soma digital do canal B atenuado, atrasado e com reverberação. Não tem distorção de caixa de som, microfone com ganho automático, nem cancelamento de eco do sistema ou do navegador.
- **Um roteiro só**: 342 s, 319 palavras da terapeuta, três silêncios longos e três interrupções. Contagens como "alucinações em silêncio" têm poucos casos por condição.
- **Gabarito por texto**: classifico segmentos casando o texto com o roteiro. Minha primeira versão usava o tempo e estava errada (sem VAD, os tempos do Whisper se esticam sobre o silêncio e fala real parecia alucinação); troquei depois de ver os resultados. As contagens por tipo dependem de como o Whisper segmenta, então só comparo contagens entre tratamentos com cautela; o WER é a medida mais confiável.
- **Não determinismo**: o resultado sem tratamento muda entre execuções (ver tabela de variação). Os números das tabelas são os de uma execução específica.
- O filtro de eco por texto exige transcrever os dois canais e depende de o canal B sair bem transcrito.

## Arquivos

```
rodar.py              pipeline completo (funções puras + Whisper + medidas)
variacao.py           repetições e ablação do tratamento 1
test_rodar.py         6 testes pytest das funções puras
requirements.txt
dados/roteiro.json    roteiro fictício
dados/linha_do_tempo.json   início e fim de cada turno, silêncios (gabarito)
resultados/           resultados.json, tabela.md, variacao.json, variacao.md, transcricoes/
audio/                WAV e mp3 gerados (ignorados pelo git, cerca de 65 MB)
```
