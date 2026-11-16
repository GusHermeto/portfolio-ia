# Agente de agenda (Python)

Um agente de IA pequeno, escrito para ser lido: um modelo, três ferramentas, um laço e uma confirmação humana. É a ideia central da Sálvia, a assistente do [Caderninho](../README.md#1-caderninho-ia-para-psicólogas), reduzida ao mínimo e com dados fictícios.

No produto, a Sálvia tem 20 ferramentas e é escrita em TypeScript. Aqui são 3, em Python, num arquivo só: [agente.py](agente.py).

## O que é um agente, em quatro partes

| Parte | O que é | Onde está |
|---|---|---|
| Modelo | Quem decide o próximo passo | `modelo_claude()` |
| Ferramentas | Funções comuns de Python, cada uma com uma descrição que o modelo lê | `FERRAMENTAS` e as três funções |
| Laço | Pergunta ao modelo, executa o que ele pediu, devolve o resultado, repete | `rodar_agente()` |
| Regras | Quando parar e o que precisa de confirmação | `MAX_VOLTAS` e `propor_agendamento()` |

## Como uma conversa acontece

Pedido: "Marca a Ana Souza na terça às 14h".

1. O código manda o pedido e a lista de ferramentas para o modelo.
2. O modelo responde "quero chamar `buscar_paciente` com nome Ana Souza". Ele não executa nada; só pede.
3. O código executa a função e devolve o resultado: id 1.
4. O modelo pede `propor_agendamento` com id 1, terça, 14:00.
5. O código confere se o horário está livre e pergunta à pessoa. Só grava com o "sim".
6. O modelo recebe "gravado" e escreve a resposta final. O laço termina.

## Três decisões

- **O modelo propõe, a pessoa confirma.** A única ferramenta que grava passa por `confirmar()`. Um erro do modelo vira uma proposta recusada, e não um dado errado na agenda.
- **Erro volta como texto.** Horário ocupado ou paciente inexistente não derruba o programa. O modelo lê o erro e pode se corrigir.
- **O laço tem limite.** No máximo 8 voltas. Um agente sem trava pode rodar sem fim e gastar sem fim.

## Rodar

```
pip install -r requirements.txt
pytest
```

Os 6 testes usam um modelo de roteiro fixo, sem chave e sem custo. Eles provam o código em volta do modelo: o laço, a confirmação, o erro e o limite de voltas.

Com o modelo real (precisa da variável `ANTHROPIC_API_KEY`):

```
python agente.py "Marca a Ana Souza na terça às 14h"
```

## O que este exemplo não prova

Os testes não medem se o modelo escolhe a ferramenta certa. Isso pede uma avaliação com pedidos reais e o modelo real, que este exemplo não tem.
