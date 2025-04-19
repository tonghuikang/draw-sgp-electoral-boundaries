import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.score_assignments import score_assignment, validate_assignment, load_json, save_json, calculate_relevance, score_assignment_file


assignment_data = load_json("assignments/official_ge_2025.json")
assignments = assignment_data["assignment"]
assignment_data["assignment_name"] = "With local optimization"
assignment_filename = "local_swap.json"
assignment_filepath = os.path.join("assignments", assignment_filename)

adjacency_data = load_json("intermediate_data/ge2025_polling_districts_to_adjacent_districts.json")

possible_constituency_names = list(pd.read_csv("raw_data/mrt_stations.csv")["name"])

best_score = score_assignment(assignment_data)["overall_score"]

adjacency_pairs = set()
for polling_district, polling_districts in adjacency_data.items():
    for polling_district_other in polling_districts:
        adjacency_pairs.add((polling_district, polling_district_other))

for iteration in range(10):
    seen_constituency_names = set()
    for assignment_idx in range(len(assignments)):
        initial_constituency_name = best_constituency_name = assignments[assignment_idx]["constituency_name"]
        for initial_constituency_name_part in initial_constituency_name.split("-"):
            seen_constituency_names.add(initial_constituency_name_part)

    for assignment_idx in range(len(assignments)):
        polling_districts = assignments[assignment_idx]["polling_districts"]
        initial_constituency_name = best_constituency_name = assignments[assignment_idx]["constituency_name"]
        best_relevance = calculate_relevance(best_constituency_name, tuple(polling_districts))
        for possible_constituency_name in possible_constituency_names:
            if possible_constituency_name in seen_constituency_names:
                continue
            relevance = calculate_relevance(possible_constituency_name, tuple(polling_districts))
            if relevance > best_relevance:
                best_relevance = relevance
                best_constituency_name = possible_constituency_name
        if initial_constituency_name != best_constituency_name:
            print(f"Replacing name {initial_constituency_name} with name {best_constituency_name}")
            assignments[assignment_idx]["constituency_name"] = best_constituency_name
            seen_constituency_names.add(best_constituency_name)
            validated, _ = validate_assignment(assignment_data)
            assert validated
            score = score_assignment(assignment_data)["overall_score"]
            print("Current score", score)

    elector_balance_and_assignment_idx = []
    for assignment_idx, annotation in enumerate(score_assignment(assignment_data)["annotations"]):
        elector_balance_and_assignment_idx.append((annotation["elector_balance"], assignment_idx))
    elector_balance_and_assignment_idx.sort()

    early_termination = elector_balance_and_assignment_idx[0][0] == score_assignment(assignment_data)["overall_score"]
    print(f"iteration {iteration}, early_termination {early_termination}")

    for _, assignment_idx_1 in elector_balance_and_assignment_idx:
        for _, assignment_idx_2 in elector_balance_and_assignment_idx:
            if assignment_idx_1 == assignment_idx_2:
                continue
            constituency_name_1 = assignments[assignment_idx_1]["constituency_name"]
            constituency_name_2 = assignments[assignment_idx_2]["constituency_name"]
            for pair_iteration in range(10):
                print(f"{constituency_name_1} {constituency_name_2} - iteration {pair_iteration}")
                pairs_tried = set()

                best_score = score_assignment(assignment_data)["overall_score"]
                best_move_1_to_2 = []
                best_move_2_to_1 = []

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

                polling_districts_1_for_consideration = list(polling_districts_1_for_consideration)
                polling_districts_2_for_consideration = list(polling_districts_2_for_consideration)

                improvement_found = False
                for a in polling_districts_1_for_consideration:
                    polling_districts_1.remove(a)
                    polling_districts_2.append(a)
                    validated, _ = validate_assignment(assignment_data)
                    if validated:
                        score = score_assignment(assignment_data)["overall_score"]
                        if score > best_score:
                            print(f"Considering {score} after moving {a} from {constituency_name_1} to {constituency_name_2}")
                            improvement_found = True
                            best_score = score
                            best_move_1_to_2 = [a]
                    polling_districts_1.append(a)
                    polling_districts_2.remove(a)

                for a in polling_districts_1_for_consideration:
                    for b in polling_districts_2_for_consideration:
                        if (a, b) in pairs_tried:
                            continue
                        polling_districts_1.remove(a)
                        polling_districts_1.append(b)
                        polling_districts_2.remove(b)
                        polling_districts_2.append(a)
                        validated, _ = validate_assignment(assignment_data)
                        if validated:
                            score = score_assignment(assignment_data)["overall_score"]
                            if score > best_score:
                                print(f"Considering {score} after swapping {a} from {constituency_name_1} with {b} from {constituency_name_2}")
                                improvement_found = True
                                best_score = score
                                best_move_1_to_2 = [a]
                                best_move_2_to_1 = [b]
                        else:
                            pairs_tried.add((a, b))
                            pairs_tried.add((b, a))
                        polling_districts_1.remove(b)
                        polling_districts_1.append(a)
                        polling_districts_2.remove(a)
                        polling_districts_2.append(b)

                if improvement_found:
                    for a in best_move_1_to_2:
                        print(f"Moving {a} from {constituency_name_1} to {constituency_name_2}")
                        polling_districts_1.remove(a)
                        polling_districts_2.append(a)
                    for b in best_move_2_to_1:
                        print(f"Moving {b} from {constituency_name_1} to {constituency_name_2}")
                        polling_districts_2.remove(b)
                        polling_districts_1.append(b)
                    save_json(assignment_data, assignment_filepath)
                    score_assignment_file(assignment_filename)

                if not improvement_found:
                    break

        if early_termination:
            break
