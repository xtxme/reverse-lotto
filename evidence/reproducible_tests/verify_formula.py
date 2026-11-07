#!/usr/bin/env python3
"""
Independent verification of the published Yeekee (THLotto) result rule.

Published rule (observed in the site's "กติกา" modal, 2026-11-07):
  result = (sum of every submitted 5-digit number in the round)
           - (the number submitted in 16th position)
  top3   = last 3 digits of result
  bottom2 = the two digits immediately before the last 3 digits
            (i.e. digits 4-5 of the last five digits)

Inputs below are the complete, publicly displayed submission lists for
rounds 53 and 54 of 2026-11-07 (period ids 229 and 230), captured from
the round pages after publication. Usernames are intentionally omitted.
"""

ROUND_229 = """74669,29568,83645,49588,58713,42612,89579,11433,17123,23740,00753,92801,03002,44384,81217,80308,95916,22847,91604,95290,83018,90928,16986,29365,46381,45441,46017,53871,80728,45322,23051,39597,54343,50788,37553,57330,81707,22396,06608,50002,74052,78563,86986,42741,83878,29192,75183,85858,93252,06582,11260,87506,12345,26646,74647,88888,99999,55014,65388,61536,20847,57002,40839,11663,95433,46014,79921,19784,36693,96102,90290,84282,66190,29778,15336,91228,69218,38548,46956,42308,49505,77631,48368,70092,56435,00671,74084,89294,83816,45105,43554,48770,37104,91613,27398,50023,50393,77834,53458,61166,36480,14537,95513,62457,67639,28745,89183,80621,08576,84575,74871,25446,07255,88660,72154,97709,90692,53871,46246,83018,03002,06830,90928,61122,18233,88888,47558,52271,74439,37012,34666,43512,25716,08886,94951,84826,20941,82248,63952,10296,55014,84551,05213,54620,71773,96203,63996,18945,86786,64140,72667,25482,49712,05352,37553,17236,28199,78956,08294,49349,64165,63585,55014,54941,50672,62426,37553,66175,45059,13771,33825,46695,50644
""".strip().split(",")

ROUND_230 = """48730,57389,64348,32827,84532,33135,49238,81956,11323,02023,08397,09948,12181,36966,28155,62839,38315,82550,44552,24004,66755,96093,03841,24586,69246,30750,91701,60064,37321,03270,32344,07551,54135,99845,37447,28957,83855,41950,19259,32928,76564,01573,00100,12673,55555,46636,67489,55555,78909,58585,37553,66666,95584,41475,32819,16315,19203,96821,00899,03186,80460,46054,57981,81798,88372,13197,53409,34419,55740,67173,00100,24112,19340,69286,68217,62090,72665,62934,69510,20865,03831,26820,69017,73407,92808,70101,57263,64076,79667,21462,39330,22708,73432,34639,63360,27004,46927,61702,60791,22394,65737,27388,73222,27548,66003,44341,23139,79001,98798,19859,86032,32230,60607,19693,25318,84651,76245,44288,74750,55555,63667,38315,62839,84109,45265,11323,03163,98005,08700,61856,52864,67064,11325,24965,13619,52750,55014,21085,86668,00000,55014,12705,10370,03129,51769,76696,30158,08444,86868,00000,73496,37553,86688,37553,72276,88888,55014,06321,46520,66666,37553,77200,20377,77978
""".strip().split(",")

CASES = {
    229: {"numbers": ROUND_229, "expected_sum": 9281577, "expected_16th": "80308",
          "expected_result": 9201269, "expected_top": "269", "expected_bottom": "01"},
    230: {"numbers": ROUND_230, "expected_sum": 7724164, "expected_16th": "62839",
          "expected_result": 7661325, "expected_top": "325", "expected_bottom": "61"},
}


def evaluate(nums):
    total = sum(int(n) for n in nums)
    sixteenth = nums[15]
    result = total - int(sixteenth)
    last5 = f"{result:05d}"[-5:]
    return {
        "count": len(nums),
        "sum": total,
        "sixteenth": sixteenth,
        "result": result,
        "last5": last5,
        "top3": last5[-3:],
        "bottom2": last5[:2],
    }


def main():
    failures = 0
    for rid, case in CASES.items():
        got = evaluate(case["numbers"])
        checks = {
            "count_16_or_more": got["count"] >= 16,
            "sum": got["sum"] == case["expected_sum"],
            "sixteenth": got["sixteenth"] == case["expected_16th"],
            "result": got["result"] == case["expected_result"],
            "top3": got["top3"] == case["expected_top"],
            "bottom2": got["bottom2"] == case["expected_bottom"],
        }
        ok = all(checks.values())
        failures += 0 if ok else 1
        print(f"round/period {rid}: {'PASS' if ok else 'FAIL'} "
              f"(n={got['count']}, sum={got['sum']}, 16th={got['sixteenth']}, "
              f"result={got['result']}, top3={got['top3']}, bottom2={got['bottom2']})")
        for name, passed in checks.items():
            if not passed:
                print(f"  - FAILED: {name}")

    print()
    if failures == 0:
        print("All observed cases are reproduced exactly by the published rule.")
    else:
        print(f"{failures} case(s) failed.")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
