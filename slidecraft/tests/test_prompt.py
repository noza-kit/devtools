from slidecraft.prompt import get_prompt


def test_prompt_mentions_key_structural_elements():
    prompt = get_prompt()
    assert 'class="presentation"' in prompt
    assert 'class="slide"' in prompt
    assert 'class="content"' in prompt
    assert 'class="notes"' in prompt
    assert "<h1>" in prompt
    assert "<strong>" in prompt
    assert "<em>" in prompt
    assert "<img" in prompt


def test_prompt_is_nonempty_string():
    assert isinstance(get_prompt(), str)
    assert len(get_prompt()) > 100
