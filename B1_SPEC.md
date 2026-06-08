# B1 — REDESENHO DO /menu (specification)

**Status:** planejado, NÃO implementado. Aguardando TBDs (Lembrete de remédio + email Suporte + escopo Histórico de treinos) + fila de épicos pra começar.

**Contexto:** redesenho da mensagem que aparece quando o user manda `/menu` no WhatsApp. Substitui o menu atual de 12 itens por uma estrutura de 16 itens + submenus.

---

## Estrutura final do /menu novo

```
🏋️ EVOLUTION FIT AI — Menu Principal
O que vamos focar hoje?

💪 TREINO
1. Criar treino personalizado
2. Cadastrar treino (do seu personal)
3. Treinar                            🔁  (renomeado, era "Registrar cargas, séries e histórico")
4. Histórico de treinos               🆕

🥗 NUTRIÇÃO
5. Criar dieta personalizada
6. Cadastrar dieta (do nutricionista)
7. Analisar refeição por foto
8. Ver minhas refeições feitas        🆕
9. Ver meu plano alimentar            🆕

📏 MEDIDAS & CORPO
10. Registrar peso e medidas
11. Análise de composição corporal (por foto)

💧 HÁBITOS DIÁRIOS
12. Água / Suplementos                🔄  (submenu)
13. Acompanhar hábitos (sem álcool / sem fumar)
14. Lembrete de remédio               🆕  (escopo TBD)

🎴 CARDS                               🆕
15. Gerar card                        🆕  (submenu)

⚙️ CONFIGURAÇÕES                       🆕
16. Configurações                     🆕  (submenu)

Responda com o número da opção desejada.
```

### Submenus

**[12] Água / Suplementos:**
- 12.1 Quanto tomei de água hoje?
- 12.2 Meus suplementos (cadastro: nome + dosagem padrão)
- 12.3 Suplementos consumidos no dia

**[15] Gerar card:**
- 15.1 Card do último treino
- 15.2 Card de exercício específico (com 1RM e evolução de força)
- 15.3 Card de treino específico
- 15.4 Card corporal (peso/medidas + gráfico de evolução)

**[16] Configurações:**
- 16.1 Perfil
  - 16.1.1 Ver meu perfil
  - 16.1.2 Limpar meu perfil (= wipe "limpar meus dados" já existente, bloco #13 HISTORICO)
- 16.2 Suporte (e-mail TBD)

---

## Mudanças vs menu atual

| Status | Item novo | Comentário |
|---|---|---|
| ✅ Mantém | 1, 2, 5-7, 10-11, 13 | Igual ao atual (só renumerou) |
| 🔁 Renomeado | 3. Treinar | Era "Registrar cargas, séries e histórico" |
| 🆕 Novo | 4. Histórico de treinos | Lista de sessões passadas. Escopo TBD. |
| 🆕 Novo | 8. Ver refeições feitas | UX WhatsApp das refeições registradas |
| 🆕 Novo | 9. Ver plano alimentar | Mostrar dieta ativa formatada |
| 🔄 Modificado | 12. Água/Suplementos | Vira submenu 12.1 Registrar + 12.2 Acompanhar |
| 🆕 Novo | 14. Lembrete de remédio | Escopo TBD (define + executa? só registra?) |
| 🆕 Novo | 15. Gerar card (4 sub) | Cards de fim de treino / exercício / treino / corporal — = backlog item C |
| 🆕 Novo | 16. Configurações | Perfil edit + Suporte (email TBD) |
| ❌ Removido | Antigo 4. Acompanhar 1RM | Vai aparecer no card de exercício (15.2) |
| ❌ Removido | Antigo 10. Painel evolução | Substituído pelos cards (15.x) |

---

## Faseamento proposto

| Fase | O que faz | Risco / tamanho |
|---|---|---|
| **B1.0** | Esqueleto: texto novo do /menu + dispatch. Itens novos (🆕) e sub-opções de submenus novos mostram "em construção 🚧". Itens existentes (✅) continuam apontando pros fluxos atuais. | Baixo. ~30-60 linhas. 1-2 rodadas. |
| **B1.1** | Itens parciais — polir: 4 (histórico treinos), 8 (ver refeições), 9 (ver plano alimentar). Já tem dados; falta UX user-friendly. | Médio. |
| **B1.2** | Submenu 12 Água/Suplementos: 12.1 água hoje (query) + 12.2 cadastro suplementos (tabela nova + UX gerenciamento) + 12.3 suplementos hoje (query). Migration 015. | Médio (~150-200 linhas). |
| **B1.3** | Submenu 15 Gerar card: 4 cards, cada um gera imagem. = backlog C completo. Não-trivial (requer Pillow/Matplotlib). | Grande. Vários sub-épicos. |
| **B1.4** | 14 Lembrete de remédio — código legado existe mas desativado. Recon primeiro, decidir o que mantém vs muda, depois adaptar pro novo /menu. | Médio-grande (depende do estado do código). | |
| **B1.5** | Submenu 16 Configurações — 16.1.1 Ver meu perfil + 16.1.2 Limpar meu perfil (reusa wipe existente) + 16.2 Suporte (página de contato). | Pequeno (~50-70 linhas). |

---

## Escopos resolvidos

**Histórico de treinos (item 4) — resolvido em 07/06:**
- Mostra **apenas o NOME** de todos os treinos feitos nas últimas 24h.
- Independente de modalidade (musc, corrida, etc — tudo junto).
- Sem timestamps, sem filtros, sem detalhes.
- **Fonte:** `SessaoTreino` filtrada por `user_id` e `iniciada_em >= now - 24h`.
- **Filtro de finalização:** mostrar todas (não filtrar por `finalizada_em`) — sessão iniciada conta como "treino feito".
- **Duplicatas:** se o mesmo treino apareceu 2x em 24h, aparece 2x na lista (não deduplica).
- **Ordem:** mais recente em cima (sort por `iniciada_em DESC`).
- **Vazio:** "Nenhum treino registrado nas últimas 24h. Manda *treinar* pra começar."
- **Format exemplo:**
  ```
  📋 Treinos feitos nas últimas 24h:
  • Peito A
  • Cardio leve
  • Costas/Bíceps
  ```
- **Implementação:** ~20-30 linhas em `claude_service.py` — função `_handle_menu_item_4(user, db)` ou similar; dispatch via `aguardando_menu`.
- **Tamanho:** trivial. Pode entrar na **B1.1** (polir itens parciais) ou junto com **B1.0** (esqueleto).

**Configurações > Perfil (16.1) — resolvido em 07/06:**

Submenu com 2 sub-itens:

- **16.1.1 Ver meu perfil** — mostra os dados atuais do perfil em formato legível:
  - Nome
  - Sexo
  - Data de nascimento + idade calculada
  - Altura (cm)
  - Peso atual (kg)
  - Nível de experiência
  - Treino-prefs (tipo, local, objetivo, dias/semana, tempo/sessão, horário)
  - Lesões/limitações
  - **Fonte:** `perfil_service.get_or_create_perfil(user.id, db)` (já é a fonte única).
  - **Aviso de imutabilidade:** ao final, lembrar que nome/sexo/nascimento/altura são permanentes; peso e nível podem ser editados pela IA conversando.
  - **Implementação:** ~30-40 linhas (handler + formatação).

- **16.1.2 Limpar meu perfil** — aciona o wipe já existente:
  - Reusa o handler `_handle_limpar_dados` e o gatilho existente (estado `confirmando_limpar_dados`).
  - Apaga atividade + zera campos editáveis do perfil; mantém identidade + conta + assinatura (regra do bloco #13 HISTORICO).
  - **Implementação:** ~5-10 linhas. Item do menu só seta o estado `confirmando_limpar_dados` e devolve o aviso forte "Digite APAGAR TUDO ou CANCELAR", reaproveitando todo o resto.

- **Edição de campos pelo menu:** **NÃO** está no escopo agora. Edição de peso e nível segue via IA conversando (como já é hoje). Identidade segue permanente. Se quiser editar via menu no futuro, vira sub-épico próprio.

- **Tamanho total:** ~40-50 linhas. Cabe em **B1.5**.

**Água / Suplementos (submenu 12) — resolvido em 07/06:**

> Registro de consumo de água/suplementos via texto ou foto **já existe no bot** (confirmado por Igor). Esse épico foca em (a) montar o submenu, (b) construir o cadastro de suplementos (12.2 = feature nova) e (c) verificar schema existente quando no Claude Code pra ajustar queries.

Submenu com 3 itens:

- **12.1 Quanto tomei de água hoje?**
  - Query existente: soma do consumo de água do dia atual.
  - **Display:** "Você tomou Xml de água hoje 💧" (formato único, total apenas).
  - **Vazio:** "Você ainda não registrou água hoje. Manda algo tipo 'tomei 500ml' ou envie uma foto."
  - **Fonte:** schema existente (verificar nome de tabela/função quando no Claude Code).
  - **Tamanho:** ~15-25 linhas.

- **12.2 Meus suplementos (cadastro — feature NOVA):**
  - **Tabela nova `suplemento_cadastrado`:**
    - `id` (PK)
    - `user_id` (FK → usuarios.id)
    - `nome` (str)
    - `dosagem_padrao` (str — formato flexível: "30g", "5cap", "1 colher")
    - `ativo` (bool, default true)
    - `criado_em` (datetime)
  - **Migration:** 015 (próxima após 014).
  - **UX (híbrido — lista + opções numeradas):**
    ```
    📋 Seus suplementos cadastrados:
    1. Whey - 30g
    2. Creatina - 5g
    3. Ômega 3 - 1g
    
    O que quer fazer?
    *A* Adicionar um novo
    *B* Remover um existente
    *C* Voltar
    ```
  - **Estados:**
    - `gerenciando_suplementos` (mostra lista + opções A/B/C)
    - `adicionando_suplemento` (espera "nome dosagem" — ex: "BCAA 10g")
    - `removendo_suplemento` (espera número da lista)
  - **Vazio:** "Você não tem suplementos cadastrados ainda. Manda *A* pra adicionar o primeiro."
  - **Remoção:** hard-delete (o log de consumo já guarda nome como string, não tem FK; nada quebra).
  - **Seed inicial:** vazio (user adiciona o que toma). Suplementos do protocolo (whey/creatina/D/omega-3) não são pré-cadastrados.
  - **Tamanho:** ~100-150 linhas + 1 migration.

- **12.3 Suplementos consumidos no dia:**
  - Query existente: lista de consumo de suplementos do dia.
  - **Display:** lista bullet com nome + dosagem, sem horário.
    ```
    Hoje você tomou:
    • Whey 30g
    • Creatina 5g
    • Ômega 3 1g
    ```
  - **Vazio:** "Você ainda não registrou suplementos hoje. Manda algo tipo 'tomei whey 30g'."
  - **Fonte:** schema existente (verificar quando no Claude Code).
  - **Tamanho:** ~15-25 linhas.

- **Tamanho total do submenu 12:** ~130-200 linhas + 1 migration (015).
- **Recon necessário quando no Claude Code:**
  - Schema atual de log de água/suplementos (tabelas, campos, função de query).
  - Confirmar que não há tabela `suplemento_cadastrado` ou equivalente já existente.

**Ver minhas refeições feitas (item 8) — resolvido em 07/06:**
- Mostra refeições do **DIA ATUAL** (00:00 até agora). Sem mecanismo de data passada no menu (se quiser ver outro dia, usa texto livre — não faz parte do B1).
- **Conteúdo por refeição:** hora (se houver) + alimentos + calorias + macros (P/C/G).
- **Total do dia** ao final.
- **Vazio:** "Nenhuma refeição registrada hoje ainda. Manda uma foto da refeição ou descreve em texto."
- **Format exemplo:**
  ```
  🍽️ Suas refeições de hoje:
  
  *Café da manhã* (07:30) — 450 kcal
  • 2 ovos mexidos (140 kcal)
  • Pão integral 2 fatias (180 kcal)
  • Café preto (5 kcal)
  P: 22g · C: 45g · G: 15g
  
  *Almoço* (12:30) — 680 kcal
  • ...
  P: 35g · C: 80g · G: 20g
  
  *TOTAL DO DIA:* 1130 kcal · P: 57g · C: 125g · G: 35g
  ```
- **Fonte:** `RegistroRefeicao` filtrada por `user_id` + `data_refeicao = date.today()`.
- **Recon necessário no Claude Code:**
  - Schema exato de `RegistroRefeicao` (campos: hora? nome refeição? alimentos como JSON ou tabela filha? calorias/macros já calculados?).
  - Função existente em `nutricao_service.py` que liste refeições (se já existir, reusar).
- **Atenção:** bug conhecido `date.today()` em UTC no Render — pode jogar refeição pós-21h BRT pro dia seguinte. Item separado em "Em observação" do CLAUDE.md. Não bloqueia esse spec.
- **Tamanho:** ~30-50 linhas.

**Ver meu plano alimentar (item 9) — resolvido em 07/06:**
- Mostra a dieta ativa **exatamente igual foi cadastrada** — sem reformatar, sem adicionar nada.
- **Format exemplo:**
  ```
  🥗 Seu plano alimentar atual:
  
  [texto da dieta como foi cadastrada]
  ```
- **Vazio:** "Você não tem dieta cadastrada ainda. Use o /menu *5* (criar) ou *6* (cadastrar uma do nutricionista)."
- **Fonte:** `MetaNutricional` ativa do user (existe gate de "1 dieta por cliente" do bloco #10, então sempre há no máximo 1 ativa).
- **Recon necessário no Claude Code:** confirmar nome da função existente (`nutricao_service.get_meta_ativa(user_id, db)` ou similar) e qual campo guarda o texto da dieta (`texto`, `conteudo`, etc).
- **Tamanho:** ~15-20 linhas.

**Suporte (item 16.2) — resolvido em 07/06:**
- Só mostra o e-mail de suporte (texto fixo) + link `mailto:` clicável.
- **Format exemplo:**
  ```
  📧 Suporte Evolution Fit
  
  Manda sua dúvida pra:
  suporte@evolutionfit.ai  (TBD — Igor vai informar)
  
  Tempo médio de resposta: 24h úteis.
  ```
- Sem canal interativo, sem formulário, sem ticket.
- **TBD:** Igor vai criar o e-mail e passar pra substituir o placeholder.
- **Tamanho:** ~10 linhas.

---

## TBDs (resolver antes do épico respectivo)

1. **Lembrete de remédio (14):**
   - **Decisão (07/06):** código legado JÁ EXISTE no projeto mas foi DESATIVADO temporariamente. Speccar depois de voltar pro Claude Code, fazer recon do que existe, analisar o que continua e o que muda. NÃO speccar a partir do zero — aproveitar o legado.
   - **Recon necessário antes:** `grep -nE "lembrete|remedio|medicamento" app/services/claude_service.py app/services/*.py app/routers/*.py` + ver tabelas relacionadas em `alembic/versions/`.

---

## Próximo passo concreto

**Não é a próxima sessão obrigatória.** Pode esperar.

Quando começar a B1.0 (esqueleto), precisa:
- Recon do menu atual no `claude_service.py` (`_handle_menu_item` e dispatch).
- Substituir o texto do menu + criar handlers placeholder pros novos itens.

**Comando de recon (pra rodar quando voltar pro Claude Code):**

```
! cd "/c/Users/Igor Hanate/Desktop/EvolutionFitIA" && ( echo "=== A. menu atual texto + handler ==="; grep -nE "EVOLUTION FIT AI|Menu Principal|_handle_menu_item|aguardando_menu|estado_pendente.*menu" app/services/claude_service.py | head -30; echo; echo "=== B. defs de menu ==="; grep -nE "^def .*menu|^async def .*menu" app/services/claude_service.py ) > /tmp/menurecon.txt ; cp /tmp/menurecon.txt "/c/Users/Igor Hanate/Desktop/menurecon.txt" ; wc -l /tmp/menurecon.txt
```
