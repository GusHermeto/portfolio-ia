# Gustavo Hermeto: portfólio de IA

Estudante de Engenharia de Computação na UNIFEI (Itajubá, MG). Construo produtos com IA de ponta a ponta: do áudio ao texto, do texto à ação. Meço o que construo e cuido de dado sensível. Meu ponto de partida é sempre a necessidade de quem vai usar.

- Site do produto: [caderninhoai.com](https://caderninhoai.com)
- LinkedIn: [linkedin.com/in/hermeto](https://www.linkedin.com/in/hermeto/)

## Em números

| Número | O que é | Base e condição |
|---|---|---|
| **14.580** | verificações automáticas passando no app publicado | Suíte inteira de 13/11/2026, antes da versão 0.2.8. 54% das linhas de código do app são teste |
| **125,4% → 1,6%** | erro de transcrição (WER) com eco, antes e depois do meu filtro | Experimento aberto e reproduzível, 319 palavras, voz sintética, eco simulado. Nenhuma fala legítima apagada |
| **94% menos** | linhas de eco na transcrição do app: de 105 para 6 | Teste com caixa de som e microfone reais, fala humana de corpus público, uma rodada de cada versão, 07/11/2026 |
| **90% menos** | custo de transcrição por sessão: de R$ 0,48 para R$ 0,05 | Sessão de 50 min, pelas tabelas públicas de preço. Custo total medido depois: R$ 0,084 por sessão de 48 min |
| **1.966 commits em 81 dias** | um produto inteiro, sozinho, coordenando agentes de IA | App, servidor, site e celular, de 27/08 a 15/11/2026. 9 versões numeradas do instalador |
| **95% de acerto** | modelo de voz rodando dentro de um microcontrolador | Prótese de mão, 6 comandos em português, cerca de 3,5 h de áudio. Destaque no blog da Arduino |

## Projetos

| Projeto | O que é | IA envolvida |
|---|---|---|
| [Caderninho](#1-caderninho-ia-para-psicólogas) | App de desktop que transcreve a sessão e rascunha o prontuário | Transcrição, LLM, agente com 20 ferramentas, busca em documentos, cancelador de eco neural |
| [Como eu construo com agentes](#2-como-eu-construo-com-agentes) | O método que uso para desenvolver sozinho com vários agentes de IA | Orquestração, roteamento de modelos, revisão automática |
| [Prótese biônica de mão](#3-prótese-biônica-de-mão-tecnologia-assistiva-e-tinyml) | Tecnologia assistiva: prótese para pessoas com deficiência, controlada por voz em português | TinyML, reconhecimento de palavras em microcontrolador |
| [Avaliação de transcrição com eco](#4-avaliação-de-transcrição-com-eco) | Experimento aberto e reproduzível: Whisper em português, com eco e silêncio | Whisper large-v3-turbo local, WER, filtro entre canais. Com [código](avaliacao-transcricao/) e [artigo](avaliacao-transcricao/ARTIGO.md) |

Também nesta página: [Como eu valido IA](#como-eu-valido-ia) · [Minha trajetória](#minha-trajetória) · [O que ainda falta medir](#o-que-ainda-falta-medir)

---

## 1. Caderninho: IA para psicólogas

**O que é.** O Caderninho é um aplicativo para psicólogas. Nasceu de um problema real da minha prima, que é psicóloga: ela queria estar inteira na sessão, sem anotar enquanto o paciente fala. Depois da sessão ainda sobrava o prontuário para escrever e o histórico para reler antes do encontro seguinte. Construí o app para ela e para o dia a dia de outras psicólogas.

**Estado hoje.** Sou o único desenvolvedor. O app está publicado (versão 0.2.8, Windows, 13/11/2026) e em teste com uma psicóloga e um testador.

**O que o app faz.**

- **Transcreve a sessão em dois canais.** O microfone é a psicóloga e o som do computador é o paciente. Quem falou vem do canal, não de um modelo adivinhando. O áudio segue em pedaços de 30 segundos.
- **Escreve o resumo e o rascunho do prontuário.** A IA rascunha; a psicóloga edita e assina. A decisão clínica continua com ela.
- **Prepara a próxima sessão.** Antes do encontro seguinte, o app mostra os temas da última sessão, o que ela marcou e a linha do tempo.
- **Tem a Sálvia.** A Sálvia é a assistente de IA do Caderninho: um agente com 20 ferramentas que responde perguntas e cuida da agenda por texto ou por voz. Ela consulta (pacientes, sessões, agenda, biblioteca, pagamentos, horários livres) e propõe ações (criar paciente, marcar, remarcar e cancelar consulta, anotar, desfazer).
- **Busca na biblioteca dela.** A psicóloga carrega seus documentos e a Sálvia busca neles. A busca roda no computador dela (BM25), e só os trechos mais relevantes vão ao modelo.
- **Limpa o eco no próprio computador.** Um cancelador de eco neural (modelo DTLN em ONNX) roda no app, sem servidor. Ele troca sozinho para um modelo menor quando o computador é fraco.

### Decisões de engenharia

**Toda ação da IA é uma proposta.** A Sálvia nunca grava nada sozinha. Ela monta a proposta ("marcar Maria na quinta às 14h?") e a psicóloga confirma. Um erro do modelo vira uma sugestão recusada, não um dado errado no prontuário.

**Dado de saúde fica com a psicóloga.**

- O banco fica no computador dela, cifrado com AES-256-GCM, com a chave protegida pelo Windows (DPAPI).
- O áudio é enviado para transcrição e não é guardado. O app guarda só o texto.
- O servidor não guarda áudio nem texto de sessão.
- Antes de ir ao modelo, os nomes viram `[TERAPEUTA]` e `[PACIENTE]`. Isso reduz exposição, mas não é anonimização, e eu não vendo como se fosse.
- A sincronia entre computadores é cifrada de ponta a ponta (AES-256-GCM com chave derivada no computador dela). O servidor só vê bytes cifrados.

**A IA passa pelo meu servidor.** O app não carrega chave de fornecedor. O servidor (Cloudflare Workers, banco D1 com 45 migrações) confere a conta, aplica os limites e repassa o pedido.

### O que eu medi

| Medida | Resultado | Base e condição |
|---|---|---|
| Testes automáticos do app | 14.580 passando (3.726 em TypeScript e 10.854 em Python) | Suíte inteira de 13/11/2026, sobre o código da versão 0.2.8 |
| Peso dos testes no código | 54% das linhas (130 mil de 239 mil) | Python e TypeScript do app, contagem nos arquivos do repositório em 16/11/2026 |
| Eco virando fala errada, com e sem o cancelador neural | de 105 linhas para 6 (94% menos); em palavras, de 513 para 13 | Fala humana de 7 min tocada em caixa de som, ninguém falando no microfone, uma rodada de cada versão, 07/11/2026 |
| Eco depois de mais um conserto | de 16 linhas para 6 (62,5% menos) | Mesmo teste, uma rodada de cada versão, 12/11/2026 |
| Erro de transcrição (WER) com fala humana | de 10,5% a 11,8% no canal do paciente | 7 rodadas, 880 palavras de fala espontânea de corpus público, tocada em caixa de som |
| Erro de transcrição (WER) com voz sintética | de 1,6% a 2,2% | 4 rodadas, 730 palavras, mesmo caminho do app |
| Custo de transcrição por sessão | de R$ 0,48 para R$ 0,05 (90% menos) | Sessão de 50 min, tabelas públicas de preço de setembro de 2026, ao trocar de fornecedor e de modelo |
| Custo total de IA por sessão | R$ 0,084 | Medido em 02/10/2026 com a API real: sessão de 48 min, dois canais, transcrição mais prontuário, voz sintética |
| Velocidade com muito histórico | 11 ms de mediana para abrir uma conversa (meta: 300 ms) | Banco cifrado de teste com 1,2 milhão de mensagens, 30 amostras por rota, 09/10/2026 |
| App de celular | 951 testes passando | Suíte de 14/11/2026. Expo e React Native. Ainda não publicado |

Duas leituras que eu tiro dessa tabela:

- **Voz sintética engana.** No mesmo caminho do app, o erro com voz sintética ficou perto de 2% e com fala humana espontânea ficou perto de 11%. Cerca de 5 vezes mais. Por isso troquei o material do teste de campo.
- **O eco varia.** Com o cancelador, o resultado foi de 0 a 39 linhas em 5 rodadas. O pior caso veio com o processador ocupado, quando o modelo neural só conseguiu rodar em 5% do tempo. Achei a causa lendo o registro do próprio cancelador.

**Tecnologia.** Electron, TypeScript, React, Python (FastAPI) no motor local, banco local cifrado, ONNX Runtime no navegador, servidor em Cloudflare Workers, transcrição (Whisper large-v3-turbo) e LLM por API. O código é privado porque o produto é comercial; explico qualquer parte em entrevista.

---

## 2. Como eu construo com agentes

Desenvolvo o Caderninho sozinho, coordenando vários agentes de IA. Em 81 dias foram 1.966 commits em quatro frentes (app, servidor e site, celular, documentos). Eu não escrevo a maior parte do código: eu decido o que construir, defino as regras e confiro o resultado. O método tem cinco partes.

**1. Uma sessão coordena, as outras executam.** Uma sessão principal conversa comigo e divide o trabalho em pacotes fechados. Cada pacote vai para um agente com um objetivo, os arquivos e a definição de pronto. Cada frente do produto tem a sua pasta e a sua branch no git, para um agente não pisar no trabalho do outro.

**2. O modelo certo para cada tarefa.** O modelo mais forte planeja e revisa código de risco. Um modelo intermediário implementa. O modelo mais barato faz volume: buscas, listas, resumos de log. Isso corta custo sem perder qualidade onde ela importa.

**3. Relatório de agente não é prova.** Um agente dizer "terminei e os testes passam" não vale. Um segundo agente, revisor, roda os testes ele mesmo. Código de risco (áudio, dado de paciente, criptografia, cobrança) passa por revisão do modelo mais forte. 174 commits registram essa revisão na própria mensagem.

**4. Portão antes de cada entrega.** Nada entra sem checagem de tipos, build e os testes do que foi tocado. A suíte inteira roda antes de gerar o instalador. Mudança visual precisa de imagem de antes e depois, porque teste verde não prova que a tela ficou boa.

**5. Memória escrita.** As regras de produto ficam num documento único de fatos vigentes. Cada sessão mantém um arquivo curto de estado. Assim um agente novo começa sabendo o que já foi decidido, e eu não repito a mesma explicação.

**O que aprendi fazendo isso.**

- Agente com tarefa vaga produz muito e acerta pouco. O ganho está em escrever um pedido fechado.
- Agentes em paralelo esgotam o limite de uso rápido. Poucos agentes bem dirigidos rendem mais que muitos.
- O erro mais caro não é o código errado; é o agente consertar a coisa errada com confiança. Hoje eu peço que ele me mostre o que entendeu antes de mexer.

**Ferramentas.** Claude Code (sessões, subagentes e worktrees do git), Antigravity (o ambiente de agentes do Google, com os modelos Gemini) como segundo par de olhos, e um grafo do código para o agente achar o caminho sem ler o projeto inteiro.

---

## 3. Prótese biônica de mão (tecnologia assistiva e TinyML)

Projeto da equipe Ex Machina, da UNIFEI, que desenvolve próteses biônicas para pessoas com deficiência. Fui analista e projetista de eletrônica da equipe de março de 2022 a abril de 2024. O projeto foi destaque no blog oficial da Arduino em 31/08/2022: [Controlling a bionic hand with tinyML keyword spotting](https://blog.arduino.cc/2022/08/31/controlling-a-bionic-hand-with-tinyml-keyword-spotting/).

**O que é.** Uma prótese de mão que abre, fecha e faz gestos por comando de voz em português, pensada para devolver autonomia a quem perdeu o movimento ou o membro. O modelo roda dentro do microcontrolador (Arduino Nano 33 BLE Sense), sem internet.

**Como foi feito.**

- A equipe gravou cerca de 3,5 horas de áudio com 6 comandos.
- O som vira características MFCC, e uma rede neural pequena (Keras, treinada no Edge Impulse) classifica o comando.
- O modelo chegou a cerca de 95% de acerto.

**Minha parte.** Projetei o circuito e a placa (Altium Designer), coletei os áudios com a equipe e treinei o modelo no Edge Impulse.

**O que ficou comigo.** IA em hardware pequeno ensina a respeitar limite: memória, bateria e latência decidem o modelo, não o contrário. Usei a mesma cabeça no Caderninho, onde o limite é privacidade e custo por sessão.

---

## 4. Avaliação de transcrição com eco

Um experimento pequeno, aberto e reproduzível em 3 comandos: [código e resultados](avaliacao-transcricao/) e [artigo](avaliacao-transcricao/ARTIGO.md). Isolei fora do produto dois problemas que encontrei no Caderninho.

**O problema.** Numa consulta online, a voz do paciente sai da caixa de som, volta pelo microfone e aparece repetida na fala da terapeuta (eco). E o Whisper inventa frases onde ninguém fala (alucinação em silêncio).

**O que eu fiz.** Montei um roteiro fictício de 54 turnos, gerei os dois canais com voz sintética, simulei quatro condições (limpo, eco baixo, eco alto, ruído) e medi o WER antes e depois de dois tratamentos, sem treinar nada. Rodei o Whisper large-v3-turbo local, numa RTX 2060.

| Resultado | Antes | Depois | Base |
|---|---|---|---|
| WER com eco baixo | 125,4% | 1,6% | Canal da terapeuta, 319 palavras |
| WER com eco alto | 123,5% | 1,9% | Mesmo canal |
| WER com ruído de ambiente | 12,5% | 0,3% | Mesmo canal |
| Fala legítima apagada pelo filtro | | 0 segmentos | Nas quatro condições, com o limiar fixado antes de ver o resultado |
| Variação entre 5 execuções iguais | de 2,5% a 12,2% | 0,3% nas cinco | Condição limpa, mesmo áudio |

**O que a medida mostrou.**

- Sem tratamento, o Whisper transcreveu o vazamento quase inteiro: 399 palavras a mais num canal em que o paciente diz 398.
- O filtro entre canais resolve o eco. Tirar o silêncio antes (VAD) não resolve, porque eco é fala.
- Uma parte do meu tratamento nunca disparou. O filtro por probabilidade de silêncio não cortou nada em 10 transcrições. Está escrito no artigo, na seção do que não funcionou.
- O resultado sem tratamento muda a cada execução. Um número único enganaria; publiquei a faixa.

---

## Como eu valido IA

**1. Escolho a métrica pelo dano, não pelo costume.** WER é o começo. Num prontuário, o erro grave é o nome de remédio trocado e a frase inventada. Em 14/09/2026 comparei três serviços de transcrição no mesmo áudio (374 palavras, voz sintética): o WER foi de 2,1% a 5,1%. Um deles apagou o nome de um remédio e marcou as palavras vizinhas com 97% a 99% de confiança. Outro trocou o remédio por outro que existe. Em 26/10/2026 comparei 6 modelos de fala com três medidas: WER, nomes de remédio certos (19 no roteiro) e palavras inventadas no silêncio. Um modelo empatou no WER com o melhor (4,4% contra 4,6%) e inventou 276 palavras em silêncio. Ficou fora.

**2. Monto a base de teste antes de mexer.** Roteiro fictício com gabarito, áudio que qualquer pessoa pode refazer e o limiar fixado antes de ver o resultado. Não uso áudio de paciente para desenvolver. Para a Sálvia, mantenho um gabarito de 44 casos, 21 deles críticos, travado por versão. Ele inclui injeção de prompt escondida dentro da transcrição de uma sessão: a assistente não pode obedecer a um texto que o paciente falou.

**3. Testo o teste (mutação).** Um teste que nunca falha não prova nada. Eu quebro o código de propósito e confiro se o teste acusa. 49 commits do projeto registram essa conferência. Um revisor que encontra um teste que passa com o código quebrado devolve o pacote.

**4. Repito e mostro a faixa.** Modelo de fala sorteia. No experimento aberto, o mesmo áudio deu de 2,5% a 12,2% de erro em cinco execuções. No app, o eco deu de 0 a 39 linhas conforme a carga do computador. Eu publico o mínimo e o máximo, e digo quantas rodadas foram.

**5. Escrevo o que não funcionou.** Voz sintética mediu cerca de 2% de erro onde fala humana mediu cerca de 11%. O corte do áudio por pausa piorou o acerto de remédios nos 6 modelos em relação ao pedaço fixo de 30 segundos (no Whisper large-v3, de 16 para 13 em 19). Meu filtro de silêncio por probabilidade nunca disparou. Cada um desses achados mudou uma decisão.

**6. Segurança entra na validação.** A IA só propõe, a pessoa confirma. O dado sensível fica cifrado no computador de quem é dona dele. Os testes cobrem o cofre trancado e a cifra da sincronia, com vetores que o computador e o celular conferem dos dois lados.

---

## Minha trajetória

Sou voltado para a necessidade de quem usa. O diretório de estudantes, a prótese para pessoas com deficiência, o suporte no instituto e o Caderninho são a mesma coisa: ouvir uma pessoa real, entender o problema e resolver.

- **Engenharia de Computação, UNIFEI (Itajubá, MG).** Formatura prevista para 2028. Não passei de primeira: comecei no campus de Itabira e entrei em Itajubá em 2019.2 pela prova de transferência, entre os três primeiros colocados.
- **DCE da UNIFEI.** Secretário Executivo (mai/2022 a abr/2023), depois Diretor Administrativo e presidente da Sede Social (mai/2023 a abr/2024), reeleito (abr/2025 a mai/2026). Cuidei de finanças, custos, equipes, fornecedores e parcerias. Na primeira semana do mandato de 2023, a prefeitura abriu a desapropriação da sede. Atuei em duas frentes: com advogado e perícia, e indo a Brasília a uma reunião no IPHAN para pedir apoio. Uma assembleia com 378 estudantes rejeitou a proposta da prefeitura (nota oficial da UNIFEI de 24/05/2023).
- **Ex Machina (mar/2022 a abr/2024).** Eletrônica e modelo de voz da [prótese biônica](#3-prótese-biônica-de-mão-tecnologia-assistiva-e-tinyml).
- **Estágio de TI no Instituto de Engenharia Mecânica da UNIFEI (set/2025 a mai/2026).** Suporte a professores e alunos, rede e infraestrutura. Traduzo o problema de quem não é técnico em solução e ensino a pessoa a resolver sozinha. Um exemplo: um professor tinha um HD externo antigo que não abria. Diagnostiquei, tirei o disco da case, liguei direto para ganhar velocidade, vi que a saúde do disco estava crítica e salvei os arquivos em backup antes de ele morrer.
- **Caderninho.** Produto próprio, do problema da minha prima ao app publicado.
- **Idiomas e estudo.** Inglês avançado. Estudo o conteúdo da certificação Claude Certified Architect (Anthropic).

---

## O que ainda falta medir

- **Voz real de consultório.** Nenhum teste usa áudio de paciente, de propósito. A maior parte usa voz sintética; o teste de campo usa fala humana de um corpus público (CORAA-MUPE-ASR, CC BY-SA 4.0) tocada em caixa de som. Falta medir numa sessão de verdade, com consentimento.
- **Eco.** Caiu muito, não zerou, e varia com a carga do computador. As comparações de eco são de uma rodada por versão.
- **Experimento aberto.** Um roteiro só, voz sintética e eco simulado por soma digital. Vale como método, não como número de produção.
- **Custo.** O valor total foi medido uma vez, com voz sintética. A queda de 90% na transcrição vem de tabela de preço, não de fatura.
- **Sessão presencial.** A separação por canal não vale com um microfone só. Sobre esse caso eu ainda não afirmo nada.
- **Celular.** Tem testes, não tem publicação.
- **Tempo economizado pela psicóloga.** Não medi. Enquanto não medir, não afirmo.

---

## Contato

[linkedin.com/in/hermeto](https://www.linkedin.com/in/hermeto/)
