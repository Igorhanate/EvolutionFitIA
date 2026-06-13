# EvolutionFit Site — Plano 1: Scaffold + Landing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o repositório `evolutionfit-site` (Next.js) com a landing page completa de venda (8 seções, conteúdo do site Canva atual, animações Framer Motion) e deploy na Vercel.

**Architecture:** Next.js App Router com landing one-page em `/` montada por componentes de seção independentes (`components/landing/`), conteúdo e links de checkout centralizados em `config/`, e rota `/studio` como placeholder (Plano 2 implementa o Studio). Tudo estático/client-side, sem backend.

**Tech Stack:** Next.js 15 (App Router, TypeScript), Tailwind CSS v4, Framer Motion (pacote `motion`), lucide-react (ícones), next/font (Poppins + Inter), Vercel.

**Spec:** `docs/superpowers/specs/2026-06-12-site-evolutionfit-design.md` (repo EvolutionFitIA)

**Workdir do plano:** o repo novo vive em `C:\Users\Igor Hanate\Desktop\evolutionfit-site`. Todos os comandos abaixo assumem esse diretório (exceto onde indicado). Este plano (e o spec) ficam no repo EvolutionFitIA.

**Validação por task:** site de marketing sem lógica de negócio — o gate de cada task é `npm run build` limpo + verificação visual no `npm run dev`. Commits frequentes, push só no final (Task 12).

---

### Task 0: Pré-requisitos da máquina

**Files:** nenhum.

- [ ] **Step 1: Verificar Node.js ≥ 18**

Run (PowerShell): `node -v`
Expected: `v18.x` ou superior (ex: `v20.x`, `v22.x`).

Se der erro "não reconhecido": instalar com `winget install OpenJS.NodeJS.LTS`, **fechar e reabrir o terminal**, e conferir `node -v` de novo.

- [ ] **Step 2: Verificar npm e git**

Run: `npm -v` e `git --version`
Expected: versões impressas sem erro (git já existe — é o mesmo do repo do bot).

- [ ] **Step 3: Verificar gh CLI (opcional, para criar o repo GitHub)**

Run: `gh --version`
Se não existir, sem problema — a Task 12 tem caminho manual pelo site do GitHub.

---

### Task 1: Scaffold do projeto

**Files:**
- Create: projeto inteiro em `C:\Users\Igor Hanate\Desktop\evolutionfit-site` via create-next-app

- [ ] **Step 1: Criar o projeto**

Run (PowerShell, em `C:\Users\Igor Hanate\Desktop`):
```powershell
npx create-next-app@latest evolutionfit-site --typescript --tailwind --eslint --app --src-dir=false --import-alias "@/*" --use-npm --no-turbopack
```
Aceitar defaults se perguntar algo a mais. Expected: pasta `evolutionfit-site` criada com `app/`, `package.json`, `tailwind` configurado (v4, via `@import "tailwindcss"` no CSS).

- [ ] **Step 2: Instalar dependências do projeto**

Run (em `evolutionfit-site`):
```powershell
npm install motion lucide-react
```
Expected: instala sem erros. (`motion` é o pacote atual do Framer Motion; importa-se de `motion/react`.)

- [ ] **Step 3: Smoke test**

Run: `npm run dev` → abrir http://localhost:3000 → página default do Next aparece. Parar com Ctrl+C.

- [ ] **Step 4: Commit inicial**

```powershell
git add -A; git commit -m "chore: scaffold next.js + tailwind + motion"
```
(create-next-app já roda `git init` com um commit; este commit cobre as deps.)

---

### Task 2: Assets (logos + ilustrações)

**Files:**
- Create: `public/logos/logo-horizontal.png`, `public/logos/logo-borda.png`
- Create: `public/illustrations/*.png` (renomeados, sem espaços/acentos)

- [ ] **Step 1: Copiar e renomear os assets**

Run (PowerShell, em `evolutionfit-site`):
```powershell
New-Item -ItemType Directory -Force public\logos, public\illustrations | Out-Null
$src = "C:\Users\Igor Hanate\Desktop\EvolutionFitIA\IMAGENS"
Copy-Item "$src\LOGO\EVOLUTION - LOGO HORIZONTAL.png" public\logos\logo-horizontal.png
Copy-Item "$src\LOGO\LOGO EVOLUTION - BORDA.png" public\logos\logo-borda.png
Copy-Item "$src\imagens site\EVOLUTION - CORREDOR.png" public\illustrations\corredor.png
Copy-Item "$src\imagens site\EVOLUTION - MULHER YOGA.png" public\illustrations\yoga.png
Copy-Item "$src\imagens site\EVOLUTION - IMAGEM BOXE DIA.png" public\illustrations\boxe-dia.png
Copy-Item "$src\imagens site\EVOLUTION - IMAGEM BOXE NOITE.png" public\illustrations\boxe-noite.png
Copy-Item "$src\imagens site\EVOLUTION - IDOSOS.png" public\illustrations\idosos.png
Copy-Item "$src\imagens site\EVOLUTION - GARMIN.png" public\illustrations\garmin.png
Copy-Item "$src\imagens site\EVOLUTION - ANALISE ALIMENTOS.png" public\illustrations\analise-alimentos.png
Copy-Item "$src\imagens site\analise de comida.png" public\illustrations\analise-comida.png
Copy-Item "$src\imagens site\EVO - AVALIAÇÃO CORPORAL.png" public\illustrations\avaliacao-corporal.png
Copy-Item "$src\imagens site\EVO - DEITA ONLINE.png" public\illustrations\dieta-online.png
Copy-Item "$src\imagens site\Imagem capa site.png" public\illustrations\capa-site.png
Copy-Item "$src\imagens site\imagem compartilhe evolução.png" public\illustrations\compartilhe-evolucao.png
Get-ChildItem public -Recurse -File | Measure-Object | Select-Object Count
```
Expected: Count = 13.

- [ ] **Step 2: Commit**

```powershell
git add public; git commit -m "feat: assets (logos + ilustracoes corporate memphis)"
```

---

### Task 3: Design system (fontes, cores, layout raiz)

**Files:**
- Modify: `app/globals.css` (substituir conteúdo)
- Modify: `app/layout.tsx` (substituir conteúdo)

- [ ] **Step 1: Escrever `app/globals.css`**

```css
@import "tailwindcss";

@theme {
  --color-evo: #1b7a3d;
  --color-evo-dark: #14592d;
  --color-evo-light: #e8f4ec;
  --color-ink: #171f1a;
  --color-paper: #fafaf8;
  --font-display: var(--font-poppins);
  --font-body: var(--font-inter);
}

html {
  scroll-behavior: smooth;
}

body {
  background: var(--color-paper);
  color: var(--color-ink);
  font-family: var(--font-body), sans-serif;
}

h1, h2, h3, h4 {
  font-family: var(--font-display), sans-serif;
}

@keyframes marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

.animate-marquee {
  animation: marquee 40s linear infinite;
}

.animate-marquee-slow {
  animation: marquee 70s linear infinite;
}

.animate-marquee:hover,
.animate-marquee-slow:hover {
  animation-play-state: paused;
}
```

- [ ] **Step 2: Escrever `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Inter, Poppins } from "next/font/google";
import "./globals.css";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
  variable: "--font-poppins",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Evolution Fit AI — A primeira IA de gestão fitness",
  description:
    "Treinos personalizados, análise de refeições por foto e acompanhamento de evolução. Tudo direto no WhatsApp, 24h por dia. Sem baixar app.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className={`${poppins.variable} ${inter.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Validar build**

Run: `npm run build`
Expected: build OK (página default ainda compila com o novo CSS).

- [ ] **Step 4: Commit**

```powershell
git add app; git commit -m "feat: design system (poppins/inter, cores evo, marquee keyframes)"
```

---

### Task 4: Config central (links + conteúdo)

**Files:**
- Create: `config/links.ts`
- Create: `config/content.ts`

- [ ] **Step 1: Escrever `config/links.ts`**

```ts
// Links de checkout Kiwify. Quando os planos Trimestral/Anual tiverem
// checkout próprio, trocar APENAS aqui.
export const CHECKOUT_VIP = "https://pay.kiwify.com.br/88Bfhea";
export const CHECKOUT_TRIMESTRAL = CHECKOUT_VIP;
export const CHECKOUT_ANUAL = CHECKOUT_VIP;

export const WHATSAPP_BOT = "https://wa.me/551153043378";
```

- [ ] **Step 2: Escrever `config/content.ts`**

```ts
export const HERO = {
  titulo: "A primeira IA de gestão fitness",
  subtitulo:
    "Tudo que você precisa, direto no WhatsApp — baseado no seu tempo e orçamento. Todas as modalidades, para todas as idades, em todos os lugares.",
  cta: "QUERO ASSINAR",
};

export const FEATURES = [
  { icone: "Dumbbell", titulo: "Treinos personalizados ilimitados", texto: "Planos sob medida para seu tempo, local e objetivo — em qualquer modalidade." },
  { icone: "Camera", titulo: "Análise de refeições por foto", texto: "Fotografe o prato e a IA calcula calorias e nutrientes em segundos." },
  { icone: "ScanLine", titulo: "Avaliação corporal por fotos", texto: "Composição corporal estimada a partir de fotos, sem equipamento." },
  { icone: "ListChecks", titulo: "Contadores de hábitos", texto: "Água, suplementos, álcool e cigarro — acompanhe seus streaks." },
  { icone: "Watch", titulo: "Conexão com Garmin", texto: "Treinos de corrida sincronizam e ajustam seu gasto calórico." },
  { icone: "Pill", titulo: "Lembrete de suplementos e remédios", texto: "O Evo lembra você nos horários certos." },
  { icone: "Share2", titulo: "Card de evolução para Instagram", texto: "Compartilhe seu progresso com cards prontos para os stories." },
  { icone: "MessageCircle", titulo: "Disponível 24h no WhatsApp", texto: "Sem baixar app. Seu personal e nutricionista no seu bolso." },
] as const;

export const FUROU_DIETA = {
  titulo: "Furou a dieta?",
  destaque: "Com a Evolution isso não é problema.",
  texto:
    "Envie uma foto da sua refeição e encaixamos automaticamente as calorias e nutrientes no seu dia.",
  tagline: "“A dieta perfeita é aquela que funciona no seu dia a dia.”",
};

export const EVOLUCAO = {
  titulo: "Acompanhe sua evolução",
  destaque: "+47% de resultados",
  texto:
    "Quem acompanha treino, dieta e medidas evolui mais. O Evo registra tudo por você e mostra seu progresso semana a semana.",
  semanas: ["Semana 1", "Semana 2", "Semana 3", "Semana 4"],
};

export const DEPOIMENTOS = [
  { nome: "Thiago Albuquerque", texto: "O melhor de tudo é a praticidade: dá para comer comida do dia a dia, sem complicação e sem pesar no bolso. Adorei!" },
  { nome: "Beatriz Fontes", texto: "Já perdi 5kg durante duas semanas, treinando em casa e seguindo o cardápio." },
  { nome: "Bruno Henrique", texto: "Os treinos sempre se adaptam exatamente ao tempo que tenho disponível." },
  { nome: "Amanda Fontes", texto: "Treino para meias maratonas e a maior dificuldade era alinhar os treinos de força com a corrida. O Evo resolveu." },
  { nome: "Tereza Medeiros", texto: "Minha neta que me indicou. Os exercícios respeitam minhas limitações. Achei maravilhoso!" },
  { nome: "Larissa Barbosa", texto: "Superou minhas expectativas pela praticidade. A dieta cabe no bolso e no dia a dia, e os treinos são ótimos. Muito satisfeita!" },
  { nome: "Felipe Cavalcanti", texto: "Ele faz uma divisão perfeita de volume por grupo muscular e me ajuda a controlar a progressão de cargas." },
  { nome: "Juliana Santos W.", texto: "Eu odiava ter que ficar pesando e digitando cada ingrediente. Essa leitura de prato por inteligência artificial mudou o jogo. Só fotografo o prato e tudo se resolve em segundos." },
  { nome: "Letícia Almeida", texto: "Amei os treinos de força! O Evo organiza as séries e o tempo de descanso. Senti uma evolução nítida." },
  { nome: "Rafael Rodrigues", texto: "Muito prático e direto ao ponto. Sem passar horas na cozinha fazendo pratos caros e sem desculpa para não treinar." },
  { nome: "Marcos Vinícius", texto: "Sensacional a integração com o Garmin! Meus treinos de corrida sincronizam na hora e já calculam o gasto calórico exato para ajustar a minha janta." },
  { nome: "Gabriela Martins R.", texto: "Amei o formato! Consigo conciliar perfeitamente com o trabalho. Alimentação básica e nutritiva sem frescura, e os treinos entram certinho na minha rotina." },
] as const;

export const BENEFICIOS_VIP = [
  "Treinos personalizados ilimitados",
  "Contadores de hábitos",
  "Análise de composição corporal por fotos",
  "Card de evolução para Instagram",
  "Disponível 24h no WhatsApp",
  "Brindes para clientes VIP",
] as const;

export const PLANOS = {
  aviso: "Sem baixar app. Disponível 24h. Cancele quando quiser.",
  vip: {
    nome: "Plano VIP — Pré-venda",
    preco: "R$ 9,99",
    sufixo: "/mês",
    selo: "LIBERAMOS APENAS 50 VAGAS DE PRÉ-VENDA",
    cta: "QUERO ASSINAR",
  },
  trimestral: { nome: "Trimestral", preco: "R$ 29,99", sufixo: "/mês", cta: "Assinar Trimestral" },
  anual: { nome: "Anual", preco: "R$ 19,99", sufixo: "/mês", cta: "Assinar Anual" },
};

export const FOOTER = {
  fechamento: "Nos vemos lá!",
  suporte: "suporte em breve", // TBD: e-mail de suporte (Igor vai criar)
};
```

- [ ] **Step 3: Validar build**

Run: `npm run build` — Expected: OK.

- [ ] **Step 4: Commit**

```powershell
git add config; git commit -m "feat: config central (links checkout + conteudo da landing)"
```

---

### Task 5: Primitivos de UI (CTAButton + Reveal)

**Files:**
- Create: `components/ui/CTAButton.tsx`
- Create: `components/ui/Reveal.tsx`

- [ ] **Step 1: Escrever `components/ui/CTAButton.tsx`**

```tsx
import Link from "next/link";

type Props = {
  href: string;
  children: React.ReactNode;
  variant?: "primary" | "outline";
  className?: string;
};

export default function CTAButton({
  href,
  children,
  variant = "primary",
  className = "",
}: Props) {
  const base =
    "inline-block rounded-xl px-7 py-3.5 font-display font-bold text-base tracking-wide transition-all duration-200";
  const styles =
    variant === "primary"
      ? "bg-evo text-white shadow-lg shadow-evo/25 hover:bg-evo-dark hover:shadow-xl hover:-translate-y-0.5"
      : "border-2 border-evo text-evo hover:bg-evo-light hover:-translate-y-0.5";
  return (
    <Link
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`${base} ${styles} ${className}`}
    >
      {children}
    </Link>
  );
}
```

- [ ] **Step 2: Escrever `components/ui/Reveal.tsx`**

```tsx
"use client";
import { motion } from "motion/react";

type Props = {
  children: React.ReactNode;
  delay?: number;
  className?: string;
};

export default function Reveal({ children, delay = 0, className }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10%" }}
      transition={{ duration: 0.6, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
```

- [ ] **Step 3: Validar build**

Run: `npm run build` — Expected: OK.

- [ ] **Step 4: Commit**

```powershell
git add components; git commit -m "feat: primitivos ui (cta button + reveal on scroll)"
```

---

### Task 6: Navbar + página base

**Files:**
- Create: `components/landing/Navbar.tsx`
- Modify: `app/page.tsx` (substituir conteúdo)
- Create: `app/studio/page.tsx` (placeholder)

- [ ] **Step 1: Escrever `components/landing/Navbar.tsx`**

```tsx
"use client";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { CHECKOUT_VIP } from "@/config/links";

const LINKS = [
  { href: "/#como-funciona", label: "Como funciona" },
  { href: "/#evolucao", label: "Evolução" },
  { href: "/#depoimentos", label: "Depoimentos" },
  { href: "/#planos", label: "Planos" },
  { href: "/studio", label: "Studio" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="fixed inset-x-0 top-0 z-50 bg-paper/90 backdrop-blur border-b border-ink/5">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" aria-label="Evolution Fit — início">
          <Image
            src="/logos/logo-horizontal.png"
            alt="Evolution Fit"
            width={160}
            height={36}
            priority
          />
        </Link>
        <div className="hidden items-center gap-6 md:flex">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-sm font-medium text-ink/70 hover:text-evo transition-colors"
            >
              {l.label}
            </Link>
          ))}
          <Link
            href={CHECKOUT_VIP}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-evo px-4 py-2 text-sm font-bold text-white hover:bg-evo-dark transition-colors"
          >
            Assinar
          </Link>
        </div>
        <button
          className="md:hidden"
          onClick={() => setOpen(!open)}
          aria-label={open ? "Fechar menu" : "Abrir menu"}
        >
          {open ? <X size={26} /> : <Menu size={26} />}
        </button>
      </nav>
      {open && (
        <div className="flex flex-col gap-1 border-t border-ink/5 bg-paper px-4 pb-4 pt-2 md:hidden">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="rounded-lg px-2 py-2.5 font-medium text-ink/80 hover:bg-evo-light"
            >
              {l.label}
            </Link>
          ))}
          <Link
            href={CHECKOUT_VIP}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 rounded-lg bg-evo px-4 py-2.5 text-center font-bold text-white"
          >
            Assinar
          </Link>
        </div>
      )}
    </header>
  );
}
```

- [ ] **Step 2: Escrever `app/page.tsx` (esqueleto; seções entram nas tasks seguintes)**

```tsx
import Navbar from "@/components/landing/Navbar";

export default function Home() {
  return (
    <main>
      <Navbar />
      <div className="pt-16" />
      {/* Hero, Features, FuroDieta, Evolucao, Depoimentos, Planos, Footer entram nas próximas tasks */}
    </main>
  );
}
```

- [ ] **Step 3: Escrever `app/studio/page.tsx` (placeholder até o Plano 2)**

```tsx
import Link from "next/link";
import Navbar from "@/components/landing/Navbar";

export const metadata = { title: "Studio de Métricas — Evolution Fit AI" };

export default function StudioPage() {
  return (
    <main>
      <Navbar />
      <section className="mx-auto flex min-h-[70vh] max-w-3xl flex-col items-center justify-center px-4 pt-16 text-center">
        <h1 className="font-display text-4xl font-extrabold">
          Studio de Métricas
        </h1>
        <p className="mt-4 text-lg text-ink/70">
          Gere cards dos seus treinos para compartilhar nos stories. Em breve.
        </p>
        <Link href="/" className="mt-8 font-bold text-evo hover:underline">
          ← Voltar ao início
        </Link>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Verificar no dev**

Run: `npm run dev` → http://localhost:3000 — navbar fixa com logo, links e botão Assinar; menu hamburguer funciona no mobile (DevTools); `/studio` mostra o placeholder.

- [ ] **Step 5: Commit**

```powershell
git add app components; git commit -m "feat: navbar + esqueleto da home + studio placeholder"
```

---

### Task 7: Hero + Marquee de personagens

**Files:**
- Create: `components/landing/Marquee.tsx`
- Create: `components/landing/Hero.tsx`
- Modify: `app/page.tsx`

- [ ] **Step 1: Escrever `components/landing/Marquee.tsx`**

```tsx
import Image from "next/image";

const ILUSTRACOES = [
  "corredor.png",
  "yoga.png",
  "boxe-dia.png",
  "idosos.png",
  "garmin.png",
  "avaliacao-corporal.png",
  "analise-alimentos.png",
  "boxe-noite.png",
  "dieta-online.png",
  "compartilhe-evolucao.png",
];

export default function Marquee() {
  // Lista duplicada: a animação desloca -50% e reinicia sem emenda visível.
  const itens = [...ILUSTRACOES, ...ILUSTRACOES];
  return (
    <div className="relative overflow-hidden py-6" aria-hidden>
      <div className="animate-marquee flex w-max gap-8">
        {itens.map((img, i) => (
          <div
            key={i}
            className="h-44 w-44 shrink-0 overflow-hidden rounded-2xl bg-white shadow-sm md:h-56 md:w-56"
          >
            <Image
              src={`/illustrations/${img}`}
              alt=""
              width={224}
              height={224}
              className="h-full w-full object-cover"
            />
          </div>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-paper to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-paper to-transparent" />
    </div>
  );
}
```

- [ ] **Step 2: Escrever `components/landing/Hero.tsx`**

```tsx
import CTAButton from "@/components/ui/CTAButton";
import Reveal from "@/components/ui/Reveal";
import Marquee from "@/components/landing/Marquee";
import { HERO } from "@/config/content";
import { CHECKOUT_VIP } from "@/config/links";

export default function Hero() {
  return (
    <section className="pt-10 md:pt-16">
      <div className="mx-auto max-w-4xl px-4 text-center">
        <Reveal>
          <h1 className="font-display text-4xl font-extrabold leading-tight md:text-6xl">
            {HERO.titulo}
          </h1>
        </Reveal>
        <Reveal delay={0.15}>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-ink/70 md:text-xl">
            {HERO.subtitulo}
          </p>
        </Reveal>
        <Reveal delay={0.3}>
          <CTAButton href={CHECKOUT_VIP} className="mt-8">
            {HERO.cta}
          </CTAButton>
        </Reveal>
      </div>
      <Reveal delay={0.4}>
        <div className="mt-12">
          <Marquee />
        </div>
      </Reveal>
    </section>
  );
}
```

- [ ] **Step 3: Adicionar à página — `app/page.tsx`**

```tsx
import Navbar from "@/components/landing/Navbar";
import Hero from "@/components/landing/Hero";

export default function Home() {
  return (
    <main>
      <Navbar />
      <div className="pt-16" />
      <Hero />
    </main>
  );
}
```

- [ ] **Step 4: Verificar no dev**

Run: `npm run dev` — Hero com título, sub, CTA verde; esteira de ilustrações rolando suavemente, pausa no hover, sem "salto" quando reinicia.

- [ ] **Step 5: Commit**

```powershell
git add app components; git commit -m "feat: hero + marquee infinito de personagens"
```

---

### Task 8: Features + seção "Furou a dieta?"

**Files:**
- Create: `components/landing/Features.tsx`
- Create: `components/landing/FuroDieta.tsx`
- Modify: `app/page.tsx`

- [ ] **Step 1: Escrever `components/landing/Features.tsx`**

```tsx
import {
  Dumbbell, Camera, ScanLine, ListChecks, Watch, Pill, Share2, MessageCircle,
} from "lucide-react";
import Reveal from "@/components/ui/Reveal";
import { FEATURES } from "@/config/content";

const ICONES = {
  Dumbbell, Camera, ScanLine, ListChecks, Watch, Pill, Share2, MessageCircle,
} as const;

export default function Features() {
  return (
    <section id="como-funciona" className="mx-auto max-w-6xl px-4 py-20 md:py-28">
      <Reveal>
        <h2 className="text-center font-display text-3xl font-extrabold md:text-4xl">
          Tudo que você precisa, direto no WhatsApp
        </h2>
        <p className="mt-3 text-center text-ink/60">
          Todas as modalidades · para todas as idades · em todos os lugares
        </p>
      </Reveal>
      <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f, i) => {
          const Icone = ICONES[f.icone as keyof typeof ICONES];
          return (
            <Reveal key={f.titulo} delay={i * 0.06}>
              <div className="h-full rounded-2xl bg-white p-6 shadow-sm ring-1 ring-ink/5 transition-shadow hover:shadow-md">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-evo-light text-evo">
                  <Icone size={22} />
                </div>
                <h3 className="mt-4 font-display text-base font-bold">
                  {f.titulo}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/65">
                  {f.texto}
                </p>
              </div>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Escrever `components/landing/FuroDieta.tsx`**

```tsx
import Image from "next/image";
import Reveal from "@/components/ui/Reveal";
import CTAButton from "@/components/ui/CTAButton";
import { FUROU_DIETA } from "@/config/content";
import { CHECKOUT_VIP } from "@/config/links";

export default function FuroDieta() {
  return (
    <section className="bg-evo-light/60">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-20 md:grid-cols-2 md:py-28">
        <Reveal>
          <div>
            <h2 className="font-display text-3xl font-extrabold md:text-4xl">
              {FUROU_DIETA.titulo}{" "}
              <span className="text-evo">{FUROU_DIETA.destaque}</span>
            </h2>
            <p className="mt-4 text-lg text-ink/70">{FUROU_DIETA.texto}</p>
            <p className="mt-6 font-display text-xl font-semibold text-ink/80">
              {FUROU_DIETA.tagline}
            </p>
            <CTAButton href={CHECKOUT_VIP} className="mt-8">
              Começar agora
            </CTAButton>
          </div>
        </Reveal>
        <Reveal delay={0.15}>
          <div className="overflow-hidden rounded-3xl shadow-lg">
            <Image
              src="/illustrations/analise-comida.png"
              alt="Análise de refeição por foto no WhatsApp"
              width={640}
              height={640}
              className="h-auto w-full"
            />
          </div>
        </Reveal>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Adicionar à página — `app/page.tsx`**

```tsx
import Navbar from "@/components/landing/Navbar";
import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import FuroDieta from "@/components/landing/FuroDieta";

export default function Home() {
  return (
    <main>
      <Navbar />
      <div className="pt-16" />
      <Hero />
      <Features />
      <FuroDieta />
    </main>
  );
}
```

- [ ] **Step 4: Verificar no dev**

Run: `npm run dev` — grid de 8 features com ícones e reveals escalonados; seção "Furou a dieta?" com fundo verde-claro e ilustração.

- [ ] **Step 5: Commit**

```powershell
git add app components; git commit -m "feat: secoes features + furou a dieta"
```

---

### Task 9: Gráfico de Evolução animado no scroll

**Files:**
- Create: `components/landing/Evolucao.tsx`
- Modify: `app/page.tsx`

- [ ] **Step 1: Escrever `components/landing/Evolucao.tsx`**

```tsx
"use client";
import { motion } from "motion/react";
import Reveal from "@/components/ui/Reveal";
import { EVOLUCAO } from "@/config/content";

// Curvas do gráfico (viewBox 0 0 600 300, y invertido: menor = mais alto)
const COM_EVOLUTION = "M 40 260 C 160 240, 240 170, 340 120 S 520 50, 560 40";
const SEM_EVOLUTION = "M 40 260 C 180 250, 300 235, 420 225 S 530 215, 560 212";

export default function Evolucao() {
  return (
    <section id="evolucao" className="mx-auto max-w-6xl px-4 py-20 md:py-28">
      <Reveal>
        <h2 className="text-center font-display text-3xl font-extrabold md:text-4xl">
          {EVOLUCAO.titulo}
        </h2>
        <p className="mt-3 text-center text-lg">
          <span className="font-display font-extrabold text-evo">
            {EVOLUCAO.destaque}
          </span>{" "}
          <span className="text-ink/60">para quem acompanha tudo com o Evo</span>
        </p>
      </Reveal>
      <Reveal delay={0.1}>
        <div className="mx-auto mt-12 max-w-3xl rounded-3xl bg-white p-6 shadow-sm ring-1 ring-ink/5 md:p-10">
          <svg viewBox="0 0 600 300" className="w-full" role="img" aria-label="Gráfico: com Evolution você evolui 47% mais em 4 semanas">
            {/* linhas de grade */}
            {[60, 120, 180, 240].map((y) => (
              <line key={y} x1="40" y1={y} x2="560" y2={y} stroke="#171f1a" strokeOpacity="0.06" strokeWidth="1" />
            ))}
            {/* sem Evolution */}
            <motion.path
              d={SEM_EVOLUTION}
              fill="none"
              stroke="#9aa39d"
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray="8 8"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true, margin: "-20%" }}
              transition={{ duration: 1.4, ease: "easeInOut" }}
            />
            {/* com Evolution */}
            <motion.path
              d={COM_EVOLUTION}
              fill="none"
              stroke="#1b7a3d"
              strokeWidth="5"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true, margin: "-20%" }}
              transition={{ duration: 1.8, ease: "easeInOut", delay: 0.2 }}
            />
            {/* ponta da linha verde */}
            <motion.circle
              cx="560" cy="40" r="7" fill="#1b7a3d"
              initial={{ opacity: 0, scale: 0 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-20%" }}
              transition={{ delay: 2.0, duration: 0.3 }}
            />
          </svg>
          <div className="mt-2 flex justify-between px-2 text-xs text-ink/50 md:text-sm">
            {EVOLUCAO.semanas.map((s) => (
              <span key={s}>{s}</span>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap justify-center gap-6 text-sm">
            <span className="flex items-center gap-2">
              <span className="inline-block h-1 w-6 rounded bg-evo" /> Com Evolution
            </span>
            <span className="flex items-center gap-2 text-ink/60">
              <span className="inline-block h-1 w-6 rounded bg-[#9aa39d]" /> Sem Evolution
            </span>
          </div>
        </div>
      </Reveal>
      <Reveal delay={0.2}>
        <p className="mx-auto mt-8 max-w-xl text-center text-ink/70">
          {EVOLUCAO.texto}
        </p>
      </Reveal>
    </section>
  );
}
```

- [ ] **Step 2: Adicionar à página — acrescentar em `app/page.tsx`**

```tsx
import Evolucao from "@/components/landing/Evolucao";
// ...dentro do <main>, após <FuroDieta />:
<Evolucao />
```

- [ ] **Step 3: Verificar no dev**

Run: `npm run dev` — ao rolar até a seção, a linha cinza tracejada e a linha verde se desenham; bolinha verde aparece na ponta ao final.

- [ ] **Step 4: Commit**

```powershell
git add app components; git commit -m "feat: grafico de evolucao animado no scroll (+47%)"
```

---

### Task 10: Depoimentos (marquee de cards)

**Files:**
- Create: `components/landing/Depoimentos.tsx`
- Modify: `app/page.tsx`

- [ ] **Step 1: Escrever `components/landing/Depoimentos.tsx`**

```tsx
import Reveal from "@/components/ui/Reveal";
import { DEPOIMENTOS } from "@/config/content";

function Card({ nome, texto }: { nome: string; texto: string }) {
  return (
    <figure className="w-80 shrink-0 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-ink/5">
      <blockquote className="text-sm leading-relaxed text-ink/75">
        “{texto}”
      </blockquote>
      <figcaption className="mt-4 font-display text-sm font-bold text-evo">
        {nome}
      </figcaption>
    </figure>
  );
}

export default function Depoimentos() {
  const metade = Math.ceil(DEPOIMENTOS.length / 2);
  const linha1 = [...DEPOIMENTOS.slice(0, metade), ...DEPOIMENTOS.slice(0, metade)];
  const linha2 = [...DEPOIMENTOS.slice(metade), ...DEPOIMENTOS.slice(metade)];
  return (
    <section id="depoimentos" className="overflow-hidden bg-white/60 py-20 md:py-28">
      <Reveal>
        <h2 className="text-center font-display text-3xl font-extrabold md:text-4xl">
          Resultados não mentem!
        </h2>
        <p className="mt-3 text-center text-ink/60">Avaliações dos clientes</p>
      </Reveal>
      <div className="mt-12 flex flex-col gap-5">
        <div className="animate-marquee-slow flex w-max gap-5">
          {linha1.map((d, i) => (
            <Card key={`a${i}`} nome={d.nome} texto={d.texto} />
          ))}
        </div>
        <div className="animate-marquee-slow flex w-max gap-5 [animation-direction:reverse]">
          {linha2.map((d, i) => (
            <Card key={`b${i}`} nome={d.nome} texto={d.texto} />
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Adicionar à página — acrescentar em `app/page.tsx`**

```tsx
import Depoimentos from "@/components/landing/Depoimentos";
// ...após <Evolucao />:
<Depoimentos />
```

- [ ] **Step 3: Verificar no dev**

Run: `npm run dev` — duas fileiras de depoimentos deslizando em direções opostas, pausam no hover.

- [ ] **Step 4: Commit**

```powershell
git add app components; git commit -m "feat: depoimentos em marquee duplo"
```

---

### Task 11: Planos + CTA final + Footer

**Files:**
- Create: `components/landing/Planos.tsx`
- Create: `components/landing/Footer.tsx`
- Modify: `app/page.tsx`

- [ ] **Step 1: Escrever `components/landing/Planos.tsx`**

```tsx
import { Check } from "lucide-react";
import Reveal from "@/components/ui/Reveal";
import CTAButton from "@/components/ui/CTAButton";
import { BENEFICIOS_VIP, PLANOS } from "@/config/content";
import { CHECKOUT_ANUAL, CHECKOUT_TRIMESTRAL, CHECKOUT_VIP } from "@/config/links";

export default function Planos() {
  return (
    <section id="planos" className="mx-auto max-w-6xl px-4 py-20 md:py-28">
      <Reveal>
        <h2 className="text-center font-display text-3xl font-extrabold md:text-4xl">
          Escolha seu plano
        </h2>
        <p className="mt-3 text-center text-ink/60">{PLANOS.aviso}</p>
      </Reveal>

      {/* VIP em destaque */}
      <Reveal delay={0.1}>
        <div className="relative mx-auto mt-12 max-w-2xl rounded-3xl bg-ink p-8 text-white shadow-xl md:p-10">
          <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-evo px-4 py-1.5 text-xs font-bold tracking-wide">
            {PLANOS.vip.selo}
          </span>
          <h3 className="font-display text-2xl font-extrabold">
            {PLANOS.vip.nome}
          </h3>
          <p className="mt-3">
            <span className="font-display text-5xl font-extrabold">
              {PLANOS.vip.preco}
            </span>
            <span className="text-white/60">{PLANOS.vip.sufixo}</span>
            <span className="ml-2 align-middle text-sm text-white/50">
              valor promocional
            </span>
          </p>
          <ul className="mt-6 grid gap-2.5 sm:grid-cols-2">
            {BENEFICIOS_VIP.map((b) => (
              <li key={b} className="flex items-start gap-2 text-sm text-white/85">
                <Check size={18} className="mt-0.5 shrink-0 text-evo" />
                {b}
              </li>
            ))}
          </ul>
          <CTAButton href={CHECKOUT_VIP} className="mt-8 w-full text-center">
            {PLANOS.vip.cta}
          </CTAButton>
        </div>
      </Reveal>

      {/* Trimestral / Anual */}
      <div className="mx-auto mt-8 grid max-w-2xl gap-5 sm:grid-cols-2">
        {[
          { plano: PLANOS.trimestral, href: CHECKOUT_TRIMESTRAL },
          { plano: PLANOS.anual, href: CHECKOUT_ANUAL },
        ].map(({ plano, href }, i) => (
          <Reveal key={plano.nome} delay={0.15 + i * 0.05}>
            <div className="flex h-full flex-col rounded-2xl bg-white p-7 shadow-sm ring-1 ring-ink/5">
              <h3 className="font-display text-lg font-bold">{plano.nome}</h3>
              <p className="mt-2">
                <span className="font-display text-3xl font-extrabold">
                  {plano.preco}
                </span>
                <span className="text-ink/50">{plano.sufixo}</span>
              </p>
              <div className="mt-auto pt-6">
                <CTAButton href={href} variant="outline" className="w-full text-center">
                  {plano.cta}
                </CTAButton>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Escrever `components/landing/Footer.tsx`**

```tsx
import Image from "next/image";
import Link from "next/link";
import Reveal from "@/components/ui/Reveal";
import CTAButton from "@/components/ui/CTAButton";
import { FOOTER } from "@/config/content";
import { CHECKOUT_VIP } from "@/config/links";

export default function Footer() {
  return (
    <footer className="bg-ink text-white">
      <div className="mx-auto max-w-6xl px-4 py-16 text-center md:py-24">
        <Reveal>
          <h2 className="font-display text-3xl font-extrabold md:text-5xl">
            {FOOTER.fechamento}
          </h2>
          <CTAButton href={CHECKOUT_VIP} className="mt-8">
            QUERO ASSINAR
          </CTAButton>
        </Reveal>
      </div>
      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-6 text-sm text-white/50 md:flex-row">
          <Image
            src="/logos/logo-horizontal.png"
            alt="Evolution Fit"
            width={130}
            height={30}
            className="brightness-0 invert"
          />
          <div className="flex gap-6">
            <Link href="/studio" className="hover:text-white">
              Studio de Métricas
            </Link>
            <span>{FOOTER.suporte}</span>
          </div>
          <span>© {new Date().getFullYear()} Evolution Fit AI</span>
        </div>
      </div>
    </footer>
  );
}
```

- [ ] **Step 3: `app/page.tsx` final**

```tsx
import Navbar from "@/components/landing/Navbar";
import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import FuroDieta from "@/components/landing/FuroDieta";
import Evolucao from "@/components/landing/Evolucao";
import Depoimentos from "@/components/landing/Depoimentos";
import Planos from "@/components/landing/Planos";
import Footer from "@/components/landing/Footer";

export default function Home() {
  return (
    <main>
      <Navbar />
      <div className="pt-16" />
      <Hero />
      <Features />
      <FuroDieta />
      <Evolucao />
      <Depoimentos />
      <Planos />
      <Footer />
    </main>
  );
}
```

- [ ] **Step 4: Verificar no dev**

Run: `npm run dev` — card VIP escuro em destaque com selo das 50 vagas; Trimestral/Anual abaixo; footer escuro com CTA "Nos vemos lá!". Todos os botões abrem o checkout Kiwify em nova aba.

- [ ] **Step 5: Commit**

```powershell
git add app components; git commit -m "feat: planos (vip pre-venda + trimestral/anual) + footer"
```

---

### Task 12: QA final + GitHub + Vercel

**Files:** nenhum novo.

- [ ] **Step 1: Build de produção**

Run: `npm run build`
Expected: build limpo, sem erros de tipo/lint.

- [ ] **Step 2: QA visual completo**

Run: `npm run start` → http://localhost:3000
Checklist:
- Desktop: todas as 8 seções, animações de scroll, marquees sem emenda.
- DevTools mobile (iPhone SE 375px e um Android ~412px): navbar hamburguer, hero legível, cards empilham, gráfico legível, botões com área de toque confortável.
- Todos os CTAs abrem `pay.kiwify.com.br/88Bfhea` em nova aba.
- `/studio` placeholder OK.

- [ ] **Step 3: Lighthouse**

DevTools → Lighthouse → Mobile → Performance.
Expected: ≥ 90. Se < 90, causa mais provável são os PNGs grandes do marquee — reduzir `width/height` solicitados no `next/image` ou converter os maiores pra WebP, e medir de novo.

- [ ] **Step 4: Criar repo GitHub e push**

Com gh CLI:
```powershell
gh repo create Igorhanate/evolutionfit-site --public --source . --push
```
Sem gh CLI (manual): criar repo vazio `evolutionfit-site` em github.com/new, depois:
```powershell
git remote add origin https://github.com/Igorhanate/evolutionfit-site.git
git push -u origin master
```

- [ ] **Step 5: Deploy na Vercel (passos do Igor, no navegador)**

1. vercel.com → login com GitHub.
2. "Add New… → Project" → importar `evolutionfit-site`.
3. Defaults (framework Next.js detectado) → Deploy.
4. Abrir a URL `*.vercel.app` gerada e repetir o checklist do Step 2 no celular real (incluindo navegador interno do Instagram).

- [ ] **Step 6: Validação final**

Site no ar na URL da Vercel, checkout abrindo do celular. A partir daqui, todo push em `master` = deploy automático.

---

## Self-review (feito na escrita)

- **Cobertura do spec:** seções 1–3 e 5–8 do spec cobertas (decisões, identidade, landing completa, arquitetura, bordas, validação). Seção 4 (Studio) fica no Plano 2 — `/studio` placeholder criado na Task 6 pra navbar não quebrar. E-mail de suporte = placeholder no footer (TBD do spec).
- **Placeholders:** nenhum "TBD/depois" em código; todo step tem código completo.
- **Consistência de tipos:** `config/content.ts` exporta HERO, FEATURES, FUROU_DIETA, EVOLUCAO, DEPOIMENTOS, BENEFICIOS_VIP, PLANOS, FOOTER — todos consumidos com esses nomes nas tasks 7–11; `config/links.ts` exporta CHECKOUT_VIP/TRIMESTRAL/ANUAL/WHATSAPP_BOT (WHATSAPP_BOT fica disponível pra uso futuro no footer/suporte).
