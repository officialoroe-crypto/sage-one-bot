from app.answer import extract_answer


def test_mission_result_shows_the_answer_not_the_dump():
    result = {
        "success": True, "mission_id": "m", "plan": {"tasks": []},
        "execution": {"status": "completed", "synthesis": {"result": {
            "summary": "Mission completed with 1 verified task result(s).",
            "key_results": [{"task_id": "t", "title": "Answer", "result": '{"provider":"p","model":"m","response":"Hello Nishant."}'}],
        }}},
    }
    assert extract_answer(result) == "Hello Nishant."


def test_python_repr_strings_and_wrapped_results_work():
    assert extract_answer({"success": True, "result": {"final": "Done: 5"}}) == "Done: 5"
    assert extract_answer(str({"response": "ok"})) == "ok"
    assert extract_answer("plain text") == "plain text"


def test_falls_back_to_summary_then_done():
    assert extract_answer({"execution": {"synthesis": {"result": {"summary": "Two tasks failed."}}}}) == "Two tasks failed."
    assert extract_answer({"x": 1}) == "Done."
