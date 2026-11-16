# O que aprendi medindo transcrição com eco

## O problema

Pense numa consulta online gravada em dois canais: o microfone da terapeuta e o som do computador, que traz a voz do paciente. Dois defeitos atrapalham a transcrição com Whisper. O primeiro é o eco: a voz do paciente sai da caixa de som, volta pelo microfone e aparece repetida no canal da terapeuta. O segundo é a alucinação em silêncio: onde ninguém fala, o Whisper às vezes inventa frases. Quis medir os dois e testar um remédio simples para cada, sem treinar nada.

## Método

Escrevi um roteiro fictício de 54 turnos sobre ansiedade com o trabalho e gerei a voz com edge-tts, uma voz feminina para a terapeuta e uma masculina para o paciente. Montei dois canais de 342 segundos, com três silêncios longos (17, 23 e 29 segundos) e três interrupções curtas da terapeuta, duas delas repetindo palavras do paciente de propósito, para ver se o filtro de eco apaga fala legítima.

O eco é simulado: somo o canal do paciente, atenuado, atrasado e com reverberação, ao canal da terapeuta, em dois níveis (menos 24 e menos 12 dB). Há também uma condição limpa e uma com ruído de ambiente. Transcrevi tudo com faster-whisper, modelo large-v3-turbo em float16, numa RTX 2060.

O tratamento 1 (silêncio) junta VAD, `condition_on_previous_text` desligado e um filtro por `no_speech_prob` e `compression_ratio`. O tratamento 2 (eco) descarta o segmento do canal da terapeuta que coincide no tempo com um segmento do canal do paciente e tem texto parecido (rapidfuzz, limiar 80, escolhido antes de ver resultados). Meço o WER com jiwer e conto segmentos de eco e de alucinação usando o roteiro como gabarito.

## Resultados

**Eco.** Sem tratamento, o WER do canal da terapeuta foi 125,4% com eco baixo e 123,5% com eco alto. O Whisper transcreveu o vazamento quase inteiro: 399 palavras inseridas, e o paciente diz 398 no roteiro. O filtro entre canais levou o WER a 2,8% e 1,9%. O tratamento 1 sozinho quase não mexeu (123,8% e 123,5%), o que faz sentido: eco é fala, e o VAD a mantém.

**Custo do filtro.** Com limiar 80, nenhum segmento legítimo da terapeuta foi apagado nas quatro condições. Isso depende de uma proteção que acrescentei: em frase de menos de quatro palavras, comparo o texto inteiro e não um trecho. Sem ela, o filtro apagou "Duvidar de novo." em três das quatro condições. Com limiar 50, apagou 11 segmentos legítimos.

**Silêncio.** Com o tratamento 1, o WER ficou em 0,3% e as alucinações em zero nas condições limpa e com ruído. Sem tratamento, o resultado oscilou com o mesmo áudio: na condição limpa, o WER foi de 2,5% a 12,2% em cinco repetições, com 0 a 7 segmentos alucinados. Na execução oficial, a condição com ruído teve 14 segmentos alucinados, quase todos um laço de "E aí...". O tratamento 1 deu o mesmo resultado nas cinco repetições.

## O que não funcionou

**Meu primeiro gabarito estava errado.** Eu classificava os segmentos pelo tempo. Só que, sem VAD, os tempos do Whisper se esticam sobre o silêncio, e uma fala real da terapeuta parecia alucinação. Passei a casar o texto com o roteiro e usar o tempo só para desempatar. Fiz isso depois de ver os números, e por isso registro aqui.

**O filtro por `no_speech_prob` e `compression_ratio` nunca disparou.** O `no_speech_prob` foi 0,000 em todos os segmentos das 10 transcrições, e o maior `compression_ratio` foi 2,29, abaixo do corte de 2,4. Fiz uma ablação: com o ruído, só o VAD deu 1,9% de WER, só `condition_on_previous_text` desligado deu 0,6%, e os dois juntos 0,3%. Quem trabalhou foram essas duas opções.

**Texto não recupera o que o modelo não ouviu.** No eco alto, as interrupções "Duvidar de novo." e "Tudo sozinho." nunca foram transcritas à parte: ficaram engolidas no segmento do eco. São cinco palavras que nenhum filtro de texto traz de volta.

**A proteção tem preço.** No eco baixo, o fragmento "Eu confiro." sobrou depois de T1 e T2, porque o VAD o separou em frase curta e a proteção não o compara por trecho.

## Próximos passos

Quero repetir com vários roteiros e vozes, e com eco gravado de verdade, com caixa de som e microfone. Também quero comparar o filtro por texto com cancelamento de eco por sinal, e medir o `small` em CPU, que é o plano B sem GPU.

## Limitações

A voz é sintética, sem hesitação nem sobreposição natural, e o Whisper costuma ir melhor nela do que em fala real. O eco é uma soma digital, sem a distorção de uma caixa de som, sem o ganho automático do microfone e sem cancelamento de eco do sistema. Usei um roteiro só: 319 palavras da terapeuta, três silêncios e três interrupções, então as contagens de alucinação têm poucos casos. O resultado sem tratamento muda de uma execução para outra, e os números aqui são de execuções específicas. O código, os dados e os testes estão no README.
