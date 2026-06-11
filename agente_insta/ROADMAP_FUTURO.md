# ROADMAP FUTURO — Agente Insta (ideias guardadas)

## Escopo atual (decidido jun/2026)
- O agente gera SÓ os BRIEFS de madrugada. Durante o dia eles viram design no Canva,
  interativamente (com a Claude nesta conversa) ou no Bulk Create.
- Motivo: evitar empilhar serviços. Fluxo enxuto e barato.

## Visão guardada: "acordar com os posts prontos" (Caminho B) — ADIADO
- Objetivo: PNGs finais prontos de madrugada, só revisar e postar.
- Por que adiado: build grande e muitos serviços. Revisitar quando fizer sentido.
### Arquitetura esboçada
- Renderizador HTML/CSS -> PNG (Playwright / Chromium headless).
- CONJUNTO de layouts (não um template só): capa foto+título; texto no topo+foto;
  dado sem foto; citação em faixa sobre a foto; etc. O renderizador rotaciona.
  Variedade = layout + foto + accent + mood. Coesão = sistema (fonte, margem, logo, capricho).
- Fotos: Pexels API (grátis).
- Entrega: Google Drive (pasta posts/ com subpasta por data) sincronizando pro PC -> PC pode ficar desligado.
- Agendamento: Render cron (tier pago, pois renderizar imagem é pesado).
- Fontes da marca como web fonts no HTML.
### Caminho alternativo A: Canva Enterprise + Autofill API
- Render automático no próprio Canva, mas exige Enterprise (caro).
### Pré-requisitos pra retomar
- Chave Pexels; OAuth Google Drive (projeto no Google Cloud); tier pago no Render;
  definir as fontes da marca; montar os templates HTML/CSS.

## Aprendizados de design (valem pra sempre)
- Referência CircleSide: serifa editorial de alto contraste (romano + itálico no remate),
  foto cinematográfica full-bleed com grão, accent que VARIA (lima/laranja/navy),
  wordmark fixo no topo, voz afiada e contraintuitiva.
- Verde da marca = assinatura RARA (um detalhe, nem todo slide, nem todo post).
- Coesão vem do SISTEMA, não de repetir cor. Detalhes anti-genérico: ver SOCIAL_DESIGN_SKILL.md.

## Limites técnicos confirmados
- Geração mágica no Canva só acontece DENTRO de uma conversa com a Claude — robô não faz sozinho no Pro.
- opensquad: orquestrador multi-agente que roda NA IDE, interativo — não resolve "sozinho de madrugada".
  Não adotar como motor; aproveitar só a ideia de papéis em pipeline.

## Onde está o código
- Tudo em agente_insta/ (db, modelos, gerador, armazenar, runner, entrega).
- Tabela posts_gerados no Postgres compartilhado (auto-contida, sem alembic).
