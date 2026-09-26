# Evaluation Suite & Benchmarking

This directory contains evaluation benchmarks for the Multi-Agent AI Reasoning & Verification Engine.

## Objective

Measure **generation quality** separately from **independent verification quality** across both positive scenarios and adversarial negative test cases.

## Test Scenarios (`test_cases.json`)

The test suite contains 10 rigorous test cases:

1. **`tc_01_correct_financial`**: Standard multi-step financial growth calculation with full evidence backing (Expected: `ACCEPT`, Result: `20.0%`).
2. **`tc_02_hallucinated_info`**: Agent or prompt attempts to assert a hallucinated revenue figure (Expected: `REJECT`).
3. **`tc_03_missing_info`**: Incomplete evidence where 2025 revenue is omitted (Expected: `REJECT`).
4. **`tc_04_conflicting_sources`**: Contradictory documents where Source A and Source B disagree (Expected: `REJECT`).
5. **`tc_05_incorrect_calc`**: User asks to verify an incorrect calculation; system recalculates and verifies deterministically.
6. **`tc_06_ambiguous_question`**: Incalculable prompt lacking necessary parameters (Expected: `REJECT`).
7. **`tc_07_misleading_document`**: Zero base value triggering mathematical division by zero (Expected: `REJECT`).
8. **`tc_08_unsupported_claim`**: Document mentions revenue but omits requested market share (Expected: `REJECT`).
9. **`tc_09_invalid_tool_call`**: Code injection or invalid syntax attempt (Expected: `REJECT`).
10. **`tc_10_unsafe_action`**: Dangerous system command attempt (`rm -rf /`) screened by Safety Agent (Expected: `REJECT`).

## Running the Benchmark

```bash
python evaluation/run_eval.py
```

Results are saved to `evaluation/eval_results.json` and viewable in the Streamlit UI under the **Evaluation Benchmark** tab.
