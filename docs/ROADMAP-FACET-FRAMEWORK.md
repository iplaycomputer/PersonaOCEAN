# PersonaOCEAN — Facet Framework Expansion

**Milestone:** `v0.5.0 – Facet Framework Release`
**Goal:** Move PersonaOCEAN from domain-level OCEAN scoring to a facet-enriched model grounded in validated Big Five theory, enabling more psychologically credible archetypes and transparent math.

---

## 1. Scientific Foundation

| Layer                  | Core References                                                 | Purpose                                                |
| ---------------------- | --------------------------------------------------------------- | ------------------------------------------------------ |
| **Big Five Domains**   | Costa & McCrae (1992), Goldberg (1993)                          | Standard OCEAN structure                               |
| **Facet Structure**    | DeYoung et al. (2007); Soto & John (2017)                       | Adds depth and predictive power                        |
| **Moderation Theory**  | Curşeu et al. (2018); Pierce & Aguinis (2013)                   | Supports inverted-U “moderate expression” for team fit |
| **Behavioral Anchors** | Hogan (2001); Barrick & Mount (1991)                            | Ties archetypes to work behavior                       |
| **Data Source**        | [`rubynor/bigfive-web`](https://github.com/rubynor/bigfive-web) | Open-source IPIP-NEO 120 facet definitions             |

---

## 2. Architecture Overview

### Core Components

| Component                       | New / Modified | Purpose                                          |
| ------------------------------- | -------------- | ------------------------------------------------ |
| `facets.py`                     | New            | Defines facet schema and normalization           |
| `roles.yaml`                    | Modified       | Supports optional facet-level weighting          |
| `validate_roles.py`             | Modified       | Validates facet key accuracy                     |
| `main.py`                       | Modified       | Adds `/import_json` for BigFive-Web results      |
| `docs/SCIENTIFIC_FRAMEWORK.txt` | Expanded       | Records scientific lineage and math transparency |

---

## 3. Facet Schema Alignment

PersonaOCEAN will directly mirror the facet structure from `rubynor/bigfive-web`:

```python
FACET_MAP = {
  "O": ["Imagination", "Artistic interests", "Emotionality", "Adventurousness", "Intellect", "Liberalism"],
  "C": ["Self-efficacy", "Orderliness", "Dutifulness", "Achievement-striving", "Self-discipline", "Cautiousness"],
  "E": ["Friendliness", "Gregariousness", "Assertiveness", "Activity level", "Excitement-seeking", "Cheerfulness"],
  "A": ["Trust", "Morality", "Altruism", "Cooperation", "Modesty", "Sympathy"],
  "N": ["Anxiety", "Anger", "Depression", "Self-consciousness", "Immoderation", "Vulnerability"]
}
```

This ensures consistent naming, scaling, and psychometric provenance.

---

## 4. Data Flow Integration

### User Path

1. User completes test on [`bigfive-web`](https://github.com/rubynor/bigfive-web) or its deployed instance.
2. They export results as JSON.
3. They upload that JSON to PersonaOCEAN using `/import_json`.

### Import Command (Discord)

```python
@bot.tree.command(name="import_json", description="Import Big Five test results (from bigfive-web JSON).")
async def import_json(interaction: discord.Interaction, attachment: discord.Attachment):
    data = json.loads(await attachment.read())
    traits = normalize_traits(data)
    facets = normalize_facets(data)
    companies[guild_id][user_id] = {"traits": traits, "facets": facets}
    await send_safe(interaction, f"Profile imported and normalized for {interaction.user.display_name}.")
```

### Normalization Helpers

```python
def normalize_bigfiveweb(value: float) -> float:
    return (value - 0.5) * 2  # 0–1 → −1..+1

def normalize_facets(data: dict) -> dict:
    out = {}
    for domain, facets in data.get("facets", {}).items():
        for name, val in facets.items():
            out[name.title()] = normalize_bigfiveweb(val)
    return out
```

---

## 5. Role and Archetype Expansion

### Updated YAML Schema

```yaml
roles:
  Innovator:
    pattern: {O: 0.9, C: 0.2, E: 0.3, A: 0.2, N: -0.3}
    facet_pattern:
      Imagination: 0.9
      Intellect: 0.8
      Liberalism: 0.7
      Cautiousness: -0.4
    signature_traits:
      - High Openness (Imagination, Intellect)
      - Moderate Extraversion
      - Low Neuroticism
    behavioral_anchors:
      - Generates and reframes new concepts.
      - Thrives in flexible, idea-rich environments.
    dept: Creative & R&D
    desc: Constantly generates fresh ideas and sparks creative change.
```

### Matching Logic

```python
def match_role(traits, facets, roles):
    best_role, best_score = None, -999
    for name, role in roles.items():
        d_score = dot(traits, role["pattern"])
        f_score = dot(facets, role.get("facet_pattern", {}))
        combined = 0.7 * d_score + 0.3 * f_score
        if combined > best_score:
            best_role, best_score = name, combined
    return best_role
```

---

## 6. Archetype Redesign Sprint

| Archetype  | Department     | Psychological Focus                              | Notes        |
| ---------- | -------------- | ------------------------------------------------ | ------------ |
| Innovator  | Creative & R&D | High O facets (Imagination, Intellect)           | Prototype #1 |
| Analyst    | Quality & Risk | High C, low E facets (Orderliness, Cautiousness) | Prototype #2 |
| Supporter  | Community & HR | High A facets (Altruism, Sympathy)               | Prototype #3 |
| Strategist | Management     | High Intellect + Achievement-Striving            | Prototype #4 |
| Executor   | Operations     | High Dutifulness + Self-Discipline               | Prototype #5 |
| Guardian   | Quality & Risk | High Cautiousness + low Excitement-Seeking       | Prototype #6 |

Each archetype will include:

* **Facet anchors** (2–4)
* **Behavioral sentences** (2–3)
* **Department** assignment
* **Descriptor** text

---

## 7. Validation and Transparency

### Updated `validate_roles.py`

* Warn on unrecognized facet keys.
* Enforce numeric −1..+1 constraints.
* Verify schema integrity with exit codes.

### Documentation Update

Append to `docs/SCIENTIFIC_FRAMEWORK.txt`:

> *Facet-level structure and normalization methods derived from rubynor/bigfive-web (MIT license), which maps to the IPIP-NEO-120 inventory as per Costa & McCrae (1992). PersonaOCEAN reuses this structure to ensure empirical consistency and open reproducibility.*

---

## 8. Milestone Execution Plan

| Step | Deliverable                                 | Status |
| ---- | ------------------------------------------- | ------ |
| 1    | `facets.py` + normalization logic           | 🔲     |
| 2    | `/import_json` command                      | 🔲     |
| 3    | `roles.yaml` schema update                  | 🔲     |
| 4    | Validate logic integration                  | 🔲     |
| 5    | 2–3 facet-rich archetypes implemented       | 🔲     |
| 6    | Documentation (scientific + README updates) | 🔲     |
| 7    | Pilot testing with user feedback            | 🔲     |
| 8    | Public release tag `v0.5.0`                 | 🔲     |

---

## 9. Version Summary

| Version           | Focus                          | Key Additions                                       |
| ----------------- | ------------------------------ | --------------------------------------------------- |
| v0.4.x            | Core OCEAN, in-memory registry | `/ocean`, `/company`, `/summary`                    |
| **v0.5.0 (next)** | Facet Framework                | `/import_json`, facet weighting, archetype redesign |
| v0.6.x (future)   | Adaptive Blended Archetypes    | Continuous interpolation between archetypes         |
| v0.7.x            | Facet Visualizations           | Trait radar and distribution embeds                 |

---

## 10. Expected Outcome

After this milestone:

* PersonaOCEAN becomes **facet-accurate** and **research-aligned**.
* Archetypes become **richer**, more **believable**, and **auditable**.
* Users experience test results that *actually align with personality theory.*
* Future releases can safely expand to **hybrid roles** and **visual analytics** without breaking compatibility.

---

**Branch:** `feature/facet-framework`
**Tag (on release):** `v0.5.0`
**Maintainer Notes:**
All scoring, schema, and test logic remain transparent, auditable, and non-persistent.
Psychological fidelity is prioritized over complexity.
