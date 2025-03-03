========================================================================= short test summary info =========================================================================
FAILED test_graph.py::test_correctness[test_case16] - AssertionError: Metrics: Correctness (GEval) (score: 0.3, threshold: 0.5, strict: False, error: None) failed.
1 failed, 24 passed, 106 warnings in 197.87s (0:03:17)
                                                                               Test Results                                                                                
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Test case                                               ┃ Metric              ┃ Score                                                   ┃ Status ┃ Overall Success Rate ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.7 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output provides more details than the │        │                      │
│                                                         │                     │ expected output, including the company's offerings and  │        │                      │
│                                                         │                     │ contact information. While it doesn't contradict the    │        │                      │
│                                                         │                     │ expected output, it includes a lot of additional        │        │                      │
│                                                         │                     │ information, meriting a score of 7., error=None)        │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output provides the answer and its    │        │                      │
│                                                         │                     │ source, which matches the expected output's answer.     │        │                      │
│                                                         │                     │ Therefore, the actual output follows the evaluation     │        │                      │
│                                                         │                     │ steps., error=None)                                     │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes all information from  │        │                      │
│                                                         │                     │ the expected output, but also adds detail. Therefore,   │        │                      │
│                                                         │                     │ the response receives a score of 10., error=None)       │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes all the details in    │        │                      │
│                                                         │                     │ the expected output, and adds more details about the    │        │                      │
│                                                         │                     │ flood, such as the number of deaths and the height the  │        │                      │
│                                                         │                     │ river rose. Thus, the actual output follows the         │        │                      │
│                                                         │                     │ evaluation steps., error=None)                          │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.7 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output contains the correct answer,   │        │                      │
│                                                         │                     │ "Mud Angels", and provides additional, irrelevant       │        │                      │
│                                                         │                     │ information. The detail included in actual output does  │        │                      │
│                                                         │                     │ not contradict the expected output., error=None)        │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output contains the correct full name │        │                      │
│                                                         │                     │ of the Duomo: Cattedrale de Santa Maria del Fiore,      │        │                      │
│                                                         │                     │ which matches the expected output: Cathedral of Santa   │        │                      │
│                                                         │                     │ Maria del Fiore. It also correctly states that it is    │        │                      │
│                                                         │                     │ Florence's most popular site. However, the actual       │        │                      │
│                                                         │                     │ output includes the additional (and unsourced) claim    │        │                      │
│                                                         │                     │ that the Duomo in Florence is the 3rd largest in the    │        │                      │
│                                                         │                     │ world, which was not included in the expected output,   │        │                      │
│                                                         │                     │ but it is not a contradicting fact., error=None)        │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output matches the expected output of │        │                      │
│                                                         │                     │ 463 steps to reach the top of Brunelleschi's Dome in    │        │                      │
│                                                         │                     │ the Duomo., error=None)                                 │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes all the facts from    │        │                      │
│                                                         │                     │ the expected output and provides additional correct     │        │                      │
│                                                         │                     │ details about the bridge's history and current          │        │                      │
│                                                         │                     │ offerings, such as when it was built and the view it    │        │                      │
│                                                         │                     │ provides. Therefore, the actual output is comprehensive │        │                      │
│                                                         │                     │ and does not contradict the expected output.,           │        │                      │
│                                                         │                     │ error=None)                                             │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output provides more detail than the  │        │                      │
│                                                         │                     │ expected output, but it doesn't contradict the expected │        │                      │
│                                                         │                     │ output. Thus, while more verbose, it is acceptable.,    │        │                      │
│                                                         │                     │ error=None)                                             │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes all the information   │        │                      │
│                                                         │                     │ in the expected output, but it is wordier. The actual   │        │                      │
│                                                         │                     │ output states that Michelangelo's David is housed in    │        │                      │
│                                                         │                     │ Florence's Galleria dell' Academia., error=None)        │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes all the details in    │        │                      │
│                                                         │                     │ the expected output, such as beautiful gardens,         │        │                      │
│                                                         │                     │ fountains, and a great view of Florence from the Forte  │        │                      │
│                                                         │                     │ Belvedere. The actual output provides additional        │        │                      │
│                                                         │                     │ details, such as the garden's location, opening times,  │        │                      │
│                                                         │                     │ and student discounts. The actual output does not       │        │                      │
│                                                         │                     │ contradict any facts in the expected output.,           │        │                      │
│                                                         │                     │ error=None)                                             │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output provides more detail than the  │        │                      │
│                                                         │                     │ expected output, but it does not contradict any facts.  │        │                      │
│                                                         │                     │ Therefore, the score is high., error=None)              │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output contains all the information   │        │                      │
│                                                         │                     │ in the expected output, but also includes additional    │        │                      │
│                                                         │                     │ details such as it being a great place to go at sunset  │        │                      │
│                                                         │                     │ and that you can bring food and drinks, which are not   │        │                      │
│                                                         │                     │ contradictory. The actual output does not omit any      │        │                      │
│                                                         │                     │ details from the expected output, but includes some of  │        │                      │
│                                                         │                     │ its own., error=None)                                   │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes all the information   │        │                      │
│                                                         │                     │ in the expected output, but it provides significantly   │        │                      │
│                                                         │                     │ more detail, meriting a high score., error=None)        │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.7 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes additional details    │        │                      │
│                                                         │                     │ about a market and the Basilica that are not present in │        │                      │
│                                                         │                     │ the expected output. This omission of detail reduces    │        │                      │
│                                                         │                     │ the score., error=None)                                 │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes all the information   │        │                      │
│                                                         │                     │ in the expected output and adds additional details      │        │                      │
│                                                         │                     │ about the market's offerings and shopping options. The  │        │                      │
│                                                         │                     │ actual output is not contradictory, but it is more      │        │                      │
│                                                         │                     │ detailed, so a high score is appropriate., error=None)  │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 0.0%                 │
│                                                         │ Correctness (GEval) │ 0.3 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ FAILED │                      │
│                                                         │                     │ reason=The actual output omits key details from the     │        │                      │
│                                                         │                     │ expected output, specifically failing to mention pizza, │        │                      │
│                                                         │                     │ pasta, or Tuscan red wine, which are crucial components │        │                      │
│                                                         │                     │ of an Italian experience., error=None)                  │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.7 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes the expected output   │        │                      │
│                                                         │                     │ but also adds extra information, such as the restaurant │        │                      │
│                                                         │                     │ being in the Santo Spirito area of Florence and that it │        │                      │
│                                                         │                     │ is a very inexpensive restaurant. This omission of      │        │                      │
│                                                         │                     │ detail leads to a lower score., error=None)             │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.7 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output provides the restaurant name,  │        │                      │
│                                                         │                     │ 'Trattoria da Mario', which matches the expected        │        │                      │
│                                                         │                     │ output. However, it includes additional, unnecessary    │        │                      │
│                                                         │                     │ information about the address and payment methods. This │        │                      │
│                                                         │                     │ omission of detail impacts the score., error=None)      │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes the address (Via dei  │        │                      │
│                                                         │                     │ Macci 111r) and the time of the performance (9:30), and │        │                      │
│                                                         │                     │ that reservations are required, which is not present in │        │                      │
│                                                         │                     │ the expected output. The actual output is more          │        │                      │
│                                                         │                     │ detailed, but does not contradict the expected output., │        │                      │
│                                                         │                     │ error=None)                                             │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output includes all the information   │        │                      │
│                                                         │                     │ in the expected output, and provides an additional tip, │        │                      │
│                                                         │                     │ which does not contradict the expected output.          │        │                      │
│                                                         │                     │ Therefore, the score is high., error=None)              │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output mirrors the expected output    │        │                      │
│                                                         │                     │ regarding checking the price before ordering,           │        │                      │
│                                                         │                     │ especially near the bridge. It also adds a detail about │        │                      │
│                                                         │                     │ being able to choose more than one flavor if ordering   │        │                      │
│                                                         │                     │ more than one scoop. The actual output does not omit    │        │                      │
│                                                         │                     │ important details., error=None)                         │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output contains all the information   │        │                      │
│                                                         │                     │ in the expected output and provides extra details.      │        │                      │
│                                                         │                     │ Therefore, the score is 10., error=None)                │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 1.0 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output and expected output are        │        │                      │
│                                                         │                     │ essentially the same, with the actual output being      │        │                      │
│                                                         │                     │ slightly more concise. Therefore, it follows the        │        │                      │
│                                                         │                     │ evaluation steps., error=None)                          │        │                      │
│                                                         │                     │                                                         │        │                      │
│ test_correctness                                        │                     │                                                         │        │ 100.0%               │
│                                                         │ Correctness (GEval) │ 0.9 (threshold=0.5, evaluation model=Gemini 2.0 Flash,  │ PASSED │                      │
│                                                         │                     │ reason=The actual output contains all the information   │        │                      │
│                                                         │                     │ in the expected output, and adds an additional detail   │        │                      │
│                                                         │                     │ about mosquito bites causing reactions and intense      │        │                      │
│                                                         │                     │ itching. The actual output does not contradict the      │        │                      │
│                                                         │                     │ expected output, so it receives a high score.,          │        │                      │
│                                                         │                     │ error=None)                                             │        │                      │
│ Note: Use Confident AI with DeepEval to analyze failed  │                     │                                                         │        │                      │
│ test cases for more details                             │                     │                                                         │        │                      │
└─────────────────────────────────────────────────────────┴─────────────────────┴─────────────────────────────────────────────────────────┴────────┴──────────────────────┘
