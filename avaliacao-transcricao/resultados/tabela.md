## WER do canal A (terapeuta), em %

| condição | antes | T1 silêncio | T2 eco | T1+T2 |
|---|---|---|---|---|
| limpo | 4,4 | 0,3 | 4,4 | 0,3 |
| eco_baixo | 125,4 | 123,8 | 2,8 | 1,6 |
| eco_alto | 123,5 | 123,5 | 1,9 | 1,9 |
| ruido | 12,5 | 0,3 | 12,5 | 0,3 |

## Segmentos do canal A por tipo (gabarito do roteiro)

`fala` = fala legítima da terapeuta; `eco` = fala do paciente no canal da terapeuta; `silêncio` = texto inventado dentro de um silêncio longo; `outro` = texto sem apoio no roteiro, fora dele.`removidos` = o que o filtro descartou; `fala removida` = fala legítima apagada por engano.

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

## Canal B (paciente, som do computador)

| tratamento | WER % | segmentos | fala | silêncio | outro |
|---|---|---|---|---|---|
| antes | 0,3 | 37 | 37 | 0 | 0 |
| T1 silêncio | 0,0 | 49 | 49 | 0 | 0 |

## Sensibilidade do filtro de eco (T2 sozinho)

Eco que sobra no canal A por condição, e fala legítima da terapeuta apagada (soma das quatro condições).

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
