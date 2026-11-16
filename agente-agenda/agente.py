"""Agente de agenda: um modelo, três ferramentas, um laço e uma confirmação.

É a ideia da Sálvia (a assistente do Caderninho) reduzida ao mínimo, com dados
fictícios. O modelo nunca grava nada sozinho: ele só propõe, e a pessoa confirma.

Uso:  python agente.py "Marca a Ana Souza na terça às 14h"
"""

import json
import sys

MODELO = "claude-opus-5-5"
MAX_VOLTAS = 8  # trava: o laço nunca roda para sempre

INSTRUCOES = (
    "Você é a assistente de agenda de uma psicóloga. Use as ferramentas para "
    "consultar pacientes e horários antes de responder. Nunca invente paciente "
    "nem horário. Para marcar uma sessão, use propor_agendamento."
)

# ---------- 1. Os dados (fictícios, em memória) ----------

PACIENTES = {1: "Ana Souza", 2: "Bruno Lima", 3: "Carla Dias"}
HORARIOS_LIVRES = {"terça": ["09:00", "14:00"], "quarta": ["10:00"]}
AGENDA = []  # cada item: {"paciente_id", "dia", "hora"}

# ---------- 2. As ferramentas (funções comuns de Python) ----------


def buscar_paciente(nome):
    achados = [
        {"id": i, "nome": n} for i, n in PACIENTES.items() if nome.lower() in n.lower()
    ]
    return {"pacientes": achados}


def listar_horarios_livres(dia):
    return {"dia": dia, "livres": HORARIOS_LIVRES.get(dia.lower(), [])}


def propor_agendamento(paciente_id, dia, hora, confirmar):
    """A única ferramenta que grava. Só grava se a pessoa confirmar."""
    if paciente_id not in PACIENTES:
        raise ValueError(f"paciente {paciente_id} não existe")
    if hora not in HORARIOS_LIVRES.get(dia.lower(), []):
        raise ValueError(f"{dia} às {hora} não está livre")
    proposta = {"paciente": PACIENTES[paciente_id], "dia": dia.lower(), "hora": hora}
    if not confirmar(proposta):
        return {"gravado": False, "motivo": "a usuária recusou a proposta"}
    AGENDA.append({"paciente_id": paciente_id, "dia": dia.lower(), "hora": hora})
    HORARIOS_LIVRES[dia.lower()].remove(hora)
    return {"gravado": True, **proposta}


# ---------- 3. A descrição das ferramentas (é isso que o modelo lê) ----------


def _ferramenta(nome, descricao, campos):
    return {
        "name": nome,
        "description": descricao,
        "strict": True,  # o modelo só pode mandar os campos do esquema
        "input_schema": {
            "type": "object",
            "properties": campos,
            "required": list(campos),
            "additionalProperties": False,
        },
    }


FERRAMENTAS = [
    _ferramenta(
        "buscar_paciente",
        "Procura pacientes pelo nome ou parte do nome. Devolve id e nome.",
        {"nome": {"type": "string"}},
    ),
    _ferramenta(
        "listar_horarios_livres",
        "Lista os horários livres de um dia da semana, por exemplo 'terça'.",
        {"dia": {"type": "string"}},
    ),
    _ferramenta(
        "propor_agendamento",
        "Propõe marcar uma sessão. A psicóloga confirma antes de gravar. "
        "Use o id devolvido por buscar_paciente e um horário livre.",
        {
            "paciente_id": {"type": "integer"},
            "dia": {"type": "string"},
            "hora": {"type": "string", "description": "formato HH:MM"},
        },
    ),
]

# ---------- 4. Executar o que o modelo pediu ----------


def executar(nome, dados, confirmar):
    """Roda uma ferramenta. Erro vira texto para o modelo ler e se corrigir."""
    try:
        if nome == "buscar_paciente":
            resultado = buscar_paciente(**dados)
        elif nome == "listar_horarios_livres":
            resultado = listar_horarios_livres(**dados)
        elif nome == "propor_agendamento":
            resultado = propor_agendamento(**dados, confirmar=confirmar)
        else:
            raise ValueError(f"ferramenta desconhecida: {nome}")
        return json.dumps(resultado, ensure_ascii=False), False
    except (ValueError, TypeError) as erro:
        return f"Erro: {erro}", True


# ---------- 5. O laço do agente ----------


def rodar_agente(pedido, chamar_modelo, confirmar):
    """Pergunta ao modelo, executa as ferramentas que ele pedir e repete.

    chamar_modelo(mensagens) devolve a resposta do modelo. Vem de fora para o
    teste poder trocar o modelo real por um roteiro fixo, sem chave e sem custo.
    """
    mensagens = [{"role": "user", "content": pedido}]
    for _ in range(MAX_VOLTAS):
        resposta = chamar_modelo(mensagens)
        if resposta.stop_reason != "tool_use":
            # terminou (ou recusou): devolve o texto que houver
            return "".join(b.text for b in resposta.content if b.type == "text")

        mensagens.append({"role": "assistant", "content": resposta.content})
        resultados = []
        for bloco in resposta.content:
            if bloco.type != "tool_use":
                continue
            texto, deu_erro = executar(bloco.name, bloco.input, confirmar)
            resultados.append(
                {
                    "type": "tool_result",
                    "tool_use_id": bloco.id,
                    "content": texto,
                    "is_error": deu_erro,
                }
            )
        # todos os resultados voltam juntos, numa única mensagem
        mensagens.append({"role": "user", "content": resultados})
    return "Parei: o limite de voltas foi atingido."


# ---------- 6. O modelo real e a confirmação no terminal ----------


def modelo_claude():
    import anthropic  # só é preciso para rodar de verdade, não para os testes

    cliente = anthropic.Anthropic()

    def chamar(mensagens):
        return cliente.beta.messages.create(
            model=MODELO,
            max_tokens=16000,
            system=INSTRUCOES,
            tools=FERRAMENTAS,
            messages=mensagens,
            # se o modelo recusar, o servidor tenta outro modelo sozinho
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    return chamar


def confirmar_no_terminal(proposta):
    print(f"\nProposta: {proposta['paciente']}, {proposta['dia']} às {proposta['hora']}.")
    return input("Confirmar? (s/n) ").strip().lower() == "s"


if __name__ == "__main__":
    pedido = " ".join(sys.argv[1:]) or "Marca a Ana Souza na terça às 14h"
    print(rodar_agente(pedido, modelo_claude(), confirmar_no_terminal))
