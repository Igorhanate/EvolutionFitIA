# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> O histórico completo de sessões/mudanças foi movido para **HISTORICO.md** (não é auto-carregado). Consulte-o quando precisar de detalhe de implementações passadas.

---

## O QUE É

SaaS de fitness via WhatsApp com IA. O bot "Evo" responde como personal + nutricionista no número **+55 11 5304-3378** (Meta Cloud API). Gerencia treinos, dietas, medidas, hábitos e evolução física. Receita por assinatura recorrente (Kiwify).

**Planos:** Trimestral R$ 29,99/mês · Anual R$ 19,99/mês.

**Dono:** Igor Hanate (não programa). Trabalha via Claude Code seguindo planos passados pelo assistente.

---

## STACK

- Python 3.12, FastAPI + Uvicorn, SQLAlchemy 2.0 + Alembic (**HEAD = migration 014**).
- PostgreSQL no **Render free tier** (SEM backup automático; dorme ~50s sem tráfego).
- **Meta Cloud API** (WhatsApp, graph.facebook.com v19.0); **Kiwify** (pagamento).
- IA: **claude-sonnet-4-6** via AsyncAnthropic (cliente global em `claude_service.py`), prompt caching ephemeral (TTL 5 min).
- Auto-deploy: push em `master` → Render builda Docker e roda `alembic upgrade head` no start.
- Banco **COMPARTILHADO** com a Evolution API → **autogenerate INVIÁVEL**; migrations 100% MANUAIS no padrão 001-014.
- Áudio (Whisper/OpenAI): **DESATIVADO** (aguarda `OPENAI_API_KEY`). Card PNG: matplotlib + Pillow. Parsing de arquivos: pandas/openpyxl (Excel), pypdf (PDF). Scheduler (lembrete 20h): **DESATIVADO**.

**Repo:** github.com/Igorhanate/EvolutionFitIA (branch `master`)
**URL prod:** https://evolutionfit-api.onrender.com
**Workdir:** `C:\Users\Igor Hanate\Desktop\EvolutionFitIA`
**Python (Windows):** `/c/Users/Igor Hanate/AppData/Local/Programs/Python/Python312/python.exe`
**IDs (não-secretos):** Meta phone number ID `1191798997340349` · App "Evolution Fit AI" ID `2038319580456035` · WABA ID `1518787246362458` · webhook `GET`/`POST /webhook/whatsapp` · verify token `evfit-webhook-verify-2026`.

---

## MÉTODO DE TRABALHO (regra de ouro)

1. Assistente **PLANEJA** e escreve comandos/edits; Igor cola no Claude Code e devolve o **RESULTADO REAL** (não o resumo do Claude Code, que colapsa outputs longos).
2. No Claude Code, comandos bash exigem o prefixo **`!`** (ex: `! cd ... && comando`). Edits são aplicados quando recebem blocos *Substituir:/Por:* em texto.
3. Outputs > ~18 linhas colapsam → mandar pra `/tmp` → `cp` pro Desktop → Igor **ANEXA o `.txt`**. Recon por janelas: `awk 'NR>=X && NR<=Y {printf "%d|%s\n", NR, $0}' arquivo`.
4. Antes de nomes novos: **grep anti-colisão**. `py_compile` valida só **sintaxe** (NÃO pega import faltando → conferir o import com grep).
5. Uma coisa de cada vez; validar localmente **ANTES** do push. Mudança em fluxo central → revisar **diff literal** antes de comitar.
6. **NUNCA** expor credenciais no chat. Igor usa `read -s` no Git Bash pra consultas admin.
7. Rodar o Claude Code no **Windows Terminal** (Ctrl+V cola normal), não no cmd antigo.

---

## REGRAS DE SEGURANÇA EM PRODUÇÃO

- Render free SEM backup → testar upgrade/downgrade local **antes** de QUALQUER migration.
- Push = migration roda em produção automaticamente (no start do container).
- Após deploy, **validar via WhatsApp + consulta admin (curl)** entre etapas.

---

## GLOSSÁRIO TÉCNICO

- **PLANO** = 1 plano (semanal) = 1 linha na tabela `treinos` (modelo `Treino`).
- **TREINO** = 1 dia dentro de um plano = item em `Treino.conteudo["dias"][i]` (ex: "Peito A", "Push").
- **EXERCÍCIO** = item em `dias[i].exercicios[j]`.
- **DIETA** = `MetaNutricional` (nome, texto_original, calorias_alvo, macros_alvo_g, flag `ativa`).
- **REFEIÇÃO** = `RegistroRefeicao` (data_refeicao, descrição, calorias/macros).
- **PERFIL** = `PerfilFitness`: sexo, data_nascimento, altura_cm, peso_kg, nivel_experiencia + campos de treino-padrão (dias_semana_padrao, local_treino_padrao, objetivo_padrao, tempo_sessao_padrao, horario_treino_padrao, lesoes).
- `treino_nome` (em `SessaoTreino` e `RegistroExercicio`) guarda o nome do **TREINO (dia)**, não do PLANO. Comando "treinar [nome]" = nome do TREINO (dia).
- **REGRAS:** 1 plano por **modalidade** (musculacao/calistenia/yoga/pilates/corrida/hibrido/funcional/crossfit/mobilidade). 1 **dieta** ativa por cliente.

---

## ESTRUTURAS DE DADOS

**`Treino.conteudo`** (JSON):
```
{
  "texto": "...",            // texto livre gerado
  "nome": "Plano Hipertrofia",   // nome do PLANO
  "modalidade": "musculacao",    // tag do gate P1/P2
  "origem": "proprio",       // "proprio" = externo; ausente = gerado pela IA
  "gerado_em": "iso-timestamp",
  "dias": [
    {
      "numero": 1,
      "nome": "Peito A",     // nome do TREINO (dia)
      "foco": "Peito + Tríceps",   // opcional
      "exercicios": [
        {"nome": "Supino reto", "series_validas": 4, "aquecimento": 2,
         "reps": "8-10", "descanso_seg": 90, "observacoes": "..."}
      ]
    }
  ]
}
```

**`RegistroExercicio`:** id, user_id, sessao_data, posicao_sessao, exercicio (normalizado), exercicio_display, treino_nome (nome do TREINO/dia, indexed), series/repeticoes/carga_kg (agregados), rm_estimado, series_detalhe (JSON nullable: lista de `{carga_kg, repeticoes, is_aquecimento}`), criado_em.

---

## ARQUITETURA

Fluxo: usuário → WhatsApp → Meta Cloud API → `POST /webhook/whatsapp` (valida HMAC-SHA256, dedup via `mensagens_processadas`, checa assinatura) → `claude_service.process_message()` → `whatsapp_service.send_message()`. Sempre HTTP 200 (sem retry da Meta).

**`process_message`** (`claude_service.py`, ~4400 linhas): handlers determinísticos de `estado_pendente` em sequência (interceptam **ANTES** da IA), depois o loop de tool_use com a IA.

**`estado_pendente`** (máquina de estados multi-turno, JSON em `Conversa`): `criando_treino`, `criando_dieta`, `confirmando_dieta_substituicao`, `importando_modalidade`, `confirmar_exercicio`, `confirmar_refeicao`, `coleta_fotos`, `aguardando_menu`, `apagando_registro`, `editando_registro`, `substituicao_dieta`, etc.

**TOOLS (IA):** registrar_exercicio, registrar_medidas, registrar_analise_foto, analisar_refeicao, cadastrar_dieta_propria, cadastrar_treino_proprio, iniciar_coleta_fotos_corpo, registrar_agua, registrar_habito_fumar/alcool, registrar_tomei_suplementos, registrar_suplementos_usuario, substituir_alimento (TACO→USDA, só leitura), consultar_historico_treino.

**`/menu`:** 12 opções — Treino (1 criar · 2 cadastrar externo · 3 registrar cargas · 4 evolução 1RM) · Nutrição (5 criar dieta · 6 cadastrar externa · 7 analisar foto) · Medidas & Corpo (8 peso/medidas · 9 composição por foto · 10 card PNG) · Hábitos (11 água/suplementos · 12 streaks álcool/fumo). **Item 5 = coleta determinística** (`_iniciar_coleta_dieta`). Item 10 = card PNG via `send_image`.

---

## MODELOS / MIGRATIONS

Tabelas: `usuarios`, `assinaturas`, `conversas`, `treinos`, `metas_nutricionais` (dietas), `perfis_fitness`, `mensagens_processadas`, `registros_exercicio`, `medidas_corporais`, `fotos_composicao`, `registros_refeicao`, `habitos_dia`, `perfis_habitos`, `alimentos_taco` (597 alimentos, referência global só-leitura).

Migrations **MANUAIS** 001-014 (**HEAD = 014**; 014 = `series_detalhe`). Autogenerate INVIÁVEL (banco compartilhado com a Evolution API, que geraria `drop_table` das tabelas dela).

---

## ARQUIVOS-CHAVE

- `main.py` — app FastAPI.
- `app/services/claude_service.py` — TODO o fluxo de conversa: tools, `SYSTEM_PROMPT`, guards, máquina de estados, menu, coletas determinísticas (treino e dieta).
- `exercicio_service.py` — registrar, 1RM (Epley/Brzycki/Lander), histórico.
- `treino_service.py` — listar_treinos, cadastrar_treino_proprio, planos_da_modalidade, apagar_treinos.
- `sessao_treino_service.py` — get_sessao_ativa, iniciar_sessao.
- `perfil_service.py` — **get_or_create_perfil (FONTE ÚNICA do perfil)**, calcular_idade, atualizar_peso_perfil, faltam_medidas_ou_fotos.
- `nutricao_service.py` — TACO, refeições, metas (cadastrar_meta, get_meta_ativa, listar_dietas, apagar_dietas), registrar_medidas, build_nutricao_context.
- `habito_service.py`, `usda_service.py`, `card_service.py`, `whatsapp_service.py`, `media_service.py`, `file_reader.py`, `subscription_service.py`, `scheduler_service.py` (lembrete 20h DESATIVADO).
- `app/routers/` — `whatsapp.py`, `kiwify.py`, `admin.py`.
- `alembic/versions/` — migrations 001-014. `alembic/seeds/taco_seed.json`.

---

## ROTAS ADMIN (header `X-Admin-Key`)

`GET /admin/users` · `/admin/users/{id}/perfil` · `/treinos` · `/dietas` · `/refeicoes` · `/medidas` · `/fotos` · `/registros-exercicio?limit=N` · `/evolucao/sessao` · `/evolucao/exercicio?exercicio=`
`DELETE /admin/registros-exercicio?confirm=APAGAR_TUDO` (destrutivo). `POST /admin/subscriptions/grant` (ativação manual).
Igor consulta via `curl` no Git Bash com `read -s ADMIN_KEY`.

---

## PERSONAGEM "EVO"

Tom amigável, direto, conhecedor (personal + nutricionista). Mensagens curtas (WhatsApp, sem paredes de texto). **NÃO** usa "RPE" no output. Diferencia treino × plano. Só funciona no WhatsApp — **NUNCA** direcionar pra app/site/painel/área do aluno. **NUNCA** indicar/prescrever remédio/hormônio/TRT/ciclo → encaminhar ao médico (suplementos do protocolo — whey/creatina/vit D/ômega-3 — liberados).

---

## USUÁRIOS DE TESTE

- **Igor:** `user_id=1` (número pessoal).
- **Maria:** `user_id=6` (ativa, validada).
- `user_id=5` = duplicata de Maria (12 dígitos vs 13) — lixo silencioso.

---

## ESTADO ATUAL (09/06/2026)

**Fechado e no ar:**
- Épico de treino 100% (criar/cadastrar/registrar/1RM/evolução, "treinar [nome]", treino guiado).
- Gestão de planos P1/P2: 1 plano por modalidade, gate "substituir SIM/NÃO", aviso 90 dias — caminhos gerado e importado.
- Dieta: única por cliente (gate substituir); coleta determinística menu 5; cadastro externo determinístico menu 6; excluir dieta em 1 passo.
- **Identidade/wipe:** "limpar meus dados" (apaga atividade + zera perfil editável, MANTÉM identidade+conta+assinatura); onboarding pula campos já preenchidos. Identidade (nome/sexo/nascimento/altura) imutável após 1º cadastro.
- **Épico E3 (criar treino via opção 3) — 100% no ar:** opção 3 = "criar um treino"; IA gera proposta de 1 dia; SIM salva no plano + abre sessão guiada; NÃO = edição em texto livre (regenera); CANCELAR sai. Caso 0-planos (E3b3): pergunta modalidade → cria "Plano de [Modalidade]". (Ver HISTORICO #14 e #15.)
- **Redesenho /menu (épico B1) — em andamento:** B1.0 esqueleto no ar (16 itens, camada de tradução no `_handle_menu_item`); item 4 Histórico de treinos no ar (nomes das sessões das últimas 24h). (Ver HISTORICO #15.)
- Regras de segurança no `SYSTEM_PROMPT` (só WhatsApp; sem remédio/hormônio).

**Princípio firmado:** PERFIL = base única de TODOS os serviços (sempre lido de `perfil_service.get_or_create_perfil`); serviços futuros leem dali e NÃO reperguntam.

**Specs no repo:** `E3B_SPEC.md` (épico E3), `B1_SPEC.md` (redesenho /menu).

---

## BACKLOG

**Em standby (esperando algo):**
- **Identidade Etapa 3 Parte A** — confirmação de permanência no 1º cadastro. 3 edits PRONTOS e NÃO commitados (standby local). Requer número NOVO de WhatsApp pra testar (user_id=1 já tem identidade). Sobe junto com o teste.
- **Lembrete de remédio** (item 14 do /menu) — código legado existe mas desativado. Recon primeiro, decidir o que mantém vs muda. NÃO speccar do zero.

**B1 — redesenho do /menu** (spec completo em `B1_SPEC.md`, 16 itens). Progresso:
- ✅ B1.0 esqueleto (no ar) · ✅ item 4 Histórico de treinos (no ar).
- Falta: item 8 ver refeições, item 9 ver plano alimentar; B1.2 submenu 12 Água/Suplementos (+ migration 015 tabela `suplemento_cadastrado`); B1.3 submenu 15 Cards (= backlog C); B1.4 lembrete remédio; B1.5 submenu 16 Configurações (Perfil ver/limpar + Suporte).
- Escopos já resolvidos no spec: ver refeições, ver plano alimentar, água/suplementos, perfil (ver/limpar), suporte.
- TBD: e-mail do suporte (Igor vai criar).

**C (imagem):** card de fim de treino (gasto calórico, tempo, kg total, % evolução). = submenu 15 do B1. Deferido (complexidade — requer Pillow/Matplotlib).

**D (produto):** fechar lista oficial de modalidades; avaliar skills de geração de treino/dieta. Deferido (Igor vai pesquisar).

**OBSOLETO (não reabrir):** "gravar perfil em coleta dieta" — o gate `perfil_minimo_completo` garante perfil completo antes da dieta; nada a gravar de volta.

**Em observação (não reproduzível):** histórico de refeições "junta tudo num dia só" — banco está correto; suspeita é `date.today()` em UTC no Render (afeta refeição/medida/sessao_data registradas após ~21h BRT).

---

## LANÇAMENTO (meta final)

- Kiwify (`KIWIFY_WEBHOOK_TOKEN_*`, `PAYMENT_LINK_*`).
- `OPENAI_API_KEY` (reativa Whisper/áudio).
- Upgrade Render (free dorme).
- Teste de compra ponta-a-ponta.
- Alerta/auto-recarga de saldo na Anthropic (bot já parou 2x por créditos zerados).
