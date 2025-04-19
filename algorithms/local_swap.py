import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.score_assignments import score_assignment, validate_assignment, load_json, save_json


assignment_data = load_json("assignments/official_ge_2025.json")
assignments = assignment_data["assignment"]
assignment_data["assignment_name"] = "With local optimization"

adjacency_data = load_json("intermediate_data/ge2025_polling_districts_to_adjacent_districts.json")


best_score = score_assignment(assignment_data)["overall_score"]

adjacency_pairs = set()
for polling_district, polling_districts in adjacency_data.items():
    for polling_district_other in polling_districts:
        adjacency_pairs.add((polling_district, polling_district_other))

pairs_tried = set()

for iteration in range(3):
    print(f"iteration {iteration}")
    for assignment_idx_1 in range(len(assignments)):
        for assignment_idx_2 in range(assignment_idx_1 + 1, len(assignments)):
            constituency_name_1 = assignments[assignment_idx_1]["constituency_name"]
            constituency_name_2 = assignments[assignment_idx_2]["constituency_name"]
            polling_districts_1: list[str] = assignments[assignment_idx_1]["polling_districts"]
            polling_districts_2: list[str] = assignments[assignment_idx_2]["polling_districts"]
            polling_districts_1_set = set(polling_districts_1)
            polling_districts_2_set = set(polling_districts_2)

            polling_districts_1_for_consideration = set()
            polling_districts_2_for_consideration = set()
            for a in polling_districts_1:
                for b in adjacency_data[a]:
                    if b in polling_districts_2_set:
                        polling_districts_1_for_consideration.add(a)
                        polling_districts_2_for_consideration.add(b)

            # don't consider all pairs
            polling_districts_1_for_consideration = list(polling_districts_1_for_consideration)[::1 + len(polling_districts_1_for_consideration) // 5]
            polling_districts_2_for_consideration = list(polling_districts_2_for_consideration)[::1 + len(polling_districts_2_for_consideration) // 5]

            escape = False
            for a in polling_districts_1_for_consideration:
                if escape:
                    break
                polling_districts_1.remove(a)
                polling_districts_2.append(a)
                validated, _ = validate_assignment(assignment_data)
                if validated:
                    score = score_assignment(assignment_data)["overall_score"]
                    if score > best_score:
                        print(f"{score} after moving {a} from {constituency_name_1} to {constituency_name_2}")
                        best_score = score
                        save_json(assignment_data, "assignments/local_swap.json")
                        escape = True
                        continue
                polling_districts_1.append(a)
                polling_districts_2.remove(a)

            for a in polling_districts_1_for_consideration:
                if escape:
                    break
                for b in polling_districts_2_for_consideration:
                    if escape:
                        break
                    if (a,b) in pairs_tried:
                        continue
                    pairs_tried.add((a,b))
                    pairs_tried.add((b,a))
                    polling_districts_1.remove(a)
                    polling_districts_1.append(b)
                    polling_districts_2.remove(b)
                    polling_districts_2.append(a)
                    validated, _ = validate_assignment(assignment_data)
                    if validated:
                        score = score_assignment(assignment_data)["overall_score"]
                        if score > best_score:
                            print(f"{score} after swapping {a} from {constituency_name_1} with {b} from {constituency_name_2}")
                            best_score = score
                            save_json(assignment_data, "assignments/local_swap.json")
                            escape = True
                            continue
                    polling_districts_1.remove(b)
                    polling_districts_1.append(a)
                    polling_districts_2.remove(a)
                    polling_districts_2.append(b)
