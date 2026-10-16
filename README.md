<img src="docs/logo.png" width="88" alt="Logotipo do Video Composer">

# Video Composer

Transforma uma navegação gravada numa aba do Chrome em um **vídeo de demonstração pronto**. O vídeo sai com:

- narração em português sincronizada com a tela;
- legendas;
- música de fundo livre de direitos, com volume automático;
- capa, abertura e encerramento com a marca.

Feito para PMs que mantêm manuais de produtos digitais atualizados: onboarding de colaboradores e clientes, capacitação de CS, time comercial, marketing e suporte.

Roda em **Docker** no Mac ou no Windows, com interface no navegador em **http://localhost:8898**.

---

## Sumário

1. [Começo rápido](#1-começo-rápido)
2. [Requisitos](#2-requisitos)
3. [Instalar, abrir, parar e desinstalar](#3-instalar-abrir-parar-e-desinstalar)
4. [Primeira configuração](#4-primeira-configuração)
5. [Como usar](#5-como-usar)
6. [Editor](#6-editor)
7. [Capa](#7-capa)
8. [Música de fundo](#8-música-de-fundo)
9. [Exportação](#9-exportação)
10. [Onde ficam os arquivos](#10-onde-ficam-os-arquivos)
11. [Segurança e privacidade](#11-segurança-e-privacidade)
12. [Custos](#12-custos)
13. [Como funciona por dentro](#13-como-funciona-por-dentro)
14. [Estrutura do código](#14-estrutura-do-código)
15. [Problemas comuns](#15-problemas-comuns)
16. [Limitações e próximos passos](#16-limitações-e-próximos-passos)

---

## 1. Começo rápido

| Passo | macOS | Windows |
|---|---|---|
| 1. Instalar (uma vez) | duplo clique em `Instalar.command` | duplo clique em `Instalar.bat` |
| 2. Informar as chaves | o instalador pede; ou depois em Configurações | igual |
| 3. Criar | **+ Novo vídeo** → gravar a aba ou importar um vídeo | igual |
| 4. Configurar | assistente de 4 passos: sobre o vídeo, abertura e encerramento, voz e música, revisar e gerar (tudo opcional) | igual |
| 5. Revisar e exportar | Editor → **Aprovar e exportar** | igual |

O vídeo fica pronto em `<pasta de trabalho>/exportados/<nome do vídeo>/`.

---

## 2. Requisitos

| Item | Para quê | Observação |
|---|---|---|
| **Docker Desktop** (Compose 2.24 ou mais novo) | roda a aplicação | o instalador verifica e oferece instalar |
| **Google Chrome** | gravar abas | outros navegadores não capturam abas da mesma forma |
| **Chave da Anthropic** | entender a tela e escrever o roteiro | obrigatória para gerar vídeos |
| **Chave da ElevenLabs** | voz de alta qualidade e música gerada (Eleven Music) | opcional para a voz: sem ela, use o **Kokoro** (voz feminina e masculinas) ou o **Piper** (só masculinas), ambos offline e gratuitos |
| Internet | APIs, catálogo de músicas, vozes do Piper | a gravação e a montagem rodam no seu computador |

Espaço em disco: cerca de 2 GB para a imagem Docker e de 5 a 10 MB por minuto de vídeo gravado.

---

## 3. Instalar, abrir, parar e desinstalar

| Ação | macOS | Windows |
|---|---|---|
| **Instalar** (uma vez) | `Instalar.command` | `Instalar.bat` |
| **Abrir** | `Iniciar.command` ou o atalho "Video Composer" na Mesa | `Iniciar.bat` ou o atalho na Área de Trabalho |
| **Parar** | `Parar.command` | `Parar.bat` |
| **Desinstalar** | `Desinstalar.command` | `Desinstalar.bat` |

### O que o instalador faz

1. Verifica o Docker Desktop e oferece instalar: Homebrew no Mac, winget no Windows. Abre o Docker se estiver fechado e confere a versão do Compose.
2. Verifica o Chrome.
3. Pergunta onde guardar os vídeos:
   - dentro da pasta da aplicação (`trabalho/`);
   - ou em `~/VideoComposer`, o recomendado quando Documentos sincroniza com iCloud ou OneDrive.
4. Constrói a imagem Docker e inicia a aplicação. A primeira vez leva alguns minutos.
5. Pede as chaves da Anthropic e da ElevenLabs (opcional) e guarda no cofre da aplicação, num volume do Docker. Elas nunca vão para um arquivo da pasta.
6. Cria o atalho e abre o Chrome.

### O que o desinstalador faz

- Remove o contêiner e a imagem.
- Pergunta se apaga também as chaves e as vozes offline (volume do Docker).
- Pergunta se apaga a pasta de vídeos. Só apaga se você digitar **APAGAR**.
- Remove o atalho. A pasta da aplicação fica para você apagar.

### Primeira vez no macOS

- Se o duplo clique não abrir, rode no Terminal, dentro da pasta: `chmod +x *.command`
- Se o macOS bloquear por segurança: botão direito no arquivo → **Abrir**.

### Windows: pacote instalável

O pacote `VideoComposer-Windows-<versão>.zip` traz só o necessário para o Windows, o `LEIA-ME primeiro.txt` e o **Tutorial de uso.pdf** (passo a passo com telas).

1. Botão direito no .zip → **Extrair tudo** (não rode de dentro do .zip).
2. Dois cliques em `Instalar.bat`. Se o Windows avisar: **Mais informações** → **Executar assim mesmo**.
3. O instalador copia a aplicação para `%LOCALAPPDATA%\Programs\VideoComposer`, instala o Docker Desktop se precisar (pode pedir para reiniciar, porque usa o WSL 2), pergunta a pasta dos vídeos (padrão: `Vídeos\VideoComposer`), constrói e inicia, pede as chaves, cria a pasta **Video Composer** no Menu Iniciar (Abrir, Parar, Desinstalar e Tutorial) e registra em **Configurações > Aplicativos > Aplicativos instalados**.
4. A pasta extraída pode ser apagada depois.

**Atualizar:** extraia o .zip novo e rode `Instalar.bat` de novo. Vídeos, chaves e configurações são mantidos.

**Desinstalar:** Configurações do Windows > Aplicativos > Video Composer > Desinstalar (ou Menu Iniciar > Desinstalar Video Composer). Remove contêiner, imagem, atalhos, registro e a pasta da aplicação. Chaves e vídeos só são apagados se você confirmar (para os vídeos, digitando **APAGAR**). O Docker Desktop continua instalado.

### Pelo Terminal (qualquer sistema)

```bash
docker compose up -d --build   # instala ou atualiza e inicia
docker compose logs -f         # acompanha o que está acontecendo
docker compose down            # para
```

---

## 4. Primeira configuração

Em **Configurações** (no rodapé do menu). Cada seção abre e fecha com um clique e mostra um resumo quando está fechada; a aplicação lembra quais você deixou abertas.

| Seção | O que fazer |
|---|---|
| Aparência | Escolha uma das 10 paletas de cor: 5 escuras (Marinho, Índigo, Grafite, Floresta, Ameixa) e 5 claras (Nuvem, Areia, Menta, Lavanda, Alto contraste). Muda na hora e fica salva |
| Claude | Cole a chave e clique em **Testar**. O padrão é Opus no entendimento e no roteiro e Haiku no controle de qualidade. Sonnet custa cerca de metade do Opus |
| Voz | Escolha o **motor** na lista. Os campos mudam conforme o motor. **ElevenLabs:** chave, **Carregar lista** (vozes pt-BR primeiro), voz e modelo. **Kokoro** (offline, uso comercial permitido): Dora (feminina), Alex e Santa (masculinas); o modelo de cerca de 350 MB é baixado no primeiro uso. **Piper** (offline): só vozes masculinas. **Ouvir amostra** toca uma frase. Salva sozinho |
| Pasta de trabalho | Mostra a pasta atual e deixa trocar: informe o caminho completo, salve, depois **Parar** e **Iniciar**. Os vídeos da pasta antiga não são movidos |
| Marca | Imagem padrão de abertura e de encerramento, logotipo, cores, fonte, tamanho da legenda e durações padrão |
| Música | Volumes e emendas; chave da ElevenLabs para gerar música, se ainda não informada |
| Padrões de narração | Idioma, tom, persona, público e **glossário de pronúncia** (ex.: "GenIntegrations" falado como "Gen Integreichons") |
| Exportação | Legenda gravada na imagem, selecionável ou nenhuma; formatos marcados por padrão |
| Privacidade, custos e gravação | Aviso de privacidade, limite de custo por vídeo, duração máxima da gravação e qualidade da compressão |

O ritmo da voz (caracteres por segundo) é **calibrado automaticamente** antes do primeiro roteiro com cada voz.

---

## 5. Como usar

```
+ NOVO VÍDEO ─► CONFIGURAR (assistente, tudo opcional) ─► GERAR ─► EDITOR (ajusta e aprova) ─► EXPORTAR
 gravar ou importar   sobre · abertura e encerramento · voz e música · revisar
```

O menu tem só o essencial: **+ Novo vídeo**, **Meus vídeos** (tela inicial) e **Configurações**. Dentro de um vídeo, o cabeçalho mostra os 3 passos (Configurar, Revisar no editor, Exportar) e o botão **⋯** com as telas avançadas: Roteiro completo, Voz e encaixe das falas, Cortes e marcadores, Nova versão e Apagar.

### 5.1 Meus vídeos

- Busca pelo nome e filtros: Todos, A configurar, Para revisar, Aprovados (com a contagem de cada um).
- Cada vídeo tem: **Editar** ou **Continuar**, **Exportar** (quando pronto), **Nova versão** e **Apagar**.
- **Nova versão:** quando o produto muda, grave de novo. A versão nova herda finalidade, briefing, abertura, encerramento (textos, imagens e falas) e capa, e recebe o nome "<vídeo> v2", "v3"...

### 5.2 Novo vídeo

1. **+ Novo vídeo** → dê um nome (opcional) → escolha **Gravar uma aba do Chrome** ou **Importar um vídeo** (.mov, .mp4, .webm, .m4v, .mkv; dá para arrastar o arquivo).
2. Ao gravar, o Chrome pede para escolher a aba. Depois há uma contagem de 3 segundos. Use **Pausar** e **Retomar** se precisar e termine em **Parar e salvar**.
3. O assistente de configuração abre na hora. A compressão do vídeo continua em segundo plano enquanto você configura.

Dicas: janela em 16:9 (de preferência 1920×1080), barra de favoritos escondida, "Não perturbe" ligado e dados de demonstração. Comece e termine parado: a aplicação corta sozinha o começo e o fim sem ação. A gravação é salva em blocos a cada 3 segundos: se o navegador travar, nada se perde.

### 5.3 Configurar (assistente)

| Passo | O que tem |
|---|---|
| 1. Sobre o vídeo | Nome; **finalidade** com um clique (Onboarding de colaboradores, Onboarding de clientes, Capacitação de CS, Time comercial, Marketing, Suporte e tutorial), que ajusta público, objetivo e tom; o que mostrar; o que precisa falar; o que **não pode** falar (ex.: nome do cliente). Mais opções: público, objetivo, tom, idioma e duração |
| 2. Abertura e encerramento | Para cada cartão: liga e desliga, título, subtítulo, **imagem própria** (enviar, trocar, remover), escrever ou não o texto sobre a imagem, **fala** (Eu escrevo, IA escreve ou Sem fala) e duração mínima. A prévia atualiza a cada mudança e tudo salva sozinho |
| 3. Voz e música | Motor e voz (com amostra) e música: **Gerar com IA**, **Minhas faixas** ou **Sem música** |
| 4. Revisar e gerar | Resumo de tudo, estimativa de custo e **Gerar vídeo completo** (ou só o roteiro, para revisar antes) |

**Fala dos cartões:** "Eu escrevo" é lida exatamente como está escrita e vira legenda. "IA escreve" (só na abertura) é escrita junto com o roteiro; depois de gerada, aparece no editor do cartão com o botão **Editar este texto**. O cartão estica sozinho para caber a fala. A imagem do cartão vem, nesta ordem: a enviada para o vídeo, a padrão da marca, ou um fundo com a cor da marca.

### 5.4 O que a geração faz sozinha

1. calibra a voz, se for preciso;
2. corta o começo parado e encurta a tela parada do fim;
3. entende a tela e identifica os momentos importantes;
4. escreve o roteiro no tamanho certo para cada cena;
5. gera a voz e **resolve o sincronismo**, nesta ordem:
   - ritmo natural, usando o silêncio até a próxima fala;
   - se não couber, um ajuste leve de velocidade;
   - se ainda não couber, o Claude encurta o texto e a fala é gerada de novo;
6. monta o vídeo e roda o controle de qualidade.

Durante a geração, o editor mostra o progresso. Pode sair da tela: ele abre sozinho quando terminar.

### 5.5 Telas avançadas (menu ⋯)

| Tela | Quando usar |
|---|---|
| Roteiro completo | Editar todas as falas de uma vez, ver os avisos e regerar com instruções. **Salvar e gerar o vídeo** refaz só o que mudou |
| Voz e encaixe das falas | Ouvir cada fala, ver velocidade e encaixe, prévia de 3 falas e calibração |
| Cortes e marcadores | Corte manual de início e fim (com **Voltar ao automático**) e marcadores para garantir que um momento seja narrado |

---

## 6. Editor

Inspirado em editores de vídeo multitrilha:

- **Player** do vídeo final, com reproduzir, fala anterior, próxima fala e zoom da linha do tempo.
- **Trilhas**, todas no tempo do vídeo final, com a linha de posição acompanhando o player:

  | Trilha | Mostra |
  |---|---|
  | Vídeo | abertura, cenas com miniaturas e nome da tela, encerramento |
  | Narração | uma caixa por fala, incluindo as falas da abertura e do encerramento |
  | Legenda | o texto de cada legenda no tempo em que aparece |
  | Música | a faixa escolhida e o autor |

- **Ícones das falas:** ✓ ritmo natural · ⚡ acelerada · ✂ encurtada pela IA · ⚠ não coube.

- **Clique para editar:** uma fala abre a ferramenta Fala; o bloco da abertura ou do encerramento (na trilha Vídeo ou na Narração) abre o editor daquele cartão; a trilha Música abre a ferramenta Música.

- **Barra de ferramentas:**

  | Ferramenta | Para quê |
  |---|---|
  | Fala | Edite legenda e texto falado e clique em **Aplicar no vídeo**. A aplicação refaz só essa fala, resolve o encaixe e monta de novo |
  | Abertura | O mesmo editor do assistente: texto, imagem, fala e duração. Salva sozinho; **Aplicar no vídeo** gera a fala nova, se houver, e monta de novo |
  | Encerramento | Igual à abertura, mais a opção de mostrar o crédito da música |
  | Capa | Ver seção 7 |
  | Música | Ver seção 8 |
  | Qualidade | Relatório do controle de qualidade e quadros-chave |
  | Exportar | Vai para a exportação |

- **Montar de novo** aplica mudanças de música, volume e capa.
- **Aprovar e exportar** registra a aprovação do corte final e abre a exportação.

---

## 7. Capa

A capa é a imagem que aparece antes do play (YouTube, LinkedIn, plataforma de treinamento). Ela pode vir de três origens:

| Origem | Como funciona |
|---|---|
| **Automática** (padrão) | Escolhe o quadro mais representativo, de preferência uma tela de resultado, e escreve título e subtítulo sobre uma faixa escura |
| **Quadro do vídeo** | Posicione o player e clique em **Usar o quadro atual do player** |
| **Imagem enviada** | PNG, JPG ou WEBP, ajustada para 16:9 sem distorcer |

A capa é **embutida no MP4** (vira a miniatura no Finder, no Explorer e nos players) e **exportada em JPG** 1920×1080.

---

## 8. Música de fundo

No assistente (passo Voz e música) ou no Editor, ferramenta **Música**. Três fontes, da mais segura para a menos segura:

| Fonte | Segurança para uso comercial | Como funciona |
|---|---|---|
| **Música gerada (Eleven Music)** · recomendado | ✅ alta: composta para você e liberada pelos termos de música da ElevenLabs | Escolha um estilo (Corporativo leve, Tecnologia moderna, Inspirador, Calmo, Lo-fi, Acústico) e clique em **Gerar e usar**. A faixa sai instrumental, no tamanho exato do vídeo, com comprovante de origem. Custo estimado de US$ 0,15 por minuto |
| 📁 **Faixa licenciada pela empresa** | ✅ alta, se a licença existir | Envie o áudio e o comprovante (.txt com o mesmo nome) e clique em **Confirmar licença**, informando a origem (ex.: Epidemic Sound, Artlist) |
| 🌐 **Catálogo aberto (Openverse)** · avançado | ⚠ baixa: o catálogo não verifica as licenças | Fica recolhido, só busca CC0 e domínio público por padrão e marca cada faixa como "licença não confirmada" até você conferir na página da obra |

**Plano da ElevenLabs e música:** os termos de música da ElevenLabs separam os planos por porte.

| Plano | Para quem | Observação |
|---|---|---|
| Free a Pro | pessoa física | o Free exige o crédito "Eleven Music" |
| Scale | empresas de até 10 funcionários | |
| Business | empresas de até 50 funcionários | |
| Enterprise | empresas acima de 50 funcionários | |

Em todos os planos, exceto Enterprise Music, ficam de fora cinema, TV, rádio e jogos de estúdio. A aplicação consulta o plano da sua conta, mostra o aviso na tela e grava o plano no comprovante. O controle de qualidade alerta quando a música foi gerada num plano individual.

**O controle de qualidade também alerta** quando a faixa em uso tem licença não confirmada.

> ⚠️ Nenhuma fonte garante imunidade ao **Content ID do YouTube**. Guarde os comprovantes (`.txt`), que a aplicação exporta junto com o vídeo, para contestar uma reivindicação.

## 9. Exportação

Em **Exportar**, escolha os formatos:

| Arquivo | Descrição |
|---|---|
| `… - 16x9 - <data>.mp4` | 1920×1080, com a capa embutida |
| `… - 9x16 - <data>.mp4` | 1080×1920 para redes sociais e celular, com fundo desfocado |
| `… - sem narracao - <data>.mp4` | só imagem e música, sem legenda, para dublar ou reaproveitar |
| `… - legendas - <data>.srt` | legenda separada para YouTube e plataformas |
| `… - capa - <data>.jpg` | capa 1920×1080 |
| `… - creditos.txt` | crédito da música (licença CC BY) para a descrição do vídeo |
| `… - licenca da musica.txt` | comprovante de licença |

Tudo vai para `trabalho/exportados/<nome do vídeo>/`.

---

## 10. Onde ficam os arquivos

```
trabalho/                         ← pasta de trabalho no seu computador (aparece no Finder/Explorer)
├── configuracoes.json            ← configurações (sem chaves)
├── biblioteca/<id do vídeo>/
│   ├── video.mp4                 ← gravação comprimida
│   ├── gravacao.json             ← nome, duração, cortes, marcadores
│   ├── briefing.json
│   └── projeto/
│       ├── mapa_de_cenas.json    ← o que a IA entendeu da tela
│       ├── roteiro.json          ← falas, orçamentos e avisos
│       ├── audio/                ← falas geradas e cache
│       ├── narracao.wav  trilha_final.wav
│       ├── legendas_final.srt  capa.jpg
│       ├── video_final.mp4
│       ├── relatorio_encaixe.tsv  relatorio_qa.md
│       └── custos.json           ← gasto real de API deste vídeo
├── marcas/                       ← imagens de abertura, encerramento e logotipo
├── musica/                       ← faixas + comprovantes (.txt) + metadados (.json)
└── exportados/<nome do vídeo>/   ← arquivos finais
```

Para mudar o local depois da instalação, rode o instalador de novo ou edite `PASTA_TRABALHO` no arquivo `.env` (criado a partir de `env.exemplo`) e reinicie.

---

## 11. Segurança e privacidade

- **Chaves de API:** ficam no volume Docker `vc-dados`, fora da pasta de trabalho, ou no arquivo `.env`. A tela mostra só o começo e o fim. Nunca vão para `trabalho/` nem para `configuracoes.json`.
- **Acesso:** a aplicação só aceita conexões deste computador (`127.0.0.1:8898`).
- **O que sai do computador:**
  - quadros do vídeo vão para a API da Anthropic (Claude);
  - o texto do roteiro vai para a ElevenLabs.

  Um aviso aparece antes da primeira geração.
- **Dados sensíveis:** grave com dados de demonstração. Use o campo **"O que não mencionar"** do briefing para nomes de clientes e valores reais.
- **Pastas na nuvem:** pastas sincronizadas (iCloud, OneDrive, Dropbox) podem travar com vídeos grandes. A aplicação avisa em Configurações.

---

## 12. Custos

- A **estimativa** aparece no passo Revisar e gerar do assistente.
- Há um **limite por vídeo** configurável (padrão US$ 2,00); acima dele, a aplicação pede confirmação.
- O gasto real de cada chamada fica em `projeto/custos.json` e aparece no topo do projeto.

Referência para um vídeo de 5 minutos, com preços de tabela de 09/10/2026:

| Configuração | Total aproximado |
|---|---|
| Opus no entendimento e no roteiro + Haiku no QA + ElevenLabs Multilingual v2 | US$ 1,20 |
| Sonnet no entendimento e no roteiro + Haiku no QA + ElevenLabs Multilingual v2 | US$ 0,85 |
| Sonnet + voz offline Piper | US$ 0,40 |

A tabela de preços usada na estimativa fica em `app/core/precos.py`. Revise antes de precificar.

---

## 13. Como funciona por dentro

Princípio: **a IA propõe, o código determinístico executa**. A IA entende o vídeo e escreve o texto. Corte, voz, encaixe, mixagem e edição são código repetível (FFmpeg).

| # | Etapa | Tipo |
|---|---|---|
| 0 | Gravação em blocos e compressão (H.264, 1080p, 30 quadros constantes) | determinístico |
| 1 | Corte automático do começo e do fim parados (ou manual) e perfil do vídeo | determinístico |
| 2 | Entendimento: trocas de cena, amostragem adaptativa, pranchas de 12 quadros com o instante escrito, quadros em alta resolução e leitura por visão → `mapa_de_cenas.json` | IA + determinístico |
| 3 | Roteiro: janelas e orçamento de caracteres calculados no código, texto escrito pela IA, validação (tamanho, números, "não mencionar", marcadores) e até 2 revisões automáticas | IA + validação |
| 4 | Legendas (até 2 linhas de 42 caracteres) e texto falado | determinístico |
| 5 | Voz: calibração automática, fala por fala com contexto das vizinhas, aparo de silêncio, encaixe automático e cache | TTS + IA + determinístico |
| 6 | Trilha: corta fade e silêncio do fim, emenda sem buracos, nivela e abaixa sob a voz | determinístico |
| 7 | Edição: abertura, transição, legendas, mixagem, encerramento, capa embutida | determinístico |
| 8 | Controle de qualidade: estouros, duração, picos de áudio, trechos pretos, números contra a tela, licença, crédito, quadros-chave | determinístico + visão |

**Orçamento de cada fala:** (janela − 0,15 s) × ritmo calibrado da voz × 0,9, contado no texto **falado**. O texto falado usa siglas soletradas ("I A") e números por extenso; a legenda usa a grafia normal ("IA", "18").

---

## 14. Estrutura do código

```
Video Composer/
├── Instalar / Iniciar / Parar / Desinstalar   (.command para Mac, .bat para Windows)
├── scripts/windows/*.ps1          ← lógica dos scripts do Windows
├── Dockerfile  docker-compose.yml  requirements.txt  env.exemplo
├── docs/estrutura_do_produto.md   ← documento de definição do produto
└── app/
    ├── main.py                    ← API (FastAPI) e servidor da interface
    ├── core/                      ← configurações, segredos, tarefas, FFmpeg, clientes Claude e ElevenLabs,
    │                                 catálogo de músicas, preços
    ├── etapas/                    ← e0 a e8 do pipeline, capa, cartões, linha do tempo
    ├── prompts/                   ← prompts de entendimento e roteiro (editáveis)
    └── web/                       ← interface (HTML, CSS e JavaScript, sem dependências)
        ├── index.html  app.js     ← estrutura e navegação
        ├── styles.css             ← identidade visual e as 10 paletas (atributo data-tema)
        ├── logo.png  favicon.ico  ← logotipo e ícone
        └── js/                    ← núcleo, vídeos, assistente, editor, configurações
```

**Modo de teste:** para testar o fluxo sem gastar créditos, adicione `VC_MODO_TESTE=1` no `.env` e reinicie. IA, voz e catálogo de músicas são simulados.

**API:** documentação interativa em http://localhost:8898/api/docs

---

## 15. Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "Este navegador não permite capturar abas" | Abra pelo Chrome em `http://localhost:8898` (não use o IP) |
| Gravação com faixas pretas | A aba não estava em 16:9. Redimensione a janela antes de gravar |
| Conteúdo preto na gravação | A página usa DRM (vídeos protegidos) e não pode ser capturada |
| O corte automático tirou algo importante | No vídeo, menu ⋯ → **Cortes e marcadores**: ajuste o início ou o fim (fica como corte manual) ou clique em **Voltar ao automático** |
| Troquei a pasta de trabalho e nada mudou | A pasta nova vale depois de **Parar** e **Iniciar**. Os vídeos da pasta antiga não são movidos |
| O menu sumiu numa janela estreita | Abaixo de 1000 px de largura o menu vai para o topo da tela |
| Erro ao gerar música | Confira a chave da ElevenLabs e se o plano tem acesso à API de música (planos pagos) |
| Catálogo aberto não responde | Verifique a internet do Docker. Se aparecer limite de buscas, aguarde alguns minutos |
| A voz Piper falha na primeira vez | O modelo é baixado da internet no primeiro uso; confira a conexão |
| Falas aceleradas | A aplicação já encurta o que não cabe. Se trocou de voz depois do roteiro, gere o vídeo completo de novo |
| Erro 401 ou 403 da API | Chave inválida: use **Testar** em Configurações |
| A aplicação não abre | Confira se o Docker Desktop está aberto e rode `Iniciar` de novo |
| Ver o que está acontecendo | `docker compose logs -f` |

---

## 16. Limitações e próximos passos

- **Extensão do Chrome:** registro de cliques, atalho de marcador durante a gravação e zoom automático nos cliques. O código já aceita `eventos` em `gravacao.json`.
- **Edição de vídeo:** aceleração de esperas longas, desfoque de áreas sensíveis e recorte 9:16 que segue o cursor. O 9:16 atual usa o quadro inteiro com fundo desfocado.
- **Música:** checagem automática de Content ID.
- **Marcas:** várias marcas pela interface. O arquivo de configuração já suporta; a tela edita a marca ativa.
- **Idiomas:** narração e legenda em outros idiomas.

O documento completo do produto, com princípios, contratos de dados, regras do roteiro e lições do caso real, está em `docs/estrutura_do_produto.md`.
