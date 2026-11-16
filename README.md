# Gustavo Hermeto: portfólio de IA

Estudante de Engenharia de Computação na UNIFEI (Itajubá, MG). Construo produtos com IA de ponta a ponta: do áudio ao texto, do texto à ação, com teste e com cuidado com dado sensível.

- Site do produto: [caderninhoai.com](https://caderninhoai.com)
- LinkedIn: [linkedin.com/in/hermeto](https://www.linkedin.com/in/hermeto/)

| Projeto | O que é | IA envolvida |
|---|---|---|
| [Caderninho](#1-caderninho-ia-para-psicólogas) | App de desktop que transcreve a sessão e rascunha o prontuário | Transcrição, LLM, agente com 21 ferramentas, busca em documentos |
| [Como eu construo com agentes](#2-como-eu-construo-com-agentes) | O método que uso para desenvolver sozinho com vários agentes de IA | Orquestração, roteamento de modelos, revisão automática |
| [Mão biônica por voz](#3-mão-biônica-controlada-por-voz-tinyml) | Prótese que obedece a comandos de voz em português | TinyML, reconhecimento de palavras em microcontrolador |
| [Avaliação de transcrição com eco](avaliacao-transcricao/) | Experimento aberto e reproduzível: Whisper em português, com eco e silêncio | Whisper large-v3-turbo local, WER, filtro entre canais. Com [artigo](avaliacao-transcricao/ARTIGO.md) |

---

## 1. Caderninho: IA para psicólogas

**Problema.** Uma psicóloga precisa estar inteira na sessão com o paciente. Anotar durante a conversa tira a atenção, e depois ainda sobra o prontuário para escrever e o histórico para reler antes do próximo encontro.

**O que eu construí.** Sou o único desenvolvedor. O app está publicado (versão 0.2.8, Windows) e em teste com uma psicóloga e um testador.

- **Transcrição em dois canais.** O microfone é a psicóloga e o som do computador é o paciente. A separação de quem fala vem do canal, não de um modelo adivinhando.
- **Resumo e rascunho de prontuário.** A IA escreve o rascunho; a psicóloga edita e assina. A decisão clínica continua com ela.
- **Resumo para a próxima sessão.** Antes do encontro seguinte, o app mostra os temas da última sessão, o que ela marcou e a linha do tempo.
- **Sálvia, a assistente.** Um agente com 21 ferramentas. Ela consulta (pacientes, sessões, agenda, biblioteca, pagamentos, horários livres) e age (criar paciente, marcar, remarcar e cancelar consulta, anotar). Aceita pedido por voz.
- **Biblioteca.** A psicóloga carrega seus documentos e a Sálvia busca neles. A busca roda no computador dela (BM25), e só os trechos mais relevantes vão ao modelo.

### Decisões de engenharia

**Toda ação da IA é uma proposta.** A Sálvia nunca grava nada sozinha. Ela monta a proposta ("marcar Maria na quinta às 14h?") e a psicóloga confirma. Um erro do modelo vira uma sugestão recusada, não um dado errado no prontuário.

**Dado de saúde fica com a psicóloga.**
- O banco fica no computador dela, cifrado com AES-256-GCM, com a chave protegida pelo Windows (DPAPI).
- O áudio é enviado para transcrição e não é guardado. O app guarda só o texto.
- O servidor não guarda áudio nem texto de sessão.
- Antes de ir ao modelo, os nomes viram `[TERAPEUTA]` e `[PACIENTE]`. Isso reduz exposição, mas não é anonimização, e eu não vendo como se fosse.
- A sincronia entre computadores é cifrada de ponta a ponta.

**Medir antes de acreditar.** O que eu medi até agora:

| Medida | Resultado | Como |
|---|---|---|
| Erro de transcrição (WER) | cerca de 10,5% no canal do paciente | Roteiro de 880 palavras com voz sintética, tocado em caixa de som |
| Eco virando fala errada | de 16 linhas para 6 | Mesmo tipo de teste, antes e depois do conserto |
| Custo de IA | cerca de R$ 0,08 por sessão de 48 min | Teste com voz sintética |
| Testes automáticos | mais de 14 mil | Suíte do projeto |

**O que ainda não está bom, e eu sei.**
- Não há medida de erro com voz real em consultório. O teste usa voz sintética, de propósito: eu não uso áudio de paciente para desenvolver.
- O eco da caixa de som ainda gera linhas erradas. Caiu de 16 para 6, não para zero.
- Sessão presencial precisa separar vozes num microfone só (diarização). Ainda não existe no app.
- Não medi quanto tempo a psicóloga economiza. Enquanto não medir, não afirmo.

**Tecnologia.** Electron, TypeScript, React, banco local cifrado, servidor em Cloudflare Workers, transcrição e LLM por API. O código é privado porque o produto é comercial; explico qualquer parte em entrevista.

---

## 2. Como eu construo com agentes

Desenvolvo o Caderninho sozinho, coordenando vários agentes de IA. Eu não escrevo a maior parte do código: eu decido o que construir, defino as regras e confiro o resultado. O método tem cinco partes.

**1. Uma sessão coordena, as outras executam.** Uma sessão principal conversa comigo e divide o trabalho em pacotes fechados. Cada pacote vai para um agente com um objetivo, os arquivos e a definição de pronto. Cada frente do produto (app, site, celular) tem a sua pasta e a sua branch no git, para um agente não pisar no trabalho do outro.

**2. O modelo certo para cada tarefa.** O modelo mais forte planeja e revisa código de risco. Um modelo intermediário implementa. O modelo mais barato faz volume: buscas, listas, resumos de log. Isso corta custo sem perder qualidade onde ela importa.

**3. Relatório de agente não é prova.** Um agente dizer "terminei e os testes passam" não vale. Um segundo agente, revisor, roda os testes ele mesmo. Código de risco (áudio, dado de paciente, criptografia, cobrança) passa por revisão do modelo mais forte.

**4. Portão antes de cada entrega.** Nada entra sem checagem de tipos, build e os testes do que foi tocado. A suíte inteira roda antes de gerar o instalador. Mudança visual precisa de imagem de antes e depois, porque teste verde não prova que a tela ficou boa.

**5. Memória escrita.** As regras de produto ficam num documento único de fatos vigentes. Cada sessão mantém um arquivo curto de estado. Assim um agente novo começa sabendo o que já foi decidido, e eu não repito a mesma explicação.

**O que aprendi fazendo isso.**
- Agente com tarefa vaga produz muito e acerta pouco. O ganho está em escrever um pedido fechado.
- Agentes em paralelo esgotam o limite de uso rápido. Poucos agentes bem dirigidos rendem mais que muitos.
- O erro mais caro não é o código errado; é o agente consertar a coisa errada com confiança. Hoje eu peço que ele me mostre o que entendeu antes de mexer.

**Ferramentas.** Claude Code (sessões, subagentes e worktrees do git), Antigravity (o ambiente de agentes do Google, com os modelos Gemini) como segundo par de olhos, e um grafo do código para o agente achar o caminho sem ler o projeto inteiro.

---

## 3. Mão biônica controlada por voz (TinyML)

Projeto da equipe Ex Machina, da UNIFEI, da qual fui analista e projetista de eletrônica de 2022 a 2024. O projeto foi destaque no blog oficial da Arduino: [Controlling a bionic hand with tinyML keyword spotting](https://blog.arduino.cc/2022/08/31/controlling-a-bionic-hand-with-tinyml-keyword-spotting/).

**O que é.** Uma mão biônica que abre, fecha e faz gestos por comando de voz em português. O modelo roda dentro do microcontrolador (Arduino Nano 33 BLE Sense), sem internet.

**Como foi feito.**
- A equipe gravou cerca de 3,5 horas de áudio com 6 comandos.
- O som vira características MFCC, e uma rede neural pequena (Keras, treinada no Edge Impulse) classifica o comando.
- O modelo chegou a cerca de 95% de acerto.

**Minha parte.** Projeto do circuito e da placa (Altium Designer), coleta dos áudios com a equipe e treino do modelo no Edge Impulse.

**O que ficou comigo.** IA em hardware pequeno ensina a respeitar limite: memória, bateria e latência decidem o modelo, não o contrário. Usei a mesma cabeça no Caderninho, onde o limite é privacidade e custo por sessão.

---

## Contato

[linkedin.com/in/hermeto](https://www.linkedin.com/in/hermeto/)
