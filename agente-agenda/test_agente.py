"""Testes do agente com um modelo de roteiro fixo: sem chave e sem custo.

O que se testa aqui é o código em volta do modelo: o laço, a execução das
ferramentas, a confirmação e as travas. Rodar:  pytest
"""

import copy
import json
from types import SimpleNamespace

import pytest

import agente


@pytest.fixture(autouse=True)
def dados_limpos(monkeypatch):
    monkeypatch.setattr(agente, "AGENDA", [])
    monkeypatch.setattr(agente, "HORARIOS_LIVRES", copy.deepcopy(agente.HORARIOS_LIVRES))


def pede(nome, dados, id_="t1"):
    bloco = SimpleNamespace(type="tool_use", id=id_, name=nome, input=dados)
    return SimpleNamespace(stop_reason="tool_use", content=[bloco])


def fala(texto):
    return SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text=texto)]
    )


def roteiro(*respostas):
    """Modelo falso: devolve as respostas em ordem e guarda o que recebeu."""
    fila = list(respostas)
    vistas = []

    def chamar(mensagens):
        vistas.append(copy.deepcopy(mensagens))
        return fila.pop(0)

    chamar.vistas = vistas
    return chamar


MARCAR = [
    pede("buscar_paciente", {"nome": "ana"}, "t1"),
    pede("propor_agendamento", {"paciente_id": 1, "dia": "terça", "hora": "14:00"}, "t2"),
    fala("Sessão marcada."),
]


def test_confirmado_grava():
    modelo = roteiro(*MARCAR)
    texto = agente.rodar_agente("Marca a Ana", modelo, confirmar=lambda p: True)
    assert texto == "Sessão marcada."
    assert agente.AGENDA == [{"paciente_id": 1, "dia": "terça", "hora": "14:00"}]
    assert "14:00" not in agente.HORARIOS_LIVRES["terça"]


def test_recusado_nao_grava():
    modelo = roteiro(*MARCAR)
    agente.rodar_agente("Marca a Ana", modelo, confirmar=lambda p: False)
    assert agente.AGENDA == []
    assert "14:00" in agente.HORARIOS_LIVRES["terça"]


def test_resultado_da_ferramenta_volta_para_o_modelo():
    modelo = roteiro(pede("buscar_paciente", {"nome": "ana"}), fala("Achei."))
    agente.rodar_agente("Quem é Ana?", modelo, confirmar=lambda p: True)
    resultado = modelo.vistas[1][-1]["content"][0]
    assert resultado["tool_use_id"] == "t1"
    assert json.loads(resultado["content"]) == {"pacientes": [{"id": 1, "nome": "Ana Souza"}]}


def test_horario_ocupado_vira_erro_e_nao_grava():
    modelo = roteiro(
        pede("propor_agendamento", {"paciente_id": 1, "dia": "terça", "hora": "23:00"}),
        fala("Esse horário não está livre."),
    )
    agente.rodar_agente("Marca às 23h", modelo, confirmar=lambda p: True)
    resultado = modelo.vistas[1][-1]["content"][0]
    assert resultado["is_error"] is True
    assert agente.AGENDA == []


def test_ferramenta_desconhecida_vira_erro():
    texto, deu_erro = agente.executar("apagar_tudo", {}, confirmar=lambda p: True)
    assert deu_erro is True
    assert "desconhecida" in texto


def test_laco_para_no_limite():
    sem_fim = [pede("listar_horarios_livres", {"dia": "terça"})] * agente.MAX_VOLTAS
    texto = agente.rodar_agente("...", roteiro(*sem_fim), confirmar=lambda p: True)
    assert "limite" in texto
