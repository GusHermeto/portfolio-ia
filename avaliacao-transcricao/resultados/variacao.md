## Variação entre 5 execuções com o mesmo áudio (mínimo / mediana / máximo)

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
