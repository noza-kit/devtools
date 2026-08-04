from uzbridge.pipeline import Pipeline


def test_process_runs_steps_in_order_and_collects_results(sample_image):
    calls = []

    def step_a(frame, context):
        calls.append("a")
        return {"value": 1}

    def step_b(frame, context):
        calls.append("b")
        assert context["step_a"] == {"value": 1}
        return {"value": context["step_a"]["value"] + 1}

    pipeline = Pipeline().add_step(step_a, name="step_a").add_step(step_b, name="step_b")
    results = pipeline.process(sample_image)

    assert calls == ["a", "b"]
    assert results == {"step_a": {"value": 1}, "step_b": {"value": 2}}


def test_process_continues_after_a_step_raises(sample_image):
    def bad_step(frame, context):
        raise RuntimeError("boom")

    def good_step(frame, context):
        return {"ok": True}

    pipeline = Pipeline().add_step(bad_step, name="bad").add_step(good_step, name="good")
    results = pipeline.process(sample_image)

    assert results["bad"] == {"error": "boom"}
    assert results["good"] == {"ok": True}


def test_add_step_defaults_name_to_function_name(sample_image):
    def my_step(frame, context):
        return {}

    pipeline = Pipeline().add_step(my_step)
    assert pipeline.steps[0][0] == "my_step"
