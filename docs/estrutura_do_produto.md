# Vídeo narrado a partir de gravação de tela · estrutura do produto

> Documento de definição para produtização. Nasceu do caso real da demonstração do GenIntegrations (09/10/2026) e serve de base para tratar o prompt e o produto num projeto próprio.
> Nome do produto: **a definir**. Sugestões de trabalho: *Narra*, *DemoCut*, *Roteiro Vivo*.
> **Versão 3 (14/10/2026):** o produto passa a ser uma **aplicação Docker** (seção 11) e a **automação passa a ser completa**: corte automático do começo e do fim parados, calibração automática da voz, sincronismo resolvido pela aplicação (silêncio seguinte, ajuste de velocidade e encurtamento pela IA) e botão único "Gerar vídeo completo". Cortes, marcadores, briefing, revisão do roteiro e abertura/encerramento ficam opcionais; a única aprovação obrigatória é a do corte final. MVP implementado nesta pasta; ver `README.md`. Correções de consistência na R1, no exemplo do `roteiro.json`, no exemplo do `mapa_de_cenas.json` e na meta de custo.
> **Versão 2 (14/10/2026):** a gravação passa a ser feita na própria aplicação (aba do Chrome), com biblioteca de vídeos, briefing opcional para orientar a narração e área de configurações. Itens novos estão nas seções 3 a 6.

---

## 1. O que é

Uma aplicação que **grava uma navegação numa aba do Chrome** (ou recebe uma gravação já feita) e devolve um **vídeo de demonstração pronto**, com:

- narração em português sincronizada com o que aparece na tela;
- legendas;
- música de fundo licenciada, com volume automático;
- abertura, transição e encerramento com a identidade visual do cliente.

**Problema que resolve:** gravar uma demonstração é rápido, mas narrar, legendar e editar leva horas. Além disso, regravar a voz a cada mudança de produto é caro. Com a gravação dentro da aplicação, o usuário só navega: não precisa de outra ferramenta, nem de cuidar de formato, compressão ou pasta.

**Foco inicial:** aplicações web, gravadas no Chrome. Outras fontes (aplicativos de desktop, tela inteira, celular) ficam para depois.

**Público:** times de produto, pré-venda, customer success e marketing que precisam de demos, tutoriais e vídeos de onboarding com frequência.

---

## 2. Princípios do produto

| Princípio | O que significa na prática |
|---|---|
| **O vídeo manda no tempo** | O roteiro se encaixa nas cenas, e não o contrário. Cada fala tem uma janela de tempo e um orçamento de caracteres |
| **IA propõe, determinístico executa** | A IA entende o vídeo e escreve o roteiro. A montagem (voz, encaixe, mixagem, edição) é código determinístico e repetível. É o mesmo princípio do GenIntegrations |
| **Humano aprova nos pontos certos** | Só o corte final é obrigatório. Revisar o roteiro e ouvir a voz são opcionais. Sincronismo e cortes são problema da aplicação, não do usuário |
| **Regerar é barato** | Cache por fala: mudar uma frase refaz só ela (e as vizinhas), não o vídeo inteiro |
| **Duas versões do texto** | Texto **falado** (escrito para a voz: "I A", "dezoito") e texto **exibido** (grafia correta: "IA", "18") |
| **Tudo rastreável** | Relatório de encaixe por fala, comprovante de licença da música e configuração versionada |

---

## 3. Fluxo da aplicação (o que o usuário faz)

```
GRAVAR ──► BIBLIOTECA ──► BRIEFING (opcional) ──► ROTEIRO (aprova) ──► VOZ (aprova) ──► VÍDEO FINAL (aprova) ──► EXPORTAR
   ▲            │
   └─ importar vídeo existente (.mov, .mp4, .webm)
```

| Tela | O que o usuário faz | O que a aplicação faz |
|---|---|---|
| **Gravar** | Escolhe a aba do Chrome, clica em **Iniciar**, navega, usa **Pausar/Retomar** se precisar e clica em **Parar** | Contagem regressiva de 3 s, indicador de gravação e cronômetro. Grava em blocos (não perde nada se o navegador travar). Ao parar, comprime e salva na pasta da biblioteca |
| **Biblioteca** | Vê os vídeos gravados ou importados, assiste, renomeia, apaga, corta início e fim, marca momentos importantes no player e seleciona um para narrar | Lista a pasta com miniatura, nome, data, duração, tamanho e situação (bruto, roteiro pronto, narrado). Importa vídeos externos para a mesma pasta |
| **Briefing** (opcional) | Escreve em texto livre o que deve ser narrado ou destacado. Pode usar campos guiados: público, objetivo, pontos obrigatórios, o que não mencionar, tom, idioma e duração desejada | Junta o briefing com os marcadores e passa para o entendimento do vídeo e o roteiro |
| **Roteiro** | Revisa e edita as falas numa linha do tempo, vendo o orçamento de caracteres de cada uma e o quadro do vídeo correspondente | Gera o mapa de cenas e o roteiro. Avisa a fala que passou do orçamento antes de gastar crédito de voz |
| **Voz** | Escolhe a voz, ouve uma prévia de 3 falas e aprova | Calibra o ritmo da voz e gera todas as falas com encaixe e cache |
| **Vídeo final** | Assiste, pede ajustes pontuais (trocar uma fala, a música, a abertura) e aprova | Monta abertura, transição, legendas, música e encerramento; refaz só o que mudou |
| **Exportar** | Escolhe os formatos | Gera MP4 16:9 e, se pedido, vertical 9:16, versão sem narração e legenda `.srt` separada |
| **Configurações** | Informa chaves, modelos, voz, marca e pasta de trabalho | Guarda as chaves com segurança e testa as conexões (seção 5) |

---

## 4. Módulo de gravação

### Como capturar a aba

| Fase | Mecanismo | Vantagem | Limite |
|---|---|---|---|
| **MVP** | A própria página da aplicação pede ao Chrome a captura de uma aba (API padrão de compartilhamento de tela). O usuário escolhe a aba no seletor do Chrome | Nada para instalar além da aplicação | Não registra cliques nem rolagens; atalhos de teclado só funcionam com a aplicação em foco |
| **v1** | **Extensão do Chrome** que captura a aba e, na mesma aba, registra os eventos de navegação | Gravação com um clique a partir da própria aba; registro de cliques, URLs, campos e rolagens com o instante exato; atalho para marcar momentos durante a navegação | Exige instalar a extensão |

O **registro de eventos** da v1 é o complemento de maior impacto: o mapa de cenas deixa de depender só da IA de visão para saber onde e quando o usuário clicou. Fica mais preciso, mais barato e permite o zoom automático nos cliques (seção 6).

### Formato e compressão

- O navegador grava em WebM (VP9). Ao parar, a aplicação converte com FFmpeg para **MP4 H.264, 30 quadros por segundo constantes**, com qualidade visual alta (CRF ≈ 23) e otimização para conteúdo de tela.
- Converter já resolve, na origem, a taxa de quadros variável que encurtou o vídeo no caso real.
- **Meta de tamanho:** de 5 a 10 MB por minuto em 1080p. Referência real: a gravação original em `.mov` tinha cerca de 42 MB por minuto; o vídeo final gerado ficou com 6,5 MB por minuto.
- O arquivo bruto em WebM é apagado após a conversão bem-sucedida (configurável).

### Boas práticas embutidas na gravação

- **Perfil de janela 1920×1080**: a aplicação sugere redimensionar a aba antes de gravar, para o vídeo não sair com proporções estranhas.
- **Checklist antes de gravar:** esconder a barra de favoritos, ativar "não perturbe", fechar abas com dados sensíveis e usar dados de demonstração.
- **Limite de duração** configurável (padrão de 15 min) e checagem de espaço em disco.
- **Áudio da aba e microfone desligados por padrão.** A narração vem depois, pela voz escolhida.

---

## 5. Configurações

| Grupo | Itens | Observação |
|---|---|---|
| **Claude** | Chave de API · modelo por etapa (entendimento do vídeo, roteiro, controle de qualidade) · botão "Testar conexão" | Padrão sugerido: **Opus 5.5** no entendimento e no roteiro, que são as etapas de qualidade, e **Haiku 5.5** no controle de qualidade. O **Sonnet 5.5** fica como opção econômica: cerca de metade do custo do Opus (seção 12) |
| **ElevenLabs** | Chave de API · voz (lista com vozes pt-BR primeiro) · modelo (Multilingual v2 ou Flash) · calibração de ritmo · "Testar conexão" | A calibração gera 3 frases-padrão e mede os caracteres por segundo da voz; o roteiro usa esse número |
| **Voz offline** | Piper, como alternativa gratuita | Usada se não houver chave da ElevenLabs |
| **Pasta de trabalho** | Onde ficam a biblioteca de gravações e os vídeos gerados | Avisar se a pasta estiver sincronizada na nuvem: vídeos são grandes |
| **Marca** | Imagem de abertura, logotipo, cores e fonte das legendas, duração da abertura | Um conjunto por marca ou cliente |
| **Música** | Pasta ou catálogo, níveis (fundo e sob a voz) | Comprovante de licença guardado junto |
| **Padrões de narração** | Idioma, tom, persona, glossário de pronúncia (ex.: "GenIntegrations") | Valem para todo projeto novo; o briefing pode sobrepor |
| **Exportação** | Resolução, 16:9 e/ou 9:16, legenda na imagem ou selecionável, `.srt` separado | |
| **Privacidade e custos** | Desfoque de áreas marcadas · limite de custo por vídeo · estimativa antes de gerar | A estimativa aparece antes de chamar Claude e ElevenLabs |

**Segurança das chaves:** guardadas num **volume Docker próprio** (`vc-dados`, fora da pasta de trabalho montada) ou no arquivo `.env`, nunca na pasta de trabalho nem no `configuracoes.json`. A tela mostra só o início e o fim da chave. É a lição da chave colada no chat, no caso real.

---

## 6. Complementos sugeridos (além do que foi pedido)

| # | Complemento | Por quê | Fase |
|---|---|---|---|
| C1 | **Pausar e retomar** a gravação | Evita regravar tudo por uma interrupção | MVP |
| C2 | **Gravação em blocos** salvos a cada poucos segundos | Uma falha do navegador não perde a gravação | MVP |
| C3 | **Importar vídeo existente** (.mov, .mp4, .webm) | Mantém o fluxo atual, que já funciona, e atende gravações feitas fora do Chrome | MVP |
| C4 | **Cortar início e fim** na biblioteca | Toda gravação começa e termina com segundos inúteis | MVP |
| C5 | **Marcadores** ("destaque aqui"), no player da biblioteca no MVP e por atalho durante a gravação na v1 | Vira fala obrigatória no roteiro naquele instante; é a forma mais precisa de dizer "isto precisa ser narrado" | MVP / v1 |
| C6 | **Briefing guiado** além do texto livre: público, objetivo, pontos obrigatórios, o que não mencionar, tom, duração | Texto livre sozinho costuma vir incompleto; os campos garantem o mínimo | MVP |
| C7 | **Editor de roteiro** com orçamento por fala e quadro do vídeo ao lado | Ponto de aprovação humana mais importante; evita gastar crédito com fala que não cabe | MVP |
| C8 | **Calibração automática da voz** | Resolve na origem o problema das 20 falas aceleradas do caso real | MVP |
| C9 | **Estimativa de custo antes de gerar** e limite por vídeo | Transparência para uso por times; evita surpresa com Opus e ElevenLabs | MVP |
| C10 | **Registro de eventos de navegação** (extensão) | Mapa de cenas mais preciso e mais barato | v1 |
| C11 | **Zoom automático nos cliques e realce do cursor** | É o "destaque" visual: a tela de 1920 px fica legível no celular e no LinkedIn | v1 |
| C12 | **Acelerar esperas longas** (carregamentos, processamentos) | Encurta o vídeo sem perder o fluxo; o roteiro pode narrar sobre a espera acelerada | v1 |
| C13 | **Desfoque de áreas ou campos sensíveis** | Gravações de sistemas reais mostram nomes, documentos e valores de clientes | v1 |
| C14 | **Versões do projeto** e regeração só do que mudou | O produto muda; a demo precisa acompanhar sem refazer tudo | v1 |
| C15 | **Exportação vertical 9:16** com recorte que segue o cursor | Redes sociais e celular | v1 |
| C16 | **Outros idiomas** de narração e legenda | Mesmo vídeo para clientes de outros países | v2 |
| C17 | **Aviso de privacidade** na primeira geração: quadros do vídeo vão para a API da Anthropic | Transparência e conformidade com a LGPD | MVP |

---

## 7. Pipeline em 9 etapas

| # | Etapa | Faz | Entrada | Saída | Tipo | Aprovação humana |
|---|---|---|---|---|---|---|
| 0 | **Gravação** | Captura a aba, comprime para MP4 H.264 a 30 quadros constantes, salva na biblioteca com metadados e marcadores (e eventos, na v1) | Aba do Chrome ou vídeo importado | `video.mp4` + `gravacao.json` | Determinístico | Não |
| 1 | **Ingestão e perfil** | Mede duração, resolução, quadros por segundo (inclusive taxa variável), presença de áudio | Gravação de tela | `perfil_video.json` | Determinístico | Não |
| 2 | **Entendimento do vídeo** | Detecta trocas de cena, amostra quadros, lê a tela (textos, números, botões, avisos) e descreve o que acontece em cada trecho | Gravação + perfil + marcadores, briefing e eventos | `mapa_de_cenas.json` | IA de visão + determinístico | Não |
| 3 | **Roteiro** | Escreve uma fala por janela de cena, respeitando o orçamento de caracteres da voz escolhida | Mapa de cenas + briefing + marcadores + ritmo calibrado da voz | `roteiro.json` | IA de texto | **Sim: aprova o roteiro** |
| 4 | **Legendas** | Gera a legenda de exibição (no máximo 2 linhas de 42 caracteres) e o texto falado | Roteiro | `legendas.srt` e `narracao.srt` | Determinístico | Não |
| 5 | **Voz** | Sintetiza fala por fala com o contexto das vizinhas, apara o silêncio, encaixa na janela (acelera até 30%) e guarda em cache | `narracao.srt` + voz | `narracao.wav` + `relatorio_encaixe.tsv` | TTS + determinístico | **Sim: ouve e aprova a voz** |
| 6 | **Trilha** | Seleciona música licenciada, checa Content ID, nivela, emenda sem "buracos" e abaixa sob a voz | Música + narração | `trilha_final.wav` + `licenca_musica.txt` | Curadoria + determinístico | Opcional |
| 7 | **Edição final** | Abertura com a imagem da marca, transição, normalização de quadros e proporção, legendas desenhadas, fade final e exportação | Vídeo + trilha + legendas + identidade | `video_final.mp4` + `legendas_final.srt` | Determinístico | **Sim: aprova o corte final** |
| 8 | **Controle de qualidade** | Confere estouros de fala, duração, picos de áudio e quadros-chave (abertura, transição, legenda, fim) | Tudo acima | `relatorio_qa.md` | Determinístico + visão | Junto com a etapa 7 |

### Como cada etapa foi feita no caso real e como produtizar

| Etapa | Como foi feito agora | Como deve ser no produto |
|---|---|---|
| 0. Gravação | Feita fora, no gravador de tela do macOS, em `.mov` de 42 MB/min e taxa de quadros variável | Dentro da aplicação, já comprimida e normalizada (seção 4) |
| 2. Entendimento | Pranchas com 1 quadro a cada 2 s, detecção de troca de cena e quadros em alta resolução nos pontos-chave, lidos por um modelo de visão | Mesma técnica, automatizada: detecção de cena + amostragem adaptativa (mais quadros onde a tela muda) + leitura de tela por visão, gerando o `mapa_de_cenas.json` |
| 3. Roteiro | Escrito à mão pela IA, com janelas definidas olhando as pranchas e um ritmo assumido de 14 car/s | Gerado por prompt a partir do mapa de cenas, com o ritmo **calibrado da voz escolhida** |
| 5. Voz | Script com Piper ou ElevenLabs, fala por fala | Igual, com calibração automática do ritmo (ver regra R1) |
| 6. Trilha | Busca no Pixabay filtrando por metadado de Content ID e duração | Catálogo curado, com filtro automático de licença e de Content ID, ou geração por Eleven Music |
| 7. Edição | Script FFmpeg com abertura, transição e legendas desenhadas como imagem | Igual, com perfis de saída (1080p, vertical para redes, versão sem legenda) |

---

## 8. Contratos de dados entre etapas

### `gravacao.json` (saída da etapa 0)

```json
{
  "arquivo": "2026-10-14 10h32 - Cadastro de fornecedor.mp4",
  "origem": "aba do Chrome",
  "url_inicial": "https://app.exemplo.com/fornecedores",
  "duracao_s": 184.2,
  "resolucao": "1920x1080",
  "fps": 30,
  "tamanho_mb": 14.8,
  "cortes": { "inicio_s": 2.1, "fim_s": 181.0 },
  "marcadores": [
    { "t_s": 42.5, "nota": "mostrar a validação do CNPJ" }
  ],
  "eventos": [
    { "t_s": 12.3, "tipo": "clique", "alvo": "botão Novo fornecedor", "url": "/fornecedores" },
    { "t_s": 20.1, "tipo": "digitacao", "alvo": "campo CNPJ" },
    { "t_s": 31.7, "tipo": "navegacao", "url": "/fornecedores/novo/revisao" }
  ]
}
```

`eventos` só existe a partir da v1 (extensão). `marcadores` existe desde o MVP, feito no player da biblioteca.

### `briefing.json` (entrada das etapas 2 e 3)

```json
{
  "texto_livre": "Mostrar como o cadastro evita fornecedor duplicado. Não citar o nome do cliente.",
  "publico": "gestores de compras",
  "objetivo": "demonstração comercial",
  "pontos_obrigatorios": ["validação do CNPJ", "aprovação em duas etapas"],
  "nao_mencionar": ["nome do cliente", "valores reais"],
  "tom": "executivo e direto",
  "idioma": "pt-BR",
  "duracao_alvo_s": null
}
```

Todos os campos são opcionais. Sem briefing, o roteiro segue os padrões de narração das configurações.

### `mapa_de_cenas.json` (saída da etapa 2)

```json
{
  "video": { "duracao_s": 184.2, "fps_real": 30, "resolucao": "1920x1080", "taxa_variavel_na_origem": false },
  "cenas": [
    {
      "id": "c03",
      "inicio_s": 20.0,
      "fim_s": 36.0,
      "tela": "Novo lote",
      "acao": "IA processando o reconhecimento de padrões",
      "texto_visivel": ["Processando…", "Layout novo para esta fonte"],
      "numeros_visiveis": {},
      "tipo": "espera",
      "importancia": "media"
    }
  ]
}
```

O campo `tipo` ajuda o roteiro: uma cena de **espera** (processamento, carregamento) é boa para dar contexto; uma de **resultado** pede citar os números que estão na tela.

### `roteiro.json` (saída da etapa 3, entrada das etapas 4 e 5)

```json
{
  "voz": { "motor": "elevenlabs", "nome": "Pri", "ritmo_car_s": 10.5 },
  "abertura": { "fala": "GenIntegrations. Integrações generativas.", "legenda": "GenIntegrations: integrações generativas." },
  "falas": [
    {
      "id": 9,
      "cena": "c07",
      "inicio_s": 63.0,
      "fim_s": 71.8,
      "orcamento_caracteres": 81,
      "texto_legenda": "\"Feira\" não tem equivalência. Na prévia, 18 linhas serão gravadas e 5 não.",
      "texto_falado": "Feira não tem equivalência. Na prévia, dezoito linhas serão gravadas e cinco não.",
      "numeros_citados": { "gravadas": 18, "rejeitadas": 5 }
    }
  ]
}
```

O campo `numeros_citados` permite à etapa 8 conferir se a narração bate com a tela. O orçamento é medido no `texto_falado` (79 caracteres no exemplo, dentro dos 81); a legenda tem limite próprio de 2 linhas de 42 caracteres e, se passar, é dividida em blocos.

### `relatorio_encaixe.tsv` (saída da etapa 5)

`fala · inicio_s · janela_s · duracao_s · velocidade · situacao · texto`. Situação: `ok` ou `ESTOURA`.

### `config.json` (do projeto)

Vídeo base, imagem de abertura, duração da abertura e da transição, motor e voz, níveis da música, legenda gravada na imagem ou selecionável, dicionário de pronúncia. O modelo atual está na raiz da pasta GenIntegrations.

---

## 9. Regras que o prompt de roteiro precisa carregar

Estes são os insumos para tratar o prompt no outro projeto. Cada regra veio de um problema real deste caso.

| # | Regra | Por quê |
|---|---|---|
| R1 | **Orçamento por fala = (janela − 0,15 s) × ritmo da voz × 0,9**, medido no **texto falado** (é o que a voz lê). O ritmo vem da calibração da voz escolhida, não de um valor fixo | O roteiro foi escrito para 14 car/s, mas a voz Pri fala 10,5 car/s: 20 das 36 falas precisaram de aceleração |
| R2 | Falar **do que está na tela naquele momento**, sem antecipar a próxima cena | A legenda descompassada da imagem confunde mais do que ajuda |
| R3 | Números citados **iguais aos da tela** (ex.: 18 gravadas, 5 rejeitadas) | Credibilidade da demo; e a etapa 8 consegue conferir |
| R4 | **Duas versões** do texto: falada (siglas soletradas, números por extenso) e exibida (grafia normal) | A voz lê "IA" como a palavra "ia" |
| R5 | Uma ideia por fala, frases curtas, sem orações encaixadas | Facilita o encaixe e a leitura da legenda |
| R6 | Cenas de **espera** viram contexto (o porquê); cenas de **resultado** viram fato (o quê) | Aproveita o tempo morto do processamento |
| R7 | A abertura apresenta o produto; a primeira fala da demonstração **não repete** o nome | Evita redundância quando há imagem de abertura |
| R8 | Fechar com a proposta de valor em uma frase | O fim do vídeo é o que fica |
| R9 | Saída em **JSON validável** no formato `roteiro.json` | O resto do pipeline é código |
| R10 | Idioma, tom, persona e público vêm do briefing (ex.: "pt-BR, executivo, para gestores de TI") | O mesmo vídeo pode gerar versões para públicos diferentes |
| R11 | Todo **ponto obrigatório** do briefing e todo **marcador** precisa aparecer no roteiro, na janela do instante marcado ou na mais próxima | É assim que o usuário diz "isto precisa ser narrado ou destacado" |
| R12 | Nada da lista **"não mencionar"** pode aparecer, nem por paráfrase; na dúvida, omitir | Protege cliente e dados reais em demonstrações comerciais |
| R13 | Com **eventos de navegação** disponíveis, nomear a ação pelo rótulo real do elemento ("clicamos em Aprovar") quando ajudar a entender | Precisão e aderência ao que o espectador vê |
| R14 | Sem briefing, inferir o objetivo pelo próprio vídeo e declarar a suposição num campo `premissas` do JSON | Dá ao revisor a chance de corrigir a direção antes de gerar a voz |

### Esqueleto do prompt (rascunho inicial)

```
Papel: roteirista de vídeos de demonstração de software B2B.

Entradas:
  - mapa_de_cenas.json (o que acontece na tela, com tempos)
  - briefing.json (opcional): texto livre, público, objetivo, pontos obrigatórios,
    o que não mencionar, tom, idioma, duração-alvo
  - marcadores e eventos de navegação, do gravacao.json
  - voz: nome e ritmo calibrado em caracteres por segundo

Tarefa:
  Para cada janela de cena, escreva no máximo uma fala que caiba no orçamento
  (janela − 0,15 s) × ritmo × 0,9, seguindo as regras R2 a R8 e R11 a R14.

Saída:
  Somente o JSON no formato roteiro.json, com texto_legenda, texto_falado,
  orcamento_caracteres e numeros_citados em cada fala.

Autoverificação antes de responder:
  - nenhuma fala acima do orçamento;
  - nenhum número citado que não esteja no mapa de cenas;
  - nenhuma fala antecipando a cena seguinte;
  - todos os pontos obrigatórios e marcadores cobertos;
  - nada da lista "não mencionar".
```

---

## 10. Lições do caso real (viram requisitos)

| Problema encontrado | Causa | Solução aplicada | Requisito do produto |
|---|---|---|---|
| Vídeo final 0,85 s mais curto, fade final cortado | Gravação de tela com taxa de quadros variável: o último quadro chega antes do fim nominal | Segurar o último quadro até o fim do arquivo | Normalizar a taxa de quadros na ingestão |
| 20 de 36 falas aceleradas, 8 estouros na 1ª geração | Ritmo da voz (10,5 car/s) abaixo do assumido (14) | Ajuste fino de velocidade + 3 falas encurtadas | Calibrar a voz antes de escrever o roteiro (R1, seção 9) |
| Falas curtas com "ritmo" de 7 car/s | A voz sintética devolve silêncio no começo e no fim | Aparar silêncio de cada fala | Aparar sempre, para qualquer motor de voz |
| "IA" lida como a palavra "ia" | Siglas em texto corrido | Texto falado separado do exibido | Duas camadas de texto (R4) + dicionário de pronúncia |
| Velocidade pedida à API não exata | Vozes neurais não respondem linearmente ao parâmetro de velocidade | Ajuste fino local, sem alterar o tom | Encaixe em duas passadas |
| Música "sumindo" a cada 2 min | Faixa de 1:57 com fade e silêncio no fim, repetida | Cortar o fade antes de repetir, emenda de 3 s | Preparar a faixa antes do loop |
| Quase todas as faixas candidatas no Content ID | Padrão do mercado de música livre | Filtro por metadado da página | Filtro automático de licença e de Content ID |
| Áudio `.m4a` entrando mudo | Formato que não pode ser lido em fluxo | Ler do arquivo | Testar todos os formatos aceitos |
| FFmpeg do macOS sem biblioteca de legendas | Instalação enxuta do Homebrew | Legendas desenhadas como imagem | Não depender de bibliotecas opcionais |
| Lista de vozes sem destaque para pt-BR | Ordenação por nome | Marcar e ordenar por idioma | Filtro de voz por idioma e sotaque |
| Chave de API colada no chat | Fluxo de configuração ausente no início | Chave guardada só no usuário, fora da pasta sincronizada | Cofre de segredos; nunca no projeto |
| Geração de voz e downloads bloqueados no ambiente de nuvem | Rede restrita | Execução no Mac do usuário | Rodar onde estão a rede, os créditos e os arquivos |

---

## 11. Empacotamento: do protótipo ao produto

| Fase | Forma | O que entra | Para quem |
|---|---|---|---|
| **Agora (protótipo)** | Pasta + atalhos de dois cliques + script local | Etapas 1, 4 a 8 automáticas; etapas 2 e 3 feitas pela IA na conversa | Uso interno, um vídeo por vez |
| **MVP** | **Aplicação Docker** (`docker compose`), com interface no navegador em `localhost:8898`, ao lado do GenIntegrations na 8897 | Gravação de aba sem extensão, biblioteca, briefing, configurações, etapas 0 a 8 automáticas, editor de roteiro com orçamento por fala, prévia de voz, complementos C1 a C9 e C17 | Times internos (produto, pré-venda, CS) |
| **v1** | Aplicação local + **extensão do Chrome** | Registro de eventos, marcadores por atalho, zoom nos cliques, aceleração de esperas, desfoque, versões, vertical 9:16 (C10 a C15); várias marcas | Vários times |
| **v1.5** | Serviço com projetos compartilhados | Biblioteca e marcas compartilhadas por time, vozes calibradas, catálogo de músicas | Vários times ou clientes |
| **v2** | Atualização contínua | Regravar só os trechos que mudaram quando o produto muda; tradução da narração | Bases de tutoriais grandes |

### Docker no MVP: como fica cada ponto

- **Gravação:** a página da aplicação roda no Chrome do usuário (`localhost` é contexto seguro, exigido para capturar abas). Os blocos de vídeo são enviados ao contêiner, que comprime com FFmpeg.
- **Arquivos:** a pasta de trabalho é montada do computador (`./trabalho` ou `PASTA_TRABALHO`), então biblioteca e exportados aparecem no Finder.
- **Chaves:** sem Keychain dentro do contêiner; ficam num volume Docker próprio ou no `.env` (seção 5).
- **FFmpeg e voz offline:** instalados na imagem (com libass para as legendas e fontes embutidas), o que elimina a diferença de instalação entre máquinas. Não há aceleração de hardware do Mac: a montagem leva um pouco mais.
- **Instalação:** Docker Desktop + `Iniciar.command` (duplo clique). A mesma imagem serve de base para o serviço compartilhado da v1.5.

---

## 12. Estimativa de custo por vídeo

Base: o caso real (vídeo de 4:39, 36 falas, cerca de 2.700 caracteres narrados). Preços de tabela em dólar, consultados em 09/10/2026. O custo cresce de forma aproximadamente linear com a duração do vídeo.

### Claude (API)

Preço por milhão de tokens: Opus 5.5 US$ 4 entrada / US$ 20 saída · Sonnet 5.5 US$ 2 / US$ 10 · Haiku 5.5 US$ 0,10 / US$ 0,50 (pedidos de até 100 mil tokens). Imagens custam 1 token a cada bloco de 28×28 pixels.

| Etapa | Tokens de entrada | Tokens de saída | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|---|---|
| 2. Entendimento do vídeo (12 pranchas de quadros + 4 quadros em alta resolução) | ≈ 37 mil | ≈ 6 mil | US$ 0,27 | US$ 0,13 | US$ 0,01 |
| 3. Roteiro (1ª versão + 2 revisões) | ≈ 46 mil | ≈ 15 mil | US$ 0,48 | US$ 0,24 | US$ 0,01 |
| 8. Controle de qualidade (6 quadros-chave) | ≈ 19 mil | ≈ 2 mil | US$ 0,12 | US$ 0,06 | < US$ 0,01 |
| **Total por vídeo** | **≈ 102 mil** | **≈ 23 mil** | **US$ 0,87** | **US$ 0,43** | **US$ 0,02** |

**Com o padrão das configurações** (Opus 5.5 no entendimento e no roteiro, Haiku 5.5 no controle de qualidade): **≈ US$ 0,76 por vídeo**. Com o registro de eventos da v1, o entendimento precisa de menos quadros, e o custo dessa etapa tende a cair.

**Alternativa econômica:** Sonnet 5.5 nas etapas 2 e 3, que pedem qualidade de leitura e de texto, e Haiku 5.5 no controle de qualidade: **≈ US$ 0,38 por vídeo**. O Haiku nas etapas 2 e 3 sai quase de graça, mas precisa ser validado: ler números pequenos na tela e escrever dentro do orçamento de caracteres são justamente as partes difíceis.

**Decisão de arquitetura que pesa no custo:** analisar o vídeo em **pranchas** (12 quadros por imagem) custa ≈ 34 mil tokens de imagem. Mandar os mesmos 140 quadros soltos custaria ≈ 161 mil, quase 5 vezes mais, sem ganho de entendimento.

### ElevenLabs

Preço de API: Multilingual v2 **US$ 0,08 por mil caracteres** · Flash/Turbo **US$ 0,04 por mil caracteres** · Eleven Music **US$ 0,15 por minuto**.

| Item | Caracteres | Multilingual v2 | Flash/Turbo |
|---|---|---|---|
| 1ª geração (36 falas) | 2.696 | US$ 0,22 | US$ 0,11 |
| Regeração das falas que precisaram de velocidade (≈ 20 falas) | ≈ 1.600 | US$ 0,13 | US$ 0,06 |
| 2 rodadas de revisão de texto (≈ 8 falas cada, com as vizinhas) | ≈ 1.350 | US$ 0,11 | US$ 0,05 |
| **Típico por vídeo** | **≈ 5.650** | **US$ 0,45** | **US$ 0,23** |
| Música gerada no Eleven Music (opcional, 5 min) | | US$ 0,75 | |

Com a calibração da voz antes do roteiro (regra R1), a regeração por velocidade praticamente desaparece, e o típico cai para **≈ 4.050 caracteres (US$ 0,32)**.

**Planos mensais** (caracteres de Multilingual v2 incluídos): Starter US$ 6 → 75 mil (≈ 13 vídeos) · Creator US$ 22 → 275 mil (≈ 48 vídeos) · Pro US$ 99 → 1,24 milhão (≈ 218 vídeos). Em todos, o custo efetivo fica em torno de US$ 0,45 por vídeo. A diferença entre os planos é o volume, não o preço unitário.

### Total por vídeo de ≈ 5 minutos

| Configuração | Claude | Voz | Música | **Total** |
|---|---|---|---|---|
| Econômica (Haiku + Flash + Pixabay) | US$ 0,02 | US$ 0,23 | grátis | **≈ US$ 0,25** |
| **Padrão das configurações** (Opus + Haiku no QA + Multilingual v2 + Pixabay) | US$ 0,76 | US$ 0,45 | grátis | **≈ US$ 1,21** |
| **Econômica com qualidade** (Sonnet + Haiku no QA + Multilingual v2 + Pixabay) | US$ 0,38 | US$ 0,45 | grátis | **≈ US$ 0,83** |
| Premium (Opus + Multilingual v2 + Eleven Music) | US$ 0,87 | US$ 0,45 | US$ 0,75 | **≈ US$ 2,07** |
| Voz offline (Sonnet + Piper + Pixabay) | US$ 0,38 | grátis | grátis | **≈ US$ 0,38** |

No padrão das configurações, isso dá **≈ US$ 0,24 por minuto de vídeo** (≈ R$ 6,65 por vídeo de 5 minutos); na econômica com qualidade, **≈ US$ 0,17 por minuto** (≈ R$ 4,57). Câmbio usado: R$ 5,50 por dólar; ajuste para o câmbio do dia.

### O que não está nessa conta

- **Gravação e compressão:** rodam no computador do usuário, sem custo variável. Armazenamento: ≈ 5 a 10 MB por minuto gravado.
- **Montagem do vídeo:** roda no computador do usuário (≈ 5 min num Mac), sem custo variável. Num servidor, é processamento comum de FFmpeg, de poucos centavos por vídeo.
- **Desenvolvimento e iteração com a IA:** a construção deste protótipo numa conversa longa consumiu muito mais tokens do que uma geração de vídeo. É custo de projeto, não de operação.
- **Impostos e IOF** sobre a cobrança em dólar.
- Os preços são de tabela e mudam com frequência: revisar em platform.claude.com/docs/en/about-claude/pricing e elevenlabs.io/pricing/api antes de precificar o produto.

## 13. Métricas de qualidade

| Métrica | Meta inicial | Caso real |
|---|---|---|
| Falas no ritmo natural da voz (sem aceleração) | ≥ 80% | 16 de 36 (44%) na 1ª geração |
| Falas que estouram a cena | 0 | 8 → 1 após os ajustes |
| Números citados que batem com a tela | 100% | Conferido manualmente |
| Tempo do vídeo bruto ao vídeo final | < 15 min | Dominado pela montagem final (≈ 5 min) |
| Custo por minuto de vídeo (econômica com qualidade: Sonnet + Haiku + Multilingual v2) | ≤ US$ 0,20 | ≈ US$ 0,17 (estimado). O padrão com Opus fica em ≈ US$ 0,24 e passa da meta |
| Revisões humanas necessárias | ≤ 2 rodadas | 3 rodadas (voz, roteiro, música) |

---

## 14. Riscos e limites

- **Leitura de tela por visão** pode errar números pequenos: por isso os números citados são conferidos na etapa 8.
- **Vozes sintéticas** variam de ritmo entre gerações: o encaixe em duas passadas absorve isso, mas falas no limite podem estourar.
- **Licença de música** muda com o tempo (faixas entram no Content ID depois): guardar o comprovante na data do download.
- **Dados sensíveis na gravação** (nomes, documentos, valores de clientes): o produto precisa de um aviso ou de desfoque antes de enviar quadros para a IA.
- **Direitos de voz**: usar só vozes com licença comercial; vozes clonadas exigem autorização da pessoa.
- **Captura de aba:** o Chrome pede ao usuário que escolha a aba a cada gravação (é uma proteção do navegador, não dá para pular). Conteúdo protegido por DRM aparece preto.
- **Gravações longas** consomem memória e disco: daí a gravação em blocos e o limite de duração.
- **Pasta sincronizada na nuvem** (iCloud, OneDrive) pode travar com vídeos grandes: a aplicação deve avisar.

---

## 15. Próximos passos para o projeto do produto

1. Definir o nome e o escopo do MVP (público interno ou externo) e validar a lista de complementos da seção 6.
2. Prototipar a gravação de aba com compressão (seção 4): é a peça nova com maior risco técnico.
3. Escrever e testar o prompt da etapa 3 com o `mapa_de_cenas.json` deste caso como teste de referência: o resultado deve caber nos orçamentos sem ajuste manual.
4. Automatizar a etapa 2 (entendimento do vídeo) e comparar com o mapa feito à mão neste caso.
5. Criar a calibração de voz (gerar 3 frases-padrão e medir car/s) como primeiro passo de qualquer projeto.
6. Desenhar as telas do MVP (seção 3) e a área de configurações (seção 5).

### Ativos deste caso que servem de referência

| Arquivo (pasta GenIntegrations) | Uso no projeto do produto |
|---|---|
| `narracao/narracao_pt-BR.srt` e `legendas_pt-BR.srt` | Exemplo de saída das etapas 3 e 4 |
| `saida/arquivos de apoio/relatorio_encaixe.tsv` | Dados reais de ritmo e encaixe da voz Pri |
| `scripts/gerar_video_demo.py` | Implementação de referência das etapas 4 a 8 |
| `config.json` | Modelo de configuração de projeto |
| `musica/LICENCA_MUSICA.txt` | Modelo de comprovante de licença |
