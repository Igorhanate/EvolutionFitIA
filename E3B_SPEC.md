# E3b — CRIAR UM TREINO NOVO (specification)

**Status:** planejado, NÃO implementado. Próximo passo: rodar recon (comando no fim) e começar E3b1.

**Contexto:** continuação do épico E3 ("criar um treino" como opção 3 do `treinar_nao_casou`). E3a (seleção do plano destino) já está no ar com placeholders 🚧 — E3b substitui esses placeholders pela implementação real.

---

## Fluxo do usuário

1. User passou pela seleção do destino na E3a (plano escolhido, ou 0-planos com modalidade pendente).
2. Bot diz "Gerando uma proposta de treino..." e chama a IA com forced tool use.
3. IA gera um dia completo: nome, foco, exercícios com séries/reps/descanso/aquecimento.
4. Bot apresenta a proposta formatada no WhatsApp.
5. Bot pergunta: "Aprovar? *SIM* / *NÃO* / *CANCELAR*".
6. Resposta do user:
   - **SIM** (sinônimos: `ok`, `aprovar`, `iniciar`, `vamos`) → salva o dia em `Treino.conteudo["dias"]` + `iniciar_sessao` + reply "sessão iniciada".
   - **NÃO** → bot pergunta "o que você quer mudar?" → user responde texto livre → IA regenera com instrução → re-apresenta. Loop. (sub-etapa E3c)
   - **CANCELAR** → sai do fluxo, estado limpo.
7. **Timeout 5 min:** se user não responde em 5 min, estado é descartado, bot pede pra recomeçar.

---

## Decomposição em sub-etapas

| Sub | O que faz | Como testar |
|---|---|---|
| **E3b1** | Caso 1+ planos. IA gera proposta + apresenta + handler de SIM/NÃO/CANCELAR. SIM=placeholder "save virá", NÃO=placeholder "edição em construção", CANCELAR=sai. Timeout 5min já implementado. | Vê proposta gerada, dá SIM → mensagem placeholder, dá CANCELAR → sai. |
| **E3b2** | SIM real: salva o dia em `Treino.conteudo["dias"]` (numero = último) + `iniciar_sessao` + reply "sessão iniciada". | Fluxo ponta-a-ponta com 1+ plano. |
| **E3b3** | 0-planos: bot pergunta modalidade ANTES da geração → IA gera com modalidade certa → no SIM, cria plano vazio + adiciona dia atomicamente. | Wipe + fluxo completo. |
| **E3c** | NÃO real: pergunta "o que mudar?" → user texto livre → IA regenera com instrução → re-apresenta → loop até SIM/CANCELAR. | Vê proposta, dá NÃO, escreve "tira o supino", vê proposta nova. |

---

## Decisões TRAVADAS

- **Palavras que aprovam:** `SIM`, `ok`, `aprovar`, `iniciar`, `vamos`
- **NÃO:** porta de entrada da edição (sub-etapa E3c)
- **CANCELAR:** sai do fluxo
- **Quantos exercícios:** IA decide livremente (sem range fixo)
- **Aquecimento por exercício:** SIM (campo `aquecimento` em cada exercício, igual à estrutura existente)
- **Timeout do estado:** 5 minutos (descartado depois)
- **Posição do novo treino no plano:** último (`numero = len(dias) + 1`); não renumera os anteriores
- **Limite de custo Anthropic por user:** sem limite agora — adicionar depois se virar problema
- **Nome auto-gerado do plano novo (E3b3):** `"Plano de [Modalidade]"` (ex: "Plano de Musculação")
- **Regra "1 plano por modalidade":** já está no ar (bloco #9 HISTORICO.md) — vale também pro E3b3 (se 0 planos não tem conflito por definição)

---

## Componentes técnicos novos a criar

- **Tool nova `propor_dia_treino`** — schema espelhando `Treino.conteudo["dias"][i]`:
  ```
  {
    "nome": str,
    "foco": str,
    "exercicios": [
      {
        "nome": str,
        "series_validas": int,
        "aquecimento": int,
        "reps": str,
        "descanso_seg": int,
        "observacoes": str (optional)
      }
    ]
  }
  ```
- **Função `_gerar_proposta_dia(...)`** — chama AsyncAnthropic com forced tool use, parseia, valida shape mínimo.
- **Função `_apresentar_proposta_dia(dia)`** — formata pra WhatsApp.
- **Estado `aguardando_aprovacao_treino_novo`** + handler, contendo:
  - `plano_id` (ou modalidade pendente no caso 0-planos)
  - `nome_treino`
  - `proposta` (dict completo)
  - `criado_em` (pro timeout 5min)
- **Estado `escolhendo_modalidade_para_novo_plano`** (só E3b3) + handler, ANTES da geração.
- **Estado `aguardando_edit_treino_novo`** (só E3c) + handler, depois do NÃO.
- **Função `_salvar_dia_no_plano(plano_id, dia_dict, db)`** — append + commit.
- **Função `_criar_plano_vazio(user_id, modalidade, db)`** (só E3b3) — cria plano stub pra receber o dia.

---

## Open items técnicos (resolver durante E3b1 com recon)

- Schema exato da tool `propor_dia_treino` — espelhar o `salvar_treino_estruturado` existente.
- Prompt da IA — contexto: perfil completo + modalidade do plano + nome digitado + dias já existentes no plano (pra evitar repetição).
- Formato exato da apresentação WhatsApp.
- Validações defensivas (JSON malformado, lista de exercícios vazia, etc).
- Posição correta da tool def e das funções no `claude_service.py`.

---

## Riscos identificados

- **IA retorna JSON malformado** → validação defensiva + fallback "não consegui gerar, tenta de novo".
- **IA propõe exercício conflitando com lesão do perfil** → validação mínima cruzando com `perfil.lesoes`.
- **Saldo Anthropic** — sem limite no MVP, monitorar uso. Bot já parou 2x por créditos zerados.
- **Atomicidade do save** — 1 `commit()` único no final do handler de SIM.

---

## Estimativa

| Sub-etapa | Tamanho aproximado | Rodadas planejamento+edits+teste |
|---|---|---|
| E3b1 | ~100-200 linhas novas | 2-3 |
| E3b2 | ~50-100 linhas | 1-2 |
| E3b3 | ~50-100 linhas | 1-2 |
| E3c | ~50-100 linhas | 1-2 |
| **Total E3 (b1+b2+b3+c)** | **~250-500 linhas** | **5-9 rodadas** |

---

## Próximo passo concreto

Recon do padrão de IA-com-tool existente. Comando pronto pra colar no Claude Code:

```
! cd "/c/Users/Igor Hanate/Desktop/EvolutionFitIA" && ( echo "=== A. marcadores tool/anthropic ==="; grep -nE "salvar_treino_estruturado|tool_choice|AsyncAnthropic|client\.messages\.create|\"name\":\s*\"[a-z_]+\"" app/services/claude_service.py | head -50; echo; echo "=== B. defs treino/gerar/salvar/process_tool ==="; grep -nE "^def |^async def " app/services/claude_service.py | grep -iE "treino|gerar|propor|salvar|process_tool" | head -30; echo; echo "=== C. _gerar_treino_de_dados ==="; grep -n "_gerar_treino_de_dados" app/services/claude_service.py ) > /tmp/iarecon.txt ; cp /tmp/iarecon.txt "/c/Users/Igor Hanate/Desktop/iarecon.txt" ; wc -l /tmp/iarecon.txt
```

Anexa o `iarecon.txt` na próxima sessão. Com base nas linhas que aparecerem, peço janelas específicas via `awk` pra ver o schema da tool existente, a função de geração, e a inicialização do AsyncAnthropic. Depois desenho os edits do E3b1.
