from snapclip.queue import PasteQueue, QueueItem


def test_fifo_order():
    q = PasteQueue()
    q.push(QueueItem(kind="text", content="A"))
    q.push(QueueItem(kind="text", content="B"))
    q.push(QueueItem(kind="text", content="C"))
    assert q.pop_oldest().content == "A"
    assert q.pop_oldest().content == "B"
    assert q.pop_oldest().content == "C"
    assert q.pop_oldest() is None


def test_pop_all_drains_in_order():
    q = PasteQueue()
    for c in ("A", "B", "C"):
        q.push(QueueItem(kind="text", content=c))
    items = q.pop_all()
    assert [i.content for i in items] == ["A", "B", "C"]
    assert len(q) == 0


def test_peek_all_does_not_drain():
    q = PasteQueue()
    q.push(QueueItem(kind="text", content="A"))
    assert [i.content for i in q.peek_all()] == ["A"]
    assert len(q) == 1


def test_clear():
    q = PasteQueue()
    q.push(QueueItem(kind="text", content="A"))
    q.clear()
    assert len(q) == 0
    assert q.pop_oldest() is None


def test_mixed_text_and_image_items():
    q = PasteQueue()
    q.push(QueueItem(kind="text", content="hello"))
    q.push(QueueItem(kind="image", content="fake-image-object"))
    assert q.pop_oldest().kind == "text"
    assert q.pop_oldest().kind == "image"
