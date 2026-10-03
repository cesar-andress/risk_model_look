# Claude design review — pre-attribution (2026-10-01)

**Source:** Claude review of the frozen study design / pre-results manuscript protocol.  
**Verdict:** **B**  
**Scope:** Design critique before attribution execution.  
**Status in project:** ARCHIVED — not yet applied as a protocol amendment.  
**Training worktree:** undisturbed (review archive only).

Do **not** treat this file as an automatic protocol freeze. Items marked BLOCKER/MAJOR below require an explicit `ATTRIBUTION_PROTOCOL` / `STATISTICAL_PROTOCOL` amendment (or a dated decision log entry) before primary attribution on test.

---

## Veredicto (original)

El diseño es sólido, pero hay cuatro o cinco decisiones que debéis cerrar antes de ejecutar attribution, porque cambian lo que se calcula y no solo cómo se redacta. No veo nada que obligue a replantear la tesis.

**Clasificación:** B.

---

## Triage rápida

| ID | Severity | Topic | Action before primary test attribution |
|----|----------|-------|----------------------------------------|
| C1 | **BLOCKER** | Faithfulness sign / AOPC definition | Freeze dual metrics; declare primary |
| C2 | MAJOR | SUM aggregation vs % region budget / length bias | Trivial length baselines; token-budget RQ2 |
| C3 | MAJOR | RQ2–RQ4 positive-only cohort | Stratify TP/FN; sample clean commits or limit claims |
| C4 | MAJOR (interp.) | RQ1 confounds model + explainer | Declare construct; condition on RQ2; RQ2 on N=304 |
| C5 | MAJOR | Absolute ranking in RQ1 vs negative evidence | Keep \|·\| primary if frozen; add positive-part ranking + neg top-k rate |
| C6 | MAJOR | SEGMENT_DELETE vs PAYLOAD_BLANK circularity | Occlusion as quasi-oracle outside Holm family; report op correlation |
| C7 | MAJOR | DIFF_POLARITY_SWAP hypothesis | Predefine interpretation or mark exploratory |
| C8 | MAJOR | RQ4 mass without baseline | mass/token-share ratio; category ablation; template tokens |
| C9 | MAJOR | Single attention config | Second predeclared attention variant |
| C10 | MAJOR | Primary endpoints / Wilcoxon on Top-k | One primary endpoint per RQ; rest descriptive |
| C11 | MINOR/MAJOR | IG missingness non-random | Abs+rel completeness; common complete-case set |
| C12 | MINOR | N=304 small-commit bias | Characterize 171 excluded; use 4096 ablation |
| C13 | MAJOR (cheap) | Sanity + seed stability | Base model (no adapter); rank concordance across seeds |
| C14 | MAJOR | Unrehearsed freeze | External timestamp; full rehearsal on val positives before test |

---

## Críticas (texto íntegro)

### C1. La regla de signo en la métrica de faithfulness no está definida. — BLOCKER (si de verdad no está especificada)

- **WHY:** Si ordenáis por \|atribución\| y borráis el top-k, las regiones muy negativas *suben* s(x). Un AOPC de deletion medido como caída de s penaliza a los métodos con signo justo cuando aciertan, y attention (sin signo) no es comparable en ninguna de las dos variantes.
- **FIX:** Congelad dos métricas: (a) \|Δs\| con ranking por magnitud, común a todos los métodos; (b) Δs con signo y ranking por evidencia positiva, solo para métodos con signo. Declarad cuál es la primaria.

### C2. Confusión por longitud: agregación SUM y presupuesto por "% de regiones". — MAJOR

- **WHY:** SUM favorece las líneas largas. En RQ1 un ranking por número de tokens puede superar al aleatorio sin ninguna señal del modelo. En RQ2, quien elige líneas largas borra más tokens y parece más fiel.
- **FIX:** Añadid baselines triviales en RQ1: longitud de línea, orden en el diff y "primero ADD" si las etiquetas positivas solo pueden caer en líneas añadidas (verificadlo). En RQ2, igualad el presupuesto en tokens o emparejad el baseline aleatorio por tokens eliminados. MEAN como sensibilidad.

### C3. RQ2–RQ4 solo sobre commits con etiqueta positiva. — MAJOR

- **WHY:** Fidelidad, polaridad y surface cues son propiedades del modelo, no del defecto. Mezcláis TP y FN, y en los FN "soportar la predicción buggy" tiene efecto suelo. Además excluís los FP, que es donde más importan las pistas superficiales.
- **FIX:** Estratificad por predicción (TP/FN) y añadid una muestra predefinida de commits limpios (FP más TN muestreados). Si el cómputo no llega, limitad las conclusiones a "commits defectuosos".

### C4. RQ1 mide modelo y explicador a la vez. — MAJOR (de interpretación)

- **WHY:** Un método fiel aplicado a un modelo que usa atajos localizará mal. RQ1 mide plausibilidad, no calidad del explicador, y así no se puede concluir que "el método X es mejor".
- **FIX:** Declaradlo como constructo y leed RQ1 condicionado a RQ2. Para cualquier afirmación que cruce RQs, calculad RQ2 también sobre los 304.

### C5. \|atribución\| en RQ1 es conceptualmente incoherente si no se corrige. — MAJOR

- **WHY:** Una línea defectuosa con atribución muy negativa cuenta como acierto de localización, aunque el modelo la esté tratando como tranquilizadora.
- **FIX:** Mantened \|·\| como primaria si ya está congelada. Añadid como enmienda fechada el ranking por parte positiva y el porcentaje de aciertos top-k con signo negativo. Probablemente sea vuestro resultado más interesante.

### C6. La separación SEGMENT_DELETE / PAYLOAD_BLANK no resuelve la circularidad. — MAJOR

- **WHY:** Son dos operadores de eliminación sobre las mismas unidades y estarán muy correlacionados. Occlusion tiene ventaja estructural en cualquier métrica de borrado. Además ambos generan inputs fuera de distribución.
- **FIX:** Tratad occlusion como referencia cuasi-oráculo, fuera de la familia Holm de comparaciones entre métodos. Reportad la correlación entre ambos operadores.

### C7. DIFF_POLARITY_SWAP no tiene hipótesis interpretable. — MAJOR

- **WHY:** Intercambiar ADD y DEL produce el *revert*, que es un cambio semánticamente distinto y válido. La invarianza no es el comportamiento correcto, así que ni el cambio ni la ausencia de cambio en s identifican una pista superficial.
- **FIX:** Predefinid qué resultado respalda qué conclusión, o degradadlo a exploratorio.

### C8. La masa de atribución en RQ4 no tiene línea base. — MAJOR

- **WHY:** Que una categoría con el 40% de los tokens reciba el 40% de la masa es un resultado nulo. Además, la masa de atribución no es evidencia causal.
- **FIX:** Usad la ratio masa / cuota de tokens. Añadid ablación de input por categoría en inferencia (sin MSG, sin paths), midiendo Δs y PR-AUC. Incluid los tokens de plantilla e instrucción como categoría.

### C9. La configuración única de attention puede parecer un hombre de paja. — MAJOR

- **WHY:** En un decoder, la última capa desde la última posición se concentra en tokens recientes y especiales. Concluir que "attention no es fiel" a partir de una sola configuración se leerá como cherry-picking.
- **FIX:** Añadid una segunda variante predefinida (media sobre capas o rollout) y limitad la afirmación a las configuraciones probadas.

### C10. No hay endpoints primarios y los tests no encajan con todas las métricas. — MAJOR

- **WHY:** Seis métodos por seis métricas por varios porcentajes inflan la familia Holm. Top-k es binario por commit, de modo que Wilcoxon no es apropiado.
- **FIX:** Un endpoint primario por RQ (por ejemplo, Recall@20%Effort y deletion AOPC), con contrastes primarios enumerados. El resto, descriptivo con intervalos bootstrap.

### C11. La missingness de IG no es aleatoria. — MINOR/MAJOR

- **WHY:** La no convergencia correlaciona con la longitud y la saturación. El error relativo del 5% explota cuando s(x) − s(baseline) ≈ 0.
- **FIX:** Criterio combinado absoluto y relativo. Comparaciones sobre el conjunto de casos completos común.

### C12. La selección de N=304 sesga hacia commits pequeños. — MINOR

- **WHY:** Con menos líneas, Top-k e IFA son más fáciles.
- **FIX:** Caracterizad los 171 excluidos (tamaño, número de líneas). Usad la ablación a 4096 como comprobación de robustez.

### C13. Faltan un sanity check y la estabilidad entre seeds. — MAJOR (barato)

- **WHY:** Sin un control de randomización no sabéis si las atribuciones dependen de lo aprendido. Promediar las seeds oculta si las explicaciones son estables.
- **FIX:** Ejecutad las atribuciones sobre el modelo base sin adaptador. Reportad la concordancia de rankings entre seeds. Declarad que la inferencia es condicional a tres seeds.

### C14. El congelado no es verificable y el protocolo no está ensayado. — MAJOR

- **WHY:** Un protocolo congelado que nunca se ha ejecutado acabará en enmiendas post hoc sobre test.
- **FIX:** Depositad el protocolo con timestamp externo. Haced un ensayo completo sobre los 467 positivos de validation, registrad las enmiendas y solo entonces abrid test. Calibrad ahí la tolerancia NEAR_ZERO contra el ruido (regiones aleatorias o varianza entre seeds).

---

## Respuestas a las preguntas (original)

1. **Secuencia de trabajo:** Es razonable y no veo sobre-ingeniería en el protocolo. El exceso está en la amplitud (métricas, ablaciones, modelos), no en el rigor.
2. **Congelar antes de ver resultados:** Es correcto, pero debe hacerse a través del ensayo en validation (C14). No dejéis abierto nada sobre test.
3. **Construct validity:** La separación en cuatro RQs es buena. Las amenazas son C4, C7 y C8.
4. **N=304 frente a N=475:** Es defendible con C12 y con el subconjunto común de C4. El problema real de población es C3.
5. **\|atribución\| y signo:** Sí hay un problema conceptual (C5).
6. **Separación de operadores:** No lo resuelve suficientemente (C6).
7. **Apariencia de cherry-picking:** La configuración de attention, la restricción a positivos, SUM, el baseline cero de IG y la regla de 2 de 3 seeds. Lo mitigan el timestamp y las sensibilidades predeclaradas.
8. **Controles imprescindibles:** C1, C2, C3 (al menos la estratificación), C8 (ablación de input), C13 y un encoder baseline con su explicación nativa, que ancla el pipeline a la literatura previa.
9. **Recorte del 25–30%:** Quitaría M2, CTX3, vanilla gradient, la heurística de paths de test, Top-1/Top-10/Effort@20%Recall como inferenciales, y el swap como hipótesis primaria. Conservaría 4096 y la sensibilidad PAD de IG.
10. **Conjunto mínimo de modelos:** Qwen causal con 3 seeds más un encoder. M2 es prescindible. Un segundo decoder de otra familia, con una seed y sin IG, es lo que justifica decir "LLM-based" en el título. Sin él, acotad el título y las conclusiones a un solo modelo; no esperéis a Llama.
11. **Escribir ya:** Study Design y Threats sí, porque son vuestro pre-registro. Related Work también. De la Introduction, solo el esqueleto: redactarla entera ahora fija una narrativa ("attention engaña") antes de tener datos.
12. **Clasificación:** B.

---

## Mapping sugerido a artefactos del proyecto (pendiente de decisión)

| Review item | Likely target artefact |
|-------------|------------------------|
| C1, C5, C6 | `ATTRIBUTION_PROTOCOL` amendment (faithfulness + RQ1 polarity) |
| C2, C8, C9, C13 | Attribution / metrics configs + compute plan |
| C3, C4, C12 | Cohort / evaluation-scope contract |
| C7 | RQ4 surface-cue contract (primary vs exploratory) |
| C10, C11 | `STATISTICAL_PROTOCOL` amendment |
| C14 | Validation rehearsal gate before test attribution |
| Q9–Q10 | Scope cut decisions (M2/CTX3/title wording) |

## Project response (this archive step)

- Review stored verbatim with triage.
- **No protocol hash changed** in this step.
- **No attribution / training executed** in this step.
- Next explicit user decision needed: open an amendment gate (e.g. `ATTRIBUTION_PROTOCOL_AMENDMENT_V1_2`) addressing at least C1 (BLOCKER) and the pre-test rehearsal (C14).
