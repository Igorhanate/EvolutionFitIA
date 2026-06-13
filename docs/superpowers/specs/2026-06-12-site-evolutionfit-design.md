# Site EvolutionFit AI — Design Spec

**Data:** 12/06/2026
**Objetivo:** Recriar o site institucional (hoje em evolutionfitai.my.canva.site) com padrão de UI/UX elevado (referência de fluidez: cairn-site-pied.vercel.app), mantendo o estilo Corporate Memphis e o conteúdo do site atual, e adicionar o **Studio de Métricas** — gerador gratuito de cards/montagens PNG para stories.

---

## 1. Decisões fechadas

| Decisão | Escolha |
|---|---|
| Estrutura | Landing one-page (`/`) + Studio em rota separada (`/studio`) |
| Stack | Next.js (App Router) + Tailwind CSS + Framer Motion + html-to-image |
| Hospedagem | Repo novo `evolutionfit-site` (GitHub Igorhanate) + Vercel free tier, deploy automático no push |
| Preços | Destaque pré-venda VIP R$ 9,99/mês (50 vagas) + cards Trimestral R$ 29,99/mês e Anual R$ 19,99/mês |
| Checkout | TODOS os botões de assinar → `https://pay.kiwify.com.br/88Bfhea` por enquanto (links centralizados em `config/links.ts`; quando os planos Trimestral/Anual tiverem checkout próprio, trocar ali). Nenhuma menção no site a "bot em construção". |
| Studio | Aberto a todos (isca de marketing), 100% client-side, saída sempre **PNG fundo transparente** 1080×1920 |
| Ilustrações | Reuso das artes Corporate Memphis existentes em `IMAGENS/imagens site/` e logos de `IMAGENS/LOGO/` — nada de arte nova |

## 2. Identidade visual

- **Cores:** verde Evolution (~`#1B7A3D`, extrair exato do logo) primário; preto/grafite texto; branco/cinza-claríssimo fundos; pastéis (lilás, sálvia) só como acentos.
- **Tipografia:** Poppins (títulos) + Inter (corpo). Studio usa fontes extras por template (script manuscrita, monospace/LED, serif).
- **Componentes:** botões arredondados com hover de elevação; cards com sombra leve; muito white space; smooth scrolling; reveals on-scroll discretos (Framer Motion).
- **Tom:** calmo e confiante (referência Cairn), mobile-first (tráfego vem de Instagram/WhatsApp).

## 3. Landing (`/`) — seções na ordem

1. **Navbar fixa** — logo horizontal; âncoras: Como funciona · Evolução · Depoimentos · Planos · Studio; botão "Assinar" → checkout.
2. **Hero** — H1 "A primeira IA de gestão fitness"; sub: "Tudo que você precisa, direto no WhatsApp — baseado no seu tempo e orçamento"; CTA → checkout; **marquee infinito** (esteira) com os personagens ilustrados.
3. **Features** — grade de cards: treinos personalizados ilimitados · análise de refeições por foto · avaliação corporal por foto · contadores de hábitos · conexão Garmin · lembrete de suplementos/remédios · card de evolução para Instagram · disponível 24h no WhatsApp.
4. **"Furou a dieta?"** — seção destaque: envia foto da refeição e a IA encaixa calorias/nutrientes (ilustração análise de comida). Tagline: "A dieta perfeita é aquela que funciona no seu dia a dia".
5. **Evolução** — gráfico "Sem Evolution × Com Evolution" (+47% de resultados), semanas 1–4, **desenha-se no scroll** (Framer Motion + path animation).
6. **Depoimentos** — "Resultados não mentem!": ~10 depoimentos reais (Thiago Albuquerque, Beatriz Fontes, Bruno Henrique, Amanda Fontes, Tereza Medeiros, Larissa Barbosa, Felipe Cavalcanti, Juliana Santos W., Letícia Almeida, Rafael Rodrigues, Marcos Vinícius, Gabriela Martins R.) em marquee/carrossel de cards.
7. **Planos** — destaque VIP pré-venda R$ 9,99/mês "LIBERAMOS APENAS 50 VAGAS DE PRÉ-VENDA" com lista de benefícios (treinos ilimitados, contadores de hábitos, análise corporal por fotos, card de evolução, 24h no WhatsApp, brindes VIP); cards Trimestral R$ 29,99/mês e Anual R$ 19,99/mês. Sub: "Sem baixar app. Disponível 24h. Cancele quando quiser." Botões "QUERO ASSINAR" → checkout.
8. **CTA final + footer** — "Nos vemos lá!"; botão assinar; link Studio; contato/redes (e-mail de suporte TBD — placeholder até Igor criar).

## 4. Studio de Métricas (`/studio`)

**Layout:** form à esquerda (topo no mobile) + preview ao vivo à direita sobre fundo quadriculado (indica transparência). Miniaturas dos templates abaixo do preview; clique troca o template. Botão **"Baixar PNG"** → html-to-image, 1080×1920.

**Form:**
- Modalidade (ícones): Musculação · Corrida · Crossfit · Ciclismo · Yoga — define os campos.
- Campos por modalidade (todos opcionais; vazio não renderiza):
  - Musculação: nome do treino, tempo, calorias, kg levantados, % evolução, 1RM máx, nº repetições, PRs batidos
  - Corrida/Ciclismo: distância, ritmo (pace), tempo, calorias
  - Crossfit: nome do WOD, tempo, calorias, PRs
  - Yoga: tempo, calorias
- Data/hora auto-preenchidas (editáveis).

**Stickers — 12 templates (sem foto):**
1. Clássico — labels+valores em grade, logo central (ref. PNGs 1–4)
2. Manuscrito — script grande (ref. PNG 12)
3. Minimal bold — data/pace pequenos + métrica gigante (ref. PNGs 15–16)
4. LED retrô — fonte relógio digital, verde Evolution (ref. Aura)
5. Evolução com gráfico — exercício, +X%, 1RM máx, linha verde (ref. PNGs 5–7)
6. Código de barras — métricas ao redor de barcode decorativo
7. Balão de mensagem — bolha estilo iMessage/WhatsApp
8. Máquina de escrever — frase com palavras em marca-texto
9. Serif elegante — métrica única em serifada fina
10. Curtida — badge de coração estilo Instagram
11. Letras cruzadas — letras em cruz vertical/horizontal (ONE MILE)
12. Stats compactos — mini-tabela Dist/Pace/Tempo/Cal

**Montagens editáveis — 6 modelos (com upload de 1–4 fotos):**
1. Polaroid — foto na moldura, logo topo, métricas manuscritas embaixo (ref. PNGs 8/10)
2. Tira photo booth — 3 fotos empilhadas + etiqueta de fita com métrica
3. Filme/negativo — foto no quadro de filme, métricas nas bordas perfuradas
4. Janelas retrô — fotos em janelas de PC antigo + bloco "stats.txt" com métricas
5. Quadros de filme em sequência — 2–3 fotos, métricas douradas nas bordas
6. Colagem com etiqueta — grade de 4 fotos + etiqueta central ("essa semana — XX km")

Upload/edição 100% no navegador (FileReader/object URL); nenhuma foto sai do dispositivo. Logo Evolution Fit presente em todos os templates.

## 5. Arquitetura do repo `evolutionfit-site`

```
app/
  page.tsx              # landing
  studio/page.tsx       # studio (client component, lazy)
  layout.tsx
components/
  landing/  (Navbar, Hero, Marquee, Features, FuroDieta, Evolucao, Depoimentos, Planos, Footer)
  studio/   (StudioForm, Preview, DownloadButton, templates/<um arquivo por template>)
config/
  links.ts              # CHECKOUT_VIP, CHECKOUT_TRIMESTRAL, CHECKOUT_ANUAL (todos = 88Bfhea por ora)
  content.ts            # textos da landing, depoimentos
public/
  illustrations/ logos/ (copiados de IMAGENS/, otimizados WebP)
```

## 6. Erros e bordas

- Studio: upload aceita jpg/png/webp, limite ~10 MB, erro amigável; campos numéricos com inputmode correto; template sem dados mostra placeholders de exemplo.
- Download: fallback de nome de arquivo `evolutionfit-card.png`; testar Safari iOS (html-to-image tem quirks — validar e, se preciso, usar fallback canvas).
- Sem backend: nada de analytics/cookies na v1.

## 7. Validação

- `npm run build` limpo antes de cada push.
- QA visual desktop + mobile (DevTools) por seção; teste real no celular do Igor (Instagram in-app browser incluso).
- Download de PNG testado em Chrome desktop + Safari/Chrome iOS/Android.
- Lighthouse: performance da landing ≥ 90 mobile.

## 8. Fora de escopo (v1)

- Domínio próprio (plugar depois na Vercel).
- E-mail de suporte (TBD Igor — placeholder no footer).
- Página `/planos` separada (conteúdo absorvido na seção Planos).
- Analytics, SEO avançado, blog.
