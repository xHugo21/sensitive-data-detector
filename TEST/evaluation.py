import json
import re

# 📂 Cargar detecciones del modelo
#json_filename = f"LLAMA4_Scout/pii_detection_sample_llama4_scout_Groq_1000_ZS_enriquecido.json"
#json_filename = f"GPT-OSS-120b/pii_detection_sample_gpt-oss-120b_Groq_paid_1000_ZS_enriquecido.json"
json_filename = f"GPT-4o-MINI/pii_detection_sample_gpt_4o_mini_1000_ZS_enriquecido.json"
#json_filename = f"GEMINI/pii_detection_sample_Gemini_1.5_pro_ZS_1000.json"
with open(json_filename, "r", encoding="utf-8") as f:
    model_results = {str(entry["id"]): entry for entry in json.load(f)}

# 📄 Cargar dataset
with open("english_pii_43k.jsonl", "r", encoding="utf-8") as f:
    dataset_entries = [json.loads(next(f)) for _ in range(1000)]

# ⚙️ Modo para mostrar solo entradas con falsos positivos
SHOW_ONLY_FALSE_POSITIVES = False  # Cambiar a True para ver solo entradas con falsos positivos

# 🔧 Normalización de texto
def normalize_text(text):
    return re.sub(r'[\W_]+', '', text.lower())

# ✅ Coincidencia parcial por valor (con logging)
def match(pred, gold, verbose=False):
    pred_value = pred["value"]
    gold_value = gold["value"]
    pred_text = normalize_text(pred_value)
    gold_text = normalize_text(gold_value)

    if verbose:
        print(f"\n🧩 Comparando predicción: \"{pred_value}\" con etiqueta real: \"{gold_value}\"")
        print(f"🔎 Normalizado: pred=\"{pred_text}\" | gold=\"{gold_text}\"")

    if gold_text in pred_text:
        if verbose: print("✅ Match por: gold_text in pred_text")
        return True
    if pred_text in gold_text:
        if verbose: print("✅ Match por: pred_text in gold_text")
        return True
    if pred_value.lower() in gold_value.lower():
        if verbose: print("✅ Match por: pred_value.lower() in gold_value.lower()")
        return True
    if gold_value.lower() in pred_value.lower():
        if verbose: print("✅ Match por: gold_value.lower() in pred_value.lower()")
        return True

    if verbose:
        print("❌ No hacen match.")
    return False

# 🚫 Detectar si una predicción está contenida dentro de otra ya emparejada
def is_redundant(pred, matched_preds):
    for m in matched_preds:
        if pred["start"] >= m["start"] and pred["end"] <= m["end"]:
            if normalize_text(pred["value"]) in normalize_text(m["value"]):
                return True
    return False

# 🧪 Evaluación
def evaluate(dataset_entries, model_results):
    total_gold = 0
    total_matched = 0
    false_negatives = []
    false_positives = []
    inferred_count = 0
    inferred_examples = []


    for entry in dataset_entries:
        entry_id = str(entry["id"])
        source_text = entry["source_text"]
        gold = entry["privacy_mask"]
        pred = model_results.get(entry_id, {}).get("predicted_labels", [])

        matched_gold_flags = [False] * len(gold)
        matched_pred_flags = [False] * len(pred)

        for i, g in enumerate(gold):
            for j, p in enumerate(pred):
                if match(p, g, verbose=False):
                    matched_gold_flags[i] = True
                    matched_pred_flags[j] = True

        matched_preds = [pred[j] for j, matched in enumerate(matched_pred_flags) if matched]

        # 🧩 Evaluar falsos positivos en esta entrada
        current_false_positives = [
            {**p, "entry_id": entry_id, "text": source_text}
            for j, p in enumerate(pred)
            if not matched_pred_flags[j] and not is_redundant(p, matched_preds)
        ]

        if SHOW_ONLY_FALSE_POSITIVES and not current_false_positives:
            continue  # ⛔ Saltar entrada si no hay falsos positivos

        # Mostrar entrada
        print(f"\n🔍 Entrada #{entry_id}")
        print("📄 Texto:")
        #print(source_text)
        SHOW_ONLY_INFERRED = False  # True para mostrar solo predicciones inferidas

        print("\n📌 Anotaciones reales (dataset):")
        for g in gold:
            print(f"  - {g['label']}: \"{g['value']}\" [start={g['start']}, end={g['end']}]")

        print("\n🤖 Predicciones del modelo:")
        if pred:
            for j, p in enumerate(pred):
                if SHOW_ONLY_INFERRED and p.get("source", "").strip().lower() != "inferred":
                    continue  # saltar si no es inferida

                if matched_pred_flags[j]:
                    status = "True Positive ✅"
                elif not is_redundant(p, matched_preds):
                    status = "False Positive ❌"
                    false_positives.append({**p, "entry_id": entry_id, "text": source_text})
                else:
                    status = "Redundant ⚠️"

                if p.get("source", "").strip().lower() == "inferred":
                    status += " (Inferred)"

                print(f"  - {p['label']} ({p.get('source', 'N/A')}): \"{p['value']}\" "
                    f"[start={p['start']}, end={p['end']}] → {status}")
        else:
            print("  - Ninguna detectada.")


        for i, matched in enumerate(matched_gold_flags):
            if not matched:
                false_negatives.append({**gold[i], "entry_id": entry_id, "text": source_text})

        total_gold += len(gold)
        total_matched += sum(matched_gold_flags)

    # 📊 Métricas
    precision = total_matched / (total_matched + len(false_positives)) if (total_matched + len(false_positives)) else 0
    recall = total_matched / total_gold if total_gold else 0
    f1 = 2 * precision * recall / (precision + recall + 1e-9) if (precision + recall) else 0

    print(f"\n✅ Total etiquetas en el dataset (gold): {total_gold}")
    print(f"✅ Total correctamente detectadas (true positives): {total_matched}")
    print(f"❌ No detectadas (false negatives): {len(false_negatives)}")
    print(f"⚠️ Falsos positivos (detecciones incorrectas): {len(false_positives)}")

    print(f"\n📊 Métricas para :")
    print(f"   🔹 Precision: {precision:.4f}")
    print(f"   🔹 Recall:    {recall:.4f}")
    print(f"   🔹 F1 Score:  {f1:.4f}")

    print(f"\n🧠 Inferred detections ({inferred_count} total):")
    for example in inferred_examples:
        p = example["detection"]
        print(f"\n🔹 Entry #{example['entry_id']}")
        print(f"📝 Text: {example['text']}")
        print(f"🔍 Inferred: {p['label']}: \"{p['value']}\" [start={p['start']}, end={p['end']}]")


    
    from collections import defaultdict

    fp_by_entry = defaultdict(list)
    for fp in false_positives:
        fp_by_entry[fp["entry_id"]].append(fp)


    with open(f"false_positive_conversations_.txt", "w", encoding="utf-8") as out_f:
        for entry_id, fps in fp_by_entry.items():
            entry = model_results[entry_id]
            dataset_entry = next((e for e in dataset_entries if str(e["id"]) == entry_id), None)
            if not dataset_entry:
                continue

            source_text = dataset_entry["source_text"]
            gold_labels = dataset_entry["privacy_mask"]
            predicted = entry.get("predicted_labels", [])

            out_f.write(f"\n🔹 Entry #{entry_id}\n")
            out_f.write(f"📝 Text:\n{source_text}\n\n")

            out_f.write(f"✅ Ground truth annotations:\n")
            for g in gold_labels:
                out_f.write(f"  - {g['label']}: \"{g['value']}\" [start={g['start']}, end={g['end']}]\n")

            # Determinar estado de cada predicción
            matched_gold_flags = [False] * len(gold_labels)
            matched_pred_flags = [False] * len(predicted)
            matched_preds = []

            for i, g in enumerate(gold_labels):
                for j, p in enumerate(predicted):
                    if match(p, g):
                        matched_gold_flags[i] = True
                        matched_pred_flags[j] = True

            matched_preds = [predicted[j] for j, matched in enumerate(matched_pred_flags) if matched]

            out_f.write(f"\n🤖 Detections by :\n")
            for j, p in enumerate(predicted):
                label = p.get("label", p.get("field", "UNKNOWN"))
                value = p["value"]
                source = p.get("source", "N/A")
                status = ""

                if matched_pred_flags[j]:
                    status = "True Positive ✅"
                elif not is_redundant(p, matched_preds):
                    status = "False Positive ❌"
                else:
                    status = "Redundant ⚠️"

                if source.lower() == "inferred":
                    status += " (Inferred)"

                out_f.write(f"  - {label}: \"{value}\" [start={p['start']}, end={p['end']}] → {status}\n")

            out_f.write("\n" + "-"*80 + "\n")



    print(f"\n⚠️ Falsos positivos detectados por :")
    for fp in false_positives:
        print(f"- Entrada #{fp['entry_id']} | {fp['label']} ({fp.get('source', 'N/A')}): \"{fp['value']}\" [start={fp['start']}, end={fp['end']}]")

    print(f"\n🚫 PII del dataset NO detectados por :")
    for fn in false_negatives:
        print(f"- Entrada #{fn['entry_id']} | {fn['label']}: \"{fn['value']}\" [start={fn['start']}, end={fn['end']}]")

# ▶ Ejecutar evaluación
evaluate(dataset_entries, model_results)
