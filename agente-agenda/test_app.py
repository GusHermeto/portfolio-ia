"""Testes da demonstração: o laço que para na proposta e continua no clique."""

import copy

import pytest

gr = pytest.importorskip("gradio")

import agente  # noqa: E402
import app  # noqa: E402
from test_agente import MARCAR, roteiro  # noqa: E402


@pytest.fixture(autouse=True)
def dados_limpos(monkeypatch):
    monkeypatch.setattr(agente, "AGENDA", [])
    monkeypatch.setattr(agente, "HORARIOS_LIVRES", copy.deepcopy(app.HORARIOS_INICIAIS))


def conversa(monkeypatch, aceitou):
    monkeypatch.setattr(app, "chamar_modelo", roteiro(*MARCAR))
    estado, chat, *_ = app.ao_enviar("Marca a Ana", {"mensagens": [], "proposta": None}, [])
    # parou na proposta, sem gravar
    assert estado["proposta"] == {"paciente": "Ana Souza", "dia": "terça", "hora": "14:00"}
    assert agente.AGENDA == []
    estado, chat, *_ = app.ao_decidir(aceitou, estado, chat)
    assert estado["proposta"] is None
    return chat


def test_confirmar_grava(monkeypatch):
    chat = conversa(monkeypatch, True)
    assert agente.AGENDA == [{"paciente_id": 1, "dia": "terça", "hora": "14:00"}]
    assert chat[-1]["content"] == "Sessão marcada."


def test_recusar_nao_grava(monkeypatch):
    conversa(monkeypatch, False)
    assert agente.AGENDA == []


def test_falha_do_modelo_vira_aviso(monkeypatch):
    def quebrado(mensagens):
        raise RuntimeError("sem rede")

    monkeypatch.setattr(app, "chamar_modelo", quebrado)
    estado, chat, *_ = app.ao_enviar("oi", {"mensagens": [], "proposta": None}, [])
    assert "Não consegui" in chat[-1]["content"]
    assert estado["mensagens"] == []


def test_limite_do_dia(monkeypatch):
    monkeypatch.setattr(app, "LIMITE_POR_DIA", 0)
    estado, chat, *_ = app.ao_enviar("oi", {"mensagens": [], "proposta": None}, [])
    assert "limite de uso" in chat[-1]["content"]
