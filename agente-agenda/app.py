"""Demonstração do agente de agenda no navegador (Hugging Face Space).

Usa o mesmo agente.py: as mesmas ferramentas e a mesma regra de confirmação.
A diferença é que a confirmação vira dois botões, então o laço precisa parar
e continuar depois do clique.

Rodar local:  python app.py   (precisa de ANTHROPIC_API_KEY)
"""

import copy
import datetime
import os

import gradio as gr

import agente

# Demonstração pública paga com chave pessoal: modelo barato e travas de uso.
MODELO = os.environ.get("MODELO", "claude-haiku-5-5")
LIMITE_POR_DIA = int(os.environ.get("LIMITE_POR_DIA", "300"))  # chamadas ao modelo
MAX_LETRAS = 300

HORARIOS_INICIAIS = copy.deepcopy(agente.HORARIOS_LIVRES)
_uso = {"dia": None, "chamadas": 0}
_cliente = None


class Pausa(Exception):
    """O agente propôs gravar: o laço para e espera o clique da pessoa."""


class LimiteDoDia(Exception):
    pass


def chamar_modelo(mensagens):
    global _cliente
    hoje = datetime.date.today()
    if _uso["dia"] != hoje:
        _uso.update(dia=hoje, chamadas=0)
    if _uso["chamadas"] >= LIMITE_POR_DIA:
        raise LimiteDoDia
    _uso["chamadas"] += 1
    if _cliente is None:
        import anthropic

        _cliente = anthropic.Anthropic()
    return _cliente.messages.create(
        model=MODELO,
        max_tokens=4000,
        system=agente.INSTRUCOES,
        tools=agente.FERRAMENTAS,
        messages=mensagens,
    )


def _pedir_confirmacao(proposta):
    raise Pausa(proposta)


def executar_turno(estado, chat, confirmar):
    """Executa as ferramentas pedidas na última resposta do modelo."""
    resultados = []
    for bloco in estado["mensagens"][-1]["content"]:
        if bloco.type != "tool_use":
            continue
        texto, deu_erro = agente.executar(bloco.name, bloco.input, confirmar)
        resultados.append(
            {
                "type": "tool_result",
                "tool_use_id": bloco.id,
                "content": texto,
                "is_error": deu_erro,
            }
        )
        argumentos = ", ".join(f"{k}={v!r}" for k, v in bloco.input.items())
        chat.append(
            {
                "role": "assistant",
                "content": texto,
                "metadata": {"title": f"Ferramenta: {bloco.name}({argumentos})"},
            }
        )
    estado["mensagens"].append({"role": "user", "content": resultados})


def avancar(estado, chat, chamar=None):
    """Roda o laço até o modelo terminar ou propor um agendamento.

    Devolve a proposta pendente, ou None se o modelo terminou.
    """
    chamar = chamar or chamar_modelo
    for _ in range(agente.MAX_VOLTAS):
        resposta = chamar(estado["mensagens"])
        estado["mensagens"].append({"role": "assistant", "content": resposta.content})
        if resposta.stop_reason != "tool_use":
            texto = "".join(b.text for b in resposta.content if b.type == "text")
            chat.append({"role": "assistant", "content": texto or "(sem resposta)"})
            return None
        try:
            executar_turno(estado, chat, _pedir_confirmacao)
        except Pausa as pausa:
            return pausa.args[0]
    chat.append({"role": "assistant", "content": "Parei: limite de voltas atingido."})
    return None


def _seguro(estado, chat, passo):
    """Roda um passo e transforma falha em mensagem, sem derrubar a página."""
    try:
        return passo()
    except LimiteDoDia:
        aviso = "A demonstração atingiu o limite de uso de hoje. Volte amanhã."
    except Exception as erro:  # chave ausente, rede, erro da API
        aviso = f"Não consegui falar com o modelo ({type(erro).__name__})."
    # a conversa recomeça limpa para não reenviar um turno pela metade
    estado["mensagens"] = []
    chat.append({"role": "assistant", "content": aviso})
    return None


def painel():
    linhas = ["**Horários livres**"]
    for dia, horas in agente.HORARIOS_LIVRES.items():
        linhas.append(f"- {dia}: {', '.join(horas) or 'nenhum'}")
    linhas.append("\n**Sessões marcadas**")
    for item in agente.AGENDA:
        nome = agente.PACIENTES[item["paciente_id"]]
        linhas.append(f"- {nome}, {item['dia']} às {item['hora']}")
    if not agente.AGENDA:
        linhas.append("- nenhuma")
    linhas.append("\n**Pacientes (fictícios)**: " + ", ".join(agente.PACIENTES.values()))
    return "\n".join(linhas)


def _saida(estado, chat, proposta):
    estado["proposta"] = proposta
    pergunta = ""
    if proposta:
        pergunta = (
            f"**O agente propõe:** {proposta['paciente']}, "
            f"{proposta['dia']} às {proposta['hora']}. Você confirma?"
        )
    return (
        estado,
        chat,
        painel(),
        gr.update(value=pergunta, visible=bool(proposta)),
        gr.update(visible=bool(proposta)),
        gr.update(visible=bool(proposta)),
        gr.update(value="", interactive=not proposta),
    )


def ao_enviar(pedido, estado, chat):
    pedido = (pedido or "").strip()[:MAX_LETRAS]
    if not pedido or estado.get("proposta"):
        return _saida(estado, chat, estado.get("proposta"))
    chat.append({"role": "user", "content": pedido})
    estado["mensagens"].append({"role": "user", "content": pedido})
    proposta = _seguro(estado, chat, lambda: avancar(estado, chat))
    return _saida(estado, chat, proposta)


def ao_decidir(aceitou, estado, chat):
    if not estado.get("proposta"):
        return _saida(estado, chat, None)
    chat.append({"role": "user", "content": "Confirmo." if aceitou else "Não confirmo."})

    def passo():
        executar_turno(estado, chat, lambda proposta: aceitou)
        return avancar(estado, chat)

    return _saida(estado, chat, _seguro(estado, chat, passo))


def recomecar():
    agente.AGENDA.clear()
    agente.HORARIOS_LIVRES.clear()
    agente.HORARIOS_LIVRES.update(copy.deepcopy(HORARIOS_INICIAIS))
    return _saida({"mensagens": [], "proposta": None}, [], None)


with gr.Blocks(title="Agente de agenda") as demo:
    gr.Markdown(
        "# Agente de agenda\n"
        "Um agente de IA com três ferramentas. Ele consulta pacientes e horários, "
        "e **só grava depois que você confirma**. Os dados são fictícios. "
        "[Código e explicação](https://github.com/GusHermeto/portfolio-ia/tree/main/agente-agenda)"
    )
    estado = gr.State({"mensagens": [], "proposta": None})
    with gr.Row():
        with gr.Column(scale=2):
            chat = gr.Chatbot(label="Conversa (cada ferramenta chamada aparece aqui)", height=420)
            pergunta = gr.Markdown(visible=False)
            with gr.Row():
                sim = gr.Button("Confirmar", variant="primary", visible=False)
                nao = gr.Button("Recusar", visible=False)
            caixa = gr.Textbox(
                label="Seu pedido",
                placeholder="Marca a Ana Souza na terça às 14h",
                max_length=MAX_LETRAS,
            )
            gr.Examples(
                [
                    "Marca a Ana Souza na terça às 14h",
                    "Quais horários estão livres na quarta?",
                    "Marca o Bruno na sexta às 8h",
                ],
                caixa,
            )
        with gr.Column(scale=1):
            quadro = gr.Markdown(painel())
            limpar = gr.Button("Recomeçar")

    saidas = [estado, chat, quadro, pergunta, sim, nao, caixa]
    caixa.submit(ao_enviar, [caixa, estado, chat], saidas)
    sim.click(lambda e, c: ao_decidir(True, e, c), [estado, chat], saidas)
    nao.click(lambda e, c: ao_decidir(False, e, c), [estado, chat], saidas)
    limpar.click(recomecar, None, saidas)

if __name__ == "__main__":
    demo.launch()
